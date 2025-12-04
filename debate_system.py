import json
import datetime
from openai import OpenAI

class DebateSystem:
    def __init__(self, num_agents=3, model="gpt-4o-mini"):
        self.num_agents = num_agents
        self.model = model
        self.client = OpenAI()
        self.agents = [f"Agent_{i+1}" for i in range(num_agents)]

    def run_debate(self, topic, num_rounds=1, output_path="debate_output.json"):
        transcript = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        system_prompt = """
You are a literary judge evaluating two short stories.

Your task is to decide which story is better based on:
- creativity
- narrative coherence
- emotional impact
- writing quality

You may write a short explanation if you want.
BUT the last line of your response MUST be exactly one of these:
Final choice: Story A
Final choice: Story B
""".strip()

        for round_id in range(1, num_rounds + 1):
            for agent_name in self.agents:

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": topic}
                    ]
                )

                # FIXED: correct extraction of message text
                msg = response.choices[0].message.content

                # FIXED: correct usage fields
                usage = response.usage
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens

                transcript.append({
                    "round": round_id,
                    "agent": agent_name,
                    "message": msg
                })

        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "topic": topic,
            "model": self.model,
            "num_agents": self.num_agents,
            "num_rounds": num_rounds,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "transcript": transcript
        }

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        return results
