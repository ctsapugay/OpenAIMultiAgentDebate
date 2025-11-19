#!/usr/bin/env python3
"""
Quick test to measure dataset loading time only (no API calls)
"""

import time
import sys
from pathlib import Path

# Import directly to avoid loading other modules that need agents
sys.path.insert(0, str(Path(__file__).parent))
from dataset_loader import SynthBioLoader

print("=" * 80)
print("DATASET LOADING PERFORMANCE TEST")
print("=" * 80)
print()

# Test lazy loading
print("Test 1: Lazy loading with sample(1)")
print("-" * 80)
start = time.time()

loader = SynthBioLoader()
print("\nStep 1: loader.load(lazy=True)")
step_start = time.time()
loader.load(lazy=True)
print(f"  Time: {time.time() - step_start:.2f}s")

print("\nStep 2: loader.sample(1, seed=42, lazy=True)")
step_start = time.time()
sample = loader.sample(1, seed=42, lazy=True)
print(f"  Time: {time.time() - step_start:.2f}s")

total = time.time() - start
print(f"\n✓ Total time for lazy loading 1 sample: {total:.2f}s")
print()

# Show what we got
if sample:
    print("Sample entry:")
    entry = sample[0]
    attrs = entry.get('attrs', {})
    print(f"  Name: {attrs.get('name', 'Unknown')}")
    print(f"  Attributes: {len(attrs)} fields")
    print(f"  Biographies: {len(entry.get('biographies', []))} reference texts")

print()
print("=" * 80)
print("ANALYSIS")
print("=" * 80)
print()
print("If this test took more than a few seconds, the bottleneck is JSON parsing.")
print("The issue is on line 280 of dataset_loader.py:")
print("  data = json.load(f)  # Loads ENTIRE 5.4M JSON file")
print()
print("Even with 'lazy=True', Python's json.load() must parse the entire file")
print("to extract specific indices from the array.")
print()

