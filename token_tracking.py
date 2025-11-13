"""
Token Tracking System - Usage Monitoring for Multi-Agent Debates

This module provides token usage tracking functionality using the OpenAI Agents SDK
usage API. It tracks input tokens, output tokens, total tokens, and costs across
all agents in a debate.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from agents import Agent, Runner
from debate_system import DebateSystem, InMemorySession
import time


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
            Dictionary with 'transcript' and 'usage' keys
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
        
        return {
            "transcript": transcript,
            "usage": self.usage_data,
            "responses": all_responses
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
    
    def print_usage_summary(self):
        """Print a formatted summary of token usage."""
        summary = self.usage_data.get_summary()
        
        print("\n" + "=" * 80)
        print("TOKEN USAGE SUMMARY")
        print("=" * 80)
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
        
        # Detailed breakdown by agent and round
        print("\n" + "-" * 80)
        print("DETAILED BREAKDOWN BY AGENT AND ROUND")
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

