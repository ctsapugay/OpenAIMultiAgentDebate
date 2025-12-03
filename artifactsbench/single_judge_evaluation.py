#load artifactsbench dataset
import datasets
import openai
from dotenv import load_dotenv, find_dotenv
import sys
import os

load_dotenv(find_dotenv())

# Add parent directory to path for token tracking
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from token_tracking import get_global_tracker, APITokenTracker, TOKEN_TRACKING_DIR

# Token tracking file for single judge evaluation
TOKEN_SINGLE_JUDGE_FILE = os.path.join(TOKEN_TRACKING_DIR, "token_usage_single_judge_evaluation.json")

# ============================================================================
# CONFIGURATION
# ============================================================================
# Model selection - choose the model you want to use:
# - "gpt-4o-mini" - GPT-4o mini (cost-effective, widely available)
# - "gpt-4o" - Full GPT-4o (more capable, higher cost)
# - "gpt-4.1-mini" - GPT-4.1 mini (newer, check availability in your region)
# - "gpt-4-turbo" - GPT-4 Turbo
MODEL_NAME = "gpt-4.1-mini"  # Change this to switch models

# Screenshot configuration
ENABLE_SCREENSHOTS = True  # Set to True to capture screenshots
NUM_SCREENSHOTS = 3  # Number of screenshots to capture (default: 3)
SCREENSHOT_INTERVAL = 1  # Time interval between screenshots in seconds
USE_SCREENSHOTS_IN_EVAL = True  # Include screenshots in evaluation (requires vision-capable model)

# Output directory configuration
OUTPUT_DIR = "artifacts_output"  # Directory to save HTML and screenshots in the project

dataset = datasets.load_dataset("tencent/ArtifactsBenchmark")

#print the dataset
# print(dataset)

#print the first example
task0 = dataset["train"][0]

# Debug: Print the question to see what we're working with
print("="*80)
print("TASK INFORMATION:")
print("="*80)
print(f"Task ID: {task0.get('index', 'N/A')}")
print(f"Category: {task0.get('class', 'Unknown')}")
print(f"Difficulty: {task0.get('difficulty', 'unknown')}")
print(f"\nQuestion (first 500 chars):")
print(task0["question"][:500])
print("="*80)

# Extract and display checklist
checklist_items = task0.get("checklist", [])
if checklist_items:
    print("\n" + "="*80)
    print("CHECKLIST ITEMS:")
    print("="*80)
    for idx, item in enumerate(checklist_items, 1):
        title = item.get("title", f"Item {idx}")
        description = item.get("description", "No description")
        print(f"\n{idx}. {title}")
        print(f"   {description}")
    print("="*80)
else:
    print("\n⚠ No checklist items found in dataset")
print()

# Generate code using the ArtifactsBench prompt format
from openai import OpenAI

client = OpenAI()

# Initialize token tracker with experiment name
task_id = task0.get('index', 'unknown')
task_category = task0.get('class', 'unknown').replace(' ', '_').lower()
experiment_name = f"experiment_task_{task_id}_{task_category}"
token_tracker = get_global_tracker(experiment_name=experiment_name)

# ArtifactsBench uses the question field directly, but we need to ensure code generation
# Add explicit system message to force code generation
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

# Use the question field as the user prompt (this is what ArtifactsBench does)
# But ensure it explicitly requests code generation
user_question = task0["question"]

# If the question doesn't explicitly mention code/implementation, add a directive
if not any(word in user_question.lower() for word in ["code", "implement", "generate code", "create", "build", "write"]):
    user_prompt = f"""{user_question}

IMPORTANT: Generate the complete, working code to implement this. Output ONLY the executable code without any explanations or descriptions."""
else:
    user_prompt = user_question

print("="*80)
print("PROMPT BEING SENT:")
print("="*80)
print(f"System: {system_message[:200]}...")
print(f"\nUser: {user_prompt[:400]}...")
print("="*80)

response = client.chat.completions.create(
    model=MODEL_NAME,  # Using model specified in configuration above
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.0  # Low temperature for deterministic code generation
)

# Track token usage
token_tracker.track_response(response, operation="code_generation", model=MODEL_NAME)

generated_content = response.choices[0].message.content
print("\n" + "="*80)
print("RAW MODEL RESPONSE:")
print("="*80)
print(generated_content)
print("="*80)

# Extract HTML code from the response (handle markdown code blocks if present)
import re
import webbrowser
import tempfile
from string import Template
import json
import os
import time
from pathlib import Path

# ============================================================================
# SCREENSHOT CAPTURE (Official ArtifactsBenchmark Format)
# ============================================================================

def capture_html_screenshots(
    html_path, img_paths, num_screenshots=3, interval=1, max_retries=2, timeout=600000
):
    """
    Captures screenshots of the given HTML content using Playwright.
    Based on official ArtifactsBenchmark implementation.
    
    Parameters:
    - html_path: Path to the HTML file to capture screenshots from
    - img_paths: List of file paths where the screenshots will be saved
    - num_screenshots: The number of screenshots to capture (default is 3)
    - interval: Time interval between screenshots (default is 1 second)
    - max_retries: Maximum number of retry attempts in case of failure (default is 2)
    - timeout: Timeout duration for the page loading and screenshot capture (default is 600000 milliseconds)
    
    Returns:
    - bool: True if successful, False otherwise
    """
    try:
        html_path = Path(html_path) if not isinstance(html_path, Path) else html_path
        
        for attempt in range(1, max_retries + 1):
            try:
                from playwright.sync_api import sync_playwright
                
                # Launch the browser using Playwright
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    try:
                        context = browser.new_context()
                        page = context.new_page()
                        page.set_default_timeout(timeout)
                        page.goto(f"file://{html_path.resolve()}", timeout=timeout)
                        page.wait_for_load_state("networkidle", timeout=timeout)

                        # Capture screenshots
                        for i in range(num_screenshots):
                            if i < len(img_paths):
                                page.screenshot(
                                    path=img_paths[i], full_page=True, timeout=timeout
                                )
                                if i < num_screenshots - 1:
                                    time.sleep(interval)
                        return True  # Success
                    finally:
                        if context:
                            context.close()
                        if browser:
                            browser.close()
            except ImportError:
                print("\n⚠ Playwright not installed. Install with: pip install playwright && playwright install chromium")
                return False
            except Exception as e:
                if attempt == max_retries:
                    print(f"Attempt {attempt} failed, Error: {str(e)}")
                    return False
                else:
                    print(f"Attempt {attempt} failed, retrying... Error: {str(e)}")
        return False
    except Exception as e:
        print(f"Screenshot capture error: {str(e)}")
        return False


def check_canvas_content(html_file_path: str) -> dict:
    """
    Check if canvas elements in the HTML have actual content rendered.
    
    Args:
        html_file_path: Path to the HTML file
        
    Returns:
        Dictionary with check results including whether canvas is blank
    """
    try:
        from playwright.sync_api import sync_playwright
        html_path = Path(html_file_path)
        
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(f"file://{html_path.resolve()}", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(3000)  # Wait for JS execution
                
                # Check for canvas elements
                canvas_info = page.evaluate("""
                    () => {
                        const canvases = document.querySelectorAll('canvas');
                        const results = {
                            canvas_count: canvases.length,
                            canvases_with_content: 0,
                            blank_canvases: 0,
                            canvas_details: []
                        };
                        
                        for (let canvas of canvases) {
                            const detail = {
                                width: canvas.width,
                                height: canvas.height,
                                has_content: false
                            };
                            
                            if (canvas.width > 0 && canvas.height > 0) {
                                try {
                                    const ctx = canvas.getContext('2d');
                                    if (ctx) {
                                        // Sample pixels from multiple areas
                                        const sampleSize = Math.min(50, Math.min(canvas.width, canvas.height));
                                        const imageData = ctx.getImageData(0, 0, sampleSize, sampleSize);
                                        // Check if any pixel is non-transparent (not all zeros/transparent)
                                        const hasContent = imageData.data.some((val, idx) => {
                                            // Check RGB channels (skip alpha)
                                            return idx % 4 !== 3 && val !== 0;
                                        });
                                        detail.has_content = hasContent;
                                        
                                        if (hasContent) {
                                            results.canvases_with_content++;
                                        } else {
                                            results.blank_canvases++;
                                        }
                                    }
                                } catch (e) {
                                    detail.error = e.toString();
                                }
                            }
                            results.canvas_details.push(detail);
                        }
                        
                        return results;
                    }
                """)
                
                browser.close()
                return canvas_info
            except Exception as e:
                if browser:
                    browser.close()
                return {"error": str(e), "canvas_count": 0}
    except ImportError:
        return {"error": "Playwright not available", "canvas_count": 0}
    except Exception as e:
        return {"error": str(e), "canvas_count": 0}


def generate_screenshots(html_file_path: str, output_dir: str = None, num_screenshots: int = 3) -> tuple:
    """
    Generate screenshots from an HTML file and check for blank canvases.
    
    Args:
        html_file_path: Path to the HTML file
        output_dir: Directory to save screenshots (default: same directory as HTML file)
        num_screenshots: Number of screenshots to capture
        
    Returns:
        Tuple of (list of screenshot file paths, canvas_check_info dict)
    """
    if not ENABLE_SCREENSHOTS:
        return [], {}
    
    try:
        html_path = Path(html_file_path)
        
        # Determine output directory
        if output_dir is None:
            output_dir = html_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate screenshot paths
        screenshot_paths = [
            str(output_dir / f"screenshot_{i + 1}.png")
            for i in range(num_screenshots)
        ]
        
        print("\n" + "="*80)
        print("CAPTURING SCREENSHOTS...")
        print("="*80)
        print(f"HTML file: {html_file_path}")
        print(f"Output directory: {output_dir}")
        print(f"Number of screenshots: {num_screenshots}")
        
        success = capture_html_screenshots(
            html_path,
            screenshot_paths,
            num_screenshots=num_screenshots,
            interval=SCREENSHOT_INTERVAL
        )
        
        # Check canvas content
        canvas_check = check_canvas_content(html_file_path)
        
        if success:
            print(f"✓ Successfully captured {num_screenshots} screenshot(s)")
            for i, path in enumerate(screenshot_paths, 1):
                if os.path.exists(path):
                    print(f"  {i}. {path}")
            
            # Report canvas check results
            if canvas_check.get("canvas_count", 0) > 0:
                print(f"\nCanvas Check:")
                print(f"  Total canvases: {canvas_check.get('canvas_count', 0)}")
                print(f"  With content: {canvas_check.get('canvases_with_content', 0)}")
                print(f"  Blank: {canvas_check.get('blank_canvases', 0)}")
                if canvas_check.get('blank_canvases', 0) > 0:
                    print("  ⚠ WARNING: Blank canvas detected! The game may not be rendering properly.")
            print("="*80)
            return screenshot_paths, canvas_check
        else:
            print("✗ Failed to capture screenshots")
            print("="*80)
            return [], canvas_check
            
    except Exception as e:
        print(f"\n⚠ Error generating screenshots: {e}")
        return [], {}

# Try multiple extraction strategies
html_code = None

# Strategy 1: Extract from markdown code blocks (most common)
html_match = re.search(r'```(?:html|javascript|js)?\s*(.*?)\s*```', generated_content, re.DOTALL)
if html_match:
    html_code = html_match.group(1).strip()
    print("\n✓ Extracted code from markdown code block")

# Strategy 2: Check if content itself is HTML/SVG
if not html_code:
    if '<html' in generated_content.lower() or '<!doctype' in generated_content.lower() or '<svg' in generated_content.lower():
        # Find the first HTML/SVG tag and extract from there
        html_start = re.search(r'(<!DOCTYPE|<html|<svg)', generated_content, re.IGNORECASE)
        if html_start:
            html_code = generated_content[html_start.start():].strip()
            print("\n✓ Extracted HTML/SVG code from response")
    
# Strategy 3: If still no code, check if there's any code-like content
if not html_code:
    # Look for any HTML tags
    if re.search(r'<[a-z]+', generated_content, re.IGNORECASE):
        # Try to extract everything after the first HTML tag
        html_start = re.search(r'<[a-z]+', generated_content, re.IGNORECASE)
        if html_start:
            html_code = generated_content[html_start.start():].strip()
            print("\n✓ Extracted partial HTML code")

# Strategy 4: If no code found, this is a problem
if not html_code:
    print("\n⚠ WARNING: No executable code detected in response!")
    print("The model generated a description instead of code.")
    print("This suggests the prompt needs to be more explicit about code generation.")
    print("\nFalling back to wrapping content in HTML structure...")
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

# Save HTML to project directory
# Get task information for filename
task_id = task0.get('index', 'unknown')
task_category = task0.get('class', 'unknown').replace(' ', '_').lower()
task_difficulty = task0.get('difficulty', 'unknown').lower()

# Create output directory structure
output_base_dir = Path(OUTPUT_DIR)
output_base_dir.mkdir(exist_ok=True)

# Create task-specific directory
task_dir = output_base_dir / f"task_{task_id}_{task_category}_{task_difficulty}"
task_dir.mkdir(exist_ok=True)

# Save HTML file
html_filename = f"artifact_{task_id}.html"
html_file_path = str(task_dir / html_filename)
with open(html_file_path, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"\nHTML saved to: {html_file_path}")
print("Opening in browser...")

# Open in the default web browser
# webbrowser.open(f'file://{html_file_path}')

# Generate screenshots if enabled
screenshot_paths = []
canvas_check_info = {}
if ENABLE_SCREENSHOTS:
    screenshot_dir = task_dir / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    screenshot_paths, canvas_check_info = generate_screenshots(
        html_file_path, 
        output_dir=str(screenshot_dir),
        num_screenshots=NUM_SCREENSHOTS
    )


# ============================================================================
# CHECKLIST EVALUATION (Official ArtifactsBenchmark Format)
# ============================================================================

# Official ArtifactsBenchmark prompt template
PROMPT_MLLM_CONTENT = (
    "You are a seasoned and meticulous code review expert, proficient in multiple "
    "programming languages, front-end technologies, and interaction design. Your task "
    "is to conduct an in-depth analysis and scoring of the received [question] and "
    "[answer]. The [answer] may include source code (in various programming languages), "
    "algorithm implementations, data structure designs, system architecture diagrams, "
    "front-end visualization code (such as HTML/SVG/JavaScript), interaction logic "
    "descriptions, and related technical explanations. Please leverage your coding "
    "expertise and aesthetic experience to thoroughly examine the [answer] content from "
    "the following dimensions and provide scores along with detailed review comments. "
    "You should be very strict and cautious when giving full marks for each dimension.\n\n"
    "Role Definition\n\n"
    "Responsibilities: Act as an authoritative technical review committee member, ensuring "
    "objectivity, comprehensiveness, and impartiality.\n"
    "Attitude: Rigorous, professional, and unsparing, adept at identifying details "
    "and potential risks.\n"
    "Additional Traits: Possess exceptional aesthetic talent, with high standards for "
    "visual appeal and user experience.\n\n"
    "I have only extracted the last segment of HTML or SVG code from the provided answer "
    "for visualization. The content is adaptively scrolled to capture the entire page.\n\n"
    "**Scoring Criteria:**\n\n"
    "$Checklist\n\n"
    "- For each criterion above, provide a score (typically 0-10 or as specified).\n"
    "- The final output should be a JSON object containing scores for each dimension and an overall score, "
    "following this example:\n"
    "```json\n"
    "{\n"
    "  \"Criterion 1 Title\": \"8\",\n"
    "  \"Criterion 2 Title\": \"7\",\n"
    "  \"Criterion 3 Title\": \"9\",\n"
    "  \"Overall Score\": \"24\"\n"
    "}\n"
    "```\n"
    "Note: The Overall Score should be the sum of all individual criterion scores.\n"
    "Reason: [Provide detailed justification for each score]...\n\n"
    "Please score the following question according to the standards above:\n\n"
    "--------Problem starts--------\n"
    "$Question\n"
    "--------Problem ends--------\n\n"
    "--------Answer starts--------\n"
    "$Answer\n"
    "--------Answer ends--------\n"
)

PROMPT_MLLM = Template(PROMPT_MLLM_CONTENT)


def get_prompt_mllm_checklist(checklist: str, question: str, answer: str) -> str:
    """
    Fill in the code-review prompt template with actual content.
    Based on official ArtifactsBenchmark implementation.
    
    Args:
        checklist: The scoring checklist or criteria to include
        question: The user's original question or problem description
        answer: The candidate answer (possibly including code snippets)
        
    Returns:
        The fully formatted prompt ready to be sent to the LLM
    """
    return PROMPT_MLLM.substitute(
        Checklist=checklist,
        Question=question,
        Answer=answer
    )


def find_pattern_matches(patterns, data):
    """
    Attempts to find matches for a list of patterns in the provided data.
    Based on official ArtifactsBenchmark implementation.
    
    Parameters:
    - patterns: A list of regex patterns to try
    - data: The data to search through
    
    Returns:
    - The last matched score (string), or None if no match is found
    """
    for pattern in patterns:
        matches = re.findall(pattern, data)
        if matches:
            # Return the last matched score (if any matches are found)
            return matches[-1][1]
    return None


def extract_mllm_overall(data: str) -> str | None:
    """
    Extracts the overall score from the given data using predefined patterns.
    Based on official ArtifactsBenchmark implementation.
    
    Parameters:
    - data: The data from which the score needs to be extracted
    
    Returns:
    - The overall score (string) or None if not found
    """
    patterns = [
        # English pattern for overall score
        r'"Overall Score":\s*(")?(\d+(\.\d+)?|\d+-\d+)(")?',
        # Chinese pattern for overall score
        r'"总体打分":\s*(")?(\d+(\.\d+)?|\d+-\d+)(")?',
    ]
    
    try:
        overall_score = find_pattern_matches(patterns, data)
        return overall_score
    except Exception as e:
        print(f"Parsing error: {e}")
        return None


def extract_individual_scores(evaluation_text: str, checklist_items: list) -> dict:
    """
    Extract individual scores for each checklist item from the evaluation response.
    
    Parameters:
    - evaluation_text: The full evaluation text from the LLM
    - checklist_items: List of checklist items with 'title' and 'description'
    
    Returns:
    - Dictionary mapping checklist item titles to their scores
    """
    individual_scores = {}
    
    try:
        # First, try to extract JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', evaluation_text, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                # Extract scores for each checklist item
                for item in checklist_items:
                    title = item.get("title", "")
                    # Try exact title match
                    if title in json_data:
                        score_str = str(json_data[title]).strip('"\'')
                        try:
                            individual_scores[title] = float(score_str)
                        except:
                            individual_scores[title] = None
                    else:
                        # Try case-insensitive match
                        found = False
                        for key in json_data.keys():
                            if key.lower() == title.lower():
                                score_str = str(json_data[key]).strip('"\'')
                                try:
                                    individual_scores[title] = float(score_str)
                                except:
                                    individual_scores[title] = None
                                found = True
                                break
                        if not found:
                            individual_scores[title] = None
                return individual_scores
            except json.JSONDecodeError:
                pass
        
        # Fallback: Try to extract scores from text using patterns
        for idx, item in enumerate(checklist_items, 1):
            title = item.get("title", f"Item {idx}")
            # Try multiple patterns to find the score
            patterns = [
                # Pattern: "Title": "8" or "Title": 8
                rf'["\']?{re.escape(title)}["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?',
                # Pattern: Title - 8 or Title: 8
                rf'{re.escape(title)}\s*[-:]\s*(\d+(?:\.\d+)?)',
                # Pattern: 1. Title: 8
                rf'{idx}\.\s*{re.escape(title)}.*?[:]\s*(\d+(?:\.\d+)?)',
            ]
            
            score_found = None
            for pattern in patterns:
                match = re.search(pattern, evaluation_text, re.IGNORECASE)
                if match:
                    try:
                        score_found = float(match.group(1))
                        break
                    except:
                        continue
            
            individual_scores[title] = score_found
        
        return individual_scores
        
    except Exception as e:
        print(f"Error extracting individual scores: {e}")
        return {item.get("title", f"Item {i+1}"): None for i, item in enumerate(checklist_items)}


def format_checklist_for_prompt(checklist_items: list) -> str:
    """
    Format checklist items for the evaluation prompt.
    
    Args:
        checklist_items: List of checklist items with 'title' and 'description'
        
    Returns:
        Formatted checklist string
    """
    checklist_text = ""
    for idx, item in enumerate(checklist_items, 1):
        title = item.get("title", f"Item {idx}")
        description = item.get("description", "No description provided")
        # Format as numbered list with title and description
        checklist_text += f"{idx}. {title}: {description}\n"
    return checklist_text


def evaluate_with_checklist(
    generated_code: str, 
    checklist_items: list, 
    task_question: str,
    screenshot_paths: list = None,
    canvas_check_info: dict = None
) -> dict:
    """
    Evaluate generated code against checklist items using LLM.
    Uses official ArtifactsBenchmark prompt format.
    
    Args:
        generated_code: The generated HTML/CSS/JS code
        checklist_items: List of checklist items with 'title' and 'description'
        task_question: Original task question
        screenshot_paths: Optional list of screenshot file paths for multimodal evaluation
        canvas_check_info: Optional dict with canvas rendering check results
        
    Returns:
        Dictionary with evaluation results
    """
    if not checklist_items:
        return {
            "error": "No checklist items provided",
            "evaluation_text": "Cannot evaluate: no checklist items found",
            "overall_score": None
        }
    
    # Format checklist items for the prompt
    checklist_text = format_checklist_for_prompt(checklist_items)
    
    # Add canvas check information to the answer if available
    answer_text = generated_code
    if canvas_check_info and canvas_check_info.get("canvas_count", 0) > 0:
        canvas_warning = f"\n\n[IMPORTANT RENDERING CHECK]\n"
        canvas_warning += f"Canvas elements found: {canvas_check_info.get('canvas_count', 0)}\n"
        canvas_warning += f"Canvases with content: {canvas_check_info.get('canvases_with_content', 0)}\n"
        canvas_warning += f"Blank canvases: {canvas_check_info.get('blank_canvases', 0)}\n"
        if canvas_check_info.get('blank_canvases', 0) > 0:
            canvas_warning += "⚠ WARNING: One or more canvas elements are blank - the game/visualization may not be rendering properly.\n"
            canvas_warning += "This should be considered a significant issue in your evaluation.\n"
        answer_text = generated_code + canvas_warning
    
    # Build the evaluation prompt using official template
    evaluation_prompt = get_prompt_mllm_checklist(
        checklist=checklist_text,
        question=task_question,
        answer=answer_text
    )

    print("\n" + "="*80)
    print("EVALUATING AGAINST CHECKLIST (Official ArtifactsBenchmark Format)...")
    print("="*80)
    print(f"Evaluating {len(checklist_items)} checklist item(s)...")
    if screenshot_paths and USE_SCREENSHOTS_IN_EVAL:
        print(f"Including {len(screenshot_paths)} screenshot(s) in evaluation")
    
    try:
        # Prepare messages for evaluation
        messages = []
        
        # If screenshots are available and we want to use them, create a multimodal message
        if screenshot_paths and USE_SCREENSHOTS_IN_EVAL and len(screenshot_paths) > 0:
            # Check if model supports vision (gpt-4o, gpt-4-turbo, etc.)
            vision_models = ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "gpt-4.1-mini"]
            if any(model in MODEL_NAME.lower() for model in vision_models):
                # Create content array with text and images
                content = [{"type": "text", "text": evaluation_prompt}]
                
                # Add screenshots as base64 encoded images
                import base64
                for screenshot_path in screenshot_paths:
                    if os.path.exists(screenshot_path):
                        with open(screenshot_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            })
                
                messages.append({"role": "user", "content": content})
                print("✓ Using multimodal evaluation with screenshots")
            else:
                # Model doesn't support vision, use text-only
                messages.append({"role": "user", "content": evaluation_prompt})
                print("⚠ Model doesn't support vision, using text-only evaluation")
        else:
            # Text-only evaluation
            messages.append({"role": "user", "content": evaluation_prompt})
        
        # Use a single message with the full prompt (as per official format)
        eval_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0  # Low temperature for consistent evaluation
        )
        
        # Track token usage for evaluation (use global tracker)
        tracker = get_global_tracker()
        if tracker:
            tracker.track_response(eval_response, operation="evaluation", model=MODEL_NAME)
        
        evaluation_text = eval_response.choices[0].message.content
        
        # Extract individual scores for each checklist item
        individual_scores = extract_individual_scores(evaluation_text, checklist_items)
        
        # Calculate sum of individual scores programmatically
        calculated_sum = None
        valid_scores = [score for score in individual_scores.values() if score is not None]
        if valid_scores:
            calculated_sum = sum(valid_scores)
        
        # Extract overall score from JSON (official method)
        overall_score = extract_mllm_overall(evaluation_text)
        
        # Try to parse JSON if present
        json_score = None
        try:
            # Look for JSON block in the response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', evaluation_text, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(1))
                json_score = json_data.get("Overall Score") or json_data.get("总体打分")
                # Try to convert to float if it's a string
                if json_score:
                    try:
                        json_score = float(str(json_score).strip('"\''))
                    except:
                        pass
        except:
            pass
        
        # Use extracted score or JSON score, but prefer calculated sum if available
        final_overall_score = json_score if json_score is not None else overall_score
        if final_overall_score:
            try:
                final_overall_score = float(str(final_overall_score).strip('"\''))
            except:
                pass
        
        return {
            "evaluation_text": evaluation_text,
            "individual_scores": individual_scores,
            "calculated_sum": calculated_sum,
            "overall_score": final_overall_score,
            "num_items": len(checklist_items),
            "checklist_items": checklist_items
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "evaluation_text": f"Error during evaluation: {e}",
            "overall_score": None
        }

# Run checklist evaluation
if checklist_items:
    evaluation_result = evaluate_with_checklist(
        html_code, 
        checklist_items, 
        task0["question"],
        screenshot_paths=screenshot_paths if USE_SCREENSHOTS_IN_EVAL else None,
        canvas_check_info=canvas_check_info if canvas_check_info else None
    )
    
    print("\n" + "="*80)
    print("CHECKLIST EVALUATION RESULTS:")
    print("="*80)
    print(evaluation_result.get("evaluation_text", "No evaluation text available"))
    
    # Display individual scores
    individual_scores = evaluation_result.get("individual_scores", {})
    if individual_scores:
        print("\n" + "-"*80)
        print("INDIVIDUAL CHECKLIST SCORES:")
        print("-"*80)
        for item in checklist_items:
            title = item.get("title", "Unknown")
            score = individual_scores.get(title)
            if score is not None:
                print(f"  {title}: {score:.1f}")
            else:
                print(f"  {title}: Not found")
        print("-"*80)
    
    # Display calculated sum
    calculated_sum = evaluation_result.get("calculated_sum")
    if calculated_sum is not None:
        print(f"\nCalculated Sum (from individual scores): {calculated_sum:.1f}")
    
    # Display overall score (official ArtifactsBenchmark format)
    overall_score = evaluation_result.get("overall_score")
    if overall_score is not None:
        print(f"Overall Score (from LLM): {overall_score}")
        
        # Compare calculated sum with overall score
        if calculated_sum is not None:
            diff = abs(calculated_sum - float(overall_score))
            if diff > 0.1:  # Allow small floating point differences
                print(f"⚠ Note: Calculated sum ({calculated_sum:.1f}) differs from LLM's overall score ({overall_score})")
            else:
                print("✓ Calculated sum matches overall score")
    
    if not individual_scores and not overall_score and not evaluation_result.get("error"):
        print("\n⚠ Warning: Could not extract scores from evaluation response.")
        print("The model may not have followed the JSON format requirement.")
    
    if evaluation_result.get("error"):
        print(f"\n⚠ Error: {evaluation_result['error']}")
    
    print("="*80)
else:
    print("\n⚠ Skipping checklist evaluation: No checklist items found in dataset")

# Print token usage summary
print("\n" + "="*80)
print("TOKEN USAGE SUMMARY")
print("="*80)
token_tracker.print_summary()

# Save token usage to file in output directory and update history
if 'task_dir' in locals():
    token_usage_file = task_dir / "token_usage.json"
    token_tracker.save_to_file(str(token_usage_file))
    # Save experiment to history with experiment name using single judge evaluation file
    token_tracker.save_experiment_to_history(token_file=TOKEN_SINGLE_JUDGE_FILE)
    print(f"\n✓ Token usage saved to: {token_usage_file}")
    print(f"✓ Experiment token usage saved to: {TOKEN_SINGLE_JUDGE_FILE}")

# Screenshots are now captured automatically if ENABLE_SCREENSHOTS is True
# and can be included in evaluation if USE_SCREENSHOTS_IN_EVAL is True
#     from playwright.sync_api import sync_playwright
#     import os
    
#     print("\n" + "="*80)
#     print("PLAYWRIGHT RENDERING & SCREENSHOT CAPTURE")
#     print("="*80)
    
#     # Ask user preference (or set to False for headless, True for visible browser)
#     USE_HEADED_MODE = False  # Set to True to see the browser window
    
#     screenshot_dir = tempfile.mkdtemp(prefix="artifacts_screenshots_")
#     print(f"Screenshot directory: {screenshot_dir}")
    
#     with sync_playwright() as p:
#         # Launch browser - headless=False shows the browser window
#         print(f"Launching browser (headless={not USE_HEADED_MODE})...")
#         browser = p.chromium.launch(headless=not USE_HEADED_MODE)
        
#         # Create a new page
#         page = browser.new_page()
        
#         # Set viewport size (optional, for consistent screenshots)
#         page.set_viewport_size({"width": 1280, "height": 720})
        
#         # Load the HTML file
#         file_url = f"file://{html_file_path}"
#         print(f"Loading: {file_url}")
#         page.goto(file_url)
        
#         # Wait for page to load
#         page.wait_for_load_state("networkidle")
        
#         # Take initial screenshot
#         screenshot_path = os.path.join(screenshot_dir, "initial.png")
#         page.screenshot(path=screenshot_path)
#         print(f"✓ Screenshot saved: {screenshot_path}")
        
#         # Try to interact with common interactive elements
#         # This simulates what ArtifactsBench does
#         print("\nInteracting with page elements...")
        
#         # Try clicking buttons
#         buttons = page.query_selector_all("button")
#         if buttons:
#             print(f"Found {len(buttons)} button(s), clicking first button...")
#             try:
#                 buttons[0].click()
#                 page.wait_for_timeout(500)  # Wait 500ms for any animations
#                 screenshot_path = os.path.join(screenshot_dir, "after_click.png")
#                 page.screenshot(path=screenshot_path)
#                 print(f"✓ Screenshot after click: {screenshot_path}")
#             except Exception as e:
#                 print(f"  Could not click button: {e}")
        
#         # Try hovering over elements
#         hoverable = page.query_selector_all("a, button, [onclick], [onmouseover]")
#         if hoverable:
#             print(f"Found {len(hoverable)} hoverable element(s), hovering first...")
#             try:
#                 hoverable[0].hover()
#                 page.wait_for_timeout(300)
#                 screenshot_path = os.path.join(screenshot_dir, "after_hover.png")
#                 page.screenshot(path=screenshot_path)
#                 print(f"✓ Screenshot after hover: {screenshot_path}")
#             except Exception as e:
#                 print(f"  Could not hover: {e}")
        
#         # Wait a bit more to capture any animations
#         page.wait_for_timeout(1000)
#         screenshot_path = os.path.join(screenshot_dir, "final.png")
#         page.screenshot(path=screenshot_path)
#         print(f"✓ Final screenshot: {screenshot_path}")
        
#         # Get page title and some metadata
#         title = page.title()
#         print(f"\nPage title: {title}")
        
#         browser.close()
    
#     print(f"\n✓ All screenshots saved to: {screenshot_dir}")
#     print("="*80)
    
# except ImportError:
#     print("\n" + "="*80)
#     print("PLAYWRIGHT NOT AVAILABLE")
#     print("="*80)
#     print("To use Playwright for rendering and screenshots, install it:")
#     print("  pip install playwright")
#     print("  playwright install chromium")
#     print("="*80)
# except Exception as e:
#     print(f"\n⚠ Playwright error: {e}")
#     print("Continuing without Playwright screenshots...")