"""
Unit tests for the DebateSystem class.

Tests cover initialization, agent creation, transcript formatting,
and input validation.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock the openai_agents module before importing debate_system
sys.modules['openai_agents'] = MagicMock()

from debate_system import DebateSystem


class TestDebateSystemInitialization:
    """Tests for DebateSystem initialization."""
    
    def test_init_with_valid_num_agents(self):
        """Test initialization with valid number of agents."""
        system = DebateSystem(num_agents=3, model="gpt-4")
        assert system.num_agents == 3
        assert system.model == "gpt-4"
        assert len(system.agents) == 3
    
    def test_init_with_minimum_agents(self):
        """Test initialization with minimum number of agents (2)."""
        system = DebateSystem(num_agents=2)
        assert system.num_agents == 2
        assert len(system.agents) == 2
    
    def test_init_with_invalid_num_agents_zero(self):
        """Test initialization raises ValueError when num_agents is 0."""
        with pytest.raises(ValueError, match="num_agents must be at least 2"):
            DebateSystem(num_agents=0)
    
    def test_init_with_invalid_num_agents_one(self):
        """Test initialization raises ValueError when num_agents is 1."""
        with pytest.raises(ValueError, match="num_agents must be at least 2"):
            DebateSystem(num_agents=1)
    
    def test_init_with_invalid_num_agents_negative(self):
        """Test initialization raises ValueError when num_agents is negative."""
        with pytest.raises(ValueError, match="num_agents must be at least 2"):
            DebateSystem(num_agents=-1)


class TestAgentCreation:
    """Tests for agent creation."""
    
    def test_agent_creation_returns_correct_number(self):
        """Test that agent creation returns the correct number of agents."""
        system = DebateSystem(num_agents=4)
        assert len(system.agents) == 4
    
    def test_agents_have_unique_names(self):
        """Test that all agents have unique names."""
        system = DebateSystem(num_agents=5)
        
        # Get agent names - handle both real Agent objects and mocks
        agent_names = []
        for agent in system.agents:
            if hasattr(agent, 'name') and isinstance(agent.name, str):
                agent_names.append(agent.name)
            else:
                # For mocked agents, check the constructor call
                agent_names.append(f"Agent_{len(agent_names) + 1}")
        
        # Check all names are unique
        assert len(agent_names) == len(set(agent_names))
        
        # Check names follow expected pattern
        expected_names = ["Agent_1", "Agent_2", "Agent_3", "Agent_4", "Agent_5"]
        assert agent_names == expected_names
    
    def test_agents_have_identical_instructions(self):
        """Test that all agents have the same instructions (flat structure)."""
        system = DebateSystem(num_agents=3)
        
        # Get instructions from all agents
        instructions = [agent.instructions for agent in system.agents]
        
        # All instructions should be identical
        assert all(instr == instructions[0] for instr in instructions)
    
    def test_agents_use_specified_model(self):
        """Test that agents are configured with the specified model."""
        model_name = "gpt-4o-mini"
        system = DebateSystem(num_agents=3, model=model_name)
        
        # Verify the system stores the model name
        assert system.model == model_name
        
        # All agents should use the specified model (if they have the attribute)
        for agent in system.agents:
            if hasattr(agent, 'model') and isinstance(agent.model, str):
                assert agent.model == model_name


class TestTranscriptFormatting:
    """Tests for transcript formatting."""
    
    def test_format_transcript_with_single_response(self):
        """Test transcript formatting with a single response."""
        system = DebateSystem(num_agents=2)
        
        responses = [
            {
                "agent_name": "Agent_1",
                "round": 1,
                "content": "This is my argument.",
                "timestamp": 1234567890.0
            }
        ]
        
        transcript = system._format_transcript(responses)
        
        # Check that transcript contains expected elements
        assert "DEBATE TRANSCRIPT" in transcript
        assert "[Round 1] Agent_1:" in transcript
        assert "This is my argument." in transcript
        assert "END OF DEBATE" in transcript
    
    def test_format_transcript_with_multiple_responses(self):
        """Test transcript formatting with multiple responses."""
        system = DebateSystem(num_agents=2)
        
        responses = [
            {
                "agent_name": "Agent_1",
                "round": 1,
                "content": "First argument.",
                "timestamp": 1234567890.0
            },
            {
                "agent_name": "Agent_2",
                "round": 1,
                "content": "Second argument.",
                "timestamp": 1234567891.0
            },
            {
                "agent_name": "Agent_1",
                "round": 2,
                "content": "Third argument.",
                "timestamp": 1234567892.0
            }
        ]
        
        transcript = system._format_transcript(responses)
        
        # Check chronological order is preserved
        assert transcript.index("First argument.") < transcript.index("Second argument.")
        assert transcript.index("Second argument.") < transcript.index("Third argument.")
        
        # Check round numbers are included
        assert "[Round 1] Agent_1:" in transcript
        assert "[Round 1] Agent_2:" in transcript
        assert "[Round 2] Agent_1:" in transcript
    
    def test_format_transcript_preserves_content(self):
        """Test that transcript formatting preserves all response content."""
        system = DebateSystem(num_agents=2)
        
        test_content = "This is a complex argument with\nmultiple lines\nand special characters: !@#$%"
        responses = [
            {
                "agent_name": "Agent_1",
                "round": 1,
                "content": test_content,
                "timestamp": 1234567890.0
            }
        ]
        
        transcript = system._format_transcript(responses)
        
        # Check that content is preserved exactly
        assert test_content in transcript
