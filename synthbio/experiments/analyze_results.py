#!/usr/bin/env python3
"""
Analyze and compare experimental results.

Loads all experiment result files and generates comparison tables.
"""

import json
from pathlib import Path
from typing import List, Dict


def load_results(results_dir: Path) -> List[Dict]:
    """Load all experiment result files."""
    results = []
    
    # Load experiments in order (1-11: baseline, consensus, and voting experiments)
    for i in range(1, 12):
        result_files = list(results_dir.glob(f"exp{i}_*.json"))
        if result_files:
            with open(result_files[0]) as f:
                results.append(json.load(f))
    
    return results


def format_config_name(config: Dict) -> str:
    """Format configuration name with voting and consensus info."""
    if config['name'] == 'baseline':
        return "Baseline (1 agent)"
    
    parts = [f"{config['num_agents']} agents, {config['num_rounds']} rounds"]
    
    # Add voting info if present
    if config.get('voting'):
        voting_mode = config.get('voting_mode', 'unknown')
        if voting_mode == 'select_best':
            parts.append("✓ voting (select)")
        elif voting_mode == 'filter':
            top_n = config.get('top_n_voted')
            if top_n:
                parts.append(f"✓ voting (filter top {top_n})")
            else:
                parts.append("✓ voting (filter)")
        else:
            parts.append("✓ voting")
    
    # Add consensus info
    if config.get('consensus'):
        parts.append("✓ consensus")
    else:
        parts.append("no consensus")
    
    return ", ".join(parts)


def print_comparison_table(results: List[Dict]):
    """Print a formatted comparison table."""
    print("\n" + "=" * 100)
    print("EXPERIMENTAL RESULTS COMPARISON")
    print("=" * 100)
    
    # Print header
    print(f"{'Configuration':<35} {'ROUGE-L':>9} {'Faith.':>8} {'Hall.':>8} {'Cov.':>8} {'Time':>9}")
    print("-" * 100)
    
    # Print each experiment
    baseline_rouge = None
    for result in results:
        config = result['config']
        summary = result['summary']
        
        # Format configuration name
        if config['name'] == 'baseline':
            config_str = "Baseline (1 agent)"
            baseline_rouge = summary['avg_rouge_l']
        else:
            config_str = format_config_name(config)
        
        # Calculate improvement over baseline
        if baseline_rouge and config['name'] != 'baseline':
            improvement = summary['avg_rouge_l'] - baseline_rouge
            improvement_str = f" ({improvement:+.3f})"
        else:
            improvement_str = ""
        
        print(f"{config_str:<35} "
              f"{summary['avg_rouge_l']:>9.4f}{improvement_str:<10} "
              f"{summary['avg_faithfulness']:>8.4f} "
              f"{summary['avg_hallucination']:>8.4f} "
              f"{summary['avg_coverage']:>8.4f} "
              f"{summary['avg_time']:>7.1f}s")
    
    print("=" * 100)


def print_best_configs(results: List[Dict]):
    """Print best configurations for each metric."""
    print("\n" + "=" * 100)
    print("BEST CONFIGURATIONS")
    print("=" * 100)
    
    metrics = [
        ('avg_rouge_l', 'ROUGE-L (similarity to reference)', True),
        ('avg_faithfulness', 'Faithfulness (accuracy)', True),
        ('avg_coverage', 'Attribute Coverage (completeness)', True),
        ('avg_hallucination', 'Hallucination Score (lower is better)', False),
        ('avg_time', 'Average Time (lower is better)', False)
    ]
    
    for metric_key, metric_name, higher_better in metrics:
        if higher_better:
            best = max(results, key=lambda r: r['summary'][metric_key])
        else:
            best = min(results, key=lambda r: r['summary'][metric_key])
        
        config = best['config']
        value = best['summary'][metric_key]
        
        config_str = format_config_name(config)
        
        if metric_key == 'avg_time':
            value_str = f"{value:.1f}s"
        else:
            value_str = f"{value:.4f}"
        
        print(f"• {metric_name}:")
        print(f"  → {config_str}: {value_str}")
    
    print("=" * 100)


def print_key_findings(results: List[Dict]):
    """Print key findings from the experiments."""
    print("\n" + "=" * 100)
    print("KEY FINDINGS")
    print("=" * 100)
    
    # Get baseline
    baseline = next(r for r in results if r['config']['name'] == 'baseline')
    baseline_rouge = baseline['summary']['avg_rouge_l']
    baseline_faith = baseline['summary']['avg_faithfulness']
    
    # Find best multi-agent config
    multi_agent = [r for r in results if r['config']['name'] != 'baseline']
    best_multi = max(multi_agent, key=lambda r: r['summary']['avg_rouge_l'])
    
    print(f"\n1. Multi-Agent vs Baseline:")
    config = best_multi['config']
    config_str = format_config_name(config)
    improvement_rouge = best_multi['summary']['avg_rouge_l'] - baseline_rouge
    improvement_faith = best_multi['summary']['avg_faithfulness'] - baseline_faith
    
    print(f"   Best multi-agent: {config_str}")
    print(f"   ROUGE-L improvement: {improvement_rouge:+.4f} ({improvement_rouge/baseline_rouge*100:+.1f}%)")
    print(f"   Faithfulness improvement: {improvement_faith:+.4f} ({improvement_faith/baseline_faith*100:+.1f}%)")
    
    # Compare 2 vs 3 agents (no consensus)
    agents_2_no = next((r for r in results if r['config']['name'] == '2agents_no_consensus'), None)
    agents_3_no = next((r for r in results if r['config']['name'] == '3agents_no_consensus'), None)
    
    if agents_2_no and agents_3_no:
        print(f"\n2. Effect of Number of Agents (no consensus, no voting):")
        diff = agents_3_no['summary']['avg_rouge_l'] - agents_2_no['summary']['avg_rouge_l']
        print(f"   2 agents: {agents_2_no['summary']['avg_rouge_l']:.4f}")
        print(f"   3 agents: {agents_3_no['summary']['avg_rouge_l']:.4f}")
        print(f"   Difference: {diff:+.4f} ({'3 agents better' if diff > 0 else '2 agents better'})")
    
    # Compare consensus vs no consensus for 2 agents
    agents_2_no = next((r for r in results if r['config']['name'] == '2agents_no_consensus'), None)
    agents_2_yes = next((r for r in results if r['config']['name'] == '2agents_with_consensus'), None)
    
    if agents_2_no and agents_2_yes:
        print(f"\n3. Effect of Consensus (2 agents, no voting):")
        diff = agents_2_yes['summary']['avg_rouge_l'] - agents_2_no['summary']['avg_rouge_l']
        print(f"   Without consensus: {agents_2_no['summary']['avg_rouge_l']:.4f}")
        print(f"   With consensus: {agents_2_yes['summary']['avg_rouge_l']:.4f}")
        print(f"   Difference: {diff:+.4f} ({'consensus helps' if diff > 0 else 'consensus hurts'})")
    
    # Compare consensus vs no consensus for 3 agents
    agents_3_no = next((r for r in results if r['config']['name'] == '3agents_no_consensus'), None)
    agents_3_yes = next((r for r in results if r['config']['name'] == '3agents_with_consensus'), None)
    
    if agents_3_no and agents_3_yes:
        print(f"\n4. Effect of Consensus (3 agents, no voting):")
        diff = agents_3_yes['summary']['avg_rouge_l'] - agents_3_no['summary']['avg_rouge_l']
        print(f"   Without consensus: {agents_3_no['summary']['avg_rouge_l']:.4f}")
        print(f"   With consensus: {agents_3_yes['summary']['avg_rouge_l']:.4f}")
        print(f"   Difference: {diff:+.4f} ({'consensus helps' if diff > 0 else 'consensus hurts'})")
    
    # Compare voting-only vs consensus-only (2 agents)
    voting_2_select = next((r for r in results if r['config'].get('name') == '2agents_voting_select'), None)
    consensus_2 = next((r for r in results if r['config'].get('name') == '2agents_with_consensus'), None)
    
    if voting_2_select and consensus_2:
        print(f"\n5. Voting-only vs Consensus-only (2 agents):")
        print(f"   Voting (select): ROUGE-L={voting_2_select['summary']['avg_rouge_l']:.4f}, Faith={voting_2_select['summary']['avg_faithfulness']:.4f}")
        print(f"   Consensus: ROUGE-L={consensus_2['summary']['avg_rouge_l']:.4f}, Faith={consensus_2['summary']['avg_faithfulness']:.4f}")
        rouge_diff = voting_2_select['summary']['avg_rouge_l'] - consensus_2['summary']['avg_rouge_l']
        faith_diff = voting_2_select['summary']['avg_faithfulness'] - consensus_2['summary']['avg_faithfulness']
        print(f"   Difference: ROUGE-L {rouge_diff:+.4f}, Faithfulness {faith_diff:+.4f}")
    
    # Compare voting-only vs consensus-only (3 agents)
    voting_3_select = next((r for r in results if r['config'].get('name') == '3agents_voting_select'), None)
    consensus_3 = next((r for r in results if r['config'].get('name') == '3agents_with_consensus'), None)
    
    if voting_3_select and consensus_3:
        print(f"\n6. Voting-only vs Consensus-only (3 agents):")
        print(f"   Voting (select): ROUGE-L={voting_3_select['summary']['avg_rouge_l']:.4f}, Faith={voting_3_select['summary']['avg_faithfulness']:.4f}")
        print(f"   Consensus: ROUGE-L={consensus_3['summary']['avg_rouge_l']:.4f}, Faith={consensus_3['summary']['avg_faithfulness']:.4f}")
        rouge_diff = voting_3_select['summary']['avg_rouge_l'] - consensus_3['summary']['avg_rouge_l']
        faith_diff = voting_3_select['summary']['avg_faithfulness'] - consensus_3['summary']['avg_faithfulness']
        print(f"   Difference: ROUGE-L {rouge_diff:+.4f}, Faithfulness {faith_diff:+.4f}")
    
    # Compare voting+consensus vs consensus-only (2 agents)
    voting_consensus_2 = next((r for r in results if r['config'].get('name') == '2agents_voting_consensus'), None)
    
    if voting_consensus_2 and consensus_2:
        print(f"\n7. Voting+Consensus vs Consensus-only (2 agents):")
        print(f"   Voting+Consensus: ROUGE-L={voting_consensus_2['summary']['avg_rouge_l']:.4f}, Faith={voting_consensus_2['summary']['avg_faithfulness']:.4f}")
        print(f"   Consensus-only: ROUGE-L={consensus_2['summary']['avg_rouge_l']:.4f}, Faith={consensus_2['summary']['avg_faithfulness']:.4f}")
        rouge_diff = voting_consensus_2['summary']['avg_rouge_l'] - consensus_2['summary']['avg_rouge_l']
        faith_diff = voting_consensus_2['summary']['avg_faithfulness'] - consensus_2['summary']['avg_faithfulness']
        print(f"   Difference: ROUGE-L {rouge_diff:+.4f}, Faithfulness {faith_diff:+.4f}")
    
    # Compare voting+consensus vs consensus-only (3 agents)
    voting_consensus_3 = next((r for r in results if r['config'].get('name') == '3agents_voting_consensus'), None)
    
    if voting_consensus_3 and consensus_3:
        print(f"\n8. Voting+Consensus vs Consensus-only (3 agents):")
        print(f"   Voting+Consensus: ROUGE-L={voting_consensus_3['summary']['avg_rouge_l']:.4f}, Faith={voting_consensus_3['summary']['avg_faithfulness']:.4f}")
        print(f"   Consensus-only: ROUGE-L={consensus_3['summary']['avg_rouge_l']:.4f}, Faith={consensus_3['summary']['avg_faithfulness']:.4f}")
        rouge_diff = voting_consensus_3['summary']['avg_rouge_l'] - consensus_3['summary']['avg_rouge_l']
        faith_diff = voting_consensus_3['summary']['avg_faithfulness'] - consensus_3['summary']['avg_faithfulness']
        print(f"   Difference: ROUGE-L {rouge_diff:+.4f}, Faithfulness {faith_diff:+.4f}")
    
    print("\n" + "=" * 100)


def main():
    """Main entry point."""
    results_dir = Path(__file__).parent / "results"
    
    if not results_dir.exists():
        print(f"✗ Results directory not found: {results_dir}")
        print("  Run experiments first: python experiments/run_experiments.py")
        return
    
    # Load results
    results = load_results(results_dir)
    
    if not results:
        print(f"✗ No experiment results found in {results_dir}")
        return
    
    print(f"\nLoaded {len(results)} experiment results")
    
    # Print analysis
    print_comparison_table(results)
    print_best_configs(results)
    print_key_findings(results)
    
    print("\n✓ Analysis complete!")
    print(f"  Detailed results available in: {results_dir}")


if __name__ == "__main__":
    main()

