"""
Multi-Agent Debate System - Core Implementation

This module contains the DebateSystem class that orchestrates debates between
multiple AI agents using the OpenAI Agents SDK.
"""

from typing import List
import time
from agents import Agent, Runner
from agents.memory import Session


class InMemorySession:
    """Simple in-memory session for conversation history."""
    
    def __init__(self):
        self.items = []
    
    async def get_items(self, limit: int | None = None) -> List[dict]:
        """Retrieve conversation history."""
        if limit is None:
            return self.items
        return self.items[-limit:]
    
    async def add_items(self, items: List[dict]) -> None:
        """Store new items."""
        self.items.extend(items)
    
    async def pop_item(self) -> dict | None:
        """Remove and return the most recent item."""
        return self.items.pop() if self.items else None
    
    async def clear_session(self) -> None:
        """Clear all items."""
        self.items.clear()
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message synchronously (for compatibility)."""
        self.items.append({"role": role, "content": content})


class DebateSystem:
    """
    Orchestrates multi-agent debates using the OpenAI Agents SDK.
    
    The DebateSystem manages the lifecycle of a debate, including agent
    initialization, round execution, and transcript generation.
    """
    
    def __init__(self, num_agents: int = 3, model: str = "gpt-4"):
        """
        Initialize the debate system.
        
        Args:
            num_agents: Number of agents to participate in the debate
            model: OpenAI model to use for agents
            
        Raises:
            ValueError: If num_agents is less than 2
        """
        if num_agents < 2:
            raise ValueError("num_agents must be at least 2")
        
        self.num_agents = num_agents
        self.model = model
        self.agents = self._create_agents()
    
    def run_debate(self, topic: str, num_rounds: int = 2) -> str:
        """
        Execute a complete debate and return the transcript.
        
        Args:
            topic: The debate topic
            num_rounds: Number of debate rounds to execute
            
        Returns:
            Formatted debate transcript as a string
        """
        # Create a simple in-memory session for conversation history
        session = InMemorySession()
        
        # Initialize conversation history with the debate topic
        session.add_message(role="user", content=f"Topic: {topic}")
        
        # Accumulate all responses across rounds
        all_responses = []
        
        # Loop through specified number of rounds
        for round_num in range(1, num_rounds + 1):
            round_responses = self._execute_round(round_num, session)
            all_responses.extend(round_responses)
        
        # Format and return the transcript
        return self._format_transcript(all_responses)
    
    def _create_agents(self) -> List[Agent]:
        """
        Create agent instances with debate instructions.
        
        Returns:
            List of configured Agent instances
        """
        agents = []
        
        # Identical instructions for all agents to maintain flat structure
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
    
    def _execute_round(self, round_num: int, session) -> List[dict]:
        """
        Execute a single debate round with all agents.
        
        Args:
            round_num: Current round number
            session: Session instance containing conversation history
            
        Returns:
            List of response dictionaries from this round
        """
        responses = []
        
        for agent in self.agents:
            # Execute agent with current conversation history
            # Provide context about the round
            input_text = f"Continue the debate (Round {round_num}). Provide your perspective."
            result = Runner.run_sync(agent, input_text, session=session)
            
            # Collect response with metadata
            response_dict = {
                "agent_name": agent.name,
                "round": round_num,
                "content": str(result.final_output),
                "timestamp": time.time()
            }
            responses.append(response_dict)
        
        return responses
    
    def _format_transcript(self, responses: List[dict]) -> str:
        """
        Format all responses into a readable transcript.
        
        Args:
            responses: List of response dictionaries
            
        Returns:
            Formatted transcript string
        """
        transcript_lines = []
        transcript_lines.append("=" * 80)
        transcript_lines.append("DEBATE TRANSCRIPT")
        transcript_lines.append("=" * 80)
        transcript_lines.append("")
        
        # Format each response with agent name, round number, and content
        for response in responses:
            transcript_lines.append(f"[Round {response['round']}] {response['agent_name']}:")
            transcript_lines.append("-" * 80)
            transcript_lines.append(response['content'])
            transcript_lines.append("")
        
        transcript_lines.append("=" * 80)
        transcript_lines.append("END OF DEBATE")
        transcript_lines.append("=" * 80)
        
        return "\n".join(transcript_lines)
