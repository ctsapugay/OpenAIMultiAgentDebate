# Multi-Agent Debate Experiments

This directory contains scripts for running systematic experiments on the multi-agent biography generation system.

## Quick Start

### Run All Experiments

```bash
python synthbio/experiments/run_experiments.py
```

This will run 11 experiments (~11 minutes total):
1. **Baseline** (1 agent)
2. **2 agents, 2 rounds, NO consensus**
3. **3 agents, 2 rounds, NO consensus**
4. **2 agents, 2 rounds, WITH consensus**
5. **3 agents, 2 rounds, WITH consensus**
6. **2 agents, 2 rounds, voting (select), NO consensus**
7. **3 agents, 2 rounds, voting (select), NO consensus**
8. **2 agents, 2 rounds, voting (filter) + consensus**
9. **3 agents, 2 rounds, voting (filter) + consensus**
10. **2 agents, 2 rounds, voting (filter top 2) + consensus**
11. **3 agents, 2 rounds, voting (filter top 2) + consensus**

### Run Only Voting Experiments

If you've already run experiments 1-5, you can run only the voting experiments:

```bash
python synthbio/experiments/run_experiments.py --voting-only
```

This runs experiments 6-11 (~6 minutes total).

### View Results

```bash
python synthbio/experiments/analyze_results.py
```

This displays:
- Comparison table of all experiments
- Best configurations for each metric
- Key findings and insights

## Configuration

### Change Number of Examples

By default, experiments use 2 examples from the dev set for speed. To test more:

```bash
python synthbio/experiments/run_experiments.py --num-examples 5
```

### Change Model

```bash
python synthbio/experiments/run_experiments.py --model gpt-4o
```

### Change Random Seed

For reproducibility, experiments use seed=42. To change:

```bash
python synthbio/experiments/run_experiments.py --seed 123
```

### Show Intermediate Outputs

To see intermediate agent outputs during generation:

```bash
# Show truncated intermediate outputs (~300 chars per agent)
python synthbio/experiments/run_experiments.py --show-intermediate

# Show full intermediate outputs (complete agent biographies)
python synthbio/experiments/run_experiments.py --show-full
```

This is useful for debugging and understanding how agents collaborate. The intermediate outputs show:
- Each agent's biography after each round
- Voting outputs from each agent (when voting is enabled)
- Consensus input biographies (before merging)
- Full or truncated views based on flag choice

## File Structure

```
synthbio/experiments/
├── run_experiments.py      # Main experiment runner
├── analyze_results.py      # Results analyzer
├── README.md              # This file
├── EXPERIMENT_OUTPUT.md   # Complete terminal output
├── RESULTS_SUMMARY.md     # Detailed results analysis
└── results/               # Experiment outputs
    ├── exp1_baseline.json
    ├── exp2_2agents_no_consensus.json
    ├── exp3_3agents_no_consensus.json
    ├── exp4_2agents_with_consensus.json
    ├── exp5_3agents_with_consensus.json
    ├── exp6_2agents_voting_select.json
    ├── exp7_3agents_voting_select.json
    ├── exp8_2agents_voting_consensus.json
    ├── exp9_3agents_voting_consensus.json
    ├── exp10_2agents_voting_top2_consensus.json
    ├── exp11_3agents_voting_top2_consensus.json
    └── summary.json
```

## Experimental Design

### Fixed Parameters
- **Dataset:** Dev set (20 examples total, sample 2 for experiments)
- **Model:** gpt-4o-mini (fast and cost-effective)
- **Rounds:** 2 (for all multi-agent experiments)
- **Seed:** 42 (ensures same examples across experiments)

### Variable Parameters
- **Number of agents:** 1 (baseline), 2, 3
- **Consensus:** Enabled/disabled
- **Voting:** Enabled/disabled
- **Voting mode:** "select_best" (use top-voted) or "filter" (vote then consensus on top N)
- **Top N voted:** Number of top biographies to use after voting (for filter mode)

### Metrics Tracked
- **ROUGE-L:** Similarity to reference biography
- **Faithfulness:** Adherence to provided attributes
- **Hallucination Score:** Invented facts not in attributes (lower is better)
- **Attribute Coverage:** Completeness of information
- **Time:** Execution time per example

## Research Questions

1. **Does multi-agent debate improve quality?**
   - Compare baseline (Exp 1) vs. multi-agent (Exp 2-11)

2. **What's the optimal number of agents?**
   - Compare 2 agents (Exp 2, 4, 6, 8, 10) vs. 3 agents (Exp 3, 5, 7, 9, 11)

3. **Does consensus improve results?**
   - Compare no consensus (Exp 2, 3, 6, 7) vs. with consensus (Exp 4, 5, 8, 9, 10, 11)

4. **Do voting mechanisms improve results?**
   - Compare voting-only (Exp 6, 7) vs. consensus-only (Exp 4, 5)
   - Compare voting+consensus (Exp 8, 9) vs. consensus-only (Exp 4, 5)
   - Compare voting filter top 2 (Exp 10, 11) vs. voting filter all (Exp 8, 9)

## Results Format

Each experiment produces a JSON file with:
- **config:** Experiment parameters
- **results:** Per-example results with biographies and evaluations
- **summary:** Aggregate statistics
- **total_time:** Total experiment duration
- **timestamp:** When experiment was run

Example structure:
```json
{
  "config": {
    "name": "2agents_with_consensus",
    "num_agents": 2,
    "num_rounds": 2,
    "consensus": true,
    "voting": false,
    "voting_mode": null,
    "top_n_voted": null,
    "model": "gpt-4o-mini"
  },
  "results": [...],
  "summary": {
    "avg_rouge_l": 0.xxx,
    "avg_faithfulness": 0.xxx,
    "avg_hallucination": 0.xxx,
    "avg_coverage": 0.xxx,
    "avg_time": x.x
  }
}
```

## Tips

- **Start small:** Use 2 examples to test quickly
- **Scale up:** Once validated, increase to 10-20 examples for more robust results
- **Reproducibility:** Keep the same seed across runs to ensure fair comparison
- **Cost tracking:** Each experiment makes API calls; monitor your OpenAI usage

## Troubleshooting

**Missing API key:**
```
Error: OPENAI_API_KEY not found in environment
```
→ Check your `.env` file in the project root

**Experiments take too long:**
- Reduce `--num-examples` (default is 2)
- Use `gpt-4o-mini` (faster than gpt-4o)

**Out of memory:**
- The dev set (20 examples) should be small enough
- If issues persist, reduce batch size in the code

## Next Steps

After running these experiments:
1. Review results with `analyze_results.py`
2. Identify best configuration for your use case:
   - **Best ROUGE-L:** 2 agents, voting (filter top 2) + consensus
   - **Best Faithfulness:** 3 agents, voting (filter) + consensus
   - **Balanced:** 2 agents, consensus-only (no voting)
   - **Fastest:** Baseline (single agent)
3. Scale up to full dataset (50-100 examples)
4. Consider additional experiments (different models, more rounds, different top_n values, etc.)

## Key Findings

Based on the experimental results:
- **Voting mechanisms enable multi-agent systems to beat baseline on ROUGE-L** (12.2% improvement)
- **Voting+Consensus achieves highest faithfulness** (9.4% improvement over baseline)
- **Voting filter top 2 + consensus produces best ROUGE-L** (0.3462)
- **3 agents + voting (filter) + consensus produces highest faithfulness** (0.7292)
- Voting adds computational overhead (7-16× slower) but enables quality improvements

See `RESULTS_SUMMARY.md` for detailed analysis and recommendations.

