"""
Biography Debate System

Extended debate system specifically designed for collaborative biographical generation
from structured attributes (infoboxes).
"""

from typing import List, Dict, Any
import sys
import os
from pathlib import Path

# Add parent directory to path to import debate_system
sys.path.insert(0, str(Path(__file__).parent.parent))
from debate_system import DebateSystem, InMemorySession
from agents import Agent, Runner
import time


class BiographyDebateSystem(DebateSystem):
    """
    Extended debate system for collaborative biographical generation.
    
    Agents work together to write Wikipedia-style biographies from structured
    attribute lists, with emphasis on faithfulness and avoiding hallucinations.
    """
    
    def __init__(self, num_agents: int = 3, model: str = "gpt-4", warmup: bool = False):
        """
        Initialize the biography debate system.
        
        Args:
            num_agents: Number of agents to participate
            model: OpenAI model to use for agents
            warmup: If True, make a small warmup API call (NOTE: This doesn't help - 
                   warmup call experiences same cold start delay. Disabled by default.)
        """
        super().__init__(num_agents, model)
        self._warmup_done = False
        if warmup:
            self._warmup_connection()
    
    def _warmup_connection(self):
        """
        Make a small warmup API call to establish connections and reduce cold start overhead.
        This helps avoid the 2-3 minute delay on the first real API call.
        """
        if self._warmup_done:
            return
        
        try:
            # Create a minimal warmup agent
            warmup_agent = Agent(
                name="Warmup",
                instructions="You are a warmup agent. Respond with exactly 'OK'.",
                model=self.model
            )
            
            # Make a tiny API call to establish connection
            warmup_session = InMemorySession()
            warmup_session.add_message(role="user", content="Say OK")
            
            start_time = time.time()
            Runner.run_sync(warmup_agent, "OK", session=warmup_session)
            elapsed = time.time() - start_time
            
            self._warmup_done = True
            # Note: We don't print here to avoid cluttering output
            # The warmup time will be reflected in faster subsequent calls
        except Exception as e:
            # If warmup fails, continue anyway - it's not critical
            # The first real call will just be slower
            pass
    
    def _create_agents(self) -> List[Agent]:
        """
        Create agent instances with biography writing instructions.
        
        Returns:
            List of configured Agent instances
        """
        agents = []
        
        # Instructions focused on biographical writing
        biography_instructions = """You are participating in collaborative biography writing. Your role is to:
1. Write a Wikipedia-style biography using ONLY the provided structured attributes
2. Be faithful to the attributes - do not invent facts not present in the attributes
3. Consider previous contributions from other agents and build upon them
4. Ensure proper formatting, fluency, and coherence
5. Focus on accuracy and completeness of information
6. In later rounds, refine and improve the biography based on previous agents' work
7. Write in a neutral, encyclopedic tone"""
        
        for i in range(1, self.num_agents + 1):
            agent_name = f"Biographer_{i}"
            agent = Agent(
                name=agent_name,
                instructions=biography_instructions,
                model=self.model
            )
            agents.append(agent)
        
        return agents
    
    def _format_attributes(self, attributes: Dict[str, Any]) -> str:
        """
        Format structured attributes into a readable prompt.
        
        Args:
            attributes: Dictionary of person attributes
            
        Returns:
            Formatted string representation of attributes
        """
        lines = ["=== PERSON ATTRIBUTES ==="]
        lines.append("Write a Wikipedia-style biography using ONLY these attributes:")
        lines.append("")
        
        for key, value in attributes.items():
            if value:  # Skip empty values
                lines.append(f"{key}: {value}")
        
        lines.append("")
        lines.append("=== INSTRUCTIONS ===")
        lines.append("- Use ONLY the information provided above")
        lines.append("- Do not invent or add facts not in the attributes")
        lines.append("- Write in Wikipedia-style format")
        lines.append("- Be concise but comprehensive")
        lines.append("- Ensure proper grammar and flow")
        
        return "\n".join(lines)
    
    def generate_biography(self, attributes: Dict[str, Any], num_rounds: int = 2, 
                          use_consensus: bool = True, max_biographies: int = None,
                          progress_callback: callable = None,
                          intermediate_callback: callable = None) -> Dict[str, Any]:
        """
        Generate a biography using multi-agent debate with optional consensus.
        
        Args:
            attributes: Dictionary of person attributes (infobox)
            num_rounds: Number of debate rounds
            use_consensus: If True, merge biographies from final round using consensus.
                         If False, use last agent's response (faster, fewer API calls)
            max_biographies: Maximum number of biographies to include in consensus.
                            If None, includes all biographies from final round.
                            Only used if use_consensus=True.
            progress_callback: Optional callback function(message: str) for progress updates
            intermediate_callback: Optional callback function(data: dict) for intermediate outputs.
                                  Receives dict with 'type', 'agent', 'round', 'content', etc.
            
        Returns:
            Dictionary containing:
                - 'biography': Final generated biography text
                - 'transcript': Full debate transcript
                - 'responses': List of all agent responses with metadata
                - 'consensus_used': Whether consensus was applied
                - 'biographies_merged': Number of biographies merged (if consensus used)
        """
        if progress_callback:
            progress_callback(f"Initializing biography generation ({self.num_agents} agents, {num_rounds} rounds)...")
        
        # Create session
        session = InMemorySession()
        
        # Format attributes and add to session
        attributes_prompt = self._format_attributes(attributes)
        session.add_message(role="user", content=attributes_prompt)
        
        # Accumulate all responses
        all_responses = []
        
        # Execute rounds
        for round_num in range(1, num_rounds + 1):
            if progress_callback:
                progress_callback(f"Round {round_num}/{num_rounds}: Generating biographies...")
            round_responses = self._execute_round(round_num, session, progress_callback, intermediate_callback)
            all_responses.extend(round_responses)
        
        # Extract final biography
        if use_consensus:
            if progress_callback:
                progress_callback("Collecting biographies for consensus...")
            # Get biographies from final round
            last_round_responses = [r for r in all_responses if r['round'] == num_rounds]
            final_biographies = self._collect_biographies_from_round(last_round_responses)
            
            # Generate consensus if multiple biographies
            if len(final_biographies) > 1:
                # Limit biographies if specified
                if max_biographies and len(final_biographies) > max_biographies:
                    # Use first N biographies (or could use a selection strategy)
                    biographies_to_merge = final_biographies[:max_biographies]
                else:
                    biographies_to_merge = final_biographies
                
                if progress_callback:
                    progress_callback(f"Generating consensus from {len(biographies_to_merge)} biographies...")
                
                # Show consensus inputs if intermediate callback is enabled
                if intermediate_callback:
                    intermediate_callback({
                        'type': 'consensus_input',
                        'biographies': biographies_to_merge,
                        'count': len(biographies_to_merge)
                    })
                
                # Don't use session for consensus - the prompt already has everything needed
                # This avoids sending duplicate context and speeds up the API call
                final_biography = self._generate_consensus(biographies_to_merge, attributes, None, progress_callback)
                consensus_used = True
                num_merged = len(biographies_to_merge)
            else:
                # Only one biography, no need for consensus
                final_biography = final_biographies[0]['content'] if final_biographies else ""
                consensus_used = False
                num_merged = 1
        else:
            if progress_callback:
                progress_callback("Extracting final biography...")
            # Use last agent's response (original behavior)
            final_biography = self._extract_final_biography(all_responses)
            consensus_used = False
            num_merged = 1
        
        # Generate transcript
        transcript = self._format_transcript(all_responses)
        
        return {
            'biography': final_biography,
            'transcript': transcript,
            'responses': all_responses,
            'consensus_used': consensus_used,
            'biographies_merged': num_merged,
            'num_agents': self.num_agents,
            'num_rounds': num_rounds
        }
    
    def _execute_round(self, round_num: int, session, progress_callback: callable = None,
                      intermediate_callback: callable = None) -> List[dict]:
        """
        Execute a single round with all agents.
        
        Args:
            round_num: Current round number
            session: Session instance containing conversation history
            progress_callback: Optional callback function(message: str) for progress updates
            intermediate_callback: Optional callback function(data: dict) for intermediate outputs
            
        Returns:
            List of response dictionaries from this round
        """
        responses = []
        
        for idx, agent in enumerate(self.agents, 1):
            if progress_callback:
                progress_callback(f"  Round {round_num}: {agent.name} ({idx}/{self.num_agents})...")
            
            # Different prompts for first vs. later rounds
            if round_num == 1:
                input_text = f"Round {round_num}: Write the initial biography based on the provided attributes. Be faithful to the attributes and write in Wikipedia style."
            else:
                input_text = f"Round {round_num}: Review and improve the biography. Refine it based on previous contributions while maintaining faithfulness to the original attributes."
            
            # Time the API call
            start_time = time.time()
            result = Runner.run_sync(agent, input_text, session=session)
            elapsed = time.time() - start_time
            
            if progress_callback:
                progress_callback(f"    ✓ {agent.name} completed in {elapsed:.1f}s")
            
            response_dict = {
                "agent_name": agent.name,
                "round": round_num,
                "content": str(result.final_output),
                "timestamp": time.time()
            }
            responses.append(response_dict)
            
            # Call intermediate callback if provided
            if intermediate_callback:
                intermediate_callback({
                    'type': 'agent_output',
                    'agent': agent.name,
                    'round': round_num,
                    'content': response_dict['content'],
                    'elapsed_time': elapsed
                })
        
        return responses
    
    def _collect_biographies_from_round(self, round_responses: List[dict]) -> List[dict]:
        """
        Collect all biographies generated in a round.
        
        Args:
            round_responses: List of response dictionaries from a round
            
        Returns:
            List of biographies with metadata
        """
        biographies = []
        for response in round_responses:
            biographies.append({
                'agent': response['agent_name'],
                'content': response['content'],
                'round': response['round']
            })
        return biographies
    
    def _format_consensus_prompt(self, biographies: List[dict], attributes: Dict[str, Any]) -> str:
        """
        Format prompt for consensus generation.
        
        Args:
            biographies: List of biographies to merge
            attributes: Original attributes for context
            
        Returns:
            Formatted consensus prompt
        """
        lines = ["=== CONSENSUS GENERATION ==="]
        lines.append("\nOriginal Attributes:")
        for key, value in attributes.items():
            if value:
                lines.append(f"  {key}: {value}")
        
        lines.append("\n=== SOURCE BIOGRAPHIES TO MERGE ===")
        for idx, bio in enumerate(biographies, 1):
            lines.append(f"\nSource {idx} (by {bio['agent']}):")
            lines.append("-" * 60)
            lines.append(bio['content'])
            lines.append("-" * 60)
        
        lines.append("\n=== TASK ===")
        lines.append("Create a single, unified biography that:")
        lines.append("1. Combines the BEST information from all source biographies")
        lines.append("2. Is faithful to the original attributes (no hallucinations)")
        lines.append("3. Is complete, covering all important attributes")
        lines.append("4. Is fluent, well-structured, and readable")
        lines.append("5. Removes any contradictions or duplicates")
        lines.append("6. Maintains Wikipedia-style formatting")
        lines.append("\nWrite the final consensus biography:")
        
        return "\n".join(lines)
    
    def _generate_consensus(self, biographies: List[dict], attributes: Dict[str, Any],
                          session: InMemorySession = None, progress_callback: callable = None) -> str:
        """
        Generate a consensus biography by merging multiple biographies.
        
        Args:
            biographies: List of biographies to merge
            attributes: Original attributes for context
            session: Optional session (not needed - prompt has all context)
            progress_callback: Optional callback function(message: str) for progress updates
            
        Returns:
            Consensus biography text
        """
        if not biographies:
            return ""
        
        if len(biographies) == 1:
            # If only one biography, return it
            return biographies[0]['content']
        
        if progress_callback:
            progress_callback("  Creating consensus agent...")
        
        # Create consensus agent
        consensus_instructions = """You are a consensus agent specializing in merging biographies.
Your role is to:
1. Combine the BEST parts from multiple biographies
2. Ensure faithfulness to the original attributes (no hallucinations)
3. Remove duplicates and contradictions
4. Create a coherent, fluent final biography
5. Include all important information from the source biographies
6. Maintain Wikipedia-style formatting"""
        
        consensus_agent = Agent(
            name="Consensus_Agent",
            instructions=consensus_instructions,
            model=self.model
        )
        
        # Format consensus prompt (includes all needed context)
        consensus_prompt = self._format_consensus_prompt(biographies, attributes)
        
        if progress_callback:
            progress_callback("  Merging biographies...")
        
        # Don't pass session - the prompt already contains all necessary context
        # This avoids sending duplicate data and significantly speeds up the call
        start_time = time.time()
        result = Runner.run_sync(consensus_agent, consensus_prompt, session=session)
        elapsed = time.time() - start_time
        
        if progress_callback:
            progress_callback(f"    ✓ Consensus completed in {elapsed:.1f}s")
        
        return str(result.final_output).strip()
    
    def _extract_final_biography(self, responses: List[dict]) -> str:
        """
        Extract the final biography from agent responses.
        
        Uses the last agent's response from the last round as the final biography.
        This is the fallback method when consensus is not used.
        
        Args:
            responses: List of all response dictionaries
            
        Returns:
            Final biography text
        """
        if not responses:
            return ""
        
        # Get the last response (last agent, last round)
        last_response = responses[-1]
        return last_response['content'].strip()
    
    def generate_single_agent_baseline(self, attributes: Dict[str, Any]) -> str:
        """
        Generate a biography using a single agent (baseline comparison).
        
        Args:
            attributes: Dictionary of person attributes
            
        Returns:
            Generated biography text
        """
        # Create a single agent
        biography_instructions = """You are writing a Wikipedia-style biography. Your role is to:
1. Write a biography using ONLY the provided structured attributes
2. Be faithful to the attributes - do not invent facts not present
3. Write in Wikipedia-style format with proper grammar and flow
4. Be concise but comprehensive"""
        
        agent = Agent(
            name="Single_Biographer",
            instructions=biography_instructions,
            model=self.model
        )
        
        # Format attributes
        attributes_prompt = self._format_attributes(attributes)
        
        # Create session and run
        session = InMemorySession()
        session.add_message(role="user", content=attributes_prompt)
        
        input_text = "Write a Wikipedia-style biography based on the provided attributes. Be faithful to the attributes."
        result = Runner.run_sync(agent, input_text, session=session)
        
        return str(result.final_output).strip()

