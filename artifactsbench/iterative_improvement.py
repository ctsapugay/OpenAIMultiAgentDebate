"""
Iterative Improvement System for ArtifactsBenchmark
Implements a divide-and-conquer approach to improve code based on evaluation feedback.
"""

import datasets
import openai
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import re
import os
import time
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

load_dotenv(find_dotenv())

# Add parent directory to path for token tracking
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from token_tracking import (
    get_global_tracker, 
    APITokenTracker,
    calculate_cost,
    TOKEN_TRACKING_DIR,
    update_iterative_statistics
)

# Token tracking file for iterative improvement
TOKEN_ITERATIVE_FILE = os.path.join(TOKEN_TRACKING_DIR, "token_usage_iterative.json")

# Import functions from experiment.py
# Using relative import since both files are in the same directory
try:
    from .experiment import (
        MODEL_NAME,
        ENABLE_SCREENSHOTS,
        NUM_SCREENSHOTS,
        SCREENSHOT_INTERVAL,
        USE_SCREENSHOTS_IN_EVAL,
        OUTPUT_DIR,
        format_checklist_for_prompt,
        get_prompt_mllm_checklist,
        extract_individual_scores,
        extract_mllm_overall,
        generate_screenshots,
        check_canvas_content,
        evaluate_with_checklist
    )
except ImportError:
    # Fallback for direct execution
    import sys
    import importlib.util
    experiment_path = os.path.join(os.path.dirname(__file__), "experiment.py")
    spec = importlib.util.spec_from_file_location("experiment", experiment_path)
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)
    
    MODEL_NAME = experiment.MODEL_NAME
    ENABLE_SCREENSHOTS = experiment.ENABLE_SCREENSHOTS
    NUM_SCREENSHOTS = experiment.NUM_SCREENSHOTS
    SCREENSHOT_INTERVAL = experiment.SCREENSHOT_INTERVAL
    USE_SCREENSHOTS_IN_EVAL = experiment.USE_SCREENSHOTS_IN_EVAL
    OUTPUT_DIR = experiment.OUTPUT_DIR
    format_checklist_for_prompt = experiment.format_checklist_for_prompt
    get_prompt_mllm_checklist = experiment.get_prompt_mllm_checklist
    extract_individual_scores = experiment.extract_individual_scores
    extract_mllm_overall = experiment.extract_mllm_overall
    generate_screenshots = experiment.generate_screenshots
    check_canvas_content = experiment.check_canvas_content
    evaluate_with_checklist = experiment.evaluate_with_checklist

# ============================================================================
# CONFIGURATION
# ============================================================================
IMPROVEMENT_THRESHOLD = 7.0  # Minimum acceptable score for each checklist item
MAX_ITERATIONS = 2  # Maximum number of improvement rounds
MIN_IMPROVEMENT = 0.5  # Minimum score improvement to continue iterating

client = OpenAI()

# Initialize token tracker (experiment name will be set in iterative_refinement)
token_tracker = get_global_tracker()

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(task_dir: Path) -> logging.Logger:
    """
    Set up logging to both file and console.
    
    Args:
        task_dir: Directory to save log file
        
    Returns:
        Configured logger
    """
    log_file = task_dir / "run_log.txt"
    
    # Create unique logger for each task (using task_dir in name)
    logger_name = f"iterative_improvement_{task_dir.name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    # Properly close file handlers before removing
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
        logger.removeHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler (with simpler format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    return logger

# ============================================================================
# CODE GENERATION FUNCTIONS
# ============================================================================

def extract_html_code(generated_content: str) -> str:
    """
    Extract HTML code from LLM response using multiple strategies.
    """
    html_code = None
    
    # Strategy 1: Extract from markdown code blocks
    html_match = re.search(r'```(?:html|javascript|js)?\s*(.*?)\s*```', generated_content, re.DOTALL)
    if html_match:
        html_code = html_match.group(1).strip()
    
    # Strategy 2: Check if content itself is HTML/SVG
    if not html_code:
        if '<html' in generated_content.lower() or '<!doctype' in generated_content.lower() or '<svg' in generated_content.lower():
            html_start = re.search(r'(<!DOCTYPE|<html|<svg)', generated_content, re.IGNORECASE)
            if html_start:
                html_code = generated_content[html_start.start():].strip()
    
    # Strategy 3: Look for any HTML tags
    if not html_code:
        if re.search(r'<[a-z]+', generated_content, re.IGNORECASE):
            html_start = re.search(r'<[a-z]+', generated_content, re.IGNORECASE)
            if html_start:
                html_code = generated_content[html_start.start():].strip()
    
    # Strategy 4: Fallback
    if not html_code:
        html_code = f"""<!DOCTYPE html>
<html>
<head>
    <title>Generated Artifact</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
{generated_content}
</body>
</html>"""
    
    return html_code


def generate_initial_code(task_question: str, logger: logging.Logger = None) -> str:
    """
    Generate initial code for the task.
    
    Args:
        task_question: The task/question to generate code for
        logger: Optional logger instance
        
    Returns:
        Generated HTML code
    """
    system_message = """You are an expert web front-end developer. Output a complete, self-contained HTML/CSS/JS file that implements the described game or application.

When given a task, you must generate the complete, working code implementation. Do not provide descriptions, explanations, or summaries. Output ONLY the executable code.

Requirements:
- Generate a complete, self-contained HTML file with embedded CSS and JavaScript
- All code must be in a single file (no external dependencies)
- The code should be production-ready and fully functional
- Include proper HTML structure, CSS styling, and JavaScript functionality
- For games: Include all game logic, interactions, and visual elements
- For SVG tasks: Generate complete SVG markup with proper structure

Your response should start with <!DOCTYPE html> and end with </html>. Include all necessary code to make it work immediately when opened in a browser."""

    user_prompt = task_question
    if not any(word in user_prompt.lower() for word in ["code", "implement", "generate code", "create", "build", "write"]):
        user_prompt = f"""{task_question}

IMPORTANT: Generate the complete, working code to implement this. Output ONLY the executable code without any explanations or descriptions."""

    if logger:
        logger.info("\n" + "="*80)
        logger.info("GENERATING INITIAL CODE...")
        logger.info("="*80)
        logger.info(f"Model: {MODEL_NAME}")
        logger.info(f"Temperature: 0.0")
        logger.info(f"Task Question (first 200 chars): {task_question[:200]}...")
    else:
        print("\n" + "="*80)
        print("GENERATING INITIAL CODE...")
        print("="*80)
    
    start_time = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0
    )
    
    # Track token usage
    token_tracker.track_response(response, operation="initial_code_generation", model=MODEL_NAME)
    
    generation_time = time.time() - start_time
    
    generated_content = response.choices[0].message.content
    html_code = extract_html_code(generated_content)
    
    if logger:
        logger.info(f"✓ Initial code generated (took {generation_time:.2f} seconds)")
        logger.info(f"Generated code length: {len(html_code)} characters")
        logger.info(f"Response length: {len(generated_content)} characters")
    else:
        print("✓ Initial code generated")
    
    return html_code


def identify_weak_areas(individual_scores: Dict[str, float], threshold: float = IMPROVEMENT_THRESHOLD) -> List[Tuple[str, float]]:
    """
    Identify checklist items with scores below the threshold.
    
    Args:
        individual_scores: Dictionary mapping checklist item titles to scores
        threshold: Minimum acceptable score
        
    Returns:
        List of tuples (item_title, score) for items below threshold
    """
    weak_areas = [(title, score) for title, score in individual_scores.items() 
                  if score is not None and score < threshold]
    return sorted(weak_areas, key=lambda x: x[1])  # Sort by score (lowest first)


def extract_weak_items_reasoning(
    evaluation_text: str, 
    weak_items: List[Tuple[str, float]], 
    checklist_items: List[Dict]
) -> str:
    """
    Extract reasoning/feedback for only the weak items from the full evaluation text.
    
    Args:
        evaluation_text: Full evaluation text from LLM
        weak_items: List of (item_title, score) tuples for weak items
        checklist_items: Full list of checklist items
        
    Returns:
        Condensed feedback string with only weak items' reasoning
    """
    if not weak_items or not evaluation_text:
        return "No specific feedback available for weak items."
    
    weak_item_titles = [title for title, _ in weak_items]
    extracted_reasoning = []
    
    # Strategy 1: Look for sections discussing each weak item by title
    for title, score in weak_items:
        # Try to find the section discussing this item
        # Look for the title in the text (case-insensitive)
        title_pattern = re.escape(title)
        
        # Try to find paragraph/section containing this title
        # Look for patterns like "Title: ..." or "Title - ..." or just the title followed by discussion
        patterns = [
            rf"{title_pattern}[:\.\s]+(.*?)(?=\n\n|\n[A-Z][^:]+:|```|$)",  # Title: discussion
            rf"{title_pattern}\s*[-–]\s*(.*?)(?=\n\n|\n[A-Z][^:]+:|```|$)",  # Title - discussion
            rf"(?i)(?:{title_pattern}).*?score[:\s]+{score}.*?((?:[^.]*\.){{1,5}})",  # Title with score
            rf"(?i)(?:{title_pattern}).*?((?:[^.]*\.){{2,5}})",  # Title followed by sentences
        ]
        
        found_reasoning = None
        for pattern in patterns:
            match = re.search(pattern, evaluation_text, re.IGNORECASE | re.DOTALL)
            if match:
                found_reasoning = match.group(1).strip()
                # Clean up the reasoning
                found_reasoning = re.sub(r'\s+', ' ', found_reasoning)
                if len(found_reasoning) > 50:  # Only use if substantial
                    break
        
        # Strategy 2: Look for numbered items or bullet points
        if not found_reasoning:
            # Try to find sections that might discuss this item
            # Look for patterns like "1. Title" or "- Title"
            numbered_patterns = [
                rf"(?i)(?:\d+\.\s*)?{title_pattern}.*?((?:[^.]*\.){{2,5}})",
                rf"(?i)(?:[-•]\s*)?{title_pattern}.*?((?:[^.]*\.){{2,5}})",
            ]
            for pattern in numbered_patterns:
                match = re.search(pattern, evaluation_text, re.IGNORECASE | re.DOTALL)
                if match:
                    found_reasoning = match.group(1).strip()
                    found_reasoning = re.sub(r'\s+', ' ', found_reasoning)
                    if len(found_reasoning) > 50:
                        break
        
        # Strategy 3: Extract context around the title
        if not found_reasoning:
            title_pos = evaluation_text.lower().find(title.lower())
            if title_pos != -1:
                # Extract 200-500 characters around the title
                start = max(0, title_pos - 100)
                end = min(len(evaluation_text), title_pos + len(title) + 400)
                context = evaluation_text[start:end]
                # Try to extract sentences
                sentences = re.findall(r'[^.]*\.', context)
                if sentences:
                    found_reasoning = ' '.join(sentences[:3]).strip()
        
        if found_reasoning:
            extracted_reasoning.append(f"{title} (Score: {score}/10):\n{found_reasoning}")
        else:
            # Fallback: just mention the item and score
            extracted_reasoning.append(f"{title} (Score: {score}/10): No specific reasoning found in evaluation.")
    
    if extracted_reasoning:
        return "\n\n".join(extracted_reasoning)
    else:
        # Fallback: return a summary mentioning weak items
        weak_items_summary = "\n".join([f"- {title}: {score}/10" for title, score in weak_items])
        return f"The following items scored below threshold:\n{weak_items_summary}\n\nPlease refer to the evaluation feedback for detailed reasoning."


def create_improvement_prompt(
    original_code: str,
    task_question: str,
    weak_items: List[Tuple[str, float]],
    checklist_items: List[Dict],
    evaluation_feedback: str
) -> str:
    """
    Create a focused improvement prompt targeting weak areas.
    
    Args:
        original_code: Current code to improve
        task_question: Original task description
        weak_items: List of (item_title, score) tuples for items needing improvement
        checklist_items: Full list of checklist items
        evaluation_feedback: Full evaluation text from LLM
        
    Returns:
        Improvement prompt string
    """
    # Get descriptions for weak items
    weak_item_details = []
    for title, score in weak_items:
        for item in checklist_items:
            if item.get("title") == title:
                weak_item_details.append({
                    "title": title,
                    "description": item.get("description", ""),
                    "current_score": score
                })
                break
    
    weak_items_text = "\n".join([
        f"- {item['title']} (Current Score: {item['current_score']:.1f}/10): {item['description']}"
        for item in weak_item_details
    ])
    
    # Extract only weak items reasoning instead of full feedback
    weak_items_reasoning = extract_weak_items_reasoning(
        evaluation_feedback, 
        weak_items, 
        checklist_items
    )
    
    improvement_prompt = f"""You are an expert web front-end developer. Your task is to improve existing code based on specific feedback.

ORIGINAL TASK:
{task_question}

CURRENT CODE:
```
{original_code}
```

AREAS NEEDING IMPROVEMENT (Score < {IMPROVEMENT_THRESHOLD}):
{weak_items_text}

FEEDBACK FOR WEAK ITEMS:
{weak_items_reasoning}

INSTRUCTIONS:
1. Focus ONLY on improving the areas listed above
2. Keep all working parts of the code intact
3. Do not break existing functionality
4. Make targeted improvements based on the feedback provided above
5. Output ONLY the complete, improved HTML code (no explanations)
6. Ensure the code is self-contained and functional

Generate the improved code that addresses the weak areas while maintaining all existing functionality."""

    return improvement_prompt


def improve_code(improvement_prompt: str, iteration: int, logger: logging.Logger = None) -> str:
    """
    Generate improved code based on the improvement prompt.
    
    Args:
        improvement_prompt: The improvement prompt
        iteration: Current iteration number
        logger: Optional logger instance
        
    Returns:
        Improved HTML code
    """
    if logger:
        logger.info(f"\n" + "="*80)
        logger.info(f"IMPROVEMENT ROUND {iteration}")
        logger.info("="*80)
        logger.info(f"Model: {MODEL_NAME}")
        logger.info(f"Temperature: 0.0")
        logger.info(f"Improvement Prompt Length: {len(improvement_prompt)} characters")
        # Log preview of improvement prompt
        prompt_preview = improvement_prompt[:500] + "..." if len(improvement_prompt) > 500 else improvement_prompt
        logger.info(f"Improvement Prompt Preview:\n{prompt_preview}")
    else:
        print(f"\n" + "="*80)
        print(f"IMPROVEMENT ROUND {iteration}")
        print("="*80)
    
    system_message = """You are an expert web front-end developer specializing in code improvement. 
Your task is to improve existing code based on specific feedback while maintaining all working functionality.

When improving code:
- Focus on the specific issues mentioned in the feedback
- Keep all working parts intact
- Make targeted, precise improvements
- Output ONLY the complete, improved HTML code
- Do not provide explanations or descriptions"""

    start_time = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": improvement_prompt}
        ],
        temperature=0.0
    )
    
    # Track token usage
    token_tracker.track_response(response, operation=f"code_improvement_iteration_{iteration}", model=MODEL_NAME)
    
    improvement_time = time.time() - start_time
    
    generated_content = response.choices[0].message.content
    improved_code = extract_html_code(generated_content)
    
    if logger:
        logger.info(f"✓ Improved code generated for iteration {iteration} (took {improvement_time:.2f} seconds)")
        logger.info(f"Improved code length: {len(improved_code)} characters")
    else:
        print(f"✓ Improved code generated for iteration {iteration}")
    
    return improved_code


# ============================================================================
# ITERATIVE IMPROVEMENT MAIN FUNCTION
# ============================================================================

def iterative_refinement(
    task_data: Dict,
    max_iterations: int = MAX_ITERATIONS,
    improvement_threshold: float = IMPROVEMENT_THRESHOLD
) -> Dict:
    """
    Main iterative improvement function.
    
    Args:
        task_data: Dictionary with task information (question, checklist, etc.)
        max_iterations: Maximum number of improvement rounds
        improvement_threshold: Minimum acceptable score
        
    Returns:
        Dictionary with final results and improvement history
    """
    task_question = task_data.get("question", "")
    checklist_items = task_data.get("checklist", [])
    task_id = task_data.get("index", "unknown")
    task_class = task_data.get("class", "unknown")  # Keep original format
    task_difficulty = task_data.get("difficulty", "unknown").lower()
    
    # Create output directory: artifacts_output/{class_name}/task_{index}/
    output_base_dir = Path(OUTPUT_DIR)
    output_base_dir.mkdir(exist_ok=True)
    class_dir = output_base_dir / task_class
    class_dir.mkdir(exist_ok=True)
    task_dir = class_dir / f"task_{task_id}"
    task_dir.mkdir(exist_ok=True)
    
    # Setup logging
    logger = setup_logging(task_dir)
    log_file = task_dir / "run_log.txt"
    
    # Set experiment name for token tracking (class name)
    experiment_name = task_class
    token_tracker.set_experiment_name(experiment_name)
    
    improvement_history = []
    current_code = None
    current_scores = {}
    start_time = datetime.now()
    
    logger.info("\n" + "="*80)
    logger.info("ITERATIVE IMPROVEMENT PROCESS STARTED")
    logger.info("="*80)
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Task Class: {task_class}")
    logger.info(f"Task Difficulty: {task_difficulty}")
    logger.info(f"Improvement Threshold: {improvement_threshold}")
    logger.info(f"Max Iterations: {max_iterations}")
    logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Screenshots Enabled: {ENABLE_SCREENSHOTS}")
    logger.info(f"Use Screenshots in Evaluation: {USE_SCREENSHOTS_IN_EVAL}")
    logger.info("="*80)
    
    # Step 1: Generate initial code
    logger.info("\n" + "="*80)
    logger.info("STEP 1: GENERATING INITIAL CODE")
    logger.info("="*80)
    current_code = generate_initial_code(task_question, logger)
    
    # Log initial HTML code
    logger.info(f"\n{'='*80}")
    logger.info("INITIAL HTML CODE")
    logger.info(f"{'='*80}")
    logger.info(current_code)
    logger.info(f"{'='*80}")
    
    # Save initial code
    initial_html_path = task_dir / "iteration_0_initial.html"
    with open(initial_html_path, 'w', encoding='utf-8') as f:
        f.write(current_code)
    logger.info(f"\n✓ Initial code saved to: {initial_html_path}")
    
    # Evaluate initial code before starting iterations
    logger.info(f"\n{'='*80}")
    logger.info("EVALUATING INITIAL CODE")
    logger.info(f"{'='*80}")
    
    initial_screenshot_paths = []
    initial_canvas_check = {}
    if ENABLE_SCREENSHOTS:
        logger.info("Generating screenshots for initial code...")
        initial_screenshot_dir = task_dir / "iteration_0_initial_screenshots"
        initial_screenshot_dir.mkdir(exist_ok=True)
        initial_screenshot_paths, initial_canvas_check = generate_screenshots(
            str(initial_html_path),
            output_dir=str(initial_screenshot_dir),
            num_screenshots=NUM_SCREENSHOTS
        )
        if initial_canvas_check:
            logger.info(f"Canvas Check: {json.dumps(initial_canvas_check, indent=2)}")
    
    logger.info("Evaluating initial code...")
    initial_eval_start = time.time()
    initial_evaluation = evaluate_with_checklist(
        current_code,
        checklist_items,
        task_question,
        screenshot_paths=initial_screenshot_paths if USE_SCREENSHOTS_IN_EVAL else None,
        canvas_check_info=initial_canvas_check if initial_canvas_check else None
    )
    initial_eval_time = time.time() - initial_eval_start
    logger.info(f"Initial evaluation completed in {initial_eval_time:.2f} seconds")
    
    initial_scores = initial_evaluation.get("individual_scores", {})
    initial_sum = initial_evaluation.get("calculated_sum")
    
    logger.info(f"\nInitial Scores:")
    logger.info(f"Individual Scores (JSON):\n{json.dumps(initial_scores, indent=2)}")
    logger.info(f"Initial Calculated Sum: {initial_sum}")
    
    # Store initial evaluation
    improvement_history.append({
        "iteration": 0,
        "code": current_code,
        "individual_scores": initial_scores,
        "calculated_sum": initial_sum,
        "overall_score": initial_evaluation.get("overall_score"),
        "evaluation_text": initial_evaluation.get("evaluation_text", ""),
        "timestamp": datetime.now().isoformat()
    })
    
    # Check if initial code already meets threshold
    weak_areas = identify_weak_areas(initial_scores, improvement_threshold)
    if not weak_areas:
        logger.info(f"\n✓ Initial code already meets all thresholds! No iterations needed.")
        last_evaluation = initial_evaluation
        completed_all_iterations = False
    else:
        last_evaluation = None
        completed_all_iterations = False
    
    # Iterative improvement loop
    logger.info("\n" + "="*80)
    logger.info("STEP 2: ITERATIVE IMPROVEMENT LOOP")
    logger.info("="*80)
    
    # Track last evaluation for final results (initialize with initial if no iterations needed)
    if 'last_evaluation' not in locals():
        last_evaluation = None
        completed_all_iterations = False
    
    # Only run iterations if initial code didn't meet threshold
    if weak_areas:
        for iteration in range(1, max_iterations + 1):
            iteration_start_time = datetime.now()
            logger.info(f"\n{'='*80}")
            logger.info(f"ITERATION {iteration}")
            logger.info(f"{'='*80}")
            logger.info(f"Iteration Start Time: {iteration_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Generate screenshots for current code
            screenshot_paths = []
            canvas_check_info = {}
            if ENABLE_SCREENSHOTS:
                # For iteration 1, save as iteration_1, for iteration 2, save as iteration_2
                logger.info(f"\nGenerating screenshots for iteration {iteration}...")
                iteration_html_path = task_dir / f"iteration_{iteration}.html"
                with open(iteration_html_path, 'w', encoding='utf-8') as f:
                    f.write(current_code)
                
                screenshot_dir = task_dir / f"iteration_{iteration}_screenshots"
                screenshot_dir.mkdir(exist_ok=True)
                screenshot_paths, canvas_check_info = generate_screenshots(
                    str(iteration_html_path),
                    output_dir=str(screenshot_dir),
                    num_screenshots=NUM_SCREENSHOTS
                )
                if canvas_check_info:
                    logger.info(f"Canvas Check: {json.dumps(canvas_check_info, indent=2)}")
            
            # Evaluate current code
            logger.info(f"\nEvaluating code for iteration {iteration}...")
            eval_start_time = time.time()
            evaluation_result = evaluate_with_checklist(
                current_code,
                checklist_items,
                task_question,
                screenshot_paths=screenshot_paths if USE_SCREENSHOTS_IN_EVAL else None,
                canvas_check_info=canvas_check_info if canvas_check_info else None
            )
            eval_time = time.time() - eval_start_time
            logger.info(f"Evaluation completed in {eval_time:.2f} seconds")
            
            individual_scores = evaluation_result.get("individual_scores", {})
            evaluation_text = evaluation_result.get("evaluation_text", "")
            calculated_sum = evaluation_result.get("calculated_sum")
            overall_score = evaluation_result.get("overall_score")
            
            # Store iteration results
            iteration_result = {
                "iteration": iteration,
                "code": current_code,
                "individual_scores": individual_scores,
                "calculated_sum": calculated_sum,
                "overall_score": overall_score,
                "evaluation_text": evaluation_text,
                "timestamp": iteration_start_time.isoformat()
            }
            improvement_history.append(iteration_result)
            
            # Store as last evaluation (will be used as final if all iterations complete)
            last_evaluation = evaluation_result
            
            # Log evaluation results with full details
            logger.info(f"\n{'='*80}")
            logger.info(f"EVALUATION RESULTS - ITERATION {iteration}")
            logger.info(f"{'='*80}")
            logger.info(f"Individual Scores (JSON):\n{json.dumps(individual_scores, indent=2)}")
            logger.info(f"Calculated Sum: {calculated_sum}")
            logger.info(f"Overall Score (from LLM): {overall_score}")
            
            # Log full evaluation text (reasoning for each checklist item)
            logger.info(f"\n{'='*80}")
            logger.info(f"FULL EVALUATION FEEDBACK - ITERATION {iteration}")
            logger.info(f"{'='*80}")
            logger.info(evaluation_text)
            logger.info(f"{'='*80}")
            
            # Log full HTML code for this iteration
            logger.info(f"\n{'='*80}")
            logger.info(f"HTML CODE - ITERATION {iteration}")
            logger.info(f"{'='*80}")
            logger.info(current_code)
            logger.info(f"{'='*80}")
            
            # Display scores for each item
            logger.info(f"\n{'='*80}")
            logger.info(f"SCORE SUMMARY - ITERATION {iteration}")
            logger.info(f"{'='*80}")
            for item in checklist_items:
                title = item.get("title", "Unknown")
                score = individual_scores.get(title)
                if score is not None:
                    status = "✓" if score >= improvement_threshold else "✗"
                    logger.info(f"{status} {title}: {score:.1f}/10")
                else:
                    logger.info(f"? {title}: Score not found")
            
            # Identify weak areas
            weak_areas = identify_weak_areas(individual_scores, improvement_threshold)
            
            if not weak_areas:
                logger.info(f"\n✓ All checklist items meet the threshold ({improvement_threshold})!")
                logger.info("Improvement process complete.")
                break
            
            logger.info(f"\n⚠ Found {len(weak_areas)} area(s) needing improvement:")
            for title, score in weak_areas:
                logger.info(f"  - {title}: {score:.1f}/10")
            
            # Check if we should continue
            if iteration >= max_iterations:
                logger.info(f"\n⚠ Reached maximum iterations ({max_iterations}). Stopping.")
                completed_all_iterations = True
                break
            
            # Create improvement prompt
            logger.info(f"\nCreating improvement prompt for {len(weak_areas)} weak area(s)...")
            improvement_prompt = create_improvement_prompt(
                current_code,
                task_question,
                weak_areas,
                checklist_items,
                evaluation_text
            )
            logger.info(f"Improvement prompt created (length: {len(improvement_prompt)} characters)")
            
            # Generate improved code
            improved_code = improve_code(improvement_prompt, iteration, logger)
            
            # Save improved code
            improved_html_path = task_dir / f"iteration_{iteration}.html"
            with open(improved_html_path, 'w', encoding='utf-8') as f:
                f.write(improved_code)
            logger.info(f"✓ Improved code saved to: {improved_html_path}")
            
            # Update current code
            current_code = improved_code
            
            # Check for minimum improvement
            if iteration > 1:
                prev_scores = improvement_history[-2].get("individual_scores", {})
                improvement_made = False
                improvements = []
                for title, score in weak_areas:
                    prev_score = prev_scores.get(title, 0)
                    improvement = score - prev_score
                    improvements.append((title, prev_score, score, improvement))
                    if improvement > MIN_IMPROVEMENT:
                        improvement_made = True
                
                logger.info(f"\nImprovement Analysis:")
                for title, prev, curr, diff in improvements:
                    logger.info(f"  {title}: {prev:.1f} → {curr:.1f} (Δ {diff:+.1f})")
                
                if not improvement_made:
                    logger.info(f"\n⚠ No significant improvement detected (threshold: {MIN_IMPROVEMENT}). Stopping.")
                    break
            
            iteration_end_time = datetime.now()
            iteration_duration = (iteration_end_time - iteration_start_time).total_seconds()
            logger.info(f"Iteration {iteration} completed in {iteration_duration:.2f} seconds")
    
    # Final evaluation - only if loop broke early (not all iterations completed) or initial code was used
    if not completed_all_iterations and last_evaluation is None:
        # Need to evaluate initial code if no iterations ran
        logger.info(f"\n{'='*80}")
        logger.info("FINAL EVALUATION")
        logger.info(f"{'='*80}")
        
        # Generate final screenshots
        final_screenshot_paths = []
        final_canvas_check = {}
        if ENABLE_SCREENSHOTS:
            logger.info("Generating final screenshots...")
            final_html_path = task_dir / "final.html"
            with open(final_html_path, 'w', encoding='utf-8') as f:
                f.write(current_code)
            
            final_screenshot_dir = task_dir / "final_screenshots"
            final_screenshot_dir.mkdir(exist_ok=True)
            final_screenshot_paths, final_canvas_check = generate_screenshots(
                str(final_html_path),
                output_dir=str(final_screenshot_dir),
                num_screenshots=NUM_SCREENSHOTS
            )
            if final_canvas_check:
                logger.info(f"Final Canvas Check: {json.dumps(final_canvas_check, indent=2)}")
        
        logger.info("Running final evaluation...")
        final_eval_start = time.time()
        last_evaluation = evaluate_with_checklist(
            current_code,
            checklist_items,
            task_question,
            screenshot_paths=final_screenshot_paths if USE_SCREENSHOTS_IN_EVAL else None,
            canvas_check_info=final_canvas_check if final_canvas_check else None
        )
        final_eval_time = time.time() - final_eval_start
        logger.info(f"Final evaluation completed in {final_eval_time:.2f} seconds")
    elif completed_all_iterations:
        # All iterations completed - use last evaluation as final
        logger.info(f"\n{'='*80}")
        logger.info("FINAL EVALUATION (Using Iteration 2 Results)")
        logger.info(f"{'='*80}")
        logger.info("All iterations completed. Using iteration 2 evaluation as final.")
    
    # Use last_evaluation as final_evaluation
    final_evaluation = last_evaluation if last_evaluation else {}
    
    # Log final scores
    final_scores = final_evaluation.get("individual_scores", {}) if final_evaluation else {}
    final_sum = final_evaluation.get("calculated_sum") if final_evaluation else None
    final_evaluation_text = final_evaluation.get("evaluation_text", "") if final_evaluation else ""
    
    logger.info(f"\n{'='*80}")
    logger.info("FINAL EVALUATION RESULTS")
    logger.info(f"{'='*80}")
    logger.info(f"Individual Scores (JSON):\n{json.dumps(final_scores, indent=2)}")
    logger.info(f"Final Calculated Sum: {final_sum}")
    logger.info(f"Final Overall Score: {final_evaluation.get('overall_score') if final_evaluation else 'N/A'}")
    
    # Log full final evaluation feedback
    if final_evaluation_text:
        logger.info(f"\n{'='*80}")
        logger.info("FINAL EVALUATION FEEDBACK (Full Reasoning)")
        logger.info(f"{'='*80}")
        logger.info(final_evaluation_text)
        logger.info(f"{'='*80}")
    
    # Log final HTML code
    logger.info(f"\n{'='*80}")
    logger.info("FINAL HTML CODE")
    logger.info(f"{'='*80}")
    logger.info(current_code)
    logger.info(f"{'='*80}")
    
    # Save final HTML
    final_html_path = task_dir / "final.html"
    with open(final_html_path, 'w', encoding='utf-8') as f:
        f.write(current_code)
    logger.info(f"✓ Final code saved to: {final_html_path}")
    
    # Save results
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    results = {
        "task_id": task_id,
        "task_question": task_question,
        "improvement_threshold": improvement_threshold,
        "max_iterations": max_iterations,
        "iterations_completed": len(improvement_history),
        "improvement_history": improvement_history,
        "final_code": current_code,
        "final_evaluation": final_evaluation,
        "final_scores": final_scores,
        "final_sum": final_sum,
        "output_directory": str(task_dir),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_duration_seconds": total_duration
    }
    
    # Get token usage summary
    token_summary = token_tracker.get_summary()
    operation_summary = token_tracker.get_operation_summary()
    
    logger.info(f"\n{'='*80}")
    logger.info("ITERATIVE IMPROVEMENT PROCESS COMPLETED")
    logger.info(f"{'='*80}")
    logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    logger.info(f"Total Iterations: {len(improvement_history)}")
    logger.info(f"Final Total Score: {final_sum}")
    logger.info(f"Log file saved to: {log_file}")
    logger.info(f"All files saved to: {task_dir}")
    
    # Print and save token usage summary
    logger.info("\n" + "="*80)
    logger.info("TOKEN USAGE SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Requests: {token_summary['total_requests']}")
    logger.info(f"Total Input Tokens: {token_summary['total_input_tokens']:,}")
    logger.info(f"Total Output Tokens: {token_summary['total_output_tokens']:,}")
    logger.info(f"Total Tokens: {token_summary['total_tokens']:,}")
    
    if operation_summary:
        logger.info("\nBreakdown by Operation:")
        for operation, stats in operation_summary.items():
            logger.info(f"  {operation}: {stats['count']} requests, {stats['total_tokens']:,} tokens")
    
    # Save token usage to file (detailed breakdown)
    token_usage_file = task_dir / "token_usage.json"
    token_tracker.save_to_file(str(token_usage_file))
    logger.info(f"\n✓ Token usage saved to: {token_usage_file}")
    
    # Save to iterative token tracking JSON
    token_summary = token_tracker.get_summary()
    models = [u.model for u in token_tracker.usage_records]
    most_common_model = max(set(models), key=models.count) if models else "unknown"
    
    task_name = f"task_{task_id}"
    update_iterative_statistics(
        experiment_name=experiment_name,
        task_name=task_name,
        input_tokens=token_summary['total_input_tokens'],
        output_tokens=token_summary['total_output_tokens'],
        total_tokens=token_summary['total_tokens'],
        model=most_common_model,
        token_file=TOKEN_ITERATIVE_FILE
    )
    logger.info(f"✓ Task token usage saved to {TOKEN_ITERATIVE_FILE}")
    logger.info("="*80)
    
    return results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Load dataset
    dataset = datasets.load_dataset("tencent/ArtifactsBenchmark")
    train_data = dataset["train"]
    
    # Run for first 10 tasks
    num_tasks = min(10, len(train_data))
    
    print("\n" + "="*80)
    print(f"RUNNING ITERATIVE IMPROVEMENT FOR FIRST {num_tasks} TASKS")
    print("="*80)
    
    all_results = []
    
    for i in range(num_tasks):
        task = train_data[i]
        task_index = task.get("index", i)
        task_class = task.get("class", "unknown")
        
        print(f"\n{'='*80}")
        print(f"TASK {i+1}/{num_tasks}: Index {task_index}, Class: {task_class}")
        print(f"{'='*80}")
        
        # Prepare task data
        task_data = {
            "index": task_index,
            "question": task.get("question", ""),
            "checklist": task.get("checklist", []),
            "class": task_class,
            "difficulty": task.get("difficulty", "unknown")
        }
        
        # Reset token tracker for each task
        token_tracker = get_global_tracker()
        token_tracker.set_experiment_name(task_class)
        
        # Run iterative improvement
        try:
            results = iterative_refinement(
                task_data,
                max_iterations=MAX_ITERATIONS,
                improvement_threshold=IMPROVEMENT_THRESHOLD
            )
            all_results.append({
                "task_index": task_index,
                "task_class": task_class,
                "iterations_completed": results.get('iterations_completed', 0),
                "final_sum": results.get('final_sum', None)
            })
            print(f"\n✓ Task {task_index} completed: {results.get('iterations_completed', 0)} iterations, Score: {results.get('final_sum', 'N/A')}")
        except Exception as e:
            print(f"\n✗ Task {task_index} failed: {str(e)}")
            all_results.append({
                "task_index": task_index,
                "task_class": task_class,
                "error": str(e)
            })
    
    print("\n" + "="*80)
    print("ALL TASKS COMPLETED")
    print("="*80)
    print(f"Total tasks processed: {len(all_results)}")
    print(f"Successful: {sum(1 for r in all_results if 'error' not in r)}")
    print(f"Failed: {sum(1 for r in all_results if 'error' in r)}")
    print("\nSummary:")
    for result in all_results:
        if 'error' in result:
            print(f"  Task {result['task_index']} ({result['task_class']}): ERROR - {result['error']}")
        else:
            print(f"  Task {result['task_index']} ({result['task_class']}): {result['iterations_completed']} iterations, Score: {result['final_sum']}")
    print("="*80)

