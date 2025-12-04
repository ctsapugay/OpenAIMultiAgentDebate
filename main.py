"""
Multi-Agent Debate System - CLI Entry Point
"""

import argparse
import os
import sys
from debate_system import DebateSystem
from dotenv import load_dotenv
load_dotenv()

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a multi-agent creative writing judge system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python main.py --topic "Story A: ... Story B: ..."
  python main.py --topic "..." --agents 5 --rounds 2
  python main.py --topic "..." --model gpt-4o-mini --output run1.json
        """
    )

    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="The story pair or writing task to evaluate"
    )

    parser.add_argument(
        "--agents",
        type=int,
        default=3,
        help="Number of agents (default 3)"
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Number of rounds (default 1)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model to use"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="debate_output.json",
        help="Where to save results"
    )

    return parser.parse_args()


def main():
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
            sys.exit(1)

        args = parse_arguments()

        if not args.topic.strip():
            print("Error: Topic cannot be empty.", file=sys.stderr)
            sys.exit(1)

        if args.agents < 1:
            print("Error: Must have at least 1 agent.", file=sys.stderr)
            sys.exit(1)

        if args.rounds < 1:
            print("Error: Must have at least 1 round.", file=sys.stderr)
            sys.exit(1)

        print("=" * 80)
        print("MULTI-AGENT LITERARY JUDGE SYSTEM")
        print("=" * 80)
        print(f"Topic: {args.topic}")
        print(f"Agents: {args.agents}")
        print(f"Rounds: {args.rounds}")
        print(f"Model: {args.model}")
        print(f"Saving output to: {args.output}")
        print("=" * 80)
        print("\nInitializing...\n")

        debate_system = DebateSystem(num_agents=args.agents, model=args.model)

        print("Starting evaluation...\n")

        results = debate_system.run_debate(
            topic=args.topic,
            num_rounds=args.rounds,
            output_path=args.output
        )

        print("Evaluation complete!")
        print(f"Total tokens used: {results['total_tokens']}")
        print(f"Saved to: {args.output}")

    except KeyboardInterrupt:
        print("\nInterrupted by user, exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
