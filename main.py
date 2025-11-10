#!/usr/bin/env python3
"""
Multi-Agent Debate System - CLI Entry Point

This script provides a command-line interface for running multi-agent debates
using the OpenAI Agents SDK.
"""

import argparse
import os
import sys
from debate_system import DebateSystem


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Run a multi-agent debate on a specified topic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python main.py --topic "Should AI systems be open source?"
  python main.py --topic "Climate change solutions" --agents 5 --rounds 3
  python main.py --topic "Future of work" --model gpt-4o-mini
        """
    )
    
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="The debate topic (required)"
    )
    
    parser.add_argument(
        "--agents",
        type=int,
        default=3,
        help="Number of agents to participate in the debate (default: 3)"
    )
    
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of debate rounds (default: 2)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="OpenAI model to use (default: gpt-4)"
    )
    
    return parser.parse_args()


def main():
    """Main execution function for the debate system CLI."""
    try:
        # Validate OPENAI_API_KEY environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
            print("Please set your OpenAI API key:", file=sys.stderr)
            print("  export OPENAI_API_KEY='your-api-key-here'", file=sys.stderr)
            sys.exit(1)
        
        # Parse command-line arguments
        args = parse_arguments()
        
        # Validate inputs
        if not args.topic.strip():
            print("Error: Topic cannot be empty.", file=sys.stderr)
            sys.exit(1)
        
        if args.agents < 2:
            print(f"Error: Number of agents must be at least 2 (got {args.agents}).", file=sys.stderr)
            sys.exit(1)
        
        if args.rounds < 1:
            print(f"Error: Number of rounds must be at least 1 (got {args.rounds}).", file=sys.stderr)
            sys.exit(1)
        
        # Display configuration
        print("=" * 80)
        print("MULTI-AGENT DEBATE SYSTEM")
        print("=" * 80)
        print(f"Topic: {args.topic}")
        print(f"Agents: {args.agents}")
        print(f"Rounds: {args.rounds}")
        print(f"Model: {args.model}")
        print("=" * 80)
        print()
        
        # Instantiate DebateSystem with parsed configuration
        print("Initializing debate system...")
        debate_system = DebateSystem(num_agents=args.agents, model=args.model)
        print(f"Created {args.agents} agents successfully.")
        print()
        
        # Display progress indicators during execution
        print("Starting debate...")
        print()
        
        # Call run_debate with topic and rounds
        transcript = debate_system.run_debate(topic=args.topic, num_rounds=args.rounds)
        
        # Print final transcript to console
        print()
        print(transcript)
        
    except ValueError as e:
        # Handle validation errors
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        # Handle user interruption gracefully
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(130)
    
    except Exception as e:
        # Handle API errors and other unexpected errors
        print(f"Error: An unexpected error occurred: {str(e)}", file=sys.stderr)
        print("Please check your API key and network connection.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
