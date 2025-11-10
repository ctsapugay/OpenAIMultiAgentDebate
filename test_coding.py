#!/usr/bin/env python3
"""
Test the multi-agent debate system with a coding task.
"""

import os
from dotenv import load_dotenv
from debate_system import DebateSystem

# Load environment variables
load_dotenv()

def main():
    print("=" * 80)
    print("CODING TASK TEST: Multi-Agent Debate System")
    print("=" * 80)
    print()
    
    # Test configuration
    topic = "Write a function in Python to test if a number is prime or not"
    num_agents = 3
    num_rounds = 2
    model = "gpt-4o-mini"
    
    print(f"Configuration:")
    print(f"  Task: {topic}")
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
        print("Starting collaborative coding session...")
        print()
        transcript = system.run_debate(topic=topic, num_rounds=num_rounds)
        
        # Display results
        print(transcript)
        print()
        print("=" * 80)
        print("✓ Coding task completed!")
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
