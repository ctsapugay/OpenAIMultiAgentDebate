# Multi-Agent Debate System: Experimental Results Summary

**Experiment Date:** November 18, 2025  
**Model:** gpt-4o-mini  
**Dataset:** SynthBio Dev Set (2 examples)  
**Test Subjects:** Louis Deschamps, Sonia Mabwe  
**Random Seed:** 42 (for reproducibility)

---

## Executive Summary

This experiment evaluated the effectiveness of multi-agent debate systems for biographical text generation. We tested 5 configurations across 2 biography generation tasks, comparing single-agent baseline performance against multi-agent systems with varying numbers of agents (2 vs 3) and consensus mechanisms (enabled vs disabled).

### Key Finding
**Surprising Result:** The single-agent baseline performed best on ROUGE-L (similarity to reference), while 3-agent systems with consensus achieved the highest faithfulness and lowest hallucination scores, despite lower ROUGE-L scores.

---

## Experimental Design

### Configurations Tested

| Experiment | Agents | Rounds | Consensus | Purpose |
|------------|--------|--------|-----------|---------|
| 1. Baseline | 1 | 1 | No | Establish single-agent performance |
| 2. Multi-Agent | 2 | 2 | No | Test basic multi-agent debate |
| 3. Multi-Agent | 3 | 2 | No | Test effect of additional agent |
| 4. Multi-Agent | 2 | 2 | Yes | Test consensus mechanism (2 agents) |
| 5. Multi-Agent | 3 | 2 | Yes | Test consensus mechanism (3 agents) |

### Evaluation Metrics

- **ROUGE-L:** Similarity to reference biography (0-1, higher is better)
- **Faithfulness:** Accuracy in representing provided attributes (0-1, higher is better)
- **Hallucination Score:** Ratio of sentences without grounding in attributes (0-1, lower is better)
- **Attribute Coverage:** Completeness of information (0-1, higher is better)
- **Time:** Average generation time per example (seconds)

---

## Results Overview

### Performance Comparison

| Configuration | ROUGE-L | Faithfulness | Hallucination | Coverage | Avg Time |
|---------------|---------|--------------|---------------|----------|----------|
| **Baseline (1 agent)** | **0.3087** | 0.6667 | 0.1429 | 0.6667 | **6.6s** |
| 2 agents, no consensus | 0.3043 | 0.6458 | 0.1099 | 0.6458 | 32.1s |
| 3 agents, no consensus | 0.3026 | 0.6250 | 0.0714 | 0.6250 | 43.1s |
| 2 agents, with consensus | 0.2904 | 0.6979 | 0.1131 | 0.6979 | 34.5s |
| **3 agents, with consensus** | 0.2836 | **0.7083** | **0.0625** | **0.7083** | 46.7s |

### Best Configurations by Metric

- **ROUGE-L (reference similarity):** Baseline (0.3087) ✅
- **Faithfulness (accuracy):** 3 agents + consensus (0.7083) ✅
- **Hallucination (lower is better):** 3 agents + consensus (0.0625) ✅
- **Coverage (completeness):** 3 agents + consensus (0.7083) ✅
- **Speed:** Baseline (6.6s) ✅

---

## Detailed Findings

### 1. Multi-Agent vs Baseline

**Question:** Does multi-agent debate improve biography quality?

**Finding:** Mixed results depending on the metric
- **ROUGE-L:** Baseline performs slightly better (-1.4% for best multi-agent)
- **Faithfulness:** Multi-agent with consensus shows improvement (+6.3% for 3-agent consensus)
- **Hallucinations:** Multi-agent systems reduce hallucinations (0.0625 vs 0.1429 baseline)

**Interpretation:** While multi-agent systems produce biographies that are less similar to reference texts (lower ROUGE-L), they are more faithful to source attributes and contain fewer hallucinations. This suggests multi-agent systems prioritize accuracy over mimicking reference style.

### 2. Effect of Number of Agents

**Question:** Does adding more agents improve performance?

**Without Consensus:**
- 2 agents: ROUGE-L = 0.3043, Faithfulness = 0.6458
- 3 agents: ROUGE-L = 0.3026, Faithfulness = 0.6250
- **Result:** Minimal difference; 2 agents slightly better

**With Consensus:**
- 2 agents: ROUGE-L = 0.2904, Faithfulness = 0.6979
- 3 agents: ROUGE-L = 0.2836, Faithfulness = 0.7083
- **Result:** 3 agents achieve better faithfulness (+1.5%) and lower hallucinations

**Interpretation:** Adding a third agent provides marginal benefits for faithfulness when consensus is enabled, but at the cost of increased computation time (~8% slower).

### 3. Effect of Consensus Mechanism

**Question:** Does consensus improve biography quality?

**2 Agents:**
- Without consensus: ROUGE-L = 0.3043, Faithfulness = 0.6458
- With consensus: ROUGE-L = 0.2904, Faithfulness = 0.6979
- **Change:** -4.6% ROUGE-L, +8.1% Faithfulness

**3 Agents:**
- Without consensus: ROUGE-L = 0.3026, Faithfulness = 0.6250
- With consensus: ROUGE-L = 0.2836, Faithfulness = 0.7083
- **Change:** -6.3% ROUGE-L, +13.3% Faithfulness

**Interpretation:** Consensus significantly improves faithfulness and reduces hallucinations, but reduces similarity to reference biographies. This trade-off suggests consensus encourages agents to prioritize accuracy over stylistic matching.

### 4. Computational Cost

**Time Analysis:**
- Baseline: 6.6s per example
- 2 agents + consensus: 34.5s per example (5.2× slower)
- 3 agents + consensus: 46.7s per example (7.1× slower)

**Interpretation:** Multi-agent systems with consensus provide accuracy improvements at significant computational cost. For production use, the trade-off between accuracy and speed must be carefully considered.

---

## Example-Level Results

### Example 1: Louis Deschamps
A French novelist, film director, and art historian with 24 attributes provided.

| Configuration | ROUGE-L | Faithfulness | Time |
|---------------|---------|--------------|------|
| Baseline | 0.285 | 0.583 | 8.9s |
| 2 agents, no consensus | 0.259 | 0.542 | 39.7s |
| 3 agents, no consensus | 0.289 | 0.500 | 45.8s |
| 2 agents, with consensus | 0.257 | 0.583 | 42.5s |
| 3 agents, with consensus | 0.303 | 0.542 | 46.2s |

### Example 2: Sonia Mabwe
A Congolese theologian, activist, and professor with 16 attributes provided.

| Configuration | ROUGE-L | Faithfulness | Time |
|---------------|---------|--------------|------|
| Baseline | 0.332 | 0.750 | 4.2s |
| 2 agents, no consensus | 0.349 | 0.750 | 24.5s |
| 3 agents, no consensus | 0.316 | 0.750 | 40.4s |
| 2 agents, with consensus | 0.324 | 0.812 | 26.5s |
| 3 agents, with consensus | 0.264 | 0.875 | 47.1s |

**Observation:** Results vary significantly by example, with Sonia Mabwe showing stronger benefits from consensus (faithfulness increased from 0.750 to 0.875 with 3-agent consensus).

---

## Conclusions

### What Works
1. ✅ **3 agents + consensus for highest accuracy:** Best faithfulness (0.7083) and lowest hallucinations (0.0625)
2. ✅ **Consensus mechanism improves factual accuracy:** Consistent +8-13% improvement in faithfulness
3. ✅ **Multi-agent reduces hallucinations:** Even without consensus, multi-agent systems show fewer hallucinations

### What Doesn't Work
1. ❌ **Multi-agent for reference similarity:** Baseline outperforms all multi-agent configs on ROUGE-L
2. ❌ **Additional agents without consensus:** Minimal benefit, increased cost
3. ❌ **Computational efficiency:** Multi-agent systems 5-7× slower than baseline

### Trade-Offs
- **Accuracy vs Speed:** 3-agent consensus is 7× slower but 6% more faithful
- **Accuracy vs Reference Similarity:** More faithful biographies are less similar to reference style
- **Agent Count vs Benefit:** Diminishing returns beyond 2 agents

---

## Recommendations

### For Production Use
**Recommended:** 2 agents, 2 rounds, with consensus
- **Rationale:** Balanced trade-off between accuracy improvement (+8% faithfulness) and computational cost (5× slower vs 7× for 3 agents)
- **Use case:** Applications prioritizing factual accuracy over reference similarity

### For Research/High-Accuracy Requirements
**Recommended:** 3 agents, 2 rounds, with consensus
- **Rationale:** Highest faithfulness and lowest hallucinations
- **Use case:** Academic, legal, or medical biography generation where accuracy is critical

### For Speed-Critical Applications
**Recommended:** Baseline (single agent)
- **Rationale:** Fastest generation with acceptable quality
- **Use case:** High-throughput applications, preliminary drafts

---

## Limitations & Future Work

### Current Limitations
1. **Small sample size:** Only 2 examples tested; results may not generalize
2. **Single model:** Only tested with gpt-4o-mini; other models may show different patterns
3. **Fixed rounds:** All multi-agent tests used 2 rounds; optimal round count unknown
4. **Domain-specific:** Results specific to biographical text generation

### Recommended Next Steps
1. **Scale up:** Test on 50-100 examples for statistical significance
2. **Model comparison:** Test with gpt-4o, gpt-4-turbo for quality comparison
3. **Round optimization:** Test 1, 3, 4 rounds to find optimal debate length
4. **Agent diversity:** Test heterogeneous agent configurations (different prompts/models)
5. **Human evaluation:** Conduct blind human evaluation of biography quality

---

## Appendix: Technical Details

### Environment
- **Python Version:** 3.13
- **Key Dependencies:** openai-agents 0.6.0, python-dotenv 1.2.1
- **Hardware:** MacBook Air M1
- **API:** OpenAI gpt-4o-mini

### Reproducibility
All experiments used seed=42 for random sampling. Complete code and data available at:
- Experiment runner: `experiments/run_experiments.py`
- Analysis script: `experiments/analyze_results.py`
- Raw results: `experiments/results/`

### Data Files
- `experiments/results/exp1_baseline.json`
- `experiments/results/exp2_2agents_no_consensus.json`
- `experiments/results/exp3_3agents_no_consensus.json`
- `experiments/results/exp4_2agents_with_consensus.json`
- `experiments/results/exp5_3agents_with_consensus.json`
- `experiments/results/summary.json`

---

**Experiment completed:** November 18, 2025  
**Total runtime:** 326.0 seconds (5.4 minutes)  
**Generated by:** `experiments/analyze_results.py`

