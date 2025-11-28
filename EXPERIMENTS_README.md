# Voting and Evaluation Experiments

This module implements comprehensive experiments for studying multi-agent voting systems, judge consensus, and artifact evaluation protocols.

## Overview

The experiments framework allows you to:

1. **Compare Voting Systems** - Test different aggregation methods
2. **Study Debate Effects** - See how agent discussions improve rankings
3. **Scale Judge Pools** - Understand how more judges affect outcomes
4. **Run Tournaments** - Iterative elimination-style competitions
5. **Test Robustness** - Evaluate with diverse artifact quality

## Experiments

### 1. Voting Systems Evaluation

**Purpose**: Compare different voting/aggregation methods for ranking artifacts.

**Methods Tested**:
- **Simple Majority**: Each judge votes for top artifact, most votes wins
- **Borda Count**: Judges rank artifacts, aggregate ranks with weighted points
- **Average Score**: Simple mean of all judge scores
- **Elo Rating**: Pairwise comparisons with dynamic rating updates

**Metrics**:
- **Stability**: Inter-judge agreement (lower std dev = more stable)
- **Fairness**: Consistency across judges (correlation between judge rankings)
- **Volatility**: How much rankings vary (score range, variance)

**Usage**:
```bash
python run_experiments.py --experiment voting_systems --num-judges 5
```

### 2. Multi-Agent Debate Rounds

**Purpose**: Test if letting judges debate improves artifact selection.

**Process**:
1. Initial scoring by all judges
2. Judges exchange critiques in debate rounds
3. Judges update scores based on debate
4. Compare initial vs. final rankings

**Metrics**:
- Ranking correlation (initial vs. final)
- Score evolution across rounds
- Consensus improvement

**Usage**:
```bash
python run_experiments.py --experiment debate_rounds --rounds 3 --num-judges 5
```

### 3. Human vs. LLM Judge Mix

**Purpose**: Calibrate LLM judges against human expert baseline.

**Process**:
1. Collect scores from LLM judges
2. Mix with human expert scores
3. Analyze consensus patterns
4. Calibrate LLM scoring against human baseline

**Metrics**:
- Human-LLM correlation
- Calibration factors (bias correction)
- Agreement patterns

**Usage**:
```python
from experiments import VotingExperiments

experiments = VotingExperiments(num_judges=5)
human_scores = {
    "human_1": {"artifact_1": 8.5, "artifact_2": 7.0},
    "human_2": {"artifact_1": 9.0, "artifact_2": 6.5}
}
result = experiments.experiment_3_human_llm_mix(artifacts, human_scores)
```

### 4. Agent Pool Scaling Effects

**Purpose**: Understand how increasing judge pool size affects rankings.

**Process**:
- Run same artifacts with different judge pool sizes (3, 5, 10, 15, 20...)
- Measure agreement rate, ranking noise, convergence

**Metrics**:
- **Agreement Rate**: % of judges that agree on top artifact
- **Ranking Noise**: Inconsistency in artifact rankings
- **Convergence**: How rankings stabilize with more judges

**Usage**:
```bash
python run_experiments.py --experiment pool_scaling --pool-sizes 3 5 10 15 20
```

### 5. Artifact Quality Diversity

**Purpose**: Stress-test voting robustness with diverse artifact quality.

**Process**:
- Mix high-quality and low-quality artifacts
- Identify "difficult" artifacts (high judge disagreement)
- Track flip-flops (rankings that change dramatically)

**Metrics**:
- Disagreement scores per artifact
- Difficult artifact identification
- Flip-flop detection

**Usage**:
```python
from experiments import VotingExperiments

experiments = VotingExperiments(num_judges=5)
strong_artifacts = [...]  # High-quality artifacts
weak_artifacts = [...]    # Low-quality artifacts
result = experiments.experiment_5_artifact_quality_diversity(strong_artifacts, weak_artifacts)
```

### 6. Iterative Multi-Round Voting

**Purpose**: Simulate tournament-style elimination.

**Process**:
1. Initial voting on all artifacts
2. Eliminate lowest-ranked artifacts
3. Re-vote on remaining artifacts
4. Repeat until winner emerges

**Metrics**:
- Ranking shifts across rounds
- Elimination patterns
- Final winner consistency

**Usage**:
```bash
python run_experiments.py --experiment iterative --elimination-rounds 5 --eliminate-per-round 1
```

### 7. Elo Pairwise Comparisons

**Purpose**: Use Elo rating system for dynamic artifact ranking.

**Process**:
- Pairwise comparisons between artifacts
- Dynamic Elo rating updates
- Final rankings based on Elo scores

**Metrics**:
- Elo rating evolution
- Match history
- Final rankings

**Usage**:
```bash
python run_experiments.py --experiment elo_pairwise --num-judges 5
```

## Quick Start

### Basic Usage

```bash
# Run voting systems comparison
python run_experiments.py --experiment voting_systems --num-judges 5

# Run debate rounds
python run_experiments.py --experiment debate_rounds --rounds 3

# Run pool scaling
python run_experiments.py --experiment pool_scaling --pool-sizes 3 5 10

# Run all experiments
python run_experiments.py --experiment all --num-judges 5
```

### Using Existing Artifacts

If you have existing artifacts from previous runs:

```bash
# Load from artifacts_results.json
python run_experiments.py \
    --experiment voting_systems \
    --artifacts-source load \
    --artifacts-file artifacts_results.json
```

### Python API

```python
from experiments import VotingExperiments, SimpleMajorityVoting, BordaCountVoting

# Initialize
experiments = VotingExperiments(num_judges=5, model="gpt-4o-mini")

# Load artifacts
artifacts = [
    {
        "id": "artifact_1",
        "task": "Create a bouncing ball",
        "generated_code": "<svg>...</svg>",
        "requirements": ["Ball bounces", "Smooth animation"]
    },
    # ... more artifacts
]

# Run experiment
results = experiments.experiment_1_voting_systems(artifacts)

# Access results
for system_name, result in results.items():
    print(f"{system_name}: {result.rankings}")
    print(f"Stability: {result.stability_metrics}")
```

## Output Format

Results are saved as JSON with the following structure:

```json
{
  "experiment_name": "VotingSystem_SimpleMajorityVoting",
  "timestamp": "2024-01-15T10:30:45",
  "config": {
    "num_judges": 5,
    "num_artifacts": 3
  },
  "rankings": {
    "artifact_1": 3.0,
    "artifact_2": 2.0,
    "artifact_3": 0.0
  },
  "stability_metrics": {
    "average_std_dev": 1.2,
    "max_std_dev": 2.5
  },
  "fairness_metrics": {
    "average_judge_agreement": 0.85
  },
  "volatility_metrics": {
    "score_range": 3.5,
    "score_std": 1.2
  },
  "raw_data": {
    "judge_scores": {...}
  }
}
```

## Metrics Explained

### Stability Metrics
- **average_std_dev**: Average standard deviation of scores per artifact (lower = more stable)
- **max_std_dev**: Maximum disagreement among judges
- **artifact_stds**: Per-artifact standard deviations

### Fairness Metrics
- **average_judge_agreement**: Correlation between judge rankings (higher = more fair)
- **num_judge_pairs**: Number of judge pairs compared

### Volatility Metrics
- **score_range**: Range of final scores (max - min)
- **score_std**: Standard deviation of final scores
- **ranking_noise**: Inconsistency in artifact rankings across judges

## Integration with Artifacts System

The experiments work seamlessly with your artifact generation system:

```python
from artifacts_debate import ArtifactsDebateSystem, load_sample_dataset_one_per_difficulty
from experiments import VotingExperiments

# Generate artifacts
artifacts_system = ArtifactsDebateSystem(num_agents=3, num_rounds=2)
tasks = load_sample_dataset_one_per_difficulty()

artifacts = []
for task in tasks:
    result = artifacts_system.run_artifacts_task(task, generate_code=True)
    artifacts.append({
        "id": result['task']['id'],
        "task": result['task']['task'],
        "generated_code": result['generated_code'],
        "requirements": result['task']['requirements']
    })

# Run experiments
experiments = VotingExperiments(num_judges=5)
results = experiments.experiment_1_voting_systems(artifacts)
```

## Best Practices

1. **Start Small**: Begin with 3-5 artifacts and 3-5 judges
2. **Use Cheaper Models**: Use `gpt-4o-mini` for judge evaluations to save costs
3. **Save Intermediate Results**: Artifacts generation is expensive, save them
4. **Compare Systems**: Always run multiple voting systems for comparison
5. **Track Metrics**: Monitor stability, fairness, and volatility across experiments

## Cost Considerations

- **Judge Evaluations**: Each judge evaluates each artifact (N judges × M artifacts)
- **Debate Rounds**: Additional rounds multiply the cost
- **Pool Scaling**: Larger pools = more evaluations
- **Recommendation**: Use `gpt-4o-mini` for experiments, `gpt-4` only for final validation

## Example Workflow

```bash
# 1. Generate artifacts (save them)
python main.py --topic ARTIFACTS --difficulty easy --model gpt-4o-mini

# 2. Run experiments on saved artifacts
python run_experiments.py \
    --experiment voting_systems \
    --artifacts-source load \
    --artifacts-file artifacts_results.json \
    --num-judges 5 \
    --model gpt-4o-mini

# 3. Analyze results
python -m json.tool experiment_results.json
```

## Future Enhancements

- [ ] Visualization tools for plotting metrics
- [ ] Statistical significance testing
- [ ] Automated report generation
- [ ] Integration with TrueSkill rating system
- [ ] Support for weighted judges
- [ ] Confidence intervals for rankings



