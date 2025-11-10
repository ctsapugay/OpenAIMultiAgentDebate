# Design Document: Multi-Agent Debate System

## Overview

The Multi-Agent Debate System is a Python application that leverages the OpenAI Agents SDK to orchestrate structured debates between multiple AI agents. The system implements a flat organizational structure where all agents are peers, enabling diverse perspectives on any given topic. This baseline implementation focuses on simplicity and extensibility, making it suitable for future enhancements like code generation and problem-solving tasks.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Interface                            │
│                  (main.py entry point)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  DebateSystem Class                          │
│  - Agent initialization                                      │
│  - Debate orchestration                                      │
│  - Transcript generation                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenAI Agents SDK Layer                         │
│  - Agent primitives                                          │
│  - Runner for execution                                      │
│  - Session for history management                            │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Simplicity First**: Minimal abstractions, straightforward control flow
2. **Flat Structure**: All agents are equal peers with identical capabilities
3. **Extensibility**: Clean interfaces that allow future enhancements
4. **SDK-Native**: Leverage OpenAI Agents SDK primitives without unnecessary wrappers

## Components and Interfaces

### 1. DebateSystem Class

The core orchestrator that manages the debate lifecycle.

**Responsibilities:**
- Initialize and configure debate agents
- Execute debate rounds sequentially
- Maintain conversation history
- Generate formatted transcripts

**Key Methods:**

```python
class DebateSystem:
    def __init__(self, num_agents: int = 3, model: str = "gpt-4"):
        """Initialize the debate system with specified number of agents"""
        
    def run_debate(self, topic: str, num_rounds: int = 2) -> str:
        """Execute a complete debate and return the transcript"""
        
    def _create_agents(self) -> List[Agent]:
        """Create agent instances with debate instructions"""
        
    def _execute_round(self, round_num: int, topic: str, history: List[dict]) -> List[dict]:
        """Execute a single debate round with all agents"""
        
    def _format_transcript(self, responses: List[dict]) -> str:
        """Format all responses into a readable transcript"""
```

### 2. Agent Configuration

Each agent is configured with instructions that encourage:
- Critical thinking and analysis
- Building on previous arguments
- Providing unique perspectives
- Constructive debate behavior

**Agent Instruction Template:**
```
You are Agent {name}, participating in a collaborative debate. Your role is to:
1. Analyze the topic critically
2. Consider previous arguments from other agents
3. Provide your unique perspective
4. Build constructively on the discussion
5. Be concise but thorough in your responses
```

### 3. CLI Interface (main.py)

Simple command-line interface for running debates.

**Arguments:**
- `--topic`: The debate topic (required)
- `--agents`: Number of agents (default: 3)
- `--rounds`: Number of debate rounds (default: 2)
- `--model`: OpenAI model to use (default: gpt-4)

**Example Usage:**
```bash
python main.py --topic "Should AI systems be open source?" --agents 3 --rounds 2
```

## Data Models

### Response Structure

Each agent response is stored with metadata:

```python
{
    "agent_name": str,      # e.g., "Agent_1"
    "round": int,           # Round number (1-indexed)
    "content": str,         # The agent's response text
    "timestamp": float      # Unix timestamp
}
```

### Conversation History

The conversation history follows the OpenAI message format:

```python
[
    {"role": "user", "content": "Topic: {topic}"},
    {"role": "assistant", "content": "Agent_1: {response}"},
    {"role": "assistant", "content": "Agent_2: {response}"},
    ...
]
```

## Error Handling

### API Key Validation
- Check for `OPENAI_API_KEY` environment variable at startup
- Provide clear error message if missing
- Exit gracefully with non-zero status code

### Input Validation
- Validate `num_agents >= 2`
- Validate `num_rounds >= 1`
- Validate topic is non-empty string
- Raise `ValueError` with descriptive messages

### API Errors
- Catch OpenAI API exceptions (rate limits, authentication, etc.)
- Display user-friendly error messages
- Log technical details for debugging

### Graceful Degradation
- If an agent fails mid-debate, log the error and continue with remaining agents
- Include error information in the transcript

## Testing Strategy

### Unit Tests
- Test agent initialization with various configurations
- Test input validation (edge cases for num_agents, num_rounds)
- Test transcript formatting with mock responses
- Test error handling for missing API keys

### Integration Tests
- Test complete debate flow with mock OpenAI responses
- Verify conversation history is properly maintained
- Verify all agents receive correct context

### Manual Testing
- Run debates with different topics and configurations
- Verify output formatting and readability
- Test with different OpenAI models
- Validate behavior with 2, 3, and 5+ agents

## Implementation Notes

### Session Management
The OpenAI Agents SDK's Session primitive automatically handles conversation history, eliminating the need for manual state management. Each agent run within a session will have access to the full conversation context.

### Synchronous vs Asynchronous
For this baseline implementation, we'll use synchronous execution (`Runner.run_sync`) for simplicity. Future versions could leverage async execution for parallel agent processing.

### Model Selection
Default to `gpt-4` for better reasoning capabilities, but allow configuration for cost optimization (e.g., `gpt-4o-mini`).

### Extensibility Points

Future enhancements can build on this baseline:

1. **Tool Integration**: Add function tools for agents to access external resources
2. **Specialized Roles**: Assign different roles/expertise to agents
3. **Voting/Consensus**: Add mechanisms for agents to reach conclusions
4. **Code Generation**: Adapt for collaborative code writing tasks
5. **Evaluation**: Add metrics to assess debate quality
6. **Handoffs**: Introduce moderator agents using the handoff primitive

## Dependencies

```
openai-agents>=0.1.0
python>=3.8
```

## File Structure

```
multi-agent-debate/
├── main.py                 # CLI entry point
├── debate_system.py        # Core DebateSystem class
├── requirements.txt        # Python dependencies
├── README.md              # Usage documentation
└── tests/
    ├── test_debate_system.py
    └── test_integration.py
```
