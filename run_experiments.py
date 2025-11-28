#!/usr/bin/env python3
"""
Experiment Runner Script

This script provides a command-line interface for running voting and evaluation experiments.
"""

import argparse
import os
import sys
import json
from experiments import (
    VotingExperiments,
    SimpleMajorityVoting,
    BordaCountVoting,
    AverageScoreVoting,
    EloRatingSystem
)
from artifacts_debate import ArtifactsDebateSystem, load_sample_dataset_one_per_difficulty
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run voting and evaluation experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Run voting systems comparison
  python run_experiments.py --experiment voting_systems --num-judges 5
  
  # Run debate rounds experiment
  python run_experiments.py --experiment debate_rounds --rounds 3
  
  # Run agent pool scaling
  python run_experiments.py --experiment pool_scaling --pool-sizes 3 5 10
  
  # Run iterative voting tournament
  python run_experiments.py --experiment iterative --elimination-rounds 5
        """
    )
    
    parser.add_argument(
        "--experiment",
        type=str,
        required=True,
        choices=[
            "voting_systems",
            "debate_rounds",
            "pool_scaling",
            "iterative",
            "elo_pairwise",
            "quality_diversity",
            "all"
        ],
        help="Experiment to run"
    )
    
    parser.add_argument(
        "--num-judges",
        type=int,
        default=5,
        help="Number of judge agents (default: 5)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of debate rounds (for debate_rounds experiment, default: 2)"
    )
    
    parser.add_argument(
        "--pool-sizes",
        type=int,
        nargs="+",
        default=[3, 5, 10],
        help="Judge pool sizes to test (for pool_scaling experiment)"
    )
    
    parser.add_argument(
        "--elimination-rounds",
        type=int,
        default=3,
        help="Number of elimination rounds (for iterative experiment, default: 3)"
    )
    
    parser.add_argument(
        "--eliminate-per-round",
        type=int,
        default=1,
        help="Artifacts to eliminate per round (for iterative experiment, default: 1)"
    )
    
    parser.add_argument(
        "--artifacts-source",
        type=str,
        choices=["generate", "load"],
        default="generate",
        help="Source of artifacts: 'generate' creates new ones, 'load' uses existing (default: generate)"
    )
    
    parser.add_argument(
        "--artifacts-file",
        type=str,
        help="Path to JSON file with artifacts (if --artifacts-source is 'load')"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="experiment_results.json",
        help="Output file for results (default: experiment_results.json)"
    )
    
    return parser.parse_args()


def load_artifacts_from_file(filepath: str) -> list:
    """Load artifacts from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Handle different file formats
    if 'tasks' in data:
        # artifacts_results.json format
        return data['tasks']
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Unknown artifacts file format")


def generate_artifacts(num_artifacts: int = 3, difficulty: str = "easy") -> list:
    """
    Generate artifacts using the artifacts debate system.
    
    Args:
        num_artifacts: Number of artifacts to generate
        difficulty: Difficulty level (easy, medium, hard)
    """
    print(f"Generating {num_artifacts} artifacts (difficulty: {difficulty})...")
    
    # Load tasks from dataset
    try:
        if difficulty == "all":
            tasks = load_sample_dataset_one_per_difficulty()
        else:
            from artifacts_debate import load_artifacts_dataset
            tasks = load_artifacts_dataset(difficulty=difficulty, limit=num_artifacts)
    except:
        from artifacts_debate import SAMPLE_ARTIFACTS_TASKS
        tasks = SAMPLE_ARTIFACTS_TASKS[:num_artifacts]
    
    # Generate artifacts
    system = ArtifactsDebateSystem(num_agents=3, num_rounds=1, model="gpt-4o-mini")
    artifacts = []
    
    for i, task in enumerate(tasks[:num_artifacts], 1):
        print(f"\nGenerating artifact {i}/{num_artifacts}...")
        try:
            result = system.run_artifacts_task(
                task,
                generate_code=True,
                evaluate_code=False  # We'll evaluate in experiments
            )
            
            artifacts.append({
                "id": result['task']['id'],
                "task": result['task']['task'],
                "generated_code": result.get('generated_code', ''),
                "requirements": result['task'].get('requirements', []),
                "category": result['task'].get('category', 'Unknown'),
                "difficulty": result['task'].get('difficulty', 'unknown')
            })
        except Exception as e:
            print(f"Error generating artifact: {e}")
            continue
    
    return artifacts


def run_experiment(args):
    """Run the specified experiment."""
    # Load or generate artifacts
    if args.artifacts_source == "load" and args.artifacts_file:
        print(f"Loading artifacts from {args.artifacts_file}...")
        artifacts = load_artifacts_from_file(args.artifacts_file)
    else:
        # Generate artifacts
        artifacts = generate_artifacts(num_artifacts=3, difficulty="easy")
    
    if not artifacts:
        print("Error: No artifacts available for experiments")
        sys.exit(1)
    
    print(f"\nRunning experiments with {len(artifacts)} artifacts")
    print("=" * 80)
    
    # Initialize experiments system
    experiments = VotingExperiments(num_judges=args.num_judges, model=args.model)
    
    results = {}
    
    if args.experiment == "voting_systems" or args.experiment == "all":
        print("\n" + "=" * 80)
        print("EXPERIMENT 1: Voting Systems Comparison")
        print("=" * 80)
        voting_results = experiments.experiment_1_voting_systems(artifacts)
        results["voting_systems"] = voting_results
        
        # Print summary
        print("\nVoting Systems Results:")
        for system_name, result in voting_results.items():
            print(f"\n{system_name}:")
            print(f"  Top artifact: {max(result.rankings.items(), key=lambda x: x[1])[0]}")
            print(f"  Stability (avg std dev): {result.stability_metrics.get('average_std_dev', 0):.2f}")
            print(f"  Fairness (judge agreement): {result.fairness_metrics.get('average_judge_agreement', 0):.2f}")
    
    if args.experiment == "debate_rounds" or args.experiment == "all":
        print("\n" + "=" * 80)
        print("EXPERIMENT 2: Multi-Agent Debate Rounds")
        print("=" * 80)
        debate_result = experiments.experiment_2_debate_rounds(
            artifacts,
            num_debate_rounds=args.rounds
        )
        results["debate_rounds"] = debate_result
        
        print("\nDebate Rounds Results:")
        print(f"  Top artifact: {max(debate_result.rankings.items(), key=lambda x: x[1])[0]}")
        print(f"  Ranking correlation (initial vs final): {debate_result.stability_metrics.get('correlation', 0):.2f}")
    
    if args.experiment == "pool_scaling" or args.experiment == "all":
        print("\n" + "=" * 80)
        print("EXPERIMENT 4: Agent Pool Scaling Effects")
        print("=" * 80)
        scaling_results = experiments.experiment_4_agent_pool_scaling(
            artifacts,
            judge_pool_sizes=args.pool_sizes
        )
        results["pool_scaling"] = scaling_results
        
        print("\nPool Scaling Results:")
        for pool_size, result in scaling_results.items():
            print(f"\n{pool_size} judges:")
            print(f"  Agreement rate: {result.stability_metrics.get('agreement_rate', 0):.2%}")
            print(f"  Ranking noise: {result.volatility_metrics.get('ranking_noise', 0):.2f}")
    
    if args.experiment == "iterative" or args.experiment == "all":
        print("\n" + "=" * 80)
        print("EXPERIMENT 6: Iterative Multi-Round Voting")
        print("=" * 80)
        iterative_result = experiments.experiment_6_iterative_voting(
            artifacts,
            elimination_rounds=args.elimination_rounds,
            eliminate_per_round=args.eliminate_per_round
        )
        results["iterative_voting"] = iterative_result
        
        print("\nIterative Voting Results:")
        print(f"  Final winner: {max(iterative_result.rankings.items(), key=lambda x: x[1])[0]}")
        print(f"  Rounds completed: {len(iterative_result.raw_data.get('round_results', []))}")
    
    if args.experiment == "elo_pairwise" or args.experiment == "all":
        print("\n" + "=" * 80)
        print("EXPERIMENT 7: Elo Pairwise Comparisons")
        print("=" * 80)
        elo_result = experiments.experiment_7_elo_pairwise(artifacts)
        results["elo_pairwise"] = elo_result
        
        print("\nElo Pairwise Results:")
        print(f"  Top artifact: {max(elo_result.rankings.items(), key=lambda x: x[1])[0]}")
        print(f"  Elo rating range: {min(elo_result.rankings.values()):.1f} - {max(elo_result.rankings.values()):.1f}")
    
    # Save results
    experiments.save_results(results, args.output)
    
    print(f"\n{'=' * 80}")
    print(f"All experiments completed! Results saved to {args.output}")
    print("=" * 80)


def main():
    """Main execution function."""
    try:
        # Validate API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
            print("Please set your OpenAI API key:", file=sys.stderr)
            print("  export OPENAI_API_KEY='your-api-key-here'", file=sys.stderr)
            sys.exit(1)
        
        # Parse arguments
        args = parse_arguments()
        
        # Run experiment
        run_experiment(args)
        
    except KeyboardInterrupt:
        print("\n\nExperiments interrupted by user.", file=sys.stderr)
        sys.exit(130)
    
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

