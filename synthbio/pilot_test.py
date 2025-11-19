#!/usr/bin/env python3
"""
Pilot Test for Biography Generation System

Tests the multi-agent debate system on a small sample of SynthBio data.

Usage:
    python pilot_test.py          # Normal mode (2 rounds, consensus enabled)
    python pilot_test.py --fast   # Fast mode (1 round, no consensus, ~2x faster)
    python pilot_test.py --dev    # Dev mode (uses small 20-entry dev set, instant loading)
    python pilot_test.py -f       # Short form for fast mode
    python pilot_test.py -d       # Short form for dev mode
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from synthbio.dataset_loader import SynthBioLoader
from synthbio.biography_debate import BiographyDebateSystem
from synthbio.evaluator import BiographyEvaluator


def format_attributes_for_display(attrs: dict) -> str:
    """Format attributes for display."""
    lines = []
    for key, value in attrs.items():
        if value:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def main():
    """Run pilot test."""
    # Start total timer
    total_start_time = time.time()
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in .env file")
        sys.exit(1)
    
    print("=" * 80)
    print("PILOT TEST: Multi-Agent Biography Generation")
    print("=" * 80)
    print()
    
    # Configuration
    import sys
    fast_mode = "--fast" in sys.argv or "-f" in sys.argv
    dev_mode = "--dev" in sys.argv or "-d" in sys.argv
    
    # Simple experiment: just 1 example for quick timing test
    num_test_examples = 1
    num_agents = 2
    num_rounds = 1 if fast_mode else 2
    use_consensus = not fast_mode  # Disable consensus in fast mode
    model = "gpt-4o-mini"  # Use cheaper model for testing
    
    # Dev mode uses small pre-extracted dataset for instant loading
    use_dev_set = dev_mode
    dev_set_file = Path(__file__).parent / "SynthBio_dev.json"
    
    print(f"Configuration:")
    print(f"  Test examples: {num_test_examples}")
    print(f"  Agents: {num_agents}")
    print(f"  Rounds: {num_rounds}")
    print(f"  Consensus: {'enabled' if use_consensus else 'disabled (fast mode)'}")
    print(f"  Model: {model}")
    print(f"  Dataset: {'Dev set (20 entries, instant load)' if use_dev_set else 'Full set (2237 entries, ~2s load)'}")
    if fast_mode:
        print(f"  ⚡ FAST MODE: Reduced rounds and no consensus for faster testing")
    if dev_mode:
        print(f"  🚀 DEV MODE: Using small dev dataset for instant loading")
    print()
    
    try:
        # Load dataset
        step_start = time.time()
        print("Initializing SynthBio dataset loader...")
        
        if use_dev_set:
            # Dev mode: Use pre-extracted small dataset for instant loading
            if not dev_set_file.exists():
                print(f"✗ Dev set not found: {dev_set_file}")
                print("  Run: python synthbio/create_dev_set.py --size 20")
                sys.exit(1)
            
            print(f"  Loading dev set from {dev_set_file.name}...")
            loader = SynthBioLoader()
            loader.cache_file = dev_set_file
            loader.count_cache_file = dev_set_file.with_suffix('.count')
            loader.load(lazy=False)  # Load all (only 20 entries, instant)
            dataset_init_time = time.time() - step_start
            print(f"✓ Dev set loaded: {len(loader.data)} entries ({dataset_init_time:.2f}s)")
            print()
            
            # Sample from dev set
            step_start = time.time()
            print(f"Sampling {num_test_examples} examples from dev set...")
            sample = loader.sample(num_test_examples, seed=42, lazy=False)
            sample_time = time.time() - step_start
            print(f"✓ Sampled {len(sample)} examples ({sample_time:.2f}s)")
        else:
            # Normal mode: Lazy load from full dataset
            print("  [DEBUG] Creating SynthBioLoader instance...")
            loader = SynthBioLoader()
            print("  [DEBUG] Calling load(lazy=True)...")
            loader.load(lazy=True)  # Don't load all entries, use lazy loading
            dataset_init_time = time.time() - step_start
            print(f"✓ Dataset loader ready ({dataset_init_time:.1f}s)")
            print()
            
            # Get sample (lazy loading - only loads sampled entries)
            step_start = time.time()
            print(f"Sampling {num_test_examples} examples (lazy loading)...")
            print("  [DEBUG] Calling sample()...")
            sample = loader.sample(num_test_examples, seed=42, lazy=True)
            sample_time = time.time() - step_start
            print(f"✓ Sampled {len(sample)} examples ({sample_time:.1f}s)")
        print()
        
        # Initialize systems
        step_start = time.time()
        print("Initializing biography generation system...")
        debate_system = BiographyDebateSystem(num_agents=num_agents, model=model, warmup=False)
        init_time = time.time() - step_start
        print(f"✓ Created {num_agents} agents ({init_time:.1f}s)")
        
        step_start = time.time()
        print("Initializing evaluator...")
        evaluator = BiographyEvaluator()
        eval_init_time = time.time() - step_start
        print(f"✓ Evaluator ready ({eval_init_time:.1f}s)")
        print()
        
        # Process each example
        results = []
        
        for idx, entry in enumerate(sample, 1):
            example_start_time = time.time()
            
            print("=" * 80)
            print(f"Example {idx}/{len(sample)}")
            print("=" * 80)
            
            # Extract data
            attrs = entry.get('attrs', {})
            references = entry.get('biographies', [])
            
            name = attrs.get('name', 'Unknown')
            print(f"Name: {name}")
            print(f"Attributes: {len(attrs)} fields")
            print(f"Reference biographies: {len(references)}")
            print()
            
            # Display key attributes
            print("Key Attributes:")
            key_attrs = ['name', 'gender', 'nationality', 'birth_date', 'occupation']
            for key in key_attrs:
                if key in attrs and attrs[key]:
                    print(f"  {key}: {attrs[key]}")
            print()
            
            # Generate biography with multi-agent system
            print("Generating biography with multi-agent system...")
            try:
                # Progress callback function
                def progress_update(message):
                    print(f"  {message}", flush=True)  # Flush to show progress immediately
                
                result = debate_system.generate_biography(
                    attrs, 
                    num_rounds=num_rounds, 
                    use_consensus=use_consensus,
                    progress_callback=progress_update
                )
                generated_bio = result['biography']
                consensus_info = f" (consensus: {result.get('biographies_merged', 1)} biographies merged)" if result.get('consensus_used', False) else " (no consensus)"
                print(f"✓ Generation complete{consensus_info}")
                print()
                
                # Generate baseline (single agent)
                print("Generating baseline (single agent)...")
                baseline_bio = debate_system.generate_single_agent_baseline(attrs)
                print("✓ Baseline complete")
                print()
                
                # Evaluate multi-agent result
                print("Evaluating multi-agent result...")
                multi_eval = evaluator.evaluate(generated_bio, attrs, references)
                
                # Evaluate baseline
                print("Evaluating baseline...")
                baseline_eval = evaluator.evaluate(baseline_bio, attrs, references)
                
                # Calculate example time
                example_elapsed = time.time() - example_start_time
                
                # Store results
                example_result = {
                    'name': name,
                    'generated': generated_bio,
                    'baseline': baseline_bio,
                    'references': references,
                    'multi_agent_eval': multi_eval,
                    'baseline_eval': baseline_eval,
                    'time_seconds': example_elapsed
                }
                results.append(example_result)
                
                print(f"\n⏱️  Example {idx} completed in {example_elapsed:.1f}s ({example_elapsed/60:.1f} minutes)")
                print()
                
                # Display results
                print("\n" + "-" * 80)
                print("EVALUATION RESULTS")
                print("-" * 80)
                print("\nMulti-Agent System:")
                print(f"  ROUGE-L: {multi_eval['rouge_l']:.4f}")
                print(f"  Faithfulness: {multi_eval['faithfulness']['score']:.4f}")
                print(f"  Hallucination Score: {multi_eval['hallucination_score']['score']:.4f}")
                print(f"  Attribute Coverage: {multi_eval['attribute_coverage']['coverage_ratio']:.4f}")
                
                print("\nBaseline (Single Agent):")
                print(f"  ROUGE-L: {baseline_eval['rouge_l']:.4f}")
                print(f"  Faithfulness: {baseline_eval['faithfulness']['score']:.4f}")
                print(f"  Hallucination Score: {baseline_eval['hallucination_score']['score']:.4f}")
                print(f"  Attribute Coverage: {baseline_eval['attribute_coverage']['coverage_ratio']:.4f}")
                
                print("\nGenerated Biography (Multi-Agent):")
                print("-" * 80)
                print(generated_bio[:500] + "..." if len(generated_bio) > 500 else generated_bio)
                print()
                
            except Exception as e:
                print(f"✗ Error processing example: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Calculate total time
        total_elapsed = time.time() - total_start_time
        
        # Summary statistics
        if results:
            print("\n" + "=" * 80)
            print("SUMMARY STATISTICS")
            print("=" * 80)
            
            print(f"\n⏱️  TOTAL TIME: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")
            print(f"   Examples processed: {len(results)}")
            if results:
                avg_time = sum(r.get('time_seconds', 0) for r in results) / len(results)
                print(f"   Average per example: {avg_time:.1f}s ({avg_time/60:.1f} minutes)")
            
            # Breakdown
            setup_time = dataset_init_time + sample_time + init_time + eval_init_time
            example_time = sum(r.get('time_seconds', 0) for r in results)
            overhead = total_elapsed - setup_time - example_time
            print(f"\n   Time breakdown:")
            print(f"   - Setup/initialization: {setup_time:.1f}s")
            print(f"   - Example processing: {example_time:.1f}s")
            print(f"   - Other overhead: {overhead:.1f}s")
            print()
            
            # Average metrics
            avg_multi_rouge = sum(r['multi_agent_eval']['rouge_l'] for r in results) / len(results)
            avg_baseline_rouge = sum(r['baseline_eval']['rouge_l'] for r in results) / len(results)
            
            avg_multi_faith = sum(r['multi_agent_eval']['faithfulness']['score'] for r in results) / len(results)
            avg_baseline_faith = sum(r['baseline_eval']['faithfulness']['score'] for r in results) / len(results)
            
            print(f"\nAverage ROUGE-L:")
            print(f"  Multi-Agent: {avg_multi_rouge:.4f}")
            print(f"  Baseline: {avg_baseline_rouge:.4f}")
            print(f"  Improvement: {avg_multi_rouge - avg_baseline_rouge:+.4f}")
            
            print(f"\nAverage Faithfulness:")
            print(f"  Multi-Agent: {avg_multi_faith:.4f}")
            print(f"  Baseline: {avg_baseline_faith:.4f}")
            print(f"  Improvement: {avg_multi_faith - avg_baseline_faith:+.4f}")
            
            # Save results
            results_file = Path(__file__).parent / "results" / "pilot_test_results.json"
            results_file.parent.mkdir(exist_ok=True)
            
            # Prepare results for JSON (remove non-serializable parts if any)
            json_results = []
            for r in results:
                json_results.append({
                    'name': r['name'],
                    'generated': r['generated'],
                    'baseline': r['baseline'],
                    'multi_agent_eval': r['multi_agent_eval'],
                    'baseline_eval': r['baseline_eval']
                })
            
            with open(results_file, 'w') as f:
                json.dump(json_results, f, indent=2)
            
            print(f"\n✓ Results saved to {results_file}")
        
        print("\n" + "=" * 80)
        print("✓ Pilot test completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

