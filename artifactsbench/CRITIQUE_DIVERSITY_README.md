# Critique Diversity Analysis Script

This script analyzes multi-candidate generation results to identify signals that indicate whether multi-agent debate or richer critique diversity would be beneficial.

## Purpose

The script tests for specific signals that suggest the current single-judge evaluation system might benefit from:
- Multi-agent debate
- Specialized evaluators
- Richer critique diversity

## Tests Performed

### 1. Re-Evaluation Consistency Test
- **What it does**: Re-evaluates each final.html file 5 times
- **Measures**: Variance in scores across evaluations
- **Signal**: If std_dev > 2.0, evaluation is inconsistent → debate may help

### 2. Feedback Quality Analysis
- **What it does**: Analyzes evaluation text for depth, specificity, actionability
- **Measures**: 
  - Code references (mentions specific functions/lines?)
  - Actionable suggestions (concrete improvement ideas?)
  - Specificity score (0-1)
- **Signal**: If specificity < 0.5, feedback is too generic → specialized critics may help

### 3. Blind Spot Detection
- **What it does**: Identifies checklist items with highest variance across evaluations
- **Measures**: Variance per checklist item
- **Signal**: If certain items consistently have high variance → specialized evaluators may help

### 4. Candidate Variance Analysis
- **What it does**: Analyzes variance in candidate scores for same weak items
- **Measures**: Score spread for candidates focusing on same item
- **Signal**: High variance suggests evaluation inconsistency or prompt quality issues

## Usage

### Basic Usage
```bash
python artifactsbench/analyze_critique_diversity.py
```

### Test Specific Number of Final Files
```bash
python artifactsbench/analyze_critique_diversity.py --num-files 10
```

### Test All Final Files
```bash
python artifactsbench/analyze_critique_diversity.py --num-files 0
```

### Custom Output File
```bash
python artifactsbench/analyze_critique_diversity.py --output results/analysis.json
```

## Prerequisites

1. **Run multi-candidate generation first**:
   ```bash
   python artifactsbench/multi_candidate_generation.py
   ```

2. **Ensure final.html files exist**:
   - Script looks for files in `artifacts_output/multi_candidate_generation/`
   - Pattern: `final.html` (the final selected code from each task)

## Output

The script generates:
1. **Console output**: Real-time progress and summary
2. **JSON file**: Detailed results saved to `artifacts_output/multi_candidate_generation/critique_diversity_analysis.json`

### Output Structure

```json
{
  "timestamp": "2025-12-02T...",
  "num_candidates_tested": 5,
  "consistency_tests": [
    {
      "candidate_info": {...},
      "n_evaluations": 5,
      "total_scores": [85.0, 86.0, 85.0, 87.0, 85.0],
      "mean_score": 85.6,
      "std_dev": 0.8,
      "variance": 0.64,
      "needs_debate": false,
      "consistency_level": "high"
    }
  ],
  "feedback_quality": [...],
  "blind_spots": {...}
}
```

## Interpreting Results

### Consistency Test Results

- **std_dev < 1.0**: ✅ High consistency - current system works well
- **std_dev 1.0-2.0**: ⚠️ Medium consistency - monitor but debate not urgent
- **std_dev > 2.0**: 🔴 Low consistency - **debate recommended**

### Feedback Quality Results

- **specificity_score > 0.7**: ✅ High quality feedback
- **specificity_score 0.4-0.7**: ⚠️ Medium quality - could be improved
- **specificity_score < 0.4**: 🔴 Low quality - **specialized critics recommended**

### Blind Spot Detection

- **High variance items**: Items with variance > 2.0
  - These items are scored inconsistently
  - Consider specialized evaluators for these items

## Recommendations Based on Results

### If std_dev > 2.0:
→ **Implement multi-agent debate** to reduce evaluation variance

### If specificity_score < 0.5:
→ **Add specialized critics** with domain expertise

### If high_variance_items found:
→ **Create item-specific evaluators** for problematic checklist items

### If all tests pass:
→ **Current system is sufficient** - no need for debate yet

## Example Output

```
================================================================================
CRITIQUE DIVERSITY SIGNAL ANALYSIS
================================================================================
Testing for signals that indicate need for richer critique diversity
Timestamp: 2025-12-02 20:30:00
================================================================================

1. Loading dataset...
   ✓ Loaded dataset with 1000 tasks

2. Finding candidate files...
   ✓ Found 15 candidate files
   Testing 5 candidates

================================================================================
TEST 1: RE-EVALUATION CONSISTENCY TEST
================================================================================
Re-evaluating candidates multiple times to check for consistency...

[1/5] Testing: Game Development-Puzzle / task_1
  Candidate: 1 (Focus: Are there any innovative features that are eye-catching?)
  Re-evaluating 5 times...
    Evaluation 1/5... Score: 86.0 (took 12.3s)
    Evaluation 2/5... Score: 85.0 (took 11.8s)
    Evaluation 3/5... Score: 86.0 (took 12.1s)
    Evaluation 4/5... Score: 87.0 (took 12.5s)
    Evaluation 5/5... Score: 85.0 (took 12.0s)
  ✓ Consistency: high (std_dev: 0.75)

================================================================================
SUMMARY
================================================================================
Consistency Tests:
  Average std_dev: 0.82
  Max std_dev: 1.2
  Candidates needing debate: 0/5

✓ Current evaluation system appears consistent
   Average variance (0.82) is below threshold (2.0)

Feedback Quality:
  Average specificity score: 0.65/1.0
```

## Notes

- **Token Usage**: Each re-evaluation uses API tokens. Testing 5 candidates × 5 evaluations = 25 API calls
- **Time**: Each evaluation takes ~10-15 seconds. Full test may take 5-10 minutes
- **Cost**: Uses same model as multi_candidate_generation.py (gpt-4.1-mini by default)

## Troubleshooting

### "No candidate files found"
- Run `multi_candidate_generation.py` first to generate candidates

### "Task index out of range"
- Some tasks may not exist in dataset - script skips them automatically

### "Could not read HTML file"
- Check file permissions and paths
- Ensure HTML files are not corrupted

