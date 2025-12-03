"""
Token Tracking System - Usage Monitoring for Multi-Agent Debates

This module provides token usage tracking functionality using the OpenAI Agents SDK
usage API. It tracks input tokens, output tokens, total tokens, and costs across
all agents in a debate. Maintains persistent statistics across runs in a JSON file.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from agents import Agent, Runner
from debate_system import DebateSystem, InMemorySession
import time
import json
import os
from datetime import datetime

# Default token tracking directory
# Individual experiment files should define their own token file paths
TOKEN_TRACKING_DIR = "token_tracking"
# Default file (for backward compatibility, but experiments should use their own)
TOKEN_USAGE_FILE = os.path.join(TOKEN_TRACKING_DIR, "token_usage_history.json")


@dataclass
class AgentUsage:
    """Track usage for a single agent response."""
    agent_name: str
    round: int
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class DebateUsage:
    """Aggregate usage statistics for an entire debate."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cached_tokens: int = 0
    total_reasoning_tokens: int = 0
    agent_usages: List[AgentUsage] = field(default_factory=list)
    
    def add_agent_usage(self, usage: AgentUsage):
        """Add an agent's usage to the total."""
        self.agent_usages.append(usage)
        self.total_requests += usage.requests
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_tokens += usage.total_tokens
        self.total_cached_tokens += usage.cached_tokens
        self.total_reasoning_tokens += usage.reasoning_tokens
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary dictionary of all usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cached_tokens": self.total_cached_tokens,
            "total_reasoning_tokens": self.total_reasoning_tokens,
            "num_agents": len(set(u.agent_name for u in self.agent_usages)),
            "num_rounds": max((u.round for u in self.agent_usages), default=0)
        }


def load_token_history(filename: str = TOKEN_USAGE_FILE) -> Dict[str, Any]:
    """
    Load token usage history from JSON file.
    Handles both old format (model keys) and new format (experiments + cumulative_by_model).
    
    Args:
        filename: Path to JSON file
        
    Returns:
        Dictionary with experiments list and cumulative_by_model
    """
    # Ensure directory exists in filename path
    if not filename.startswith(TOKEN_TRACKING_DIR) and TOKEN_TRACKING_DIR not in filename:
        filename = os.path.join(TOKEN_TRACKING_DIR, os.path.basename(filename))
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Migrate old format to new format if needed
            if "experiments" not in data:
                # Old format: just model keys
                data = migrate_old_format(data)
            
            return data
        except (json.JSONDecodeError, IOError):
            return {"experiments": [], "cumulative_by_model": {}}
    return {"experiments": [], "cumulative_by_model": {}}


def migrate_old_format(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old format (model keys) to new format (experiments + cumulative_by_model).
    
    Args:
        old_data: Old format dictionary with model keys
        
    Returns:
        New format dictionary
    """
    new_data = {
        "experiments": [],
        "cumulative_by_model": {}
    }
    
    # Convert old format to new format
    for model, stats in old_data.items():
        if isinstance(stats, dict) and "input_tokens" in stats:
            # This is a model entry in old format
            new_data["cumulative_by_model"][model] = stats.copy()
            # Create placeholder experiments for old data (we don't have individual records)
            # Just keep cumulative totals
        else:
            # Might be something else, preserve it
            new_data["cumulative_by_model"][model] = stats
    
    return new_data


def save_token_history(history: Dict[str, Any], filename: str = TOKEN_USAGE_FILE):
    """
    Save token usage history to JSON file.
    
    Args:
        history: Dictionary of model statistics
        filename: Path to JSON file
    """
    # Ensure directory exists in filename path
    if not filename.startswith(TOKEN_TRACKING_DIR) and TOKEN_TRACKING_DIR not in filename:
        filename = os.path.join(TOKEN_TRACKING_DIR, os.path.basename(filename))
    
    # Create directory if it doesn't exist
    dir_path = os.path.dirname(filename) if os.path.dirname(filename) else TOKEN_TRACKING_DIR
    os.makedirs(dir_path, exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(history, f, indent=2)


# Model pricing (per 1K tokens) - as of 2024
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # $0.15/$0.60 per 1M tokens
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.15, "output": 0.60},  # Assuming same as gpt-4o-mini
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost based on model pricing.
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Cost in USD
    """
    # Normalize model name (handle variations)
    model_lower = model.lower()
    pricing = None
    
    for key in MODEL_PRICING:
        if key in model_lower:
            pricing = MODEL_PRICING[key]
            break
    
    if not pricing:
        # Default to gpt-4o-mini pricing if unknown
        pricing = MODEL_PRICING["gpt-4o-mini"]
    
    # Calculate cost (pricing is per 1M tokens, so divide by 1,000,000)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost


def update_model_statistics(
    model: str, 
    input_tokens: int, 
    output_tokens: int, 
    total_tokens: int,
    experiment_name: str = None,
    token_file: str = None
) -> Dict[str, Any]:
    """
    Update persistent statistics for a specific model and add experiment record.
    
    This function loads existing statistics, adds the current run's tokens to the
    cumulative totals for the model, and saves back to the JSON file.
    Also records individual experiment details.
    
    Args:
        model: Model name (e.g., 'gpt-4', 'gpt-4o-mini')
        input_tokens: Input tokens from current run
        output_tokens: Output tokens from current run
        total_tokens: Total tokens from current run
        experiment_name: Optional name/identifier for this experiment run
        
    Returns:
        Updated statistics for the model
    """
    # Load existing history
    history = load_token_history()
    
    # Initialize structure if needed
    if "experiments" not in history:
        history["experiments"] = []
    
    if "cumulative_by_model" not in history:
        history["cumulative_by_model"] = {}
    
    # Calculate cost
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    # Add experiment record
    experiment_record = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost, 4),
        "experiment_name": experiment_name or "unnamed_experiment",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    history["experiments"].append(experiment_record)
    
    # Update cumulative totals by model
    cumulative = history["cumulative_by_model"]
    if model not in cumulative:
        cumulative[model] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_runs": 0,
            "last_updated": None
        }
    
    # Add current run's tokens to cumulative totals
    cumulative[model]["input_tokens"] += input_tokens
    cumulative[model]["output_tokens"] += output_tokens
    cumulative[model]["total_tokens"] += total_tokens
    cumulative[model]["total_runs"] += 1
    cumulative[model]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save updated history (use custom file if provided)
    if token_file:
        save_token_history(history, token_file)
    else:
        save_token_history(history)
    
    return cumulative[model]


class TokenTrackingDebateSystem:
    """
    Enhanced DebateSystem with token usage tracking.
    
    This class wraps the standard DebateSystem to provide detailed token
    usage tracking for all agent interactions during a debate.
    """
    
    def __init__(self, num_agents: int = 3, model: str = "gpt-4"):
        """
        Initialize the token tracking debate system.
        
        Args:
            num_agents: Number of agents to participate in the debate
            model: OpenAI model to use for agents
        """
        self.num_agents = num_agents
        self.model = model
        self.agents = self._create_agents()
        self.usage_data = DebateUsage()
    
    def run_debate(self, topic: str, num_rounds: int = 2) -> Dict[str, Any]:
        """
        Execute a debate with token tracking.
        
        Args:
            topic: The debate topic
            num_rounds: Number of debate rounds
            
        Returns:
            Dictionary with 'transcript', 'usage', 'responses', and 'persistent_stats' keys
        """
        # Reset usage data for new debate
        self.usage_data = DebateUsage()
        
        # Create session for conversation history
        session = InMemorySession()
        session.add_message(role="user", content=f"Topic: {topic}")
        
        # Accumulate all responses
        all_responses = []
        
        # Execute rounds with tracking
        for round_num in range(1, num_rounds + 1):
            round_responses = self._execute_round_with_tracking(round_num, session)
            all_responses.extend(round_responses)
        
        # Format transcript
        transcript = self._format_transcript(all_responses)
        
        # Update persistent statistics for this model
        experiment_name = f"debate_{self.num_agents}agents_{len(self.usage_data.agent_usages)}responses"
        persistent_stats = update_model_statistics(
            model=self.model,
            input_tokens=self.usage_data.total_input_tokens,
            output_tokens=self.usage_data.total_output_tokens,
            total_tokens=self.usage_data.total_tokens,
            experiment_name=experiment_name
        )
        
        return {
            "transcript": transcript,
            "usage": self.usage_data,
            "responses": all_responses,
            "persistent_stats": persistent_stats
        }
    
    def _create_agents(self) -> List[Agent]:
        """Create agent instances with debate instructions."""
        agents = []
        
        debate_instructions = """You are participating in a collaborative debate. Your role is to:
1. Analyze the topic critically
2. Consider previous arguments from other agents
3. Provide your unique perspective
4. Build constructively on the discussion
5. Be concise but thorough in your responses"""
        
        for i in range(1, self.num_agents + 1):
            agent_name = f"Agent_{i}"
            agent = Agent(
                name=agent_name,
                instructions=debate_instructions,
                model=self.model
            )
            agents.append(agent)
        
        return agents
    
    def _execute_round_with_tracking(self, round_num: int, session) -> List[dict]:
        """
        Execute a single debate round with token tracking.
        
        Args:
            round_num: Current round number
            session: Session instance containing conversation history
            
        Returns:
            List of response dictionaries from this round
        """
        responses = []
        
        for agent in self.agents:
            # Execute agent with current conversation history
            input_text = f"Continue the debate (Round {round_num}). Provide your perspective."
            result = Runner.run_sync(agent, input_text, session=session)
            
            # Extract usage information from result
            usage = result.context_wrapper.usage
            
            # Safely extract cached and reasoning tokens if available
            cached_tokens = 0
            reasoning_tokens = 0
            
            if hasattr(usage, 'details') and usage.details:
                if hasattr(usage.details, 'input_tokens_details') and usage.details.input_tokens_details:
                    cached_tokens = getattr(usage.details.input_tokens_details, 'cached_tokens', 0)
                if hasattr(usage.details, 'output_tokens_details') and usage.details.output_tokens_details:
                    reasoning_tokens = getattr(usage.details.output_tokens_details, 'reasoning_tokens', 0)
            
            # Create AgentUsage record
            agent_usage = AgentUsage(
                agent_name=agent.name,
                round=round_num,
                requests=usage.requests,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                cached_tokens=cached_tokens,
                reasoning_tokens=reasoning_tokens
            )
            
            # Add to debate usage
            self.usage_data.add_agent_usage(agent_usage)
            
            # Collect response with metadata
            response_dict = {
                "agent_name": agent.name,
                "round": round_num,
                "content": str(result.final_output),
                "timestamp": time.time(),
                "usage": agent_usage
            }
            responses.append(response_dict)
        
        return responses
    
    def _format_transcript(self, responses: List[dict]) -> str:
        """Format all responses into a readable transcript."""
        transcript_lines = []
        transcript_lines.append("=" * 80)
        transcript_lines.append("DEBATE TRANSCRIPT (WITH TOKEN TRACKING)")
        transcript_lines.append("=" * 80)
        transcript_lines.append("")
        
        for response in responses:
            usage = response['usage']
            transcript_lines.append(f"[Round {response['round']}] {response['agent_name']}:")
            transcript_lines.append(f"  Tokens: {usage.total_tokens} (in: {usage.input_tokens}, out: {usage.output_tokens})")
            transcript_lines.append("-" * 80)
            transcript_lines.append(response['content'])
            transcript_lines.append("")
        
        transcript_lines.append("=" * 80)
        transcript_lines.append("END OF DEBATE")
        transcript_lines.append("=" * 80)
        
        return "\n".join(transcript_lines)
    
    def print_usage_summary(self, show_history: bool = True):
        """
        Print a formatted summary of token usage.
        
        Args:
            show_history: Whether to display cumulative statistics from persistent file
        """
        summary = self.usage_data.get_summary()
        
        print("\n" + "=" * 80)
        print("TOKEN USAGE SUMMARY (CURRENT RUN)")
        print("=" * 80)
        print(f"Model: {self.model}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Input Tokens: {summary['total_input_tokens']:,}")
        print(f"Total Output Tokens: {summary['total_output_tokens']:,}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        
        if summary['total_cached_tokens'] > 0:
            print(f"Cached Tokens: {summary['total_cached_tokens']:,}")
        if summary['total_reasoning_tokens'] > 0:
            print(f"Reasoning Tokens: {summary['total_reasoning_tokens']:,}")
        
        print(f"\nAgents: {summary['num_agents']}")
        print(f"Rounds: {summary['num_rounds']}")
        print(f"Average Tokens per Agent Response: {summary['total_tokens'] // summary['total_requests'] if summary['total_requests'] > 0 else 0:,}")
        
        # Show persistent cumulative history
        if show_history:
            history = load_token_history()
            if history and self.model in history:
                print("\n" + "=" * 80)
                print(f"CUMULATIVE STATISTICS FOR {self.model}")
                print("=" * 80)
                model_stats = history[self.model]
                print(f"Total Runs: {model_stats['total_runs']}")
                print(f"Cumulative Input Tokens: {model_stats['input_tokens']:,}")
                print(f"Cumulative Output Tokens: {model_stats['output_tokens']:,}")
                print(f"Cumulative Total Tokens: {model_stats['total_tokens']:,}")
                print(f"Last Updated: {model_stats['last_updated']}")
                
                # Show all models if there are multiple
                if len(history) > 1:
                    print("\n" + "-" * 80)
                    print("ALL MODELS SUMMARY")
                    print("-" * 80)
                    for model_name, stats in sorted(history.items()):
                        print(f"{model_name}: {stats['total_tokens']:,} tokens ({stats['total_runs']} runs)")
        
        # Detailed breakdown by agent and round
        print("\n" + "-" * 80)
        print("DETAILED BREAKDOWN BY AGENT AND ROUND (CURRENT RUN)")
        print("-" * 80)
        for usage in self.usage_data.agent_usages:
            print(f"{usage.agent_name} (Round {usage.round}): {usage.total_tokens:,} tokens "
                  f"(in: {usage.input_tokens:,}, out: {usage.output_tokens:,})")
        print("=" * 80)


def run_debate_with_tracking(topic: str, num_agents: int = 3, 
                             num_rounds: int = 2, model: str = "gpt-4") -> Dict[str, Any]:
    """
    Convenience function to run a debate with token tracking.
    
    Args:
        topic: The debate topic
        num_agents: Number of agents to participate
        num_rounds: Number of debate rounds
        model: OpenAI model to use
        
    Returns:
        Dictionary with transcript and usage data
    """
    debate_system = TokenTrackingDebateSystem(num_agents=num_agents, model=model)
    result = debate_system.run_debate(topic, num_rounds)
    
    # Print usage summary
    debate_system.print_usage_summary()
    
    return result


# ============================================================================
# DIRECT OPENAI API TOKEN TRACKING
# ============================================================================

@dataclass
class APIUsage:
    """Track usage for a single OpenAI API call."""
    operation: str  # e.g., "code_generation", "evaluation"
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class APITokenTracker:
    """
    Track token usage for direct OpenAI API calls (not using Agents SDK).
    """
    
    def __init__(self, experiment_name: str = None):
        """
        Initialize the API token tracker.
        
        Args:
            experiment_name: Optional name/identifier for this experiment run
        """
        self.usage_records: List[APIUsage] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.experiment_name = experiment_name
    
    def set_experiment_name(self, experiment_name: str):
        """Set or update the experiment name."""
        self.experiment_name = experiment_name
    
    def track_response(self, response, operation: str, model: str) -> APIUsage:
        """
        Track token usage from an OpenAI API response.
        
        Args:
            response: Response object from client.chat.completions.create()
            operation: Description of the operation (e.g., "code_generation", "evaluation")
            model: Model name used
            
        Returns:
            APIUsage object with token information
        """
        usage = response.usage
        
        api_usage = APIUsage(
            operation=operation,
            model=model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens
        )
        
        self.usage_records.append(api_usage)
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        
        # Update persistent statistics (will be saved when experiment completes)
        # We don't call update_model_statistics here to avoid saving on every call
        # Instead, we'll save once at the end with the experiment name
        
        return api_usage
    
    def save_experiment_to_history(self, token_file: str = None):
        """
        Save the complete experiment's token usage to history.
        Should be called once at the end of an experiment.
        Only saves final totals, not per-iteration.
        
        Args:
            token_file: Optional custom token file path (defaults to TOKEN_USAGE_FILE)
        """
        if self.total_tokens > 0:
            # Determine model from usage records (most common model)
            models = [u.model for u in self.usage_records]
            if models:
                most_common_model = max(set(models), key=models.count)
            else:
                most_common_model = "unknown"
            
            # Only save once at the end with final totals
            update_model_statistics(
                model=most_common_model,
                input_tokens=self.total_input_tokens,
                output_tokens=self.total_output_tokens,
                total_tokens=self.total_tokens,
                experiment_name=self.experiment_name,
                token_file=token_file
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked API calls."""
        return {
            "total_requests": len(self.usage_records),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "operations": list(set(u.operation for u in self.usage_records)),
            "models": list(set(u.model for u in self.usage_records))
        }
    
    def get_operation_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary grouped by operation type."""
        operation_summary = {}
        for usage in self.usage_records:
            if usage.operation not in operation_summary:
                operation_summary[usage.operation] = {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }
            op_sum = operation_summary[usage.operation]
            op_sum["count"] += 1
            op_sum["input_tokens"] += usage.input_tokens
            op_sum["output_tokens"] += usage.output_tokens
            op_sum["total_tokens"] += usage.total_tokens
        return operation_summary
    
    def print_summary(self, show_history: bool = True):
        """
        Print a formatted summary of token usage.
        
        Args:
            show_history: Whether to display cumulative statistics from persistent file
        """
        summary = self.get_summary()
        operation_summary = self.get_operation_summary()
        
        print("\n" + "=" * 80)
        print("TOKEN USAGE SUMMARY (CURRENT RUN - DIRECT API CALLS)")
        print("=" * 80)
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Input Tokens: {summary['total_input_tokens']:,}")
        print(f"Total Output Tokens: {summary['total_output_tokens']:,}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        
        if operation_summary:
            print("\n" + "-" * 80)
            print("BREAKDOWN BY OPERATION")
            print("-" * 80)
            for operation, stats in operation_summary.items():
                print(f"{operation}:")
                print(f"  Requests: {stats['count']}")
                print(f"  Input Tokens: {stats['input_tokens']:,}")
                print(f"  Output Tokens: {stats['output_tokens']:,}")
                print(f"  Total Tokens: {stats['total_tokens']:,}")
        
        # Show persistent cumulative history for each model
        if show_history:
            history = load_token_history()
            if history:
                print("\n" + "=" * 80)
                print("CUMULATIVE STATISTICS (ALL MODELS)")
                print("=" * 80)
                for model_name in summary['models']:
                    if model_name in history:
                        model_stats = history[model_name]
                        print(f"\n{model_name}:")
                        print(f"  Total Runs: {model_stats['total_runs']}")
                        print(f"  Cumulative Input Tokens: {model_stats['input_tokens']:,}")
                        print(f"  Cumulative Output Tokens: {model_stats['output_tokens']:,}")
                        print(f"  Cumulative Total Tokens: {model_stats['total_tokens']:,}")
                        print(f"  Last Updated: {model_stats['last_updated']}")
        
        print("=" * 80)
    
    def save_to_file(self, filename: str = None):
        """
        Save usage records to a JSON file.
        
        Args:
            filename: Optional filename, defaults to timestamped file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_token_usage_{timestamp}.json"
        
        data = {
            "summary": self.get_summary(),
            "operation_summary": self.get_operation_summary(),
            "detailed_records": [
                {
                    "operation": u.operation,
                    "model": u.model,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "total_tokens": u.total_tokens,
                    "timestamp": u.timestamp
                }
                for u in self.usage_records
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filename


# Global tracker instance for easy access
_global_tracker = None

def get_global_tracker(experiment_name: str = None) -> APITokenTracker:
    """
    Get or create the global API token tracker.
    
    Args:
        experiment_name: Optional name/identifier for the experiment
        
    Returns:
        Global APITokenTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = APITokenTracker(experiment_name=experiment_name)
    elif experiment_name and not _global_tracker.experiment_name:
        _global_tracker.set_experiment_name(experiment_name)
    return _global_tracker


# ============================================================================
# ITERATIVE REFINEMENT TOKEN TRACKING
# ============================================================================

def load_iterative_history(filename: str = None) -> Dict[str, Any]:
    """
    Load iterative refinement token usage history from JSON file.
    
    Args:
        filename: Path to JSON file (required - should be provided by calling experiment)
        
    Returns:
        Dictionary with experiment-level token usage
    """
    if filename is None:
        raise ValueError("filename is required for load_iterative_history")
    
    # Ensure directory exists in filename path
    if not filename.startswith(TOKEN_TRACKING_DIR) and TOKEN_TRACKING_DIR not in filename:
        filename = os.path.join(TOKEN_TRACKING_DIR, os.path.basename(filename))
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_iterative_history(history: Dict[str, Any], filename: str = None):
    """
    Save iterative refinement token usage history to JSON file.
    
    Args:
        history: Dictionary with experiment-level token usage
        filename: Path to JSON file (required - should be provided by calling experiment)
    """
    if filename is None:
        raise ValueError("filename is required for save_iterative_history")
    
    # Ensure directory exists in filename path
    if not filename.startswith(TOKEN_TRACKING_DIR) and TOKEN_TRACKING_DIR not in filename:
        filename = os.path.join(TOKEN_TRACKING_DIR, os.path.basename(filename))
    
    # Create directory if it doesn't exist
    dir_path = os.path.dirname(filename) if os.path.dirname(filename) else TOKEN_TRACKING_DIR
    os.makedirs(dir_path, exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(history, f, indent=2)


def update_iterative_statistics(
    experiment_name: str,
    task_name: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    model: str,
    token_file: str = None
) -> Dict[str, Any]:
    """
    Update iterative refinement statistics for a specific task within an experiment.
    
    Args:
        experiment_name: Experiment name (class name from dataset)
        task_name: Task identifier (e.g., "task_0", "task_1")
        input_tokens: Input tokens from current task
        output_tokens: Output tokens from current task
        total_tokens: Total tokens from current task
        model: Model name used
        token_file: Path to token tracking JSON file (required - should be provided by calling experiment)
        
    Returns:
        Updated statistics for the experiment
    """
    if token_file is None:
        raise ValueError("token_file is required for update_iterative_statistics")
    
    # Load existing history
    history = load_iterative_history(token_file)
    
    # Initialize experiment entry if doesn't exist
    if experiment_name not in history:
        history[experiment_name] = {
            "tasks": {},
            "total_cost_usd": 0.0
        }
    
    # Calculate cost
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    # Add task record
    history[experiment_name]["tasks"][task_name] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost, 4),
        "model": model,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Update total cost for experiment
    history[experiment_name]["total_cost_usd"] = round(
        sum(task.get("cost_usd", 0) for task in history[experiment_name]["tasks"].values()),
        4
    )
    
    # Save updated history
    save_iterative_history(history, token_file)
    
    return history[experiment_name]


if __name__ == "__main__":
    # Example usage
    import os
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Run a debate with token tracking
    topic = "What are the main benefits of renewable energy?"
    result = run_debate_with_tracking(topic, num_agents=3, num_rounds=2)
    
    print("\n" + result['transcript'])

