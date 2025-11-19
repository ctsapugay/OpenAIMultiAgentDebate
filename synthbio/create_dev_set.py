#!/usr/bin/env python3
"""
Create a small development dataset for fast testing.
This extracts a subset of SynthBio for quick iteration without loading the full 5.4MB file.
"""

import json
import sys
from pathlib import Path

# Import directly
sys.path.insert(0, str(Path(__file__).parent))
from dataset_loader import SynthBioLoader

def create_dev_set(size=10, output_file="SynthBio_dev.json", seed=42):
    """
    Create a small development dataset.
    
    Args:
        size: Number of entries to extract
        output_file: Output filename
        seed: Random seed for reproducibility
    """
    print(f"Creating development dataset with {size} entries...")
    
    # Load full dataset and sample
    loader = SynthBioLoader()
    
    # First time: load full dataset (this is slow, but only done once)
    print("  Loading full dataset (this will be slow the first time)...")
    sample = loader.sample(size, seed=seed, lazy=True)
    
    # Save to new file
    output_path = Path(__file__).parent / output_file
    print(f"  Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample, f, indent=2)
    
    # Create count cache for dev set
    count_file = output_path.with_suffix('.count')
    with open(count_file, 'w') as f:
        f.write(str(len(sample)))
    
    print(f"✓ Created {output_file} with {len(sample)} entries")
    print(f"✓ Created {count_file.name} cache file")
    print()
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    print()
    print("Usage in your tests:")
    print(f'  loader = SynthBioLoader()')
    print(f'  loader.cache_file = Path("{output_file}")')
    print(f'  loader.count_cache_file = Path("{count_file.name}")')
    print(f'  data = loader.load(lazy=False)  # Fast! Only {size} entries')
    

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create a small dev dataset')
    parser.add_argument('--size', type=int, default=10, help='Number of entries (default: 10)')
    parser.add_argument('--output', default='SynthBio_dev.json', help='Output filename')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    
    create_dev_set(args.size, args.output, args.seed)

