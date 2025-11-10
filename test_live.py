#!/usr/bin/env python3
"""
Live test of the multi-agent debate system with actual OpenAI API calls.
"""

import os
from dotenv import load_dotenv
from debate_system import DebateSystem

# Load environment variables
load_dotenv()

def main():
    print("=" * 80)
    print("LIVE TEST: Multi-Agent Debate System")
    print("=" * 80)
    print()
    
    # Verify API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        return
    
    print(f"✓ API key loaded (ends with: ...{api_key[-4:]})")
    print()
    
    # Test configuration
    topic = "Should AI systems be open source?"
    num_agents = 2
    num_rounds = 1
    model = "gpt-4o-mini"  # Using cheaper model for testing
    
    print(f"Configuration:")
    print(f"  Topic: {topic}")
    print(f"  Agents: {num_agents}")
    print(f"  Rounds: {num_rounds}")
    print(f"  Model: {model}")
    print()
    
    try:
        # Initialize system
        print("Initializing debate system...")
        system = DebateSystem(num_agents=num_agents, model=model)
        print(f"✓ Created {num_agents} agents")
        print()
        
        # Run debate
        print("Starting debate (this may take a moment)...")
        print()
        transcript = system.run_debate(topic=topic, num_rounds=num_rounds)
        
        # Display results
        print(transcript)
        print()
        print("=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ Error: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
