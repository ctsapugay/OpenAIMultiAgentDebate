#!/usr/bin/env python3
"""
Automated Experiment Runner for Multi-Agent Biography Generation

Runs a series of experiments to test:
1. Baseline (single agent)
2. Multi-agent debate without consensus (2 and 3 agents)
3. Multi-agent debate with consensus (2 and 3 agents)

All experiments use 2 examples from the dev set for speed.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path (now need to go up two levels)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from synthbio.dataset_loader import SynthBioLoader
from synthbio.biography_debate import BiographyDebateSystem
from synthbio.evaluator import BiographyEvaluator


class ExperimentRunner:
    """Runs and tracks experiments."""
    
    def __init__(self, num_examples=2, model="gpt-4o-mini", seed=42):
        """
        Initialize experiment runner.
        
        Args:
            num_examples: Number of examples to test (default: 2 for speed)
            model: Model to use for all experiments
            seed: Random seed for reproducibility
        """
        self.num_examples = num_examples
        self.model = model
        self.seed = seed
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Load environment
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Load dataset once
        print("Loading dev dataset...")
        self.loader = SynthBioLoader()
        dev_file = Path(__file__).parent.parent / "SynthBio_dev.json"
        self.loader.cache_file = dev_file
        self.loader.count_cache_file = dev_file.with_suffix('.count')
        self.loader.load(lazy=False)
        
        # Sample examples
        self.samples = self.loader.sample(num_examples, seed=seed, lazy=False)
        print(f"✓ Loaded {len(self.samples)} examples for testing\n")
        
        # Initialize evaluator
        self.evaluator = BiographyEvaluator()
    
    def run_baseline(self):
        """Run baseline experiment (single agent)."""
        print("=" * 80)
        print("EXPERIMENT 1: BASELINE (1 agent)")
        print("=" * 80)
        
        experiment_start = time.time()
        results = []
        
        # Create debate system (needs min 2 agents to initialize, but we only use baseline method)
        debate_system = BiographyDebateSystem(num_agents=2, model=self.model, warmup=False)
        
        for idx, entry in enumerate(self.samples, 1):
            print(f"\nExample {idx}/{len(self.samples)}: {entry['attrs']['name']}")
            
            attrs = entry['attrs']
            references = entry['biographies']
            
            # Generate biography with single agent
            start = time.time()
            biography = debate_system.generate_single_agent_baseline(attrs)
            gen_time = time.time() - start
            
            # Evaluate
            eval_result = self.evaluator.evaluate(biography, attrs, references)
            
            results.append({
                'name': attrs['name'],
                'biography': biography,
                'evaluation': eval_result,
                'time': gen_time
            })
            
            print(f"  Time: {gen_time:.1f}s | ROUGE-L: {eval_result['rouge_l']:.3f} | "
                  f"Faithfulness: {eval_result['faithfulness']['score']:.3f}")
        
        experiment_time = time.time() - experiment_start
        
        # Save results
        output = {
            'config': {
                'name': 'baseline',
                'num_agents': 1,
                'num_rounds': 1,
                'consensus': False,
                'model': self.model,
                'num_examples': self.num_examples,
                'seed': self.seed
            },
            'results': results,
            'summary': self._compute_summary(results),
            'total_time': experiment_time,
            'timestamp': datetime.now().isoformat()
        }
        
        output_file = self.results_dir / "exp1_baseline.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Experiment 1 complete in {experiment_time:.1f}s")
        print(f"  Avg ROUGE-L: {output['summary']['avg_rouge_l']:.3f}")
        print(f"  Results saved to {output_file.name}\n")
        
        return output
    
    def run_multi_agent_experiment(self, num_agents, num_rounds, use_consensus, exp_num, name):
        """
        Run a multi-agent experiment.
        
        Args:
            num_agents: Number of agents
            num_rounds: Number of debate rounds
            use_consensus: Whether to use consensus
            exp_num: Experiment number
            name: Experiment name for output file
        """
        print("=" * 80)
        consensus_str = "WITH consensus" if use_consensus else "NO consensus"
        print(f"EXPERIMENT {exp_num}: {num_agents} agents, {num_rounds} rounds, {consensus_str}")
        print("=" * 80)
        
        experiment_start = time.time()
        results = []
        
        # Create debate system
        debate_system = BiographyDebateSystem(num_agents=num_agents, model=self.model, warmup=False)
        
        for idx, entry in enumerate(self.samples, 1):
            print(f"\nExample {idx}/{len(self.samples)}: {entry['attrs']['name']}")
            
            attrs = entry['attrs']
            references = entry['biographies']
            
            # Generate biography
            start = time.time()
            result = debate_system.generate_biography(
                attrs,
                num_rounds=num_rounds,
                use_consensus=use_consensus,
                progress_callback=lambda msg: print(f"  {msg}")
            )
            gen_time = time.time() - start
            
            biography = result['biography']
            
            # Evaluate
            eval_result = self.evaluator.evaluate(biography, attrs, references)
            
            results.append({
                'name': attrs['name'],
                'biography': biography,
                'evaluation': eval_result,
                'time': gen_time,
                'transcript': result['transcript'],
                'consensus_used': result.get('consensus_used', False)
            })
            
            print(f"  Total time: {gen_time:.1f}s | ROUGE-L: {eval_result['rouge_l']:.3f} | "
                  f"Faithfulness: {eval_result['faithfulness']['score']:.3f}")
        
        experiment_time = time.time() - experiment_start
        
        # Save results
        output = {
            'config': {
                'name': name,
                'num_agents': num_agents,
                'num_rounds': num_rounds,
                'consensus': use_consensus,
                'model': self.model,
                'num_examples': self.num_examples,
                'seed': self.seed
            },
            'results': results,
            'summary': self._compute_summary(results),
            'total_time': experiment_time,
            'timestamp': datetime.now().isoformat()
        }
        
        output_file = self.results_dir / f"exp{exp_num}_{name}.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Experiment {exp_num} complete in {experiment_time:.1f}s")
        print(f"  Avg ROUGE-L: {output['summary']['avg_rouge_l']:.3f}")
        print(f"  Results saved to {output_file.name}\n")
        
        return output
    
    def _compute_summary(self, results):
        """Compute summary statistics."""
        n = len(results)
        
        return {
            'num_examples': n,
            'avg_rouge_l': sum(r['evaluation']['rouge_l'] for r in results) / n,
            'avg_faithfulness': sum(r['evaluation']['faithfulness']['score'] for r in results) / n,
            'avg_hallucination': sum(r['evaluation']['hallucination_score']['score'] for r in results) / n,
            'avg_coverage': sum(r['evaluation']['attribute_coverage']['coverage_ratio'] for r in results) / n,
            'avg_time': sum(r['time'] for r in results) / n,
            'total_time': sum(r['time'] for r in results)
        }
    
    def run_all_experiments(self):
        """Run all experiments in sequence."""
        print("\n" + "=" * 80)
        print("STARTING EXPERIMENTAL SUITE")
        print("=" * 80)
        print(f"Model: {self.model}")
        print(f"Examples per experiment: {self.num_examples}")
        print(f"Seed: {self.seed}")
        print(f"Results directory: {self.results_dir}")
        print("=" * 80 + "\n")
        
        total_start = time.time()
        all_results = []
        
        try:
            # Experiment 1: Baseline
            all_results.append(self.run_baseline())
            
            # Experiment 2: 2 agents, 2 rounds, NO consensus
            all_results.append(self.run_multi_agent_experiment(
                num_agents=2,
                num_rounds=2,
                use_consensus=False,
                exp_num=2,
                name="2agents_no_consensus"
            ))
            
            # Experiment 3: 3 agents, 2 rounds, NO consensus
            all_results.append(self.run_multi_agent_experiment(
                num_agents=3,
                num_rounds=2,
                use_consensus=False,
                exp_num=3,
                name="3agents_no_consensus"
            ))
            
            # Experiment 4: 2 agents, 2 rounds, WITH consensus
            all_results.append(self.run_multi_agent_experiment(
                num_agents=2,
                num_rounds=2,
                use_consensus=True,
                exp_num=4,
                name="2agents_with_consensus"
            ))
            
            # Experiment 5: 3 agents, 2 rounds, WITH consensus
            all_results.append(self.run_multi_agent_experiment(
                num_agents=3,
                num_rounds=2,
                use_consensus=True,
                exp_num=5,
                name="3agents_with_consensus"
            ))
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Experiments interrupted by user")
            print(f"Completed {len(all_results)}/5 experiments")
            return all_results
        except Exception as e:
            print(f"\n\n✗ Error during experiments: {e}")
            import traceback
            traceback.print_exc()
            return all_results
        
        total_time = time.time() - total_start
        
        # Save summary
        summary = {
            'experiments': [
                {
                    'name': r['config']['name'],
                    'config': r['config'],
                    'summary': r['summary']
                }
                for r in all_results
            ],
            'total_time': total_time,
            'completed': datetime.now().isoformat()
        }
        
        summary_file = self.results_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "=" * 80)
        print("ALL EXPERIMENTS COMPLETE!")
        print("=" * 80)
        print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"Results saved to: {self.results_dir}")
        print(f"\nRun 'python experiments/analyze_results.py' to view comparison")
        print("=" * 80 + "\n")
        
        return all_results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run multi-agent debate experiments")
    parser.add_argument("--num-examples", type=int, default=2,
                       help="Number of examples to test (default: 2)")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                       help="Model to use (default: gpt-4o-mini)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed (default: 42)")
    
    args = parser.parse_args()
    
    # Run experiments
    runner = ExperimentRunner(
        num_examples=args.num_examples,
        model=args.model,
        seed=args.seed
    )
    
    runner.run_all_experiments()


if __name__ == "__main__":
    main()

