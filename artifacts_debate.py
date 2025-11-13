"""
ArtifactsBench Multi-Agent Debate System

This module implements ArtifactsBench-style tasks using the multi-agent debate system.
Agents debate on design and implementation approaches for visual/interactive artifacts,
then generate consensus-based code.
"""

from typing import Dict, Any, List
import re
import json
from token_tracking import TokenTrackingDebateSystem
from consensus_system import ConsensusSystem
from agents import Agent, Runner
from debate_system import InMemorySession


# Sample ArtifactsBench-style tasks
SAMPLE_ARTIFACTS_TASKS = [
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
    
    # Run a single task (bouncing ball - simplest example)
    print("Running single artifacts task demo...")
    result = system.run_artifacts_task(
        SAMPLE_ARTIFACTS_TASKS[1],  # Bouncing ball task
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

