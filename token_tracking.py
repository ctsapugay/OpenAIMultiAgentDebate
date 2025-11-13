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

# File to store persistent token usage across runs
TOKEN_USAGE_FILE = "token_usage_history.json"


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
    
    Args:
        filename: Path to JSON file
        
    Returns:
        Dictionary of model statistics
    """
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_token_history(history: Dict[str, Any], filename: str = TOKEN_USAGE_FILE):
    """
    Save token usage history to JSON file.
    
    Args:
        history: Dictionary of model statistics
        filename: Path to JSON file
    """
    with open(filename, 'w') as f:
        json.dump(history, f, indent=2)


def update_model_statistics(model: str, input_tokens: int, output_tokens: int, total_tokens: int) -> Dict[str, Any]:
    """
    Update persistent statistics for a specific model.
    
    This function loads existing statistics, adds the current run's tokens to the
    cumulative totals for the model, and saves back to the JSON file.
    
    Args:
        model: Model name (e.g., 'gpt-4', 'gpt-4o-mini')
        input_tokens: Input tokens from current run
        output_tokens: Output tokens from current run
        total_tokens: Total tokens from current run
        
    Returns:
        Updated statistics for the model
    """
    # Load existing history
    history = load_token_history()
    
    # Initialize model entry if doesn't exist
    if model not in history:
        history[model] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_runs": 0,
            "last_updated": None
        }
    
    # Add current run's tokens to cumulative totals
    history[model]["input_tokens"] += input_tokens
    history[model]["output_tokens"] += output_tokens
    history[model]["total_tokens"] += total_tokens
    history[model]["total_runs"] += 1
    history[model]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save updated history
    save_token_history(history)
    
    return history[model]


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
        persistent_stats = update_model_statistics(
            model=self.model,
            input_tokens=self.usage_data.total_input_tokens,
            output_tokens=self.usage_data.total_output_tokens,
            total_tokens=self.usage_data.total_tokens
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

