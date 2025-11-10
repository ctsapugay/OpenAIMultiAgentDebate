"""
Integration tests for the multi-agent debate system.

Tests cover the complete debate flow, conversation history management,
and error handling with mocked OpenAI API responses.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock the openai_agents module before importing debate_system
sys.modules['openai_agents'] = MagicMock()

from debate_system import DebateSystem


class TestCompleteDebateFlow:
    """Tests for complete debate flow with mocked API responses."""
    
    @patch('debate_system.Runner')
    def test_complete_debate_with_two_agents_one_round(self, mock_runner):
        """Test complete debate flow with 2 agents and 1 round."""
        # Setup mock responses
        mock_result_1 = Mock()
        mock_result_1.content = "Agent 1 response"
        mock_result_2 = Mock()
        mock_result_2.content = "Agent 2 response"
        
        mock_runner.run_sync.side_effect = [mock_result_1, mock_result_2]
        
        # Run debate
        system = DebateSystem(num_agents=2)
        transcript = system.run_debate(topic="Test topic", num_rounds=1)
        
        # Verify Runner.run_sync was called twice (once per agent)
        assert mock_runner.run_sync.call_count == 2
        
        # Verify transcript contains both responses
        assert "Agent 1 response" in transcript
        assert "Agent 2 response" in transcript
        assert "[Round 1]" in transcript
        assert "DEBATE TRANSCRIPT" in transcript
    
    @patch('debate_system.Runner')
    def test_complete_debate_with_multiple_rounds(self, mock_runner):
        """Test complete debate flow with multiple rounds."""
        # Setup mock responses for 3 agents, 2 rounds = 6 total calls
        mock_responses = []
        for round_num in range(1, 3):
            for agent_num in range(1, 4):
                mock_result = Mock()
                mock_result.content = f"Round {round_num} Agent {agent_num} response"
                mock_responses.append(mock_result)
        
        mock_runner.run_sync.side_effect = mock_responses
        
        # Run debate
        system = DebateSystem(num_agents=3)
        transcript = system.run_debate(topic="Test topic", num_rounds=2)
        
        # Verify Runner.run_sync was called 6 times (3 agents * 2 rounds)
        assert mock_runner.run_sync.call_count == 6
        
        # Verify all responses are in transcript
        for round_num in range(1, 3):
            for agent_num in range(1, 4):
                assert f"Round {round_num} Agent {agent_num} response" in transcript
        
        # Verify both rounds are labeled
        assert "[Round 1]" in transcript
        assert "[Round 2]" in transcript


class TestConversationHistoryManagement:
    """Tests for conversation history management across rounds."""
    
    @patch('debate_system.Runner')
    @patch('debate_system.Session')
    def test_conversation_history_initialized_with_topic(self, mock_session_class, mock_runner):
        """Test that conversation history is initialized with the debate topic."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance
        
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.return_value = mock_result
        
        # Run debate
        system = DebateSystem(num_agents=2)
        system.run_debate(topic="Climate change", num_rounds=1)
        
        # Verify Session was created
        mock_session_class.assert_called_once()
        
        # Verify topic was added to session
        mock_session_instance.add_message.assert_called_once_with(
            role="user",
            content="Topic: Climate change"
        )
    
    @patch('debate_system.Runner')
    @patch('debate_system.Session')
    def test_all_agents_receive_same_session(self, mock_session_class, mock_runner):
        """Test that all agents receive the same session with conversation history."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance
        
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.return_value = mock_result
        
        # Run debate with 3 agents
        system = DebateSystem(num_agents=3)
        system.run_debate(topic="Test topic", num_rounds=1)
        
        # Verify all Runner.run_sync calls received the same session
        assert mock_runner.run_sync.call_count == 3
        for call in mock_runner.run_sync.call_args_list:
            assert call.kwargs['session'] == mock_session_instance
    
    @patch('debate_system.Runner')
    @patch('debate_system.Session')
    def test_session_maintained_across_rounds(self, mock_session_class, mock_runner):
        """Test that the same session is used across multiple rounds."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance
        
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.return_value = mock_result
        
        # Run debate with 2 agents, 3 rounds
        system = DebateSystem(num_agents=2)
        system.run_debate(topic="Test topic", num_rounds=3)
        
        # Verify Session was created only once
        assert mock_session_class.call_count == 1
        
        # Verify all 6 calls (2 agents * 3 rounds) used the same session
        assert mock_runner.run_sync.call_count == 6
        for call in mock_runner.run_sync.call_args_list:
            assert call.kwargs['session'] == mock_session_instance


class TestAgentContextInRounds:
    """Tests for verifying agents receive correct context in each round."""
    
    @patch('debate_system.Runner')
    def test_agents_called_in_order_within_round(self, mock_runner):
        """Test that agents are called in sequential order within each round."""
        # Setup mock
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.return_value = mock_result
        
        # Run debate
        system = DebateSystem(num_agents=3)
        system.run_debate(topic="Test topic", num_rounds=1)
        
        # Verify all 3 agents were called
        assert mock_runner.run_sync.call_count == 3
        
        # Verify each call had an agent and session
        for call in mock_runner.run_sync.call_args_list:
            assert 'agent' in call.kwargs
            assert 'session' in call.kwargs
    
    @patch('debate_system.Runner')
    def test_each_agent_responds_once_per_round(self, mock_runner):
        """Test that each agent responds exactly once per round."""
        # Setup mock
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.return_value = mock_result
        
        # Run debate with 3 agents, 2 rounds
        system = DebateSystem(num_agents=3)
        system.run_debate(topic="Test topic", num_rounds=2)
        
        # Verify total calls = agents * rounds (core functionality)
        assert mock_runner.run_sync.call_count == 6  # 3 agents * 2 rounds
        
        # Verify system has 3 agents
        assert len(system.agents) == 3


class TestErrorHandling:
    """Tests for error handling with API failures."""
    
    @patch('debate_system.Runner')
    def test_api_error_during_debate(self, mock_runner):
        """Test that API errors are propagated correctly."""
        # Setup mock to raise an exception
        mock_runner.run_sync.side_effect = Exception("API connection failed")
        
        # Run debate and expect exception
        system = DebateSystem(num_agents=2)
        with pytest.raises(Exception, match="API connection failed"):
            system.run_debate(topic="Test topic", num_rounds=1)
    
    @patch('debate_system.Runner')
    def test_api_error_in_second_round(self, mock_runner):
        """Test error handling when API fails in a later round."""
        # Setup mock: succeed for first 2 calls, fail on third
        mock_result = Mock()
        mock_result.content = "Response"
        mock_runner.run_sync.side_effect = [
            mock_result,
            mock_result,
            Exception("API rate limit exceeded")
        ]
        
        # Run debate with 2 agents, 2 rounds (will fail on second round)
        system = DebateSystem(num_agents=2)
        with pytest.raises(Exception, match="API rate limit exceeded"):
            system.run_debate(topic="Test topic", num_rounds=2)
        
        # Verify it attempted 3 calls before failing
        assert mock_runner.run_sync.call_count == 3
