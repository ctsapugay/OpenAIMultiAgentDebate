#!/usr/bin/env python3
"""
Analyze Pilot Test Results

Summarizes and visualizes results from the pilot test.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def analyze_results(results_file: Path) -> None:
    """Analyze and display results."""
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    if not results:
        print("No results to analyze")
        return
    
    print("=" * 80)
    print("PILOT TEST RESULTS ANALYSIS")
    print("=" * 80)
    print(f"\nTotal examples processed: {len(results)}\n")
    
    # Aggregate metrics
    multi_rouge_scores = [r['multi_agent_eval']['rouge_l'] for r in results]
    baseline_rouge_scores = [r['baseline_eval']['rouge_l'] for r in results]
    
    multi_faith_scores = [r['multi_agent_eval']['faithfulness']['score'] for r in results]
    baseline_faith_scores = [r['baseline_eval']['faithfulness']['score'] for r in results]
    
    multi_halluc_scores = [r['multi_agent_eval']['hallucination_score']['score'] for r in results]
    baseline_halluc_scores = [r['baseline_eval']['hallucination_score']['score'] for r in results]
    
    multi_coverage_scores = [r['multi_agent_eval']['attribute_coverage']['coverage_ratio'] for r in results]
    baseline_coverage_scores = [r['baseline_eval']['attribute_coverage']['coverage_ratio'] for r in results]
    
    # Compute averages
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0
    
    print("METRIC COMPARISON")
    print("-" * 80)
    print(f"{'Metric':<25} {'Multi-Agent':<15} {'Baseline':<15} {'Difference':<15}")
    print("-" * 80)
    
    avg_multi_rouge = avg(multi_rouge_scores)
    avg_baseline_rouge = avg(baseline_rouge_scores)
    print(f"{'ROUGE-L':<25} {avg_multi_rouge:<15.4f} {avg_baseline_rouge:<15.4f} {avg_multi_rouge - avg_baseline_rouge:+.4f}")
    
    avg_multi_faith = avg(multi_faith_scores)
    avg_baseline_faith = avg(baseline_faith_scores)
    print(f"{'Faithfulness':<25} {avg_multi_faith:<15.4f} {avg_baseline_faith:<15.4f} {avg_multi_faith - avg_baseline_faith:+.4f}")
    
    avg_multi_halluc = avg(multi_halluc_scores)
    avg_baseline_halluc = avg(baseline_halluc_scores)
    print(f"{'Hallucination Score':<25} {avg_multi_halluc:<15.4f} {avg_baseline_halluc:<15.4f} {avg_multi_halluc - avg_baseline_halluc:+.4f}")
    print("  (Lower is better)")
    
    avg_multi_coverage = avg(multi_coverage_scores)
    avg_baseline_coverage = avg(baseline_coverage_scores)
    print(f"{'Attribute Coverage':<25} {avg_multi_coverage:<15.4f} {avg_baseline_coverage:<15.4f} {avg_multi_coverage - avg_baseline_coverage:+.4f}")
    
    print("\n" + "=" * 80)
    print("DETAILED RESULTS BY EXAMPLE")
    print("=" * 80)
    
    for idx, result in enumerate(results, 1):
        print(f"\nExample {idx}: {result['name']}")
        print("-" * 80)
        print(f"Multi-Agent:")
        print(f"  ROUGE-L: {result['multi_agent_eval']['rouge_l']:.4f}")
        print(f"  Faithfulness: {result['multi_agent_eval']['faithfulness']['score']:.4f}")
        print(f"  Coverage: {result['multi_agent_eval']['attribute_coverage']['coverage_ratio']:.4f}")
        print(f"  Missing attributes: {len(result['multi_agent_eval']['attribute_coverage']['missing_attributes'])}")
        
        print(f"\nBaseline:")
        print(f"  ROUGE-L: {result['baseline_eval']['rouge_l']:.4f}")
        print(f"  Faithfulness: {result['baseline_eval']['faithfulness']['score']:.4f}")
        print(f"  Coverage: {result['baseline_eval']['attribute_coverage']['coverage_ratio']:.4f}")
        print(f"  Missing attributes: {len(result['baseline_eval']['attribute_coverage']['missing_attributes'])}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    improvements = {
        'rouge_l': avg_multi_rouge - avg_baseline_rouge,
        'faithfulness': avg_multi_faith - avg_baseline_faith,
        'hallucination': avg_baseline_halluc - avg_multi_halluc,  # Lower is better
        'coverage': avg_multi_coverage - avg_baseline_coverage
    }
    
    print(f"\nMulti-Agent system shows:")
    for metric, improvement in improvements.items():
        direction = "improvement" if improvement > 0 else "degradation"
        print(f"  {metric}: {improvement:+.4f} ({direction})")
    
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    results_file = Path(__file__).parent / "results" / "pilot_test_results.json"
    
    if not results_file.exists():
        print(f"Error: Results file not found at {results_file}")
        print("Please run pilot_test.py first")
    else:
        analyze_results(results_file)

