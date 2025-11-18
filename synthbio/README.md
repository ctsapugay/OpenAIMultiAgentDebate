# SynthBio Experiment Module

This module implements experiments for evaluating the multi-agent debate system's performance on biographical generation using the SynthBio dataset.

## Overview

The SynthBio dataset contains 2,237 fictional individuals with structured attributes (infoboxes) and reference biographies. This module allows you to:

1. Load and analyze the SynthBio dataset
2. Generate biographies using multi-agent debate
3. Compare against single-agent baseline
4. Evaluate using multiple metrics (ROUGE-L, faithfulness, hallucination detection)

## Files

- **`dataset_loader.py`**: Downloads and loads the SynthBio dataset
- **`biography_debate.py`**: Extended debate system for biographical generation
- **`evaluator.py`**: Evaluation metrics (ROUGE-L, faithfulness, hallucination detection)
- **`pilot_test.py`**: Pilot test script for quick validation
- **`analyze_results.py`**: Analyze and summarize test results
- **`synthbio_guide.md`**: Guide to the SynthBio dataset

## Quick Start

### 1. Run Pilot Test

```bash
cd /path/to/MADsystem
source venv/bin/activate
python synthbio/pilot_test.py
```

This will:
- Download the SynthBio dataset (if not already cached)
- Test on 3 examples with 2 agents and 2 rounds
- Generate both multi-agent and baseline biographies
- Evaluate and save results

### 2. Analyze Results

```bash
python synthbio/analyze_results.py
```

This displays a summary of the pilot test results.

## Usage

### Load Dataset

```python
from synthbio import SynthBioLoader

loader = SynthBioLoader()
data = loader.load()  # Downloads if needed

# Get statistics
stats = loader.get_statistics()
print(f"Total entries: {stats['total_entries']}")

# Sample entries
sample = loader.sample(10, seed=42)
```

### Generate Biography

```python
from synthbio import BiographyDebateSystem

# Initialize system
system = BiographyDebateSystem(num_agents=3, model="gpt-4o-mini")

# Generate biography
attributes = loader.get_attributes(0)
result = system.generate_biography(attributes, num_rounds=2)

print(result['biography'])
print(result['transcript'])  # Full debate transcript
```

### Evaluate Biography

```python
from synthbio import BiographyEvaluator

evaluator = BiographyEvaluator()

generated = result['biography']
references = loader.get_biographies(0)
attributes = loader.get_attributes(0)

eval_results = evaluator.evaluate(generated, attributes, references)
print(f"ROUGE-L: {eval_results['rouge_l']:.4f}")
print(f"Faithfulness: {eval_results['faithfulness']['score']:.4f}")
```

## Configuration

Edit `pilot_test.py` to change:
- Number of test examples
- Number of agents
- Number of rounds
- Model (gpt-4o-mini, gpt-4, etc.)

## Results

Results are saved to `synthbio/results/pilot_test_results.json` with:
- Generated biographies (multi-agent and baseline)
- Evaluation metrics for each
- Reference biographies for comparison

## Next Steps

For full experiments, you can:
1. Increase the number of test examples
2. Experiment with different agent counts (2, 3, 4, 5)
3. Test different round counts (1, 2, 3, 4)
4. Compare different models
5. Analyze performance by demographic attributes
6. Test on complex vs. simple attribute sets

## Dataset

The SynthBio dataset is downloaded from:
https://storage.googleapis.com/gem-benchmark/SynthBio.json

It's cached locally in `synthbio/SynthBio.json` after first download.

