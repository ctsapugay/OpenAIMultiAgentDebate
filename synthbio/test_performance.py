#!/usr/bin/env python3
"""
Quick performance test to verify dataset loading optimization.

This script demonstrates the performance improvement from count caching.

Usage:
    # First run - will be slower (count not cached)
    python test_performance.py
    
    # Second run - should be ~50% faster (count is cached)
    python test_performance.py
    
    # To reset and test again, delete SynthBio.count:
    rm SynthBio.count
"""

import time
from dataset_loader import SynthBioLoader
from pathlib import Path


def test_loading_performance():
    """Test dataset loading performance."""
    print("=" * 80)
    print("Dataset Loading Performance Test")
    print("=" * 80)
    print()
    
    # Check if count is already cached
    count_cache = Path(__file__).parent / "SynthBio.count"
    if count_cache.exists():
        print("⚠️  Count cache exists - this run should be FAST")
        print(f"   Delete {count_cache} to test first-run performance")
    else:
        print("ℹ️  Count cache doesn't exist - this will be the SLOW first run")
        print("   Run this script again to see the performance improvement!")
    print()
    
    # Test 1: Load with lazy mode and sample
    print("Test: Loading dataset and sampling 3 entries (lazy mode)")
    print("-" * 80)
    
    total_start = time.time()
    
    # Initialize loader
    print("1. Creating loader...")
    init_start = time.time()
    loader = SynthBioLoader()
    init_time = time.time() - init_start
    print(f"   ✓ Loader created ({init_time:.3f}s)")
    print()
    
    # Load (lazy)
    print("2. Loading dataset (lazy mode - should be instant)...")
    load_start = time.time()
    loader.load(lazy=True)
    load_time = time.time() - load_start
    print(f"   ✓ Dataset ready ({load_time:.3f}s)")
    print()
    
    # Sample
    print("3. Sampling 3 entries...")
    print("   This is where the main work happens:")
    sample_start = time.time()
    sample = loader.sample(3, seed=42, lazy=True)
    sample_time = time.time() - sample_start
    print(f"   ✓ Sampled {len(sample)} entries ({sample_time:.3f}s)")
    print()
    
    total_time = time.time() - total_start
    
    # Results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total time: {total_time:.3f}s")
    print(f"  - Initialization: {init_time:.3f}s")
    print(f"  - Load (lazy): {load_time:.3f}s")
    print(f"  - Sampling: {sample_time:.3f}s")
    print()
    
    # Check if count was cached
    if count_cache.exists():
        print("✓ Count cache file exists")
        print("  Next run should be faster (count reading is instant)")
    else:
        print("⚠️  Count cache file not created")
        print("  Something may be wrong with the caching implementation")
    print()
    
    # Display sample info
    print("Sample data:")
    for i, entry in enumerate(sample, 1):
        attrs = entry.get('attrs', {})
        name = attrs.get('name', 'Unknown')
        print(f"  {i}. {name}")
    print()
    
    print("=" * 80)
    if count_cache.exists() and count_cache.stat().st_mtime > total_start:
        print("ℹ️  This was the FIRST run - count was just cached")
        print("   Run this script again to see the performance improvement!")
    else:
        print("ℹ️  Count was already cached - this was a FAST run")
        print("   To test first-run performance, delete SynthBio.count and run again")
    print("=" * 80)


if __name__ == "__main__":
    test_loading_performance()

