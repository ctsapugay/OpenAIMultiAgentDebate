# Multi-Agent Debate System

A Python application that leverages the OpenAI Agents SDK to orchestrate structured debates between multiple AI agents. The system implements a flat organizational structure where all agents are peers, enabling diverse perspectives on any given topic.

Perfect for collaborative problem-solving, coding tasks, and exploring complex topics from multiple angles!

## Features

- 🤖 Configure multiple AI agents to debate any topic
- 💬 Execute multiple rounds of debate with sequential agent responses
- 🧠 Automatic conversation history management across rounds
- 📝 Generate formatted debate transcripts
- 💻 Handle coding tasks with collaborative agent solutions
- 🎯 Simple command-line interface
- 📊 **Token usage tracking** - Monitor API costs for all agent interactions
- 🤝 **Consensus generation** - Synthesize agent perspectives into unified answers
- 📝 **MMLU testing** - Test debate system on multiple-choice questions
- 🎨 **ArtifactsBench integration** - Generate visual/interactive code artifacts (automatically pulls “easy” tasks from the Tencent dataset on Hugging Face when available)
- ✅ Comprehensive test suite included

## Prerequisites

- Python 3.9 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ctsapugay/OpenAIMultiAgentDebate.git
cd OpenAIMultiAgentDebate
```

### 2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your-actual-api-key-here
```

Alternatively, set it as an environment variable:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

### Command-Line Interface

Run a debate using the CLI:

```bash
python main.py --topic "Your debate topic here"
```

#### Command-Line Arguments

- `--topic` (required): The debate topic, "MMLU" for MMLU tests, or "ARTIFACTS" for code generation tasks
- `--agents` (optional): Number of agents to participate (default: 3)
- `--rounds` (optional): Number of debate rounds (default: 2)
- `--model` (optional): OpenAI model to use (default: gpt-4)
- `--consensus` (optional): Generate consensus after debate (flag, default: disabled)

#### Examples

**Basic debate** with default settings (3 agents, 2 rounds):
```bash
python main.py --topic "Should AI systems be open source?"
```

**Debate with consensus generation**:
```bash
python main.py --topic "What are the benefits of renewable energy?" --consensus
```

**Coding task** - agents collaborate on writing code:
```bash
python main.py --topic "Write a function in Python to test if a number is prime"
```

**Custom configuration** with more agents and rounds:
```bash
python main.py --topic "What is the future of renewable energy?" --agents 5 --rounds 3
```

**Use a cheaper model** for faster/cheaper responses:
```bash
python main.py --topic "How can we improve education?" --model gpt-4o-mini
```

**Run MMLU test suite** - test on multiple-choice questions:
```bash
python main.py --topic MMLU --model gpt-4o-mini
```

**MMLU with consensus** - get synthesized answers:
```bash
python main.py --topic MMLU --consensus --agents 3 --rounds 2
```

**ArtifactsBench code generation** - generate visual/interactive code:
```bash
python main.py --topic ARTIFACTS --model gpt-4o-mini
```

**ArtifactsBench with more rounds** - deeper implementation discussion:
```bash
python main.py --topic ARTIFACTS --agents 5 --rounds 3 --model gpt-4
```

### Test Scripts

Try the included test scripts to see the system in action:

**Live debate test:**
```bash
python test_live.py
```

**Coding task test:**
```bash
python test_coding.py
```

### Running Tests

Run the full test suite:

```bash
pytest tests/ -v
```

## Sample Output

### Debate Example

```
================================================================================
MULTI-AGENT DEBATE SYSTEM
================================================================================
Topic: Should AI systems be open source?
Agents: 3
Rounds: 2
Model: gpt-4o-mini
================================================================================

Initializing debate system...
Created 3 agents successfully.

Starting debate...

================================================================================
DEBATE TRANSCRIPT
================================================================================

[Round 1] Agent_1:
--------------------------------------------------------------------------------
The debate over whether AI systems should be open source involves multiple 
factors, including innovation, ethical considerations, accessibility, and 
security...

[Agent provides detailed analysis with multiple perspectives]

[Round 1] Agent_2:
--------------------------------------------------------------------------------
Building on the previous discussion, it's important to delve deeper into the 
implications of the chosen approach...

[Agent builds on Agent_1's points and adds new perspectives]

[Round 1] Agent_3:
--------------------------------------------------------------------------------
Continuing this debate, let's consider some broader implications and 
applications...

[Agent synthesizes previous arguments and proposes solutions]

[Round 2] Agent_1:
--------------------------------------------------------------------------------
In this second round, I'd like to broaden the scope to encompass algorithmic 
complexity and community engagement...

[Agents continue iterating and refining their positions]

================================================================================
END OF DEBATE
================================================================================
```

### Coding Task Example

When given a coding task like "Write a function in Python to test if a number is prime", the agents will:

1. **Agent_1**: Provide an initial efficient implementation
2. **Agent_2**: Enhance it with error handling and optimizations
3. **Agent_3**: Add caching, benchmarking, and documentation

The result is a collaborative, well-thought-out solution with multiple iterations and improvements!

## Project Structure

```
OpenAIMultiAgentDebate/
├── main.py                    # CLI entry point (with MMLU & Artifacts support)
├── debate_system.py           # Core DebateSystem class
├── token_tracking.py          # Token usage tracking system
├── consensus_system.py        # Consensus/merging functionality
├── test_mmlu.py              # MMLU testing framework
├── artifacts_debate.py        # ArtifactsBench code generation
├── test_live.py              # Live API test script
├── test_coding.py            # Coding task test script
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment configuration
├── README.md                 # This file
└── tests/                    # Test suite
    ├── __init__.py
    ├── test_debate_system.py # Unit tests
    └── test_integration.py   # Integration tests
```

## How It Works

1. **Initialization**: The system creates multiple AI agents using the OpenAI Agents SDK
2. **Debate Rounds**: Each round, agents respond sequentially to the topic
3. **Context Sharing**: All agents receive the complete conversation history before responding
4. **Transcript Generation**: After all rounds complete, a formatted transcript is generated

## Architecture

The system uses three key primitives from the OpenAI Agents SDK:

- **Agent**: Individual debate participants with specific instructions
- **Runner**: Executes agent interactions synchronously
- **Session**: Maintains conversation history across agent turns

## Use Cases

This system is perfect for:

- 🎓 **Educational discussions** - Explore complex topics from multiple angles
- 💻 **Collaborative coding** - Get multiple AI perspectives on code solutions
- 🔬 **Research brainstorming** - Generate diverse ideas and approaches
- 🤔 **Problem-solving** - Break down complex problems with multi-agent analysis
- 📊 **Decision-making** - Evaluate options from different viewpoints
- 📝 **MMLU evaluation** - Test model accuracy on multiple-choice questions with debate
- 🎨 **Code artifact generation** - Create interactive visualizations and web apps

## Output Files

The system generates JSON output files for different modes:

- **`mmlu_debate_results.json`** - MMLU test results with accuracy scores and full transcripts
- **`artifacts_results.json`** - Generated code artifacts with evaluation scores
- Both include complete debate transcripts, consensus, and token usage statistics

## Future Enhancements

This baseline implementation can be extended with:

- 🔧 Tool integration for agents to access external resources
- 👥 Specialized roles and expertise for different agents
- 🗳️ Voting and consensus mechanisms
- 📈 Debate quality evaluation metrics
- 🎯 Moderator agents using handoff primitives
- 💾 Persistent session storage (SQLite/Redis)
- 🌐 Web interface for easier interaction

## Contributing

Contributions are welcome! Feel free to:

- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## License

This project is provided as-is for educational and development purposes.

## Acknowledgments

Built with the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) - a lightweight framework for building multi-agent workflows.

## Support

If you encounter any issues or have questions:

1. Check the [OpenAI Agents SDK documentation](https://openai.github.io/openai-agents-python/)
2. Review the test files for usage examples
3. Open an issue on GitHub
