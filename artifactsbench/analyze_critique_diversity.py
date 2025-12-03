"""
Analysis Script for Testing Signals That Indicate Need for Richer Critique Diversity

This script analyzes multi-candidate generation results to identify signals that suggest
multi-agent debate or richer critique diversity would be beneficial.

Tests:
1. Re-evaluation Consistency Test - Check if same code gets different scores
2. Feedback Quality Analysis - Measure depth, specificity, actionability
3. Blind Spot Detection - Identify checklist items with high variance
4. Candidate Variance Analysis - Investigate why candidates vary so much
"""

import datasets
import json
import statistics
import re
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Import token tracking
from token_tracking import get_global_tracker, APITokenTracker, TOKEN_TRACKING_DIR

# Import evaluation functions from experiment.py
try:
    from .experiment import (
        MODEL_NAME,
        ENABLE_SCREENSHOTS,
        NUM_SCREENSHOTS,
        USE_SCREENSHOTS_IN_EVAL,
        evaluate_with_checklist,
        generate_screenshots,
        check_canvas_content
    )
except ImportError:
    import importlib.util
    experiment_path = os.path.join(os.path.dirname(__file__), "experiment.py")
    spec = importlib.util.spec_from_file_location("experiment", experiment_path)
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)
    
    MODEL_NAME = experiment.MODEL_NAME
    ENABLE_SCREENSHOTS = experiment.ENABLE_SCREENSHOTS
    NUM_SCREENSHOTS = experiment.NUM_SCREENSHOTS
    USE_SCREENSHOTS_IN_EVAL = experiment.USE_SCREENSHOTS_IN_EVAL
    evaluate_with_checklist = experiment.evaluate_with_checklist
    generate_screenshots = experiment.generate_screenshots
    check_canvas_content = experiment.check_canvas_content

# ============================================================================
# CONFIGURATION
# ============================================================================
MULTI_CANDIDATE_OUTPUT_DIR = "artifacts_output/multi_candidate_generation"
RE_EVALUATION_COUNT = 3  # Number of times to re-evaluate each candidate
CONSISTENCY_THRESHOLD = 2.0  # Std dev threshold for needing debate

# Token tracking file for critique diversity analysis
TOKEN_CRITIQUE_DIVERSITY_FILE = os.path.join(TOKEN_TRACKING_DIR, "token_usage_critique_diversity.json")

# Initialize token tracker
token_tracker = get_global_tracker(experiment_name="critique_diversity_analysis")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def find_final_html_files() -> List[Dict]:
    """
    Find all final.html files from multi-candidate generation results.
    These are the final selected codes from each task.
    Also finds existing screenshot directories.
    
    Returns:
        List of dicts with task info and file paths
    """
    base_dir = Path(MULTI_CANDIDATE_OUTPUT_DIR)
    final_files = []
    
    if not base_dir.exists():
        print(f"⚠ Directory {MULTI_CANDIDATE_OUTPUT_DIR} does not exist")
        return final_files
    
    # Find all final.html files
    for final_file in base_dir.rglob("final.html"):
        # Extract task info from path
        parts = final_file.parts
        if len(parts) >= 3:
            class_name = parts[-3]
            task_name = parts[-2]
            task_dir = final_file.parent
            
            # Find corresponding run_log.txt
            log_file = task_dir / "run_log.txt"
            
            # Extract task index from task_name (e.g., "task_1" -> 1)
            task_index_match = re.search(r'task_(\d+)', task_name)
            task_index = int(task_index_match.group(1)) if task_index_match else None
            
            # Find existing screenshot directories (look for final_screenshots or highest iteration_X_screenshots)
            screenshot_dir = None
            # Check for final_screenshots first
            final_screenshots = task_dir / "final_screenshots"
            if final_screenshots.exists() and final_screenshots.is_dir():
                screenshot_dir = final_screenshots
            else:
                # Find the highest iteration number screenshots (last iteration)
                iteration_dirs = []
                for item in task_dir.iterdir():
                    if item.is_dir() and item.name.startswith("iteration_") and item.name.endswith("_screenshots"):
                        # Extract iteration number
                        match = re.search(r'iteration_(\d+)', item.name)
                        if match:
                            iteration_dirs.append((int(match.group(1)), item))
                
                if iteration_dirs:
                    # Sort by iteration number (descending) and take the highest (last iteration)
                    iteration_dirs.sort(key=lambda x: x[0], reverse=True)
                    screenshot_dir = iteration_dirs[0][1]
            
            final_files.append({
                "class": class_name,
                "task": task_name,
                "task_index": task_index,
                "html_path": final_file,
                "log_path": log_file if log_file.exists() else None,
                "screenshot_dir": screenshot_dir,
                "task_dir": task_dir
            })
    
    # Sort by task_index to ensure consistent ordering (task_1, task_2, etc.)
    final_files.sort(key=lambda x: (x.get("task_index") if x.get("task_index") is not None else float('inf'), x.get("class", ""), x.get("task", "")))
    
    return final_files


def load_task_data_from_log(log_path: Path) -> Optional[Dict]:
    """
    Extract task data from run_log.txt file.
    
    Args:
        log_path: Path to run_log.txt
        
    Returns:
        Dictionary with task question and checklist, or None if not found
    """
    if not log_path or not log_path.exists():
        return None
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract task question (look for "ORIGINAL TASK:" or similar)
        # Extract checklist items from evaluation feedback
        
        # For now, we'll need to load from dataset
        # This is a simplified version - in practice, you'd parse the log more carefully
        return None
    except Exception as e:
        print(f"Error reading log file {log_path}: {e}")
        return None


def read_html_file(file_path: Path) -> str:
    """Read HTML content from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading HTML file {file_path}: {e}")
        return ""


# ============================================================================
# TEST 1: RE-EVALUATION CONSISTENCY TEST
# ============================================================================

def test_evaluation_consistency(
    code: str,
    checklist_items: List[Dict],
    task_question: str,
    n: int = RE_EVALUATION_COUNT,
    file_info: Optional[Dict] = None
) -> Dict:
    """
    Re-evaluate the same code N times to check for consistency.
    
    Args:
        code: HTML code to evaluate
        checklist_items: List of checklist items
        task_question: Original task question
        n: Number of re-evaluations
        
    Returns:
        Dictionary with consistency metrics
    """
    print(f"  Re-evaluating {n} times...")
    scores = []
    individual_scores_list = []
    evaluation_texts = []
    
    # Import extract_individual_scores for parsing
    try:
        from .experiment import extract_individual_scores
    except ImportError:
        import importlib.util
        experiment_path = os.path.join(os.path.dirname(__file__), "experiment.py")
        spec = importlib.util.spec_from_file_location("experiment", experiment_path)
        experiment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(experiment)
        extract_individual_scores = experiment.extract_individual_scores
    
    for i in range(n):
        print(f"    Evaluation {i+1}/{n}...", end=" ", flush=True)
        start_time = time.time()
        
        # Use existing screenshots if available, otherwise generate new ones
        screenshot_paths = []
        canvas_check_info = {}
        if ENABLE_SCREENSHOTS:
            # Check if we have existing screenshot directory from file_info
            existing_screenshot_dir = None
            if file_info and file_info.get("screenshot_dir"):
                existing_screenshot_dir = file_info["screenshot_dir"]
            
            if existing_screenshot_dir and existing_screenshot_dir.exists():
                # Use existing screenshots
                screenshot_files = sorted(existing_screenshot_dir.glob("screenshot_*.png"))
                screenshot_paths = [str(f) for f in screenshot_files]
                if screenshot_paths:
                    print(f"(using existing screenshots)", end=" ", flush=True)
                else:
                    screenshot_paths = []
            else:
                # Generate new screenshots if none exist
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp:
                    tmp.write(code)
                    tmp_path = tmp.name
                
                try:
                    screenshot_dir = tempfile.mkdtemp()
                    screenshot_paths, canvas_check_info = generate_screenshots(
                        tmp_path,
                        output_dir=screenshot_dir,
                        num_screenshots=NUM_SCREENSHOTS
                    )
                except Exception as e:
                    print(f"Warning: Screenshot generation failed: {e}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
        
        # Evaluate
        result = evaluate_with_checklist(
            code,
            checklist_items,
            task_question,
            screenshot_paths=screenshot_paths if USE_SCREENSHOTS_IN_EVAL else None,
            canvas_check_info=canvas_check_info if canvas_check_info else None
        )
        
        eval_time = time.time() - start_time
        total_score = result.get("calculated_sum", 0)
        individual_scores = result.get("individual_scores", {})
        
        # If individual_scores is empty, try to extract from evaluation_text
        if not individual_scores:
            eval_text = result.get("evaluation_text", "")
            if eval_text:
                try:
                    individual_scores = extract_individual_scores(eval_text, checklist_items)
                except Exception as e:
                    print(f"      Warning: Could not extract individual scores: {e}")
        
        scores.append(total_score)
        individual_scores_list.append(individual_scores)
        evaluation_texts.append(result.get("evaluation_text", ""))
        
        print(f"Score: {total_score:.1f} (took {eval_time:.1f}s)")
    
    # Calculate statistics
    if len(scores) > 1:
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores)
        variance = statistics.variance(scores)
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
    else:
        mean_score = scores[0] if scores else 0
        std_dev = 0
        variance = 0
        min_score = mean_score
        max_score = mean_score
        score_range = 0
    
    # Calculate per-item variance
    item_variance = {}
    if individual_scores_list:
        all_item_names = set()
        for scores_dict in individual_scores_list:
            all_item_names.update(scores_dict.keys())
        
        for item_name in all_item_names:
            item_scores = [s.get(item_name, 0) for s in individual_scores_list]
            if len(item_scores) > 1:
                item_variance[item_name] = {
                    "mean": statistics.mean(item_scores),
                    "std_dev": statistics.stdev(item_scores),
                    "variance": statistics.variance(item_scores),
                    "min": min(item_scores),
                    "max": max(item_scores),
                    "range": max(item_scores) - min(item_scores)
                }
            else:
                item_variance[item_name] = {
                    "mean": item_scores[0] if item_scores else 0,
                    "std_dev": 0,
                    "variance": 0,
                    "min": item_scores[0] if item_scores else 0,
                    "max": item_scores[0] if item_scores else 0,
                    "range": 0
                }
    
    return {
        "n_evaluations": n,
        "total_scores": scores,
        "mean_score": mean_score,
        "std_dev": std_dev,
        "variance": variance,
        "min_score": min_score,
        "max_score": max_score,
        "score_range": score_range,
        "item_variance": item_variance,
        "individual_scores_list": individual_scores_list,  # Store for blind spot detection
        "evaluation_texts": evaluation_texts,
        "needs_debate": std_dev > CONSISTENCY_THRESHOLD,
        "consistency_level": "high" if std_dev < 1.0 else "medium" if std_dev < 2.0 else "low"
    }


# ============================================================================
# TEST 2: FEEDBACK QUALITY ANALYSIS
# ============================================================================

def analyze_feedback_quality(evaluation_text: str) -> Dict:
    """
    Analyze the quality of evaluation feedback.
    
    Args:
        evaluation_text: Full evaluation text from LLM
        
    Returns:
        Dictionary with quality metrics
    """
    if not evaluation_text:
        return {
            "length": 0,
            "has_code_references": False,
            "has_actionable_suggestions": False,
            "specificity_score": 0.0,
            "mentions_specific_lines": False,
            "mentions_specific_functions": False,
            "has_concrete_examples": False,
            "sentence_count": 0,
            "word_count": 0
        }
    
    # Basic metrics
    length = len(evaluation_text)
    sentences = re.split(r'[.!?]+', evaluation_text)
    sentence_count = len([s for s in sentences if s.strip()])
    words = evaluation_text.split()
    word_count = len(words)
    
    # Check for code references
    code_patterns = [
        r'line\s+\d+',
        r'function\s+\w+',
        r'class\s+\w+',
        r'variable\s+\w+',
        r'`[^`]+`',  # Code backticks
        r'<[^>]+>',  # HTML tags
        r'\w+\(\)',  # Function calls
    ]
    has_code_references = any(re.search(pattern, evaluation_text, re.IGNORECASE) for pattern in code_patterns)
    mentions_specific_lines = bool(re.search(r'line\s+\d+', evaluation_text, re.IGNORECASE))
    mentions_specific_functions = bool(re.search(r'function\s+\w+|method\s+\w+', evaluation_text, re.IGNORECASE))
    
    # Check for actionable suggestions
    actionable_patterns = [
        r'should\s+\w+',
        r'could\s+\w+',
        r'recommend\s+\w+',
        r'suggest\s+\w+',
        r'consider\s+\w+',
        r'add\s+\w+',
        r'implement\s+\w+',
        r'improve\s+\w+',
    ]
    has_actionable_suggestions = any(re.search(pattern, evaluation_text, re.IGNORECASE) for pattern in actionable_patterns)
    
    # Check for concrete examples
    example_patterns = [
        r'for example',
        r'such as',
        r'like\s+\w+',
        r'e\.g\.',
        r'instance',
    ]
    has_concrete_examples = any(re.search(pattern, evaluation_text, re.IGNORECASE) for pattern in example_patterns)
    
    # Calculate specificity score (0-1)
    specificity_factors = [
        has_code_references,
        mentions_specific_lines,
        mentions_specific_functions,
        has_actionable_suggestions,
        has_concrete_examples,
    ]
    specificity_score = sum(specificity_factors) / len(specificity_factors)
    
    return {
        "length": length,
        "has_code_references": has_code_references,
        "has_actionable_suggestions": has_actionable_suggestions,
        "specificity_score": specificity_score,
        "mentions_specific_lines": mentions_specific_lines,
        "mentions_specific_functions": mentions_specific_functions,
        "has_concrete_examples": has_concrete_examples,
        "sentence_count": sentence_count,
        "word_count": word_count
    }


# ============================================================================
# TEST 3: BLIND SPOT DETECTION
# ============================================================================

def detect_blind_spots(all_evaluations: List[Dict]) -> Dict:
    """
    Identify checklist items with highest variance across evaluations.
    
    Args:
        all_evaluations: List of evaluation results with individual_scores
        
    Returns:
        Dictionary with blind spot analysis
    """
    if not all_evaluations:
        return {}
    
    # Collect scores for each checklist item
    item_scores = defaultdict(list)
    
    for eval_result in all_evaluations:
        individual_scores = eval_result.get("individual_scores", {})
        for item_name, score in individual_scores.items():
            if score is not None:
                item_scores[item_name].append(score)
    
    # Calculate variance for each item
    item_variance_analysis = {}
    for item_name, scores in item_scores.items():
        if len(scores) > 1:
            item_variance_analysis[item_name] = {
                "count": len(scores),
                "mean": statistics.mean(scores),
                "std_dev": statistics.stdev(scores),
                "variance": statistics.variance(scores),
                "min": min(scores),
                "max": max(scores),
                "range": max(scores) - min(scores),
                "coefficient_of_variation": statistics.stdev(scores) / statistics.mean(scores) if statistics.mean(scores) > 0 else 0
            }
        else:
            item_variance_analysis[item_name] = {
                "count": len(scores),
                "mean": scores[0] if scores else 0,
                "std_dev": 0,
                "variance": 0,
                "min": scores[0] if scores else 0,
                "max": scores[0] if scores else 0,
                "range": 0,
                "coefficient_of_variation": 0
            }
    
    # Sort by variance (highest first)
    sorted_items = sorted(
        item_variance_analysis.items(),
        key=lambda x: x[1]["variance"],
        reverse=True
    )
    
    return {
        "item_variance": item_variance_analysis,
        "sorted_by_variance": sorted_items,
        "high_variance_items": [item for item, stats in sorted_items if stats["variance"] > 2.0],
        "medium_variance_items": [item for item, stats in sorted_items if 1.0 < stats["variance"] <= 2.0],
        "low_variance_items": [item for item, stats in sorted_items if stats["variance"] <= 1.0]
    }


# ============================================================================
# TEST 4: CANDIDATE VARIANCE ANALYSIS
# ============================================================================

def analyze_candidate_variance(candidates_data: List[Dict]) -> Dict:
    """
    Analyze variance in candidate scores for same weak items.
    
    Args:
        candidates_data: List of candidate evaluation results
        
    Returns:
        Dictionary with variance analysis
    """
    # Group candidates by focus item
    by_focus_item = defaultdict(list)
    
    for candidate in candidates_data:
        focus_item = candidate.get("focus_item", "unknown")
        score = candidate.get("total_score", 0)
        by_focus_item[focus_item].append({
            "score": score,
            "task": candidate.get("task", "unknown"),
            "candidate_num": candidate.get("candidate_num", 0)
        })
    
    # Calculate variance for each focus item
    focus_item_analysis = {}
    for focus_item, candidates in by_focus_item.items():
        if len(candidates) > 1:
            scores = [c["score"] for c in candidates]
            focus_item_analysis[focus_item] = {
                "count": len(candidates),
                "scores": scores,
                "mean": statistics.mean(scores),
                "std_dev": statistics.stdev(scores),
                "variance": statistics.variance(scores),
                "min": min(scores),
                "max": max(scores),
                "range": max(scores) - min(scores)
            }
        else:
            focus_item_analysis[focus_item] = {
                "count": 1,
                "scores": [candidates[0]["score"]],
                "mean": candidates[0]["score"],
                "std_dev": 0,
                "variance": 0,
                "min": candidates[0]["score"],
                "max": candidates[0]["score"],
                "range": 0
            }
    
    return {
        "by_focus_item": focus_item_analysis,
        "high_variance_focus_items": [
            item for item, stats in focus_item_analysis.items()
            if stats["variance"] > 10.0
        ]
    }


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def run_consistency_tests(
    num_files: int = 5,
    output_file: Optional[str] = None
) -> Dict:
    """
    Run all consistency tests on final.html files from multi-candidate generation results.
    Re-evaluates each final.html file multiple times to test judge consistency.
    
    Args:
        num_files: Number of final.html files to test (0 = test all)
        output_file: Optional path to save results JSON
        
    Returns:
        Dictionary with all test results
    """
    print("="*80)
    print("CRITIQUE DIVERSITY SIGNAL ANALYSIS")
    print("="*80)
    print(f"Testing for signals that indicate need for richer critique diversity")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Load dataset
    print("\n1. Loading dataset...")
    dataset = datasets.load_dataset("tencent/ArtifactsBenchmark")
    train_data = dataset["train"]
    print(f"   ✓ Loaded dataset with {len(train_data)} tasks")
    
    # Find final.html files
    print("\n2. Finding final.html files...")
    final_files = find_final_html_files()
    print(f"   ✓ Found {len(final_files)} final.html files")
    
    if not final_files:
        print("   ⚠ No final.html files found. Run multi_candidate_generation.py first.")
        return {}
    
    # Show which files will be tested
    if final_files:
        print(f"\n   Files found (sorted by task_index):")
        for i, f in enumerate(final_files[:10], 1):  # Show first 10
            task_idx = f.get("task_index", "?")
            print(f"     {i}. {f['class']} / {f['task']} (index: {task_idx})")
        if len(final_files) > 10:
            print(f"     ... and {len(final_files) - 10} more")
    
    # Limit number if specified
    if num_files > 0:
        final_files = final_files[:num_files]
        print(f"\n   Testing first {len(final_files)} file(s):")
        for i, f in enumerate(final_files, 1):
            task_idx = f.get("task_index", "?")
            print(f"     {i}. {f['class']} / {f['task']} (index: {task_idx})")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "num_files_tested": len(final_files),
        "consistency_tests": [],
        "feedback_quality": [],
        "blind_spots": None,
        "candidate_variance": None
    }
    
    # Test 1: Re-evaluation Consistency
    print("\n" + "="*80)
    print("TEST 1: RE-EVALUATION CONSISTENCY TEST")
    print("="*80)
    print("Re-evaluating final.html files multiple times to check for consistency...")
    
    all_evaluations_for_blind_spots = []
    
    for i, file_info in enumerate(final_files, 1):
        print(f"\n[{i}/{len(final_files)}] Testing: {file_info['class']} / {file_info['task']}")
        print(f"  Reading existing final.html: {file_info['html_path']}")
        
        # Read HTML code (NOT generating - just reading existing file)
        code = read_html_file(file_info["html_path"])
        if not code:
            print("  ⚠ Could not read HTML file, skipping...")
            continue
        
        print(f"  ✓ Read {len(code)} characters from existing file")
        print(f"  NOTE: This script does NOT generate code - only re-evaluates existing code")
        
        # Find corresponding task in dataset by matching the "index" field
        # The directory name "task_X" contains the actual index field from the dataset, not array position
        task_index_from_dir = file_info.get("task_index")
        if task_index_from_dir is None:
            # Try to extract from task name
            task_index_match = re.search(r'task_(\d+)', file_info["task"])
            if task_index_match:
                task_index_from_dir = int(task_index_match.group(1))
            else:
                print(f"  ⚠ Could not extract task index from {file_info['task']}, skipping...")
                continue
        
        # Find task by matching the "index" field (not array position!)
        task = None
        for t in train_data:
            if t.get("index") == task_index_from_dir:
                task = t
                break
        
        if task is None:
            print(f"  ⚠ Task with index {task_index_from_dir} not found in dataset, skipping...")
            continue
        
        checklist_items = task.get("checklist", [])
        task_question = task.get("question", "")
        
        if not checklist_items:
            print("  ⚠ No checklist items found, skipping...")
            continue
        
        # Run consistency test (pass file_info so it can use existing screenshots)
        consistency_result = test_evaluation_consistency(
            code,
            checklist_items,
            task_question,
            n=RE_EVALUATION_COUNT,
            file_info=file_info  # Pass file_info to access screenshot directory
        )
        
        consistency_result["file_info"] = file_info
        results["consistency_tests"].append(consistency_result)
        
        # Store individual scores for blind spot detection
        # We'll collect all individual score dictionaries from the consistency test
        for individual_scores in consistency_result.get("individual_scores_list", []):
            all_evaluations_for_blind_spots.append({
                "individual_scores": individual_scores,
                "file_info": file_info
            })
        
        # Analyze feedback quality
        if consistency_result["evaluation_texts"]:
            feedback_quality = analyze_feedback_quality(consistency_result["evaluation_texts"][0])
            feedback_quality["file_info"] = file_info
            results["feedback_quality"].append(feedback_quality)
        
        print(f"  ✓ Consistency: {consistency_result['consistency_level']} (std_dev: {consistency_result['std_dev']:.2f})")
        if consistency_result["needs_debate"]:
            print(f"  ⚠ HIGH VARIANCE DETECTED - Debate may be beneficial")
    
    # Test 2: Blind Spot Detection
    print("\n" + "="*80)
    print("TEST 2: BLIND SPOT DETECTION")
    print("="*80)
    
    if all_evaluations_for_blind_spots:
        blind_spots = detect_blind_spots(all_evaluations_for_blind_spots)
        results["blind_spots"] = blind_spots
        
        print(f"  ✓ Analyzed {len(blind_spots.get('item_variance', {}))} checklist items")
        if blind_spots.get("high_variance_items"):
            print(f"  ⚠ Found {len(blind_spots['high_variance_items'])} high-variance items:")
            for item in blind_spots["high_variance_items"][:5]:
                stats = blind_spots["item_variance"].get(item, {})
                print(f"    - {item}: variance={stats.get('variance', 0):.2f}, range={stats.get('range', 0):.1f}")
        else:
            print(f"  ✓ No high-variance items detected")
    else:
        print("  ⚠ No evaluation data collected for blind spot detection")
    
    # Test 3: Candidate Variance Analysis
    print("\n" + "="*80)
    print("TEST 3: CANDIDATE VARIANCE ANALYSIS")
    print("="*80)
    
    # This would require loading candidate evaluation results from logs
    # For now, we'll skip this or implement a simplified version
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    consistency_tests = results["consistency_tests"]
    if consistency_tests:
        avg_std_dev = statistics.mean([t["std_dev"] for t in consistency_tests])
        max_std_dev = max([t["std_dev"] for t in consistency_tests])
        needs_debate_count = sum([1 for t in consistency_tests if t["needs_debate"]])
        
        print(f"Consistency Tests:")
        print(f"  Average std_dev: {avg_std_dev:.2f}")
        print(f"  Max std_dev: {max_std_dev:.2f}")
        print(f"  Candidates needing debate: {needs_debate_count}/{len(consistency_tests)}")
        
        if avg_std_dev > CONSISTENCY_THRESHOLD:
            print(f"\n⚠ RECOMMENDATION: Multi-agent debate may be beneficial")
            print(f"   Average variance ({avg_std_dev:.2f}) exceeds threshold ({CONSISTENCY_THRESHOLD})")
        else:
            print(f"\n✓ Current evaluation system appears consistent")
            print(f"   Average variance ({avg_std_dev:.2f}) is below threshold ({CONSISTENCY_THRESHOLD})")
    
    if results["feedback_quality"]:
        avg_specificity = statistics.mean([f["specificity_score"] for f in results["feedback_quality"]])
        print(f"\nFeedback Quality:")
        print(f"  Average specificity score: {avg_specificity:.2f}/1.0")
        if avg_specificity < 0.5:
            print(f"  ⚠ Low specificity - feedback may be too generic")
    
    # Save results
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Results saved to: {output_path}")
    
    # Print and save token usage
    print("\n" + "="*80)
    print("TOKEN USAGE SUMMARY")
    print("="*80)
    token_tracker.print_summary()
    
    # Save token usage to file
    os.makedirs(TOKEN_TRACKING_DIR, exist_ok=True)
    token_usage_file = Path(TOKEN_CRITIQUE_DIVERSITY_FILE)
    token_tracker.save_to_file(str(token_usage_file))
    
    # Save experiment to history
    token_tracker.save_experiment_to_history(token_file=TOKEN_CRITIQUE_DIVERSITY_FILE)
    print(f"\n✓ Token usage saved to: {token_usage_file}")
    print(f"✓ Experiment token usage saved to: {TOKEN_CRITIQUE_DIVERSITY_FILE}")
    
    return results


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze multi-candidate generation results for critique diversity signals"
    )
    parser.add_argument(
        "--num-files",
        type=int,
        default=1,
        help="Number of final.html files to test (0 = test all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts_output/multi_candidate_generation/critique_diversity_analysis.json",
        help="Output file path for results"
    )
    
    args = parser.parse_args()
    
    results = run_consistency_tests(
        num_files=args.num_files,
        output_file=args.output
    )
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

