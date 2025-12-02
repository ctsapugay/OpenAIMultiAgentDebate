# Multi-Agent Debate Experiment: Terminal Output

**Date:** November 18, 2025  
**Model:** gpt-4o-mini  
**Examples per experiment:** 2  
**Seed:** 42  
**Total Runtime:** 326.0s (5.4 minutes)

**Note:** This log shows the output from the original 5 experiments (baseline + consensus). Voting experiments (6-11) were run separately. See `RESULTS_SUMMARY.md` for complete results including voting experiments.

---

## Experiment Execution Log

```
Loading dev dataset...
  [DEBUG] load() called with lazy=False
Dataset already cached at /Users/clara/Desktop/main/ucsc/WangLab/MADsystem/synthbio/SynthBio_dev.json
  [DEBUG] Download check took 0.00s
Loading dataset from /Users/clara/Desktop/main/ucsc/WangLab/MADsystem/synthbio/SynthBio_dev.json...
Loaded 20 entries (parsing: 0.00s, total: 0.00s)
  [DEBUG] sample() called: n=2, lazy=False
  [DEBUG] Getting count took 0.00s
  [DEBUG] Generated 2 random indices: [3, 0]
  [DEBUG] sample() total time: 0.00s
✓ Loaded 2 examples for testing


================================================================================
STARTING EXPERIMENTAL SUITE
================================================================================
Model: gpt-4o-mini
Examples per experiment: 2
Seed: 42
Results directory: /Users/clara/Desktop/main/ucsc/WangLab/MADsystem/experiments/results
================================================================================

================================================================================
EXPERIMENT 1: BASELINE (1 agent)
================================================================================

Example 1/2: Louis Deschamps
  Time: 8.9s | ROUGE-L: 0.285 | Faithfulness: 0.583

Example 2/2: Sonia Mabwe
  Time: 4.2s | ROUGE-L: 0.332 | Faithfulness: 0.750

✓ Experiment 1 complete in 13.1s
  Avg ROUGE-L: 0.309
  Results saved to exp1_baseline.json

================================================================================
EXPERIMENT 2: 2 agents, 2 rounds, NO consensus
================================================================================

Example 1/2: Louis Deschamps
  Initializing biography generation (2 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 10.4s
    Round 1: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 8.6s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 9.8s
    Round 2: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 11.0s
  Extracting final biography...
  Total time: 39.7s | ROUGE-L: 0.259 | Faithfulness: 0.542

Example 2/2: Sonia Mabwe
  Initializing biography generation (2 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 9.3s
    Round 1: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 3.2s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 7.2s
    Round 2: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 4.7s
  Extracting final biography...
  Total time: 24.5s | ROUGE-L: 0.349 | Faithfulness: 0.750

✓ Experiment 2 complete in 64.2s
  Avg ROUGE-L: 0.304
  Results saved to exp2_2agents_no_consensus.json

================================================================================
EXPERIMENT 3: 3 agents, 2 rounds, NO consensus
================================================================================

Example 1/2: Louis Deschamps
  Initializing biography generation (3 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 7.5s
    Round 1: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 7.0s
    Round 1: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 6.3s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 8.5s
    Round 2: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 9.2s
    Round 2: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 7.3s
  Extracting final biography...
  Total time: 45.8s | ROUGE-L: 0.289 | Faithfulness: 0.500

Example 2/2: Sonia Mabwe
  Initializing biography generation (3 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 4.6s
    Round 1: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 4.7s
    Round 1: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 4.8s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 5.8s
    Round 2: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 5.6s
    Round 2: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 14.9s
  Extracting final biography...
  Total time: 40.4s | ROUGE-L: 0.316 | Faithfulness: 0.750

✓ Experiment 3 complete in 86.1s
  Avg ROUGE-L: 0.303
  Results saved to exp3_3agents_no_consensus.json

================================================================================
EXPERIMENT 4: 2 agents, 2 rounds, WITH consensus
================================================================================

Example 1/2: Louis Deschamps
  Initializing biography generation (2 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 7.5s
    Round 1: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 11.5s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 7.4s
    Round 2: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 8.2s
  Collecting biographies for consensus...
  Generating consensus from 2 biographies...
    Creating consensus agent...
    Merging biographies...
      ✓ Consensus completed in 7.9s
  Total time: 42.5s | ROUGE-L: 0.257 | Faithfulness: 0.583

Example 2/2: Sonia Mabwe
  Initializing biography generation (2 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 5.4s
    Round 1: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 6.1s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/2)...
      ✓ Biographer_1 completed in 5.0s
    Round 2: Biographer_2 (2/2)...
      ✓ Biographer_2 completed in 6.4s
  Collecting biographies for consensus...
  Generating consensus from 2 biographies...
    Creating consensus agent...
    Merging biographies...
      ✓ Consensus completed in 3.7s
  Total time: 26.5s | ROUGE-L: 0.324 | Faithfulness: 0.812

✓ Experiment 4 complete in 69.1s
  Avg ROUGE-L: 0.290
  Results saved to exp4_2agents_with_consensus.json

================================================================================
EXPERIMENT 5: 3 agents, 2 rounds, WITH consensus
================================================================================

Example 1/2: Louis Deschamps
  Initializing biography generation (3 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 7.1s
    Round 1: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 6.3s
    Round 1: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 6.7s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 6.6s
    Round 2: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 6.4s
    Round 2: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 7.4s
  Collecting biographies for consensus...
  Generating consensus from 3 biographies...
    Creating consensus agent...
    Merging biographies...
      ✓ Consensus completed in 5.8s
  Total time: 46.2s | ROUGE-L: 0.303 | Faithfulness: 0.542

Example 2/2: Sonia Mabwe
  Initializing biography generation (3 agents, 2 rounds)...
  Round 1/2: Generating biographies...
    Round 1: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 6.5s
    Round 1: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 6.8s
    Round 1: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 6.4s
  Round 2/2: Generating biographies...
    Round 2: Biographer_1 (1/3)...
      ✓ Biographer_1 completed in 5.8s
    Round 2: Biographer_2 (2/3)...
      ✓ Biographer_2 completed in 7.3s
    Round 2: Biographer_3 (3/3)...
      ✓ Biographer_3 completed in 6.9s
  Collecting biographies for consensus...
  Generating consensus from 3 biographies...
    Creating consensus agent...
    Merging biographies...
      ✓ Consensus completed in 7.4s
  Total time: 47.1s | ROUGE-L: 0.264 | Faithfulness: 0.875

✓ Experiment 5 complete in 93.4s
  Avg ROUGE-L: 0.284
  Results saved to exp5_3agents_with_consensus.json


================================================================================
ALL EXPERIMENTS COMPLETE!
================================================================================
Total time: 326.0s (5.4 minutes)
Results saved to: /Users/clara/Desktop/main/ucsc/WangLab/MADsystem/experiments/results

Run 'python experiments/analyze_results.py' to view comparison
================================================================================
```

---

## Analysis Results

```
Loaded 5 experiment results

====================================================================================================
EXPERIMENTAL RESULTS COMPARISON
====================================================================================================
Configuration                         ROUGE-L   Faith.    Hall.     Cov.      Time
----------------------------------------------------------------------------------------------------
Baseline (1 agent)                     0.3087             0.6667   0.1429   0.6667     6.6s
2 agents, 2 rounds, no consensus       0.3043 (-0.004)    0.6458   0.1099   0.6458    32.1s
3 agents, 2 rounds, no consensus       0.3026 (-0.006)    0.6250   0.0714   0.6250    43.1s
2 agents, 2 rounds, ✓ consensus        0.2904 (-0.018)    0.6979   0.1131   0.6979    34.5s
3 agents, 2 rounds, ✓ consensus        0.2836 (-0.025)    0.7083   0.0625   0.7083    46.7s
====================================================================================================

====================================================================================================
BEST CONFIGURATIONS
====================================================================================================
• ROUGE-L (similarity to reference):
  → Baseline (1 agent): 0.3087
• Faithfulness (accuracy):
  → 3 agents, 2 rounds, with consensus: 0.7083
• Attribute Coverage (completeness):
  → 3 agents, 2 rounds, with consensus: 0.7083
• Hallucination Score (lower is better):
  → 3 agents, 2 rounds, with consensus: 0.0625
• Average Time (lower is better):
  → Baseline (1 agent): 6.6s
====================================================================================================

====================================================================================================
KEY FINDINGS
====================================================================================================

1. Multi-Agent vs Baseline:
   Best multi-agent: 2 agents, no consensus
   ROUGE-L improvement: -0.0044 (-1.4%)
   Faithfulness improvement: -0.0208 (-3.1%)

2. Effect of Number of Agents (no consensus):
   2 agents: 0.3043
   3 agents: 0.3026
   Difference: -0.0017 (2 agents better)

3. Effect of Consensus (2 agents):
   Without consensus: 0.3043
   With consensus: 0.2904
   Difference: -0.0139 (consensus hurts)

4. Effect of Consensus (3 agents):
   Without consensus: 0.3026
   With consensus: 0.2836
   Difference: -0.0190 (consensus hurts)

====================================================================================================

✓ Analysis complete!
  Detailed results available in: /Users/clara/Desktop/main/ucsc/WangLab/MADsystem/experiments/results
```

