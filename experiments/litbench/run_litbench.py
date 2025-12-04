import json
import datetime
import os
from openai import OpenAI


# ================================
# Path Setup
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_DIR = os.path.join(BASE_DIR, "prompts")
RESULT_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULT_DIR, exist_ok=True)


# ================================
# Prompt Loader
# ================================
def load_prompt_file():
    prompt_files = sorted(f for f in os.listdir(PROMPT_DIR) if f.endswith(".txt"))

    if not prompt_files:
        raise FileNotFoundError("No .txt files found in prompts/ folder.")

    print("\nAvailable prompt files:")
    for idx, name in enumerate(prompt_files, 1):
        print(f"{idx}. {name}")

    while True:
        try:
            selection = int(input("\nChoose a prompt number: ")) - 1
            chosen = prompt_files[selection]
            break
        except (ValueError, IndexError):
            print("Invalid choice — try again.")

    prompt_path = os.path.join(PROMPT_DIR, chosen)

    with open(prompt_path, "r") as f:
        content = f.read()

    print(f"\nLoaded: {chosen}")
    return content, chosen


# ================================
# DebateSystem Class
# ================================
class DebateSystem:
    def __init__(self, num_agents=2, num_rounds=3, model="gpt-4o-mini"):
        self.num_agents = num_agents
        self.num_rounds = num_rounds
        self.model = model
        self.client = OpenAI()
        self.agents = [f"Agent_{i+1}" for i in range(num_agents)]

    def run(self, story_pair_text, output_file):
        transcript = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        system_prompt = (
            "You are a literary judge evaluating two short stories.\n\n"
            "You must decide which story is better based on:\n"
            "- creativity\n"
            "- narrative coherence\n"
            "- emotional impact\n"
            "- writing quality\n\n"
            "You may explain your reasoning, but your FINAL LINE must be:\n"
            "Final choice: Story A\n"
            "or\n"
            "Final choice: Story B"
        )

        for round_id in range(1, self.num_rounds + 1):
            for agent in self.agents:

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": story_pair_text}
                    ]
                )

                msg = response.choices[0].message.content

                usage = response.usage
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens

                transcript.append({
                    "round": round_id,
                    "agent": agent,
                    "message": msg
                })

        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": self.model,
            "num_agents": self.num_agents,
            "num_rounds": self.num_rounds,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "topic": story_pair_text,
            "transcript": transcript
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nSaved results to {output_file}")
        return results


# ================================
# Main Interactive Runner
# ================================
if __name__ == "__main__":
    print("\n=== LitBench Multi-Agent Runner ===")

    # 1. Let user choose model
    model = input("\nEnter model (default gpt-4o-mini): ").strip()
    if model == "":
        model = "gpt-4o-mini"

    # 2. Let user choose number of agents
    try:
        agents = int(input("Enter number of agents (default 2): "))
    except:
        agents = 2

    # 3. Let user choose number of rounds
    try:
        rounds = int(input("Enter number of rounds (default 3): "))
    except:
        rounds = 3

    # 4. Select a prompt file
    prompt_text, prompt_filename = load_prompt_file()

    # 5. Output file naming
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"litbench_{prompt_filename.replace('.txt','')}_{timestamp}.json"
    output_path = os.path.join(RESULT_DIR, output_name)

    # 6. Run system
    system = DebateSystem(num_agents=agents, num_rounds=rounds, model=model)
    system.run(prompt_text, output_path)
