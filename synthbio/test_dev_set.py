#!/usr/bin/env python3
"""
Test loading performance: Full dataset vs Dev set
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dataset_loader import SynthBioLoader

print("=" * 80)
print("COMPARING: Full Dataset vs Dev Set Loading Time")
print("=" * 80)
print()

# Test 1: Full dataset with lazy loading
print("Test 1: Full dataset (5.4 MB, 2237 entries)")
print("-" * 80)
start = time.time()
loader_full = SynthBioLoader()
loader_full.load(lazy=True)
sample_full = loader_full.sample(1, seed=42, lazy=True)
time_full = time.time() - start
print(f"✓ Time: {time_full:.3f}s")
print()

# Test 2: Dev set
print("Test 2: Dev set (61.8 KB, 20 entries)")
print("-" * 80)
start = time.time()
loader_dev = SynthBioLoader()
dev_file = Path(__file__).parent / "SynthBio_dev.json"
loader_dev.cache_file = dev_file
loader_dev.count_cache_file = dev_file.with_suffix('.count')
loader_dev.load(lazy=False)  # Load all 20 entries
sample_dev = loader_dev.sample(1, seed=42, lazy=False)
time_dev = time.time() - start
print(f"✓ Time: {time_dev:.3f}s")
print()

# Comparison
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"Full dataset: {time_full:.3f}s")
print(f"Dev set:      {time_dev:.3f}s")
print(f"Speedup:      {time_full/time_dev:.1f}x faster")
print()
print("✅ Use --dev flag in pilot_test.py to use the fast dev set!")
print()

