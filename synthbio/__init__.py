"""
SynthBio Experiment Package

Tools for running multi-agent debate experiments on biographical generation.
"""

from .dataset_loader import SynthBioLoader
from .biography_debate import BiographyDebateSystem
from .evaluator import BiographyEvaluator

__all__ = ['SynthBioLoader', 'BiographyDebateSystem', 'BiographyEvaluator']

