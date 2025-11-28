#load artifactsbench dataset
import datasets

# ============================================================================
# CONFIGURATION
# ============================================================================
# Model selection - choose the model you want to use:
# - "gpt-4o-mini" - GPT-4o mini (cost-effective, widely available)
# - "gpt-4o" - Full GPT-4o (more capable, higher cost)
# - "gpt-4.1-mini" - GPT-4.1 mini (newer, check availability in your region)
# - "gpt-4-turbo" - GPT-4 Turbo
MODEL_NAME = "gpt-4.1-mini"  # Change this to switch models

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
print()

# Generate code using the ArtifactsBench prompt format
from openai import OpenAI

client = OpenAI()

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

# Save HTML to a temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(html_code)
    html_file_path = f.name

print(f"\nHTML saved to: {html_file_path}")
print("Opening in browser...")

# Open in the default web browser
# webbrowser.open(f'file://{html_file_path}')

# Optional: Use Playwright to render and capture screenshots (like ArtifactsBench)
# This demonstrates both headless and headed modes
# try:
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