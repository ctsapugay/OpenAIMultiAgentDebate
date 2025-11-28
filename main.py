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
from artifacts_debate import (
    ArtifactsDebateSystem,
    SAMPLE_ARTIFACTS_TASKS,
    load_artifacts_dataset,
    load_sample_dataset_one_per_difficulty,
)

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

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
  
  # Run ArtifactsBench with specific difficulty
  python main.py --topic ARTIFACTS --difficulty easy
  python main.py --topic ARTIFACTS --difficulty medium
  python main.py --topic ARTIFACTS --difficulty hard
  
  # Run all difficulties (default for ARTIFACTS)
  python main.py --topic ARTIFACTS
  
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
    
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard", "all"],
        default=None,
        help='For ARTIFACTS mode: select difficulty level ("easy", "medium", "hard") or "all" for all three. Default: "all"'
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
    
    # Determine which difficulty to load
    difficulty = args.difficulty
    if difficulty is None or difficulty == "all":
        # Load one task from each difficulty level
        print("Loading sample dataset (one task per difficulty: easy, medium, hard)...")
        try:
            sample_tasks = load_sample_dataset_one_per_difficulty()
            if not sample_tasks:
                raise ValueError("No tasks loaded from dataset")
            print(f"✓ Successfully loaded {len(sample_tasks)} tasks from ArtifactsBench dataset\n")
        except Exception as e:
            print(f"Warning: Unable to load Hugging Face dataset ({e}).")
            print("Using built-in sample tasks instead.\n")
            # Use first 3 tasks from fallback (should cover different difficulties)
            sample_tasks = SAMPLE_ARTIFACTS_TASKS[:3]
    else:
        # Load tasks for specific difficulty
        print(f"Loading tasks with difficulty: {difficulty.upper()}...")
        try:
            sample_tasks = load_artifacts_dataset(difficulty=difficulty, limit=1)
            if not sample_tasks:
                raise ValueError(f"No tasks found for difficulty: {difficulty}")
            print(f"✓ Successfully loaded 1 task ({difficulty.upper()}) from ArtifactsBench dataset\n")
        except Exception as e:
            print(f"Warning: Unable to load Hugging Face dataset ({e}).")
            print("Using built-in sample tasks instead.\n")
            # Find a task with matching difficulty from fallback
            sample_tasks = [t for t in SAMPLE_ARTIFACTS_TASKS if t.get('difficulty', '').lower() == difficulty.lower()]
            if not sample_tasks:
                # If no match, use first task
                sample_tasks = SAMPLE_ARTIFACTS_TASKS[:1]
    
    # Run all tasks in the sample dataset
    results = []
    for i, task in enumerate(sample_tasks, 1):
        print(f"\n{'='*80}")
        if len(sample_tasks) == 1:
            print(f"TASK: {task['difficulty'].upper()} - {task['category']}")
        else:
            print(f"TASK {i}/{len(sample_tasks)}: {task['difficulty'].upper()} - {task['category']}")
        print(f"{'='*80}")
        
        try:
            result = system.run_artifacts_task(
                task,
                generate_code=True,
                evaluate_code=True
            )
            results.append(result)
        except Exception as e:
            print(f"Error processing task: {e}")
            results.append({
                "task": task,
                "error": str(e)
            })
    
    # Calculate summary statistics
    total_tokens = sum(r.get('token_usage', {}).get('total_tokens', 0) for r in results if 'token_usage' in r)
    avg_scores = [r.get('evaluation', {}).get('average_score', 0) for r in results if 'evaluation' in r]
    avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
    
    summary = {
        "total_tasks": len(sample_tasks),
        "successful_tasks": len([r for r in results if 'error' not in r]),
        "total_tokens": total_tokens,
        "average_evaluation_score": avg_score,
        "results": results
    }
    
    # Save results
    system.save_results(summary, "artifacts_results.json")
    
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
        if topic_upper == 'ARTIFACTS':
            difficulty_display = args.difficulty if args.difficulty else "all"
            print(f"Difficulty: {difficulty_display.upper()}")
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
