#!/usr/bin/env python3
"""
Multi-Agent Debate System - CLI Entry Point

This script provides a command-line interface for running multi-agent debates
using the OpenAI Agents SDK with token tracking and optional consensus.
"""

import argparse
import os
import sys
from token_tracking import TokenTrackingDebateSystem
from consensus_system import ConsensusSystem
from test_mmlu import MMLUDebateTest, SAMPLE_MMLU_QUESTIONS
from artifacts_debate import ArtifactsDebateSystem, SAMPLE_ARTIFACTS_TASKS


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Run a multi-agent debate on a specified topic with token tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Regular debate with token tracking (default)
  python main.py --topic "Should AI systems be open source?"
  
  # Debate with consensus generation
  python main.py --topic "Climate change solutions" --consensus --agents 5 --rounds 3
  
  # Run MMLU test suite
  python main.py --topic MMLU --agents 3 --rounds 2
  
  # Run ArtifactsBench task (code generation)
  python main.py --topic ARTIFACTS --agents 3 --rounds 2
  
  # MMLU or Artifacts with consensus
  python main.py --topic MMLU --consensus
  python main.py --topic ARTIFACTS --consensus
        """
    )
    
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help='The debate topic, "MMLU" for MMLU tests, or "ARTIFACTS" for ArtifactsBench tasks (required)'
    )
    
    parser.add_argument(
        "--consensus",
        action="store_true",
        help="Generate consensus after debate (optional)"
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


def run_mmlu_mode(args):
    """Run MMLU test suite."""
    print("Running MMLU Test Suite...")
    print()
    
    # Create MMLU test instance
    test = MMLUDebateTest(
        num_agents=args.agents,
        num_rounds=args.rounds,
        model=args.model
    )
    
    # Run test suite with consensus if requested
    summary = test.run_test_suite(
        questions=[SAMPLE_MMLU_QUESTIONS[0]],
        use_consensus=args.consensus,
        track_tokens=True  # Always track tokens
    )
    
    # Save results
    test.save_results("mmlu_debate_results.json")
    
    print(f"\n✓ Results saved to mmlu_debate_results.json")


def run_artifacts_mode(args):
    """Run ArtifactsBench task suite."""
    print("Running ArtifactsBench Task Suite...")
    print()
    
    # Create artifacts debate system
    system = ArtifactsDebateSystem(
        num_agents=args.agents,
        num_rounds=args.rounds,
        model=args.model
    )
    
    # Run single task demo (bouncing ball - simplest example)
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
    system.save_results(single_result_summary, "artifacts_results.json")
    
    print(f"\n✓ Results saved to artifacts_results.json")


def run_debate_mode(args):
    """Run regular debate on a specific topic."""
    print("Starting debate...")
    print()
    
    # Create token tracking debate system (always enabled)
    debate_system = TokenTrackingDebateSystem(
        num_agents=args.agents,
        model=args.model
    )
    
    if args.consensus:
        # Run with consensus
        consensus_system = ConsensusSystem(debate_system)
        result = consensus_system.run_debate_with_consensus(
            topic=args.topic,
            num_rounds=args.rounds
        )
        
        # Print transcript
        print()
        print(result['transcript'])
        
        # Print consensus
        print()
        print("=" * 80)
        print("CONSENSUS")
        print("=" * 80)
        print()
        print(result['consensus'])
        print()
        print("=" * 80)
    else:
        # Run without consensus
        result = debate_system.run_debate(
            topic=args.topic,
            num_rounds=args.rounds
        )
        
        # Print transcript
        print()
        print(result['transcript'])
    
    # Always print token usage summary
    print()
    debate_system.print_usage_summary()


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
        
        # Determine mode
        topic_upper = args.topic.upper()
        if topic_upper == 'MMLU':
            mode = 'MMLU Test Suite'
        elif topic_upper == 'ARTIFACTS':
            mode = 'ArtifactsBench Tasks'
        else:
            mode = 'Debate'
        
        print(f"Mode: {mode}")
        print(f"Topic: {args.topic}")
        print(f"Agents: {args.agents}")
        print(f"Rounds: {args.rounds}")
        print(f"Model: {args.model}")
        print(f"Token Tracking: Enabled (default)")
        print(f"Consensus: {'Enabled' if args.consensus else 'Disabled'}")
        print("=" * 80)
        print()
        
        # Route to appropriate mode
        if topic_upper == "MMLU":
            run_mmlu_mode(args)
        elif topic_upper == "ARTIFACTS":
            run_artifacts_mode(args)
        else:
            print("Initializing debate system...")
            print(f"Created {args.agents} agents successfully.")
            print()
            run_debate_mode(args)
        
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
