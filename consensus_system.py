"""
Consensus System - Merging and Consensus Functionality

This module extends the DebateSystem to provide consensus/merging capabilities
that synthesize multiple agent perspectives into a unified answer.
"""

from typing import List, Dict
from agents import Agent, Runner
from debate_system import DebateSystem, InMemorySession


class ConsensusSystem:
    """
    Extends DebateSystem to provide consensus and merging functionality.
    
    After agents debate, this system uses a moderator agent to synthesize
    the various perspectives into a coherent consensus answer.
    """
    
    def __init__(self, debate_system: DebateSystem):
        """
        Initialize the consensus system with a debate system.
        
        Args:
            debate_system: The DebateSystem instance to extend
        """
        self.debate_system = debate_system
        self.moderator_agent = self._create_moderator_agent()
    
    def run_debate_with_consensus(self, topic: str, num_rounds: int = 2) -> Dict[str, str]:
        """
        Execute a debate and generate consensus from the results.
        
        Args:
            topic: The debate topic or question
            num_rounds: Number of debate rounds
            
        Returns:
            Dictionary containing 'transcript' and 'consensus'
        """
        # Run the standard debate
        transcript = self.debate_system.run_debate(topic, num_rounds)
        
        # Generate consensus from the debate
        consensus = self._generate_consensus(topic, transcript)
        
        return {
            "transcript": transcript,
            "consensus": consensus
        }
    
    def _create_moderator_agent(self) -> Agent:
        """
        Create a moderator agent responsible for synthesizing consensus.
        
        Returns:
            Configured moderator Agent instance
        """
        moderator_instructions = """You are a moderator tasked with synthesizing consensus from a multi-agent debate.

Your role is to:
1. Carefully read all agent perspectives from the debate
2. Identify common themes and agreements
3. Note key disagreements or alternative viewpoints
4. Synthesize a balanced, comprehensive consensus answer
5. Present the consensus clearly and concisely

When generating consensus:
- Highlight areas of strong agreement
- Acknowledge legitimate differences of opinion
- Provide a synthesized answer that captures the collective wisdom
- Be objective and fair to all perspectives
- Keep the final answer clear and actionable"""

        moderator = Agent(
            name="Moderator",
            instructions=moderator_instructions,
            model=self.debate_system.model
        )
        return moderator
    
    def _generate_consensus(self, topic: str, transcript: str) -> str:
        """
        Generate consensus from debate transcript.
        
        Args:
            topic: The original debate topic
            transcript: The full debate transcript
            
        Returns:
            Synthesized consensus answer
        """
        # Create a prompt for the moderator
        consensus_prompt = f"""Based on the following debate transcript, please synthesize a consensus answer.

Original Topic/Question: {topic}

{transcript}

Please provide a clear consensus that:
1. Summarizes the key points of agreement
2. Addresses any significant disagreements
3. Provides a balanced final answer or recommendation"""

        # Use a fresh session for consensus generation
        session = InMemorySession()
        result = Runner.run_sync(self.moderator_agent, consensus_prompt, session=session)
        
        return str(result.final_output)
    
    def format_output(self, result: Dict[str, str]) -> str:
        """
        Format the debate and consensus into a readable output.
        
        Args:
            result: Dictionary with 'transcript' and 'consensus' keys
            
        Returns:
            Formatted string with both debate and consensus
        """
        output_lines = [
            result['transcript'],
            "",
            "=" * 80,
            "CONSENSUS",
            "=" * 80,
            "",
            result['consensus'],
            "",
            "=" * 80
        ]
        
        return "\n".join(output_lines)


def run_debate_with_consensus(topic: str, num_agents: int = 3, 
                               num_rounds: int = 2, model: str = "gpt-4") -> str:
    """
    Convenience function to run a debate with consensus in one call.
    
    Args:
        topic: The debate topic or question
        num_agents: Number of agents to participate
        num_rounds: Number of debate rounds
        model: OpenAI model to use
        
    Returns:
        Formatted output with debate transcript and consensus
    """
    # Create debate system
    debate_system = DebateSystem(num_agents=num_agents, model=model)
    
    # Create consensus system
    consensus_system = ConsensusSystem(debate_system)
    
    # Run debate with consensus
    result = consensus_system.run_debate_with_consensus(topic, num_rounds)
    
    # Format and return output
    return consensus_system.format_output(result)


if __name__ == "__main__":
    # Example usage
    import os
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Run a simple debate with consensus
    topic = "Should AI systems be open source?"
    output = run_debate_with_consensus(topic, num_agents=3, num_rounds=2)
    print(output)

