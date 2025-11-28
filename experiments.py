"""
Multi-Agent Voting and Evaluation Experiments

This module implements various voting systems, debate protocols, and evaluation
experiments for artifact generation and ranking.

Experiments:
1. Voting Systems Evaluation - Compare Simple Majority, Borda Count, Elo/TrueSkill
2. Multi-Agent Debate Rounds - Judges debate and update scores
3. Human vs LLM Judge Mix - Hybrid evaluation with human experts
4. Agent Pool Scaling Effects - Test with different numbers of judges
5. Artifact Quality Diversity - Test with strong/weak artifacts
6. Iterative Multi-Round Voting - Tournament-style elimination
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import json
import statistics
import random
import math
from datetime import datetime
from agents import Agent, Runner
from debate_system import InMemorySession


# ============================================================================
# Voting Systems
# ============================================================================

class VotingSystem:
    """Base class for voting systems."""
    
    def vote(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate scores from multiple judges.
        
        Args:
            judge_scores: {judge_id: {artifact_id: score}}
            
        Returns:
            {artifact_id: aggregated_score}
        """
        raise NotImplementedError


class SimpleMajorityVoting(VotingSystem):
    """Simple majority: Most votes wins."""
    
    def vote(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Each judge votes for their top artifact. Most votes wins.
        """
        artifact_votes = defaultdict(int)
        
        for judge_id, scores in judge_scores.items():
            if scores:
                # Judge votes for highest-scored artifact
                top_artifact = max(scores.items(), key=lambda x: x[1])[0]
                artifact_votes[top_artifact] += 1
        
        return dict(artifact_votes)


class BordaCountVoting(VotingSystem):
    """Borda Count: Judges rank artifacts, aggregate ranks."""
    
    def vote(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Convert scores to ranks, assign Borda points, aggregate.
        """
        artifact_borda_scores = defaultdict(float)
        
        for judge_id, scores in judge_scores.items():
            if not scores:
                continue
            
            # Sort artifacts by score (descending)
            sorted_artifacts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            
            # Assign Borda points: 1st gets n-1 points, 2nd gets n-2, etc.
            num_artifacts = len(sorted_artifacts)
            for rank, (artifact_id, _) in enumerate(sorted_artifacts):
                borda_points = num_artifacts - rank - 1
                artifact_borda_scores[artifact_id] += borda_points
        
        return dict(artifact_borda_scores)


class EloRatingSystem:
    """Elo/TrueSkill-style dynamic rating system."""
    
    def __init__(self, initial_rating: float = 1500.0, k_factor: float = 32.0):
        self.ratings = defaultdict(lambda: initial_rating)
        self.k_factor = k_factor
        self.match_history = []
        self.initial_rating = initial_rating
    
    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for A against B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
    
    def update_ratings(self, artifact_a: str, artifact_b: str, score_a: float, score_b: float):
        """
        Update Elo ratings based on pairwise comparison.
        
        Args:
            artifact_a, artifact_b: Artifact IDs
            score_a, score_b: Normalized scores (0-1, where 1 means A wins)
        """
        rating_a = self.ratings[artifact_a]
        rating_b = self.ratings[artifact_b]
        
        expected_a = self.expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a
        
        # Update ratings
        self.ratings[artifact_a] = rating_a + self.k_factor * (score_a - expected_a)
        self.ratings[artifact_b] = rating_b + self.k_factor * (score_b - expected_b)
        
        self.match_history.append({
            "artifact_a": artifact_a,
            "artifact_b": artifact_b,
            "score_a": score_a,
            "score_b": score_b,
            "rating_a_before": rating_a,
            "rating_b_before": rating_b,
            "rating_a_after": self.ratings[artifact_a],
            "rating_b_after": self.ratings[artifact_b]
        })
    
    def get_rankings(self) -> Dict[str, float]:
        """Get current Elo ratings."""
        return dict(self.ratings)
    
    def reset(self):
        """Reset all ratings to initial value."""
        self.ratings = defaultdict(lambda: self.initial_rating)
        self.match_history = []


class AverageScoreVoting(VotingSystem):
    """Simple average of all judge scores."""
    
    def vote(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Average scores across all judges."""
        artifact_scores = defaultdict(list)
        
        for judge_id, scores in judge_scores.items():
            for artifact_id, score in scores.items():
                artifact_scores[artifact_id].append(score)
        
        # Calculate average for each artifact
        return {
            artifact_id: statistics.mean(scores)
            for artifact_id, scores in artifact_scores.items()
        }


# ============================================================================
# Experiment Results
# ============================================================================

@dataclass
class ExperimentResult:
    """Results from a single experiment run."""
    experiment_name: str
    timestamp: str
    config: Dict[str, Any]
    rankings: Dict[str, float]
    stability_metrics: Dict[str, float] = field(default_factory=dict)
    fairness_metrics: Dict[str, float] = field(default_factory=dict)
    volatility_metrics: Dict[str, float] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "experiment_name": self.experiment_name,
            "timestamp": self.timestamp,
            "config": self.config,
            "rankings": self.rankings,
            "stability_metrics": self.stability_metrics,
            "fairness_metrics": self.fairness_metrics,
            "volatility_metrics": self.volatility_metrics,
            "raw_data": self.raw_data
        }


# ============================================================================
# Main Experiments Class
# ============================================================================

class VotingExperiments:
    """Main class for running voting system experiments."""
    
    def __init__(self, num_judges: int = 5, model: str = "gpt-4o-mini"):
        """
        Initialize experiments system.
        
        Args:
            num_judges: Default number of judge agents
            model: OpenAI model to use for judges
        """
        self.num_judges = num_judges
        self.model = model
        self.judges = []
    
    def _create_judge_agents(self, num_judges: Optional[int] = None) -> List[Agent]:
        """Create judge agents for evaluation."""
        if num_judges is None:
            num_judges = self.num_judges
        
        judges = []
        instructions = """You are an expert evaluator of code artifacts.

Evaluate artifacts based on:
1. Code quality and correctness
2. Visual fidelity and aesthetics (if applicable)
3. Functionality and completeness
4. Innovation and creativity
5. Adherence to requirements

Provide a score from 0-10 for each artifact. Be thorough and objective in your evaluation."""
        
        for i in range(num_judges):
            judge = Agent(
                name=f"Judge_{i+1}",
                instructions=instructions,
                model=self.model
            )
            judges.append(judge)
        
        return judges
    
    def _evaluate_artifact(self, judge: Agent, artifact: Dict[str, Any]) -> float:
        """
        Evaluate a single artifact with a judge agent.
        
        Args:
            judge: Judge agent
            artifact: Artifact dictionary with 'id', 'generated_code', 'task', etc.
            
        Returns:
            Score from 0-10
        """
        prompt = f"""Evaluate the following code artifact:

Task: {artifact.get('task', 'N/A')}

Generated Code:
```
{artifact.get('generated_code', 'N/A')}
```

Requirements:
{chr(10).join(f"- {req}" for req in artifact.get('requirements', []))}

Please provide a single numerical score from 0-10 representing the overall quality of this artifact.
Respond with ONLY the number (e.g., "8.5" or "7")."""

        session = InMemorySession()
        result = Runner.run_sync(judge, prompt, session=session)
        
        # Extract score from response
        response_text = str(result.final_output).strip()
        
        # Try to extract number
        import re
        score_match = re.search(r'(\d+\.?\d*)', response_text)
        if score_match:
            score = float(score_match.group(1))
            # Clamp to 0-10 range
            return max(0.0, min(10.0, score))
        
        # Default if extraction fails
        return 5.0
    
    def _aggregate_scores(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Aggregate scores using simple average."""
        aggregator = AverageScoreVoting()
        return aggregator.vote(judge_scores)
    
    def _calculate_stability(
        self,
        rankings: Dict[str, float],
        judge_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate stability metrics.
        
        Returns:
            Dictionary with stability metrics
        """
        if not judge_scores:
            return {}
        
        # Calculate inter-judge agreement (standard deviation of scores per artifact)
        artifact_stds = {}
        for artifact_id in rankings.keys():
            scores = [
                scores.get(artifact_id, 0)
                for scores in judge_scores.values()
                if artifact_id in scores
            ]
            if scores:
                artifact_stds[artifact_id] = statistics.stdev(scores) if len(scores) > 1 else 0.0
        
        avg_std = statistics.mean(artifact_stds.values()) if artifact_stds else 0.0
        
        return {
            "average_std_dev": avg_std,
            "max_std_dev": max(artifact_stds.values()) if artifact_stds else 0.0,
            "min_std_dev": min(artifact_stds.values()) if artifact_stds else 0.0,
            "artifact_stds": artifact_stds
        }
    
    def _calculate_fairness(
        self,
        rankings: Dict[str, float],
        judge_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate fairness metrics (consistency across judges).
        """
        if not judge_scores:
            return {}
        
        # Calculate correlation between judge rankings
        judge_rankings = {}
        for judge_id, scores in judge_scores.items():
            sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            judge_rankings[judge_id] = {item[0]: rank for rank, item in enumerate(sorted_items)}
        
        # Calculate pairwise agreement
        agreements = []
        judge_list = list(judge_rankings.keys())
        for i in range(len(judge_list)):
            for j in range(i + 1, len(judge_list)):
                judge_a = judge_rankings[judge_list[i]]
                judge_b = judge_rankings[judge_list[j]]
                
                # Calculate Spearman-like correlation
                common_artifacts = set(judge_a.keys()) & set(judge_b.keys())
                if len(common_artifacts) > 1:
                    ranks_a = [judge_a[a] for a in common_artifacts]
                    ranks_b = [judge_b[a] for a in common_artifacts]
                    # Simple correlation
                    if len(ranks_a) > 1:
                        try:
                            correlation = statistics.correlation(ranks_a, ranks_b)
                            agreements.append(abs(correlation))
                        except:
                            pass
        
        avg_agreement = statistics.mean(agreements) if agreements else 0.0
        
        return {
            "average_judge_agreement": avg_agreement,
            "num_judge_pairs": len(agreements)
        }
    
    def _calculate_volatility(self, rankings: Dict[str, float]) -> Dict[str, float]:
        """Calculate volatility metrics."""
        if not rankings:
            return {}
        
        scores = list(rankings.values())
        return {
            "score_range": max(scores) - min(scores) if scores else 0.0,
            "score_std": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "score_variance": statistics.variance(scores) if len(scores) > 1 else 0.0
        }
    
    def _calculate_agreement_rate(self, judge_scores: Dict[str, Dict[str, float]]) -> float:
        """Calculate percentage of judges that agree on top artifact."""
        if not judge_scores:
            return 0.0
        
        top_artifacts = []
        for scores in judge_scores.values():
            if scores:
                top = max(scores.items(), key=lambda x: x[1])[0]
                top_artifacts.append(top)
        
        if not top_artifacts:
            return 0.0
        
        # Most common top artifact
        counter = Counter(top_artifacts)
        most_common_count = counter.most_common(1)[0][1] if counter else 0
        return most_common_count / len(top_artifacts)
    
    def _calculate_ranking_noise(self, judge_scores: Dict[str, Dict[str, float]]) -> float:
        """Calculate ranking noise (inconsistency in rankings)."""
        if not judge_scores:
            return 0.0
        
        # Get all artifacts
        all_artifacts = set()
        for scores in judge_scores.values():
            all_artifacts.update(scores.keys())
        
        # Calculate average rank variance for each artifact
        rank_variances = []
        for artifact_id in all_artifacts:
            ranks = []
            for scores in judge_scores.values():
                if artifact_id in scores:
                    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    rank = next((i for i, (aid, _) in enumerate(sorted_items) if aid == artifact_id), len(sorted_items))
                    ranks.append(rank)
            
            if len(ranks) > 1:
                rank_variances.append(statistics.variance(ranks))
        
        return statistics.mean(rank_variances) if rank_variances else 0.0
    
    def _calculate_convergence(self, judge_scores: Dict[str, Dict[str, float]]) -> float:
        """Calculate how much judges converge (lower is better convergence)."""
        return self._calculate_ranking_noise(judge_scores)
    
    def _calculate_disagreement(self, judge_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate disagreement score for each artifact."""
        all_artifacts = set()
        for scores in judge_scores.values():
            all_artifacts.update(scores.keys())
        
        disagreement = {}
        for artifact_id in all_artifacts:
            scores = [
                scores.get(artifact_id, 0)
                for scores in judge_scores.values()
                if artifact_id in scores
            ]
            if scores:
                disagreement[artifact_id] = statistics.stdev(scores) if len(scores) > 1 else 0.0
        
        return disagreement
    
    def _detect_flip_flops(self, judge_scores: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Detect artifacts where rankings flip dramatically."""
        # This would compare rankings across different voting rounds
        # For now, return empty list
        return []
    
    def _calculate_ranking_shifts(self, round_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate how rankings shift across rounds."""
        if len(round_results) < 2:
            return {}
        
        shifts = {}
        for i in range(1, len(round_results)):
            prev_rankings = round_results[i-1]["rankings"]
            curr_rankings = round_results[i]["rankings"]
            
            # Calculate rank changes
            prev_sorted = sorted(prev_rankings.items(), key=lambda x: x[1], reverse=True)
            curr_sorted = sorted(curr_rankings.items(), key=lambda x: x[1], reverse=True)
            
            rank_changes = {}
            for artifact_id, _ in prev_sorted:
                prev_rank = next((j for j, (aid, _) in enumerate(prev_sorted) if aid == artifact_id), -1)
                curr_rank = next((j for j, (aid, _) in enumerate(curr_sorted) if aid == artifact_id), -1)
                if prev_rank >= 0 and curr_rank >= 0:
                    rank_changes[artifact_id] = curr_rank - prev_rank
            
            shifts[f"round_{i-1}_to_{i}"] = rank_changes
        
        return shifts
    
    def _compare_rankings(
        self,
        initial_scores: Dict[str, Dict[str, float]],
        updated_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Compare initial and updated rankings."""
        initial_rankings = self._aggregate_scores(initial_scores)
        updated_rankings = self._aggregate_scores(updated_scores)
        
        # Calculate rank correlation
        common_artifacts = set(initial_rankings.keys()) & set(updated_rankings.keys())
        if len(common_artifacts) < 2:
            return {"correlation": 0.0}
        
        initial_sorted = sorted(initial_rankings.items(), key=lambda x: x[1], reverse=True)
        updated_sorted = sorted(updated_rankings.items(), key=lambda x: x[1], reverse=True)
        
        initial_ranks = {aid: rank for rank, (aid, _) in enumerate(initial_sorted)}
        updated_ranks = {aid: rank for rank, (aid, _) in enumerate(updated_sorted)}
        
        ranks_a = [initial_ranks[a] for a in common_artifacts]
        ranks_b = [updated_ranks[a] for a in common_artifacts]
        
        try:
            correlation = statistics.correlation(ranks_a, ranks_b)
        except:
            correlation = 0.0
        
        return {"correlation": correlation}
    
    def _analyze_consensus_patterns(
        self,
        all_scores: Dict[str, Dict[str, float]],
        human_scores: Dict[str, Dict[str, float]],
        llm_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Analyze consensus patterns between human and LLM judges."""
        # Calculate agreement between human and LLM judges
        human_avg = self._aggregate_scores(human_scores)
        llm_avg = self._aggregate_scores(llm_scores)
        
        common_artifacts = set(human_avg.keys()) & set(llm_avg.keys())
        if len(common_artifacts) < 2:
            return {"agreement": 0.0}
        
        human_scores_list = [human_avg[a] for a in common_artifacts]
        llm_scores_list = [llm_avg[a] for a in common_artifacts]
        
        try:
            correlation = statistics.correlation(human_scores_list, llm_scores_list)
        except:
            correlation = 0.0
        
        return {
            "human_llm_correlation": correlation,
            "num_common_artifacts": len(common_artifacts)
        }
    
    def _calibrate_llm_judges(
        self,
        llm_scores: Dict[str, Dict[str, float]],
        human_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calibrate LLM judges against human baseline."""
        human_avg = self._aggregate_scores(human_scores)
        llm_avg = self._aggregate_scores(llm_scores)
        
        common_artifacts = set(human_avg.keys()) & set(llm_avg.keys())
        
        if not common_artifacts:
            return {"calibration_factor": 1.0, "bias": 0.0}
        
        # Calculate average difference
        differences = [llm_avg[a] - human_avg[a] for a in common_artifacts]
        avg_bias = statistics.mean(differences)
        
        return {
            "average_bias": avg_bias,
            "calibration_factor": 1.0 - (avg_bias / 10.0) if avg_bias != 0 else 1.0,
            "num_artifacts": len(common_artifacts)
        }
    
    def _create_debate_prompt(
        self,
        artifacts: List[Dict[str, Any]],
        current_scores: Dict[str, Dict[str, float]],
        round_num: int
    ) -> str:
        """Create prompt for debate round."""
        prompt = f"""Debate Round {round_num + 1}

Current scores from all judges:
"""
        for artifact in artifacts:
            artifact_id = artifact['id']
            scores = [scores.get(artifact_id, 0) for scores in current_scores.values() if artifact_id in scores]
            avg_score = statistics.mean(scores) if scores else 0.0
            prompt += f"\n{artifact_id}: Average score {avg_score:.2f} (range: {min(scores):.2f}-{max(scores):.2f})"
        
        prompt += "\n\nPlease provide your critique and any score adjustments you'd like to make."
        return prompt
    
    def _get_judge_critique(self, judge: Agent, debate_prompt: str) -> str:
        """Get critique from a judge during debate."""
        session = InMemorySession()
        result = Runner.run_sync(judge, debate_prompt, session=session)
        return str(result.final_output)
    
    def _update_scores_from_debate(
        self,
        judge: Agent,
        artifacts: List[Dict[str, Any]],
        critiques: Dict[str, str]
    ) -> Dict[str, float]:
        """Update scores based on debate critiques."""
        # Simplified: re-evaluate with context of critiques
        updated_scores = {}
        for artifact in artifacts:
            score = self._evaluate_artifact(judge, artifact)
            updated_scores[artifact['id']] = score
        return updated_scores
    
    # ========================================================================
    # Experiment Implementations
    # ========================================================================
    
    def experiment_1_voting_systems(
        self,
        artifacts: List[Dict[str, Any]],
        voting_systems: Optional[List[VotingSystem]] = None
    ) -> Dict[str, ExperimentResult]:
        """
        Experiment 1: Compare different voting systems.
        
        Args:
            artifacts: List of artifacts to evaluate
            voting_systems: List of voting system instances (default: all systems)
            
        Returns:
            Results for each voting system
        """
        if voting_systems is None:
            voting_systems = [
                SimpleMajorityVoting(),
                BordaCountVoting(),
                AverageScoreVoting()
            ]
        
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        # Get scores from all judges
        print("Collecting scores from all judges...")
        judge_scores = {}
        for judge in self.judges:
            print(f"  Evaluating with {judge.name}...")
            scores = {}
            for artifact in artifacts:
                score = self._evaluate_artifact(judge, artifact)
                scores[artifact['id']] = score
            judge_scores[judge.name] = scores
        
        # Run each voting system
        results = {}
        for voting_system in voting_systems:
            system_name = voting_system.__class__.__name__
            print(f"\nRunning {system_name}...")
            
            rankings = voting_system.vote(judge_scores)
            
            # Calculate metrics
            stability = self._calculate_stability(rankings, judge_scores)
            fairness = self._calculate_fairness(rankings, judge_scores)
            volatility = self._calculate_volatility(rankings)
            
            results[system_name] = ExperimentResult(
                experiment_name=f"VotingSystem_{system_name}",
                timestamp=datetime.now().isoformat(),
                config={
                    "num_judges": len(self.judges),
                    "num_artifacts": len(artifacts),
                    "voting_system": system_name
                },
                rankings=rankings,
                stability_metrics=stability,
                fairness_metrics=fairness,
                volatility_metrics=volatility,
                raw_data={"judge_scores": judge_scores}
            )
        
        return results
    
    def experiment_2_debate_rounds(
        self,
        artifacts: List[Dict[str, Any]],
        num_debate_rounds: int = 2
    ) -> ExperimentResult:
        """
        Experiment 2: Multi-agent debate after initial scoring.
        
        Judges debate over decisions and update scores.
        """
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        # Initial scoring
        print("Initial scoring round...")
        initial_scores = {}
        for judge in self.judges:
            scores = {}
            for artifact in artifacts:
                score = self._evaluate_artifact(judge, artifact)
                scores[artifact['id']] = score
            initial_scores[judge.name] = scores
        
        # Debate rounds
        print(f"\nRunning {num_debate_rounds} debate rounds...")
        debate_transcripts = []
        current_scores = initial_scores.copy()
        
        for round_num in range(num_debate_rounds):
            print(f"  Debate Round {round_num + 1}...")
            
            # Create debate session
            debate_prompt = self._create_debate_prompt(artifacts, current_scores, round_num)
            
            # Each judge provides critique
            critiques = {}
            for judge in self.judges:
                critique = self._get_judge_critique(judge, debate_prompt)
                critiques[judge.name] = critique
            
            debate_transcripts.append({
                "round": round_num + 1,
                "critiques": critiques
            })
            
            # Judges update scores based on debate
            updated_scores = {}
            for judge in self.judges:
                updated = self._update_scores_from_debate(judge, artifacts, critiques)
                updated_scores[judge.name] = updated
            
            current_scores = updated_scores
        
        # Final rankings
        final_rankings = self._aggregate_scores(current_scores)
        initial_rankings = self._aggregate_scores(initial_scores)
        
        return ExperimentResult(
            experiment_name="DebateRounds",
            timestamp=datetime.now().isoformat(),
            config={
                "num_judges": len(self.judges),
                "num_debate_rounds": num_debate_rounds,
                "num_artifacts": len(artifacts)
            },
            rankings=final_rankings,
            stability_metrics=self._compare_rankings(initial_scores, current_scores),
            fairness_metrics={},
            volatility_metrics={},
            raw_data={
                "debate_transcripts": debate_transcripts,
                "initial_rankings": initial_rankings,
                "final_rankings": final_rankings,
                "score_evolution": {
                    "initial": initial_scores,
                    "final": current_scores
                }
            }
        )
    
    def experiment_3_human_llm_mix(
        self,
        artifacts: List[Dict[str, Any]],
        human_scores: Dict[str, Dict[str, float]]
    ) -> ExperimentResult:
        """
        Experiment 3: Mix human expert votes with LLM committee.
        
        Args:
            artifacts: Artifacts to evaluate
            human_scores: {human_judge_id: {artifact_id: score}}
        """
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        # Get LLM judge scores
        print("Collecting LLM judge scores...")
        llm_scores = {}
        for judge in self.judges:
            scores = {}
            for artifact in artifacts:
                score = self._evaluate_artifact(judge, artifact)
                scores[artifact['id']] = score
            llm_scores[judge.name] = scores
        
        # Combine human and LLM scores
        all_scores = {**llm_scores, **human_scores}
        
        # Analyze consensus patterns
        consensus_metrics = self._analyze_consensus_patterns(all_scores, human_scores, llm_scores)
        
        # Calibrate LLM judges against human baseline
        calibration = self._calibrate_llm_judges(llm_scores, human_scores)
        
        return ExperimentResult(
            experiment_name="HumanLLMMix",
            timestamp=datetime.now().isoformat(),
            config={
                "num_llm_judges": len(self.judges),
                "num_human_judges": len(human_scores),
                "num_artifacts": len(artifacts)
            },
            rankings=self._aggregate_scores(all_scores),
            stability_metrics={},
            fairness_metrics=consensus_metrics,
            volatility_metrics={},
            raw_data={
                "calibration": calibration,
                "human_scores": human_scores,
                "llm_scores": llm_scores
            }
        )
    
    def experiment_4_agent_pool_scaling(
        self,
        artifacts: List[Dict[str, Any]],
        judge_pool_sizes: List[int] = [3, 5, 10, 15, 20]
    ) -> Dict[int, ExperimentResult]:
        """
        Experiment 4: Test effects of increasing judge pool size.
        
        Args:
            artifacts: Artifacts to evaluate
            judge_pool_sizes: List of judge pool sizes to test
            
        Returns:
            Results for each pool size
        """
        results = {}
        
        for pool_size in judge_pool_sizes:
            print(f"\nTesting with {pool_size} judges...")
            
            # Create judge pool of this size
            pool_judges = self._create_judge_agents(pool_size)
            
            # Get scores
            judge_scores = {}
            for judge in pool_judges:
                scores = {}
                for artifact in artifacts:
                    score = self._evaluate_artifact(judge, artifact)
                    scores[artifact['id']] = score
                judge_scores[judge.name] = scores
            
            # Calculate metrics
            rankings = self._aggregate_scores(judge_scores)
            agreement_rate = self._calculate_agreement_rate(judge_scores)
            ranking_noise = self._calculate_ranking_noise(judge_scores)
            convergence = self._calculate_convergence(judge_scores)
            
            results[pool_size] = ExperimentResult(
                experiment_name=f"AgentPoolScaling_{pool_size}",
                timestamp=datetime.now().isoformat(),
                config={
                    "pool_size": pool_size,
                    "num_artifacts": len(artifacts)
                },
                rankings=rankings,
                stability_metrics={
                    "agreement_rate": agreement_rate,
                    "convergence": convergence
                },
                fairness_metrics={},
                volatility_metrics={"ranking_noise": ranking_noise},
                raw_data={"judge_scores": judge_scores}
            )
        
        return results
    
    def experiment_5_artifact_quality_diversity(
        self,
        strong_artifacts: List[Dict[str, Any]],
        weak_artifacts: List[Dict[str, Any]]
    ) -> ExperimentResult:
        """
        Experiment 5: Test voting robustness with diverse artifact quality.
        
        Args:
            strong_artifacts: High-quality artifacts
            weak_artifacts: Low-quality artifacts
        """
        all_artifacts = strong_artifacts + weak_artifacts
        
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        # Get scores from judges
        print("Evaluating artifacts with diverse quality...")
        judge_scores = {}
        
        for judge in self.judges:
            scores = {}
            for artifact in all_artifacts:
                score = self._evaluate_artifact(judge, artifact)
                scores[artifact['id']] = score
            judge_scores[judge.name] = scores
        
        # Identify difficult artifacts (high disagreement)
        disagreement_scores = self._calculate_disagreement(judge_scores)
        difficult_artifacts = [
            artifact_id for artifact_id, score in disagreement_scores.items()
            if score > statistics.median(list(disagreement_scores.values()))
        ]
        
        # Track flip-flops (rankings that change dramatically)
        flip_flops = self._detect_flip_flops(judge_scores)
        
        return ExperimentResult(
            experiment_name="ArtifactQualityDiversity",
            timestamp=datetime.now().isoformat(),
            config={
                "num_strong": len(strong_artifacts),
                "num_weak": len(weak_artifacts),
                "num_judges": len(self.judges)
            },
            rankings=self._aggregate_scores(judge_scores),
            stability_metrics={"disagreement": disagreement_scores},
            fairness_metrics={},
            volatility_metrics={"flip_flops": flip_flops},
            raw_data={
                "difficult_artifacts": difficult_artifacts,
                "judge_scores": judge_scores,
                "strong_artifacts": [a['id'] for a in strong_artifacts],
                "weak_artifacts": [a['id'] for a in weak_artifacts]
            }
        )
    
    def experiment_6_iterative_voting(
        self,
        artifacts: List[Dict[str, Any]],
        elimination_rounds: int = 3,
        eliminate_per_round: int = 1
    ) -> ExperimentResult:
        """
        Experiment 6: Multi-round elimination tournament.
        
        Args:
            artifacts: Initial artifact pool
            elimination_rounds: Number of elimination rounds
            eliminate_per_round: Number of artifacts to eliminate per round
        """
        remaining_artifacts = artifacts.copy()
        round_results = []
        
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        print(f"Starting elimination tournament: {len(artifacts)} artifacts, {elimination_rounds} rounds")
        
        for round_num in range(elimination_rounds):
            if len(remaining_artifacts) <= eliminate_per_round:
                print(f"  Not enough artifacts remaining for round {round_num + 1}")
                break
            
            print(f"\nRound {round_num + 1}: {len(remaining_artifacts)} artifacts remaining")
            
            # Vote on remaining artifacts
            judge_scores = {}
            for judge in self.judges:
                scores = {}
                for artifact in remaining_artifacts:
                    score = self._evaluate_artifact(judge, artifact)
                    scores[artifact['id']] = score
                judge_scores[judge.name] = scores
            
            rankings = self._aggregate_scores(judge_scores)
            
            # Eliminate lowest-ranked artifacts
            sorted_artifacts = sorted(rankings.items(), key=lambda x: x[1])
            eliminated = [aid for aid, _ in sorted_artifacts[:eliminate_per_round]]
            remaining_artifacts = [
                a for a in remaining_artifacts if a['id'] not in eliminated
            ]
            
            print(f"  Eliminated: {eliminated}")
            print(f"  Remaining: {[a['id'] for a in remaining_artifacts]}")
            
            round_results.append({
                "round": round_num + 1,
                "rankings": rankings,
                "eliminated": eliminated,
                "remaining": [a['id'] for a in remaining_artifacts]
            })
        
        # Final rankings
        final_rankings = round_results[-1]["rankings"] if round_results else {}
        
        # Calculate ranking shifts
        ranking_shifts = self._calculate_ranking_shifts(round_results)
        
        return ExperimentResult(
            experiment_name="IterativeVoting",
            timestamp=datetime.now().isoformat(),
            config={
                "initial_artifacts": len(artifacts),
                "elimination_rounds": elimination_rounds,
                "eliminate_per_round": eliminate_per_round
            },
            rankings=final_rankings,
            stability_metrics={"ranking_shifts": ranking_shifts},
            fairness_metrics={},
            volatility_metrics={},
            raw_data={"round_results": round_results}
        )
    
    def experiment_7_elo_pairwise(
        self,
        artifacts: List[Dict[str, Any]],
        num_matchups: Optional[int] = None
    ) -> ExperimentResult:
        """
        Experiment 7: Elo rating system with pairwise comparisons.
        
        Args:
            artifacts: Artifacts to rank
            num_matchups: Number of pairwise matchups (default: all pairs)
        """
        # Create judges if not already created
        if not self.judges:
            self.judges = self._create_judge_agents()
        
        elo_system = EloRatingSystem()
        
        # Generate pairwise matchups
        if num_matchups is None:
            num_matchups = len(artifacts) * (len(artifacts) - 1) // 2
        
        print(f"Running Elo pairwise comparisons: {num_matchups} matchups")
        
        # Create all possible pairs
        pairs = []
        for i in range(len(artifacts)):
            for j in range(i + 1, len(artifacts)):
                pairs.append((artifacts[i], artifacts[j]))
        
        # Randomly sample if needed
        if len(pairs) > num_matchups:
            pairs = random.sample(pairs, num_matchups)
        
        # Evaluate each pair
        for idx, (artifact_a, artifact_b) in enumerate(pairs):
            print(f"  Matchup {idx + 1}/{len(pairs)}: {artifact_a['id']} vs {artifact_b['id']}")
            
            # Get scores from all judges for both artifacts
            scores_a = []
            scores_b = []
            
            for judge in self.judges:
                score_a = self._evaluate_artifact(judge, artifact_a)
                score_b = self._evaluate_artifact(judge, artifact_b)
                scores_a.append(score_a)
                scores_b.append(score_b)
            
            # Average scores
            avg_a = statistics.mean(scores_a) / 10.0  # Normalize to 0-1
            avg_b = statistics.mean(scores_b) / 10.0
            
            # Update Elo ratings
            elo_system.update_ratings(
                artifact_a['id'],
                artifact_b['id'],
                avg_a,
                avg_b
            )
        
        # Get final rankings
        final_rankings = elo_system.get_rankings()
        
        return ExperimentResult(
            experiment_name="EloPairwise",
            timestamp=datetime.now().isoformat(),
            config={
                "num_artifacts": len(artifacts),
                "num_matchups": len(pairs),
                "num_judges": len(self.judges)
            },
            rankings=final_rankings,
            stability_metrics={},
            fairness_metrics={},
            volatility_metrics={},
            raw_data={
                "elo_history": elo_system.match_history,
                "initial_rating": elo_system.initial_rating
            }
        )
    
    def save_results(self, results: Dict[str, Any], filename: str = "experiment_results.json"):
        """Save experiment results to JSON file."""
        serializable = {}
        for key, value in results.items():
            if isinstance(value, ExperimentResult):
                serializable[key] = value.to_dict()
            elif isinstance(value, dict):
                serializable[key] = {
                    k: v.to_dict() if isinstance(v, ExperimentResult) else v
                    for k, v in value.items()
                }
            else:
                serializable[key] = value
        
        with open(filename, 'w') as f:
            json.dump(serializable, f, indent=2)
        
        print(f"\nResults saved to {filename}")


def main():
    """Example usage of experiments."""
    import os
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Example: Run voting systems experiment
    experiments = VotingExperiments(num_judges=3, model="gpt-4o-mini")
    
    # Sample artifacts (would come from your artifact generation)
    sample_artifacts = [
        {
            "id": "artifact_1",
            "task": "Create a bouncing ball",
            "generated_code": "<svg>...</svg>",
            "requirements": ["Ball bounces", "Smooth animation"]
        },
        {
            "id": "artifact_2",
            "task": "Create a clock",
            "generated_code": "<html>...</html>",
            "requirements": ["Shows time", "Analog display"]
        }
    ]
    
    print("Running Experiment 1: Voting Systems Comparison")
    results = experiments.experiment_1_voting_systems(sample_artifacts)
    
    experiments.save_results(results, "voting_systems_results.json")


if __name__ == "__main__":
    main()

