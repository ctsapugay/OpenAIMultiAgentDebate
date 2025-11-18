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
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the SynthBio loader.
        
        Args:
            cache_dir: Directory to cache the dataset. Defaults to synthbio folder.
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / "SynthBio.json"
        self.data: List[Dict[str, Any]] = []
    
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
    
    def load(self, force_download: bool = False) -> List[Dict[str, Any]]:
        """
        Load the SynthBio dataset.
        
        Args:
            force_download: If True, re-download the dataset
            
        Returns:
            List of dataset entries, each containing 'attrs' and 'biographies'
        """
        # Download if needed
        self.download(force=force_download)
        
        # Load JSON
        if not self.cache_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.cache_file}")
        
        print(f"Loading dataset from {self.cache_file}...")
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print(f"Loaded {len(self.data)} entries")
        return self.data
    
    def get_entry(self, index: int) -> Dict[str, Any]:
        """Get a specific entry by index."""
        if not self.data:
            self.load()
        return self.data[index]
    
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
        if not self.data:
            self.load()
        
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
    
    def sample(self, n: int, seed: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a random sample of entries.
        
        Args:
            n: Number of entries to sample
            seed: Random seed for reproducibility
            
        Returns:
            List of sampled entries
        """
        import random
        
        if not self.data:
            self.load()
        
        if seed is not None:
            random.seed(seed)
        
        return random.sample(self.data, min(n, len(self.data)))


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

