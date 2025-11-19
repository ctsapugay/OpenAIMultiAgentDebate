"""
SynthBio Dataset Loader

Downloads and loads the SynthBio dataset for biographical generation experiments.
"""

import json
import os
import urllib.request
from typing import List, Dict, Any, Optional
from pathlib import Path


SYNTHBIO_URL = "https://storage.googleapis.com/gem-benchmark/SynthBio.json"
DEFAULT_CACHE_DIR = Path(__file__).parent
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "SynthBio.json"


class SynthBioLoader:
    """Loader for the SynthBio dataset."""
    
    def __init__(self, cache_dir: Optional[Path] = None, dataset_size: Optional[int] = None):
        """
        Initialize the SynthBio loader.
        
        Args:
            cache_dir: Directory to cache the dataset. Defaults to synthbio folder.
            dataset_size: If known, the total number of entries in the dataset.
                         This avoids having to parse the entire JSON to get the count.
                         If None, will be computed on first access (slower).
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / "SynthBio.json"
        self.count_cache_file = self.cache_dir / "SynthBio.count"
        self.data: List[Dict[str, Any]] = []
        self._cached_count = dataset_size  # Allow manual override
    
    def download(self, force: bool = False) -> Path:
        """
        Download the SynthBio dataset if not already cached.
        
        Args:
            force: If True, re-download even if file exists
            
        Returns:
            Path to the downloaded JSON file
        """
        if self.cache_file.exists() and not force:
            print(f"Dataset already cached at {self.cache_file}")
            return self.cache_file
        
        print(f"Downloading SynthBio dataset from {SYNTHBIO_URL}...")
        try:
            urllib.request.urlretrieve(SYNTHBIO_URL, self.cache_file)
            print(f"Downloaded dataset to {self.cache_file}")
            return self.cache_file
        except Exception as e:
            raise RuntimeError(f"Failed to download dataset: {e}")
    
    def load(self, force_download: bool = False, lazy: bool = True) -> List[Dict[str, Any]]:
        """
        Load the SynthBio dataset.
        
        Args:
            force_download: If True, re-download the dataset
            lazy: If True, don't load all data into memory (use lazy loading instead)
            
        Returns:
            List of dataset entries, each containing 'attrs' and 'biographies'
            If lazy=True, returns empty list (use get_entry() or sample() for lazy access)
        """
        import time
        start = time.time()
        print(f"  [DEBUG] load() called with lazy={lazy}")
        
        # Download if needed
        download_start = time.time()
        self.download(force=force_download)
        download_time = time.time() - download_start
        print(f"  [DEBUG] Download check took {download_time:.2f}s")
        
        # Load JSON
        if not self.cache_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.cache_file}")
        
        if lazy:
            # Lazy mode: don't load everything, just verify file exists
            print(f"  [DEBUG] Lazy mode: skipping full dataset load")
            print(f"  [DEBUG] Dataset file ready for lazy loading: {self.cache_file}")
            elapsed = time.time() - start
            print(f"  [DEBUG] load(lazy=True) completed in {elapsed:.2f}s")
            return []
        
        print(f"Loading dataset from {self.cache_file}...")
        parse_start = time.time()
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        parse_time = time.time() - parse_start
        
        elapsed = time.time() - start
        print(f"Loaded {len(self.data)} entries (parsing: {parse_time:.2f}s, total: {elapsed:.2f}s)")
        return self.data
    
    def get_entry(self, index: int) -> Dict[str, Any]:
        """
        Get a specific entry by index.
        Uses lazy loading if data not already loaded.
        """
        if not self.data:
            # Lazy load: load only this entry
            return self._load_entry_by_index(index)
        return self.data[index]
    
    def _load_entry_by_index(self, index: int) -> Dict[str, Any]:
        """
        Load a specific entry by index.
        Note: Still requires parsing JSON, but only loads when entry is accessed.
        For better performance with large datasets, consider caching loaded entries.
        """
        if not self.cache_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.cache_file}")
        
        # Load JSON and get specific entry
        # TODO: Could optimize with streaming JSON parser for very large files
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if index >= len(data):
                raise IndexError(f"Index {index} out of range (dataset has {len(data)} entries)")
            return data[index]
    
    def _get_total_count(self) -> int:
        """
        Get total number of entries without loading all data into memory.
        First tries to read from a count cache file, then falls back to parsing JSON.
        """
        # If data is already loaded, use its length
        if self.data:
            return len(self.data)
        
        # If dataset file doesn't exist, return 0
        if not self.cache_file.exists():
            return 0
        
        # If count is already cached in memory, return it
        if self._cached_count is not None:
            return self._cached_count
        
        # Try to read count from cache file
        if self.count_cache_file.exists():
            try:
                with open(self.count_cache_file, 'r') as f:
                    self._cached_count = int(f.read().strip())
                print(f"  [DEBUG] Read count from cache: {self._cached_count} entries")
                return self._cached_count
            except (ValueError, IOError) as e:
                print(f"  [DEBUG] Failed to read count cache: {e}, will recompute")
        
        # No cached count available - need to parse JSON (this is slow)
        print("  [DEBUG] Parsing JSON to get entry count (this may take a while for large datasets)...")
        import time
        start = time.time()
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self._cached_count = len(data)
        elapsed = time.time() - start
        print(f"  [DEBUG] Count parsing took {elapsed:.2f}s, found {self._cached_count} entries")
        
        # Save count to cache file for next time
        try:
            with open(self.count_cache_file, 'w') as f:
                f.write(str(self._cached_count))
            print(f"  [DEBUG] Saved count to cache file: {self.count_cache_file}")
        except IOError as e:
            print(f"  [DEBUG] Warning: Failed to save count cache: {e}")
        
        return self._cached_count
    
    def get_attributes(self, index: int) -> Dict[str, Any]:
        """Get attributes (infobox) for a specific entry."""
        entry = self.get_entry(index)
        return entry.get('attrs', {})
    
    def get_biographies(self, index: int) -> List[str]:
        """Get reference biographies for a specific entry."""
        entry = self.get_entry(index)
        return entry.get('biographies', [])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        # For statistics, we need to load all data
        if not self.data:
            self.load(lazy=False)
        
        stats = {
            'total_entries': len(self.data),
            'total_biographies': sum(len(entry.get('biographies', [])) for entry in self.data),
            'avg_biographies_per_entry': 0,
            'gender_distribution': {},
            'nationality_distribution': {},
            'occupation_distribution': {},
        }
        
        if self.data:
            stats['avg_biographies_per_entry'] = stats['total_biographies'] / len(self.data)
            
            for entry in self.data:
                attrs = entry.get('attrs', {})
                
                # Gender
                gender = attrs.get('gender', 'unknown')
                stats['gender_distribution'][gender] = stats['gender_distribution'].get(gender, 0) + 1
                
                # Nationality
                nationality = attrs.get('nationality', 'unknown')
                stats['nationality_distribution'][nationality] = stats['nationality_distribution'].get(nationality, 0) + 1
                
                # Occupation
                occupation = attrs.get('occupation', 'unknown')
                stats['occupation_distribution'][occupation] = stats['occupation_distribution'].get(occupation, 0) + 1
        
        return stats
    
    def precompute_count(self) -> int:
        """
        Precompute and cache the dataset count.
        Call this once to avoid the count computation overhead on first sample().
        
        Returns:
            The total number of entries in the dataset
        """
        return self._get_total_count()
    
    def sample(self, n: int, seed: Optional[int] = None, lazy: bool = True) -> List[Dict[str, Any]]:
        """
        Get a random sample of entries.
        
        Args:
            n: Number of entries to sample
            seed: Random seed for reproducibility
            lazy: If True, load only sampled entries (faster for small samples).
                 Note: Even in lazy mode, the JSON must be parsed once to extract samples.
                 For large datasets, this can still be slow. Consider using precompute_count()
                 first to cache the count and reduce overhead.
            
        Returns:
            List of sampled entries
        """
        import random
        import time
        
        sample_start = time.time()
        print(f"  [DEBUG] sample() called: n={n}, lazy={lazy}")
        
        # Get total count (fast if cached)
        count_start = time.time()
        total_count = self._get_total_count()
        count_time = time.time() - count_start
        print(f"  [DEBUG] Getting count took {count_time:.2f}s")
        
        if total_count == 0:
            raise RuntimeError("Dataset not available. Call download() first.")
        
        if seed is not None:
            random.seed(seed)
        
        # Generate random indices
        indices = random.sample(range(total_count), min(n, total_count))
        print(f"  [DEBUG] Generated {len(indices)} random indices: {indices}")
        
        if lazy and not self.data:
            # Lazy mode: load only the sampled entries
            # Parse JSON once and extract only needed entries (don't keep all in memory)
            print(f"  [DEBUG] Lazy loading {len(indices)} entries...")
            start = time.time()
            entries = []
            # Load JSON once and extract only needed entries
            print(f"  [DEBUG] Opening and parsing JSON file (this is the main bottleneck for large files)...")
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                parse_start = time.time()
                data = json.load(f)
                parse_time = time.time() - parse_start
                print(f"  [DEBUG] JSON parsing took {parse_time:.2f}s")
                
                print(f"  [DEBUG] Extracting {len(indices)} entries...")
                extract_start = time.time()
                for idx in indices:
                    if idx >= len(data):
                        raise IndexError(f"Index {idx} out of range")
                    entries.append(data[idx])
                extract_time = time.time() - extract_start
                print(f"  [DEBUG] Entry extraction took {extract_time:.2f}s")
            
            total_time = time.time() - start
            print(f"  [DEBUG] Total lazy loading time: {total_time:.2f}s")
            
            sample_elapsed = time.time() - sample_start
            print(f"  [DEBUG] sample() total time: {sample_elapsed:.2f}s")
            
            # Clear data reference to free memory (we only keep the sampled entries)
            del data
            return entries
        else:
            # Load all data if not already loaded
            if not self.data:
                self.load(lazy=False)
            selected = [self.data[idx] for idx in indices]
            
            sample_elapsed = time.time() - sample_start
            print(f"  [DEBUG] sample() total time: {sample_elapsed:.2f}s")
            return selected


if __name__ == "__main__":
    # Test the loader
    loader = SynthBioLoader()
    data = loader.load()
    
    print("\nDataset Statistics:")
    stats = loader.get_statistics()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Total biographies: {stats['total_biographies']}")
    print(f"Avg biographies per entry: {stats['avg_biographies_per_entry']:.2f}")
    
    print("\nFirst entry:")
    entry = loader.get_entry(0)
    print(f"Attributes keys: {list(entry.get('attrs', {}).keys())}")
    print(f"Number of biographies: {len(entry.get('biographies', []))}")

