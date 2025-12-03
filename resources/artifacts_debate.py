"""
ArtifactsBench Multi-Agent Debate System

This module implements ArtifactsBench-style tasks using the multi-agent debate system.
Agents debate on design and implementation approaches for visual/interactive artifacts,
then generate consensus-based code.
"""

from typing import Dict, Any, List
import re
import json
from datasets import load_dataset
from token_tracking import TokenTrackingDebateSystem
from consensus_system import ConsensusSystem
from agents import Agent, Runner
from debate_system import InMemorySession



def _extract_requirements_from_question(question_text: str) -> List[str]:
    """
    Convert the verbose question text from the dataset into a list of requirements.

    Args:
        question_text: Raw task description from the dataset

    Returns:
        List of cleaned requirement strings
    """
    if not question_text:
        return []

    requirements: List[str] = []
    bullet_markers = ("- ", "* ", "• ")

    for raw_line in question_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for marker in bullet_markers:
            if line.startswith(marker):
                line = line[len(marker):].strip()
                break
        if line:
            requirements.append(line)

    if not requirements:
        requirements = [question_text.strip()]

    return requirements


def load_artifacts_dataset(
    difficulty: str = "easy",
    limit: int | None = None,
    dataset_name: str = "tencent/ArtifactsBenchmark",
    split: str = "train"
) -> List[Dict[str, Any]]:
    """
    Load tasks from the Tencent ArtifactsBenchmark dataset hosted on Hugging Face.

    Args:
        difficulty: Difficulty level to filter on (e.g., "easy", "medium", "hard")
        limit: Optional maximum number of tasks to return
        dataset_name: Hugging Face dataset identifier
        split: Dataset split to load

    Returns:
        List of task dictionaries compatible with ArtifactsDebateSystem
    """
    dataset = load_dataset(dataset_name, split=split)
    target_difficulty = difficulty.lower() if difficulty else None

    tasks: List[Dict[str, Any]] = []

    for row in dataset:
        row_difficulty = (row.get("difficulty") or "").lower()
        if target_difficulty and row_difficulty != target_difficulty:
            continue

        question_text = row.get("question", "").strip()
        requirements = _extract_requirements_from_question(question_text)

        evaluation_criteria = {}
        checklist_items = row.get("checklist") or []
        for idx, item in enumerate(checklist_items):
            title = (item.get("title") or f"criterion_{idx}").strip()
            key = re.sub(r"\s+", "_", title.lower())
            evaluation_criteria[key] = item.get("description", "").strip()

        if not evaluation_criteria:
            evaluation_criteria = {
                "overall_quality": "Evaluate the overall quality of the generated artifact."
            }

        task_id = row.get("index")
        if task_id is None:
            task_id = len(tasks)

        tasks.append(
            {
                "id": f"hf_{task_id}",
                "category": row.get("class", "Unknown"),
                "difficulty": row.get("difficulty", "unknown"),
                "task": question_text,
                "requirements": requirements,
                "evaluation_criteria": evaluation_criteria,
            }
        )

        if limit and len(tasks) >= limit:
            break

    return tasks


def load_sample_dataset_one_per_difficulty(
    dataset_name: str = "tencent/ArtifactsBenchmark",
    split: str = "train"
) -> List[Dict[str, Any]]:
    """
    Load a sample dataset with exactly one task from each difficulty level.
    
    This function fetches one task from "easy", one from "medium", and one from "hard"
    difficulty levels from the ArtifactsBench dataset.
    
    Args:
        dataset_name: Hugging Face dataset identifier
        split: Dataset split to load
        
    Returns:
        List of exactly 3 task dictionaries (one per difficulty level)
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("Warning: datasets library not available. Using fallback sample tasks.")
        return SAMPLE_ARTIFACTS_TASKS[:3]  # Return first 3 from fallback
    
    try:
        dataset = load_dataset(dataset_name, split=split)
        
        # Track which difficulties we've found
        found_difficulties = {"easy": False, "medium": False, "hard": False}
        sample_tasks = []
        
        for row in dataset:
            difficulty = (row.get("difficulty") or "").lower()
            
            # Skip if we already have this difficulty or it's not one we want
            if difficulty not in found_difficulties or found_difficulties[difficulty]:
                continue
            
            question_text = row.get("question", "").strip()
            if not question_text:
                continue
            
            requirements = _extract_requirements_from_question(question_text)
            
            evaluation_criteria = {}
            checklist_items = row.get("checklist") or []
            for idx, item in enumerate(checklist_items):
                title = (item.get("title") or f"criterion_{idx}").strip()
                key = re.sub(r"\s+", "_", title.lower())
                evaluation_criteria[key] = item.get("description", "").strip()
            
            if not evaluation_criteria:
                evaluation_criteria = {
                    "overall_quality": "Evaluate the overall quality of the generated artifact."
                }
            
            task_id = row.get("index")
            if task_id is None:
                task_id = len(sample_tasks)
            
            sample_tasks.append({
                "id": f"hf_{task_id}_{difficulty}",
                "category": row.get("class", "Unknown"),
                "difficulty": difficulty,
                "task": question_text,
                "requirements": requirements,
                "evaluation_criteria": evaluation_criteria,
            })
            
            found_difficulties[difficulty] = True
            
            # Stop when we have all three difficulties
            if all(found_difficulties.values()):
                break
        
        # Sort by difficulty: easy, medium, hard
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        sample_tasks.sort(key=lambda x: difficulty_order.get(x["difficulty"], 99))
        
        print(f"Loaded sample dataset: {len(sample_tasks)} tasks")
        for task in sample_tasks:
            print(f"  - {task['difficulty'].upper()}: {task['category']} (ID: {task['id']})")
        
        return sample_tasks
        
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("Using fallback sample tasks.")
        return SAMPLE_ARTIFACTS_TASKS[:3]


# Sample ArtifactsBench-style tasks (used as fallback when dataset loading fails)
SAMPLE_ARTIFACTS_TASKS = [
    {
        "id": "svg_earth_continents",
        "category": "SVG Generation-SVG Images",
        "difficulty": "easy",
        "task": "Please help me implement this SVG image using code. The earth has seven continents, including South America, which is part of the Americas.",
        "requirements": [
            "SVG element properly set up with appropriate viewBox, width, height attributes and correct namespaces",
            "All seven continents (Asia, Africa, North America, South America, Antarctica, Europe, and Australia) properly represented",
            "South America clearly defined as part of the Americas",
            "Each continent has appropriate fill colors/patterns that make them distinguishable from each other and from oceans",
            "Appropriate map projection used (e.g., Mercator, Robinson, equirectangular) with recognizable continent shapes",
            "Well-structured SVG code using proper nesting, grouping related elements with <g> tags, and proper path commands",
            "SVG handles different viewport sizes properly and maintains crisp edges when scaled",
            "Professional color scheme with good contrast (no more than 3-4 primary colors)",
            "Clean visual hierarchy with appropriate stroke weights and fills",
            "Code structure supports adding interactions later if needed"
        ],
        "evaluation_criteria": {
            "basic_svg_structure": "SVG element is properly set up with appropriate viewBox, width, height attributes. Verify that namespaces are correctly declared. Score 0 if SVG is not implemented at all, 5 if basic structure exists but with errors, 10 if properly set up with correct dimensions and namespaces.",
            "earth_representation": "Evaluate whether all seven continents (Asia, Africa, North America, South America, Antarctica, Europe, and Australia) are properly represented on the SVG map. Check continent shapes for reasonable accuracy. Deduct 2 points for each missing continent. Deduct 3 points if South America is not clearly defined as part of the Americas. The full score is 10 points.",
            "continent_coloring": "Review whether each continent has appropriate fill colors/patterns that make them distinguishable from each other and from oceans. Check if South America has a distinct visual representation while still maintaining a visual relationship with North America. Score 0 if continents are not visually distinct, 5 if basic differentiation exists, 10 if professional color schemes are applied with good contrast.",
            "map_projection": "Assess whether an appropriate map projection is used (e.g., Mercator, Robinson, equirectangular). Check if the projection handles distortion reasonably and maintains recognizable continent shapes. Deduct 5 points for severe distortions that make continents unrecognizable, 3 points for inappropriate projection choice. The full score is 10 points.",
            "code_robustness": "Evaluate whether the SVG code is well-structured, uses proper nesting, and follows best practices (e.g., grouping related elements with <g> tags, using proper path commands). Check if the SVG handles different viewport sizes properly. Code with strong robustness should gracefully handle browser variations, giving 10 points. If the robustness is average, give 5 points, and if it breaks easily in different contexts, give 0 points.",
            "scalability": "Judge whether the SVG properly scales across different display sizes and resolutions: 1) Maintains crisp edges when scaled up 2) Preserves all details when scaled down 3) Responds appropriately to container constraints. Deduct 5 points if the logo blurs or pixelates at larger sizes, 3 points if small details are lost at smaller sizes, and 5 points if the aspect ratio distorts during scaling. The full score is 10 points.",
            "code_quality": "Review modular organization (such as separating continent definitions, styling, and any interactive components), code comments, and optimization for file size. Deduct 5 points if global attributes are inconsistently applied; deduct 5 points if there's significant duplicated path data or styling; deduct 5 points if the SVG is not optimized for rendering performance. The full score is 10 points.",
            "design_standards": "Evaluate whether the overall design follows modern visualization principles: 1) Harmonious color matching for continents and oceans (no more than 3-4 primary colors) 2) Clean visual hierarchy with appropriate stroke weights and fills 3) Professional presentation of labels or legends if included. Deduct 3 points for each cluttered visual element, 5 points for jarring color combinations, and 5 points for poor visual balance. The full score is 10 points.",
            "interaction_smoothness": "Judge whether any interactive elements (if implemented) conform to user expectations: 1) Responsive hover/click states ≤ 100ms 2) Smooth transitions between states 3) Intuitive interaction patterns. For static SVGs without interaction, evaluate whether the code structure would easily support adding interactions later. Deduct 5 points for each broken interaction, 3 points for laggy animations, and 5 points for confusing interaction patterns. The full score is 10 points."
        }
    },
    {
        "id": "svg_solar_system",
        "category": "SVG Generation",
        "difficulty": "medium",
        "task": "Create an SVG visualization of a simple solar system",
        "requirements": [
            "Sun at the center (yellow/orange circle)",
            "At least 3 planets orbiting at different distances",
            "Planets should have different sizes and colors",
            "Smooth orbital animations at different speeds",
            "Pleasant color scheme and proper spacing",
            "SVG should be 800x600 pixels"
        ],
        "evaluation_criteria": {
            "visual_fidelity": "Sun and planets clearly visible with distinct colors",
            "interactivity": "Smooth continuous orbital animations",
            "code_quality": "Clean SVG structure with proper use of animations",
            "aesthetics": "Visually appealing color scheme and layout"
        }
    },
    {
        "id": "bouncing_ball",
        "category": "SVG Generation",
        "difficulty": "easy",
        "task": "Create an animated bouncing ball in SVG",
        "requirements": [
            "Single ball that bounces vertically",
            "Ball should accelerate downward (gravity effect)",
            "Ball should bounce off bottom of container",
            "Smooth animation using SVG animate or CSS",
            "SVG should be 400x400 pixels"
        ],
        "evaluation_criteria": {
            "visual_fidelity": "Ball is clearly visible",
            "interactivity": "Ball bounces realistically with physics",
            "code_quality": "Proper use of SVG animation elements",
            "aesthetics": "Clean design with good color contrast"
        }
    },
    {
        "id": "interactive_clock",
        "category": "Web Applications",
        "difficulty": "medium",
        "task": "Create an interactive analog clock using HTML/CSS/JavaScript",
        "requirements": [
            "Circular clock face with numbers 1-12",
            "Hour, minute, and second hands",
            "Hands should move in real-time",
            "Centered on page with proper sizing",
            "Clean, readable design"
        ],
        "evaluation_criteria": {
            "visual_fidelity": "Clock face and hands clearly visible",
            "interactivity": "Real-time clock updates correctly",
            "code_quality": "Efficient JavaScript for time calculation",
            "aesthetics": "Professional appearance"
        }
    },
    {
        "id": "data_chart",
        "category": "Data Science",
        "difficulty": "medium",
        "task": "Create an interactive bar chart using SVG",
        "requirements": [
            "Display 5 data points as bars",
            "Each bar with different height based on value",
            "Labels for each bar",
            "Hover effect showing exact values",
            "Axes with proper scaling and labels"
        ],
        "evaluation_criteria": {
            "visual_fidelity": "Bars and labels clearly visible",
            "interactivity": "Hover effects work smoothly",
            "code_quality": "Proper SVG structure and data binding",
            "aesthetics": "Professional chart appearance"
        }
    }
]


def format_artifacts_task(task_data: Dict[str, Any]) -> str:
    """
    Format an ArtifactsBench task for the debate system.
    
    Args:
        task_data: Dictionary containing task details
        
    Returns:
        Formatted task string
    """
    lines = [
        f"Category: {task_data['category']}",
        f"Difficulty: {task_data['difficulty']}",
        "",
        f"TASK: {task_data['task']}",
        "",
        "REQUIREMENTS:",
    ]
    
    for i, req in enumerate(task_data['requirements'], 1):
        lines.append(f"  {i}. {req}")
    
    lines.append("")
    lines.append("EVALUATION CRITERIA:")
    for criterion, description in task_data['evaluation_criteria'].items():
        lines.append(f"  - {criterion.replace('_', ' ').title()}: {description}")
    
    lines.append("")
    lines.append("Discuss the implementation approach, considering design decisions, ")
    lines.append("technical constraints, and best practices. Provide your perspective ")
    lines.append("on how to best accomplish this task.")
    
    return "\n".join(lines)


class ArtifactsCodeGenerator:
    """
    Generates actual code based on consensus from debate.
    """
    
    def __init__(self, model: str = "gpt-4"):
        """Initialize the code generator."""
        self.model = model
        self.generator_agent = self._create_generator_agent()
    
    def _create_generator_agent(self) -> Agent:
        """Create a specialized code generation agent."""
        instructions = """You are an expert code generator specializing in visual and interactive artifacts.

Your role is to:
1. Read the task requirements and implementation consensus
2. Generate clean, working code that fulfills all requirements
3. Include proper comments explaining key sections
4. Ensure the code is production-ready and follows best practices
5. Output ONLY the code without additional explanation

For SVG tasks: Generate complete SVG markup with animations
For HTML/JS tasks: Generate complete HTML with embedded CSS and JavaScript
For data visualization: Generate SVG with proper data representation

IMPORTANT: Your response should be ONLY the code, starting with the opening tag and ending with the closing tag."""

        return Agent(
            name="CodeGenerator",
            instructions=instructions,
            model=self.model
        )
    
    def generate_code(self, task_data: Dict[str, Any], consensus: str) -> str:
        """
        Generate code based on task and consensus.
        
        Args:
            task_data: Original task data
            consensus: Consensus from debate
            
        Returns:
            Generated code as string
        """
        prompt = f"""Task: {task_data['task']}

Requirements:
{chr(10).join(f"- {req}" for req in task_data['requirements'])}

Implementation Consensus from Multi-Agent Debate:
{consensus}

Generate the complete, working code to implement this artifact. 
Output ONLY the code without any explanations or markdown formatting."""

        session = InMemorySession()
        result = Runner.run_sync(self.generator_agent, prompt, session=session)
        
        return str(result.final_output)


class ArtifactsEvaluator:
    """
    Evaluates generated artifacts against criteria.
    """
    
    def __init__(self, model: str = "gpt-4"):
        """Initialize the evaluator."""
        self.model = model
        self.evaluator_agent = self._create_evaluator_agent()
    
    def _create_evaluator_agent(self) -> Agent:
        """Create a specialized evaluation agent."""
        instructions = """You are an expert evaluator of visual and interactive artifacts.

Your role is to:
1. Analyze the generated code against the task requirements
2. Assess each evaluation criterion thoroughly
3. Provide a score for each criterion (0-10 scale)
4. Give specific feedback on strengths and weaknesses
5. Provide an overall assessment

Evaluation Format:
For each criterion, provide:
- Score (0-10)
- Justification
- Specific examples from the code

Be objective, thorough, and constructive in your evaluation."""

        return Agent(
            name="ArtifactsEvaluator",
            instructions=instructions,
            model=self.model
        )
    
    def evaluate_artifact(self, task_data: Dict[str, Any], generated_code: str) -> Dict[str, Any]:
        """
        Evaluate generated artifact.
        
        Args:
            task_data: Original task data
            generated_code: Generated code
            
        Returns:
            Evaluation results dictionary
        """
        prompt = f"""Task: {task_data['task']}

Requirements:
{chr(10).join(f"- {req}" for req in task_data['requirements'])}

Evaluation Criteria:
{chr(10).join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in task_data['evaluation_criteria'].items())}

Generated Code:
```
{generated_code}
```

Please evaluate this artifact thoroughly against all criteria.
Provide scores (0-10) and detailed justification for each criterion."""

        session = InMemorySession()
        result = Runner.run_sync(self.evaluator_agent, prompt, session=session)
        
        evaluation_text = str(result.final_output)
        
        # Extract scores using regex
        scores = self._extract_scores(evaluation_text)
        
        return {
            "evaluation_text": evaluation_text,
            "scores": scores,
            "average_score": sum(scores.values()) / len(scores) if scores else 0
        }
    
    def _extract_scores(self, evaluation_text: str) -> Dict[str, float]:
        """Extract numerical scores from evaluation text."""
        scores = {}
        
        # Look for patterns like "Score: 8/10" or "8 out of 10" or "Score: 8"
        patterns = [
            r'(\w+(?:\s+\w+)*)\s*[:-]\s*(?:Score[:-])?\s*(\d+(?:\.\d+)?)\s*(?:/\s*10)?',
            r'(?:Score|Rating)\s+for\s+(\w+(?:\s+\w+)*)\s*[:-]\s*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, evaluation_text, re.IGNORECASE)
            for criterion, score in matches:
                criterion_key = criterion.lower().strip().replace(' ', '_')
                try:
                    scores[criterion_key] = float(score)
                except ValueError:
                    continue
        
        return scores


class ArtifactsDebateSystem:
    """
    Complete system for ArtifactsBench-style tasks using multi-agent debate.
    """
    
    def __init__(self, num_agents: int = 3, num_rounds: int = 2, model: str = "gpt-4"):
        """
        Initialize the artifacts debate system.
        
        Args:
            num_agents: Number of agents for debate
            num_rounds: Number of debate rounds
            model: OpenAI model to use
        """
        self.num_agents = num_agents
        self.num_rounds = num_rounds
        self.model = model
        self.code_generator = ArtifactsCodeGenerator(model)
        self.evaluator = ArtifactsEvaluator(model)
    
    def run_artifacts_task(self, task_data: Dict[str, Any], 
                          generate_code: bool = True,
                          evaluate_code: bool = True) -> Dict[str, Any]:
        """
        Run complete artifacts task with debate, code generation, and evaluation.
        
        Args:
            task_data: Task data dictionary
            generate_code: Whether to generate code from consensus
            evaluate_code: Whether to evaluate generated code
            
        Returns:
            Complete results dictionary
        """
        print(f"\n{'='*80}")
        print(f"ARTIFACTS TASK: {task_data['task']}")
        print(f"Category: {task_data['category']} | Difficulty: {task_data['difficulty']}")
        print(f"{'='*80}\n")
        
        # Format task for debate
        formatted_task = format_artifacts_task(task_data)
        
        # Run multi-agent debate with token tracking
        print("Step 1: Multi-Agent Debate on Implementation Approach...")
        debate_system = TokenTrackingDebateSystem(
            num_agents=self.num_agents,
            model=self.model
        )
        
        debate_result = debate_system.run_debate(formatted_task, self.num_rounds)
        
        # Generate consensus
        print("\nStep 2: Generating Consensus from Debate...")
        consensus_system = ConsensusSystem(debate_system)
        consensus = consensus_system._generate_consensus(formatted_task, debate_result['transcript'])
        
        print("\n" + "="*80)
        print("IMPLEMENTATION CONSENSUS")
        print("="*80)
        print(consensus)
        print("="*80)
        
        result = {
            "task": task_data,
            "debate_transcript": debate_result['transcript'],
            "consensus": consensus,
            "token_usage": debate_result['usage'].get_summary()
        }
        
        # Generate code if requested
        if generate_code:
            print("\nStep 3: Generating Code from Consensus...")
            generated_code = self.code_generator.generate_code(task_data, consensus)
            result['generated_code'] = generated_code
            
            print("\n" + "="*80)
            print("GENERATED CODE")
            print("="*80)
            print(generated_code)
            print("="*80)
        
        # Evaluate code if requested
        if evaluate_code and generate_code:
            print("\nStep 4: Evaluating Generated Artifact...")
            evaluation = self.evaluator.evaluate_artifact(task_data, generated_code)
            result['evaluation'] = evaluation
            
            print("\n" + "="*80)
            print("EVALUATION RESULTS")
            print("="*80)
            print(evaluation['evaluation_text'])
            if evaluation['scores']:
                print(f"\nAverage Score: {evaluation['average_score']:.1f}/10")
            print("="*80)
        
        # Print token usage summary
        print("\n")
        debate_system.print_usage_summary()
        
        return result
    
    def run_task_suite(self, tasks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run multiple artifacts tasks.
        
        Args:
            tasks: List of task dictionaries (uses default if None)
            
        Returns:
            Summary results
        """
        if tasks is None:
            tasks = SAMPLE_ARTIFACTS_TASKS
        
        print(f"\n{'='*80}")
        print("ARTIFACTSBENCH MULTI-AGENT DEBATE SYSTEM")
        print(f"{'='*80}")
        print(f"Total Tasks: {len(tasks)}")
        print(f"Agents: {self.num_agents}")
        print(f"Rounds per Task: {self.num_rounds}")
        print(f"Model: {self.model}")
        print(f"{'='*80}\n")
        
        results = []
        
        for i, task_data in enumerate(tasks, 1):
            print(f"\n{'*'*80}")
            print(f"TASK {i}/{len(tasks)}")
            print(f"{'*'*80}")
            
            try:
                result = self.run_artifacts_task(task_data)
                results.append(result)
            except Exception as e:
                print(f"Error processing task: {e}")
                results.append({
                    "task": task_data,
                    "error": str(e)
                })
        
        # Calculate summary statistics
        total_tokens = sum(r.get('token_usage', {}).get('total_tokens', 0) for r in results)
        avg_scores = [r.get('evaluation', {}).get('average_score', 0) for r in results if 'evaluation' in r]
        avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        summary = {
            "total_tasks": len(tasks),
            "successful_tasks": len([r for r in results if 'error' not in r]),
            "total_tokens": total_tokens,
            "average_evaluation_score": avg_score,
            "results": results
        }
        
        self._print_summary(summary)
        
        return summary
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary of task suite results."""
        print(f"\n\n{'='*80}")
        print("TASK SUITE SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tasks: {summary['total_tasks']}")
        print(f"Successful: {summary['successful_tasks']}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        
        if summary['average_evaluation_score'] > 0:
            print(f"Average Score: {summary['average_evaluation_score']:.1f}/10")
        
        print(f"{'='*80}\n")
    
    def save_results(self, results: Dict[str, Any], filename: str = "artifacts_results.json"):
        """Save results to JSON file."""
        # Prepare for JSON serialization
        serializable_results = {
            "total_tasks": results['total_tasks'],
            "successful_tasks": results['successful_tasks'],
            "total_tokens": results['total_tokens'],
            "average_evaluation_score": results['average_evaluation_score'],
            "tasks": []
        }
        
        for result in results['results']:
            task_result = {
                "task_id": result['task']['id'],
                "task_name": result['task']['task'],
                "category": result['task']['category'],
                "debate_transcript": result.get('debate_transcript', ''),
                "consensus": result.get('consensus', ''),
                "generated_code": result.get('generated_code', ''),
                "evaluation": result.get('evaluation', {}),
                "token_usage": result.get('token_usage', {})
            }
            serializable_results['tasks'].append(task_result)
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"Results saved to {filename}")


def main():
    """Main function to run artifacts debate system."""
    import os
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Create artifacts debate system
    system = ArtifactsDebateSystem(
        num_agents=3,
        num_rounds=2,
        model="gpt-4o-mini"  # Using mini for cost efficiency
    )
    
    # Run a single task (Earth SVG - actual ArtifactsBench dataset task)
    print("Running single artifacts task demo...")
    result = system.run_artifacts_task(
        SAMPLE_ARTIFACTS_TASKS[0],  # Earth continents SVG task from ArtifactsBench dataset
        generate_code=True,
        evaluate_code=True
    )
    
    # Save results
    single_result_summary = {
        "total_tasks": 1,
        "successful_tasks": 1,
        "total_tokens": result['token_usage']['total_tokens'],
        "average_evaluation_score": result.get('evaluation', {}).get('average_score', 0),
        "results": [result]
    }
    system.save_results(single_result_summary, "artifacts_single_result.json")


if __name__ == "__main__":
    main()

