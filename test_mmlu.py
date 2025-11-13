"""
MMLU Test Suite for Multi-Agent Debate System

This module tests the debate system on simple MMLU (Massive Multitask Language Understanding)
multiple-choice questions to demonstrate how the debate mechanism can reach consensus
on objective questions.
"""

from typing import List, Dict, Any
import json
from token_tracking import TokenTrackingDebateSystem
from consensus_system import ConsensusSystem
from debate_system import DebateSystem


# Sample MMLU questions across different domains
SAMPLE_MMLU_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "choices": ["A) London", "B) Berlin", "C) Paris", "D) Madrid"],
        "correct_answer": "C",
        "subject": "Geography",
        "difficulty": "easy"
    },
    {
        "question": "Which of the following is a prime number?",
        "choices": ["A) 12", "B) 15", "C) 17", "D) 21"],
        "correct_answer": "C",
        "subject": "Mathematics",
        "difficulty": "easy"
    },
    {
        "question": "What is the chemical symbol for gold?",
        "choices": ["A) Go", "B) Au", "C) Gd", "D) Ag"],
        "correct_answer": "B",
        "subject": "Chemistry",
        "difficulty": "easy"
    },
    {
        "question": "In computer science, what does CPU stand for?",
        "choices": [
            "A) Central Processing Unit",
            "B) Computer Personal Unit",
            "C) Central Program Utility",
            "D) Computer Processing Utility"
        ],
        "correct_answer": "A",
        "subject": "Computer Science",
        "difficulty": "easy"
    },
    {
        "question": "Which planet in our solar system is known for its rings?",
        "choices": ["A) Mars", "B) Jupiter", "C) Saturn", "D) Neptune"],
        "correct_answer": "C",
        "subject": "Astronomy",
        "difficulty": "easy"
    },
    {
        "question": "What is the result of 15 × 8?",
        "choices": ["A) 110", "B) 120", "C) 130", "D) 140"],
        "correct_answer": "B",
        "subject": "Mathematics",
        "difficulty": "easy"
    },
    {
        "question": "Which of the following programming languages is primarily used for statistical computing?",
        "choices": ["A) JavaScript", "B) R", "C) C++", "D) HTML"],
        "correct_answer": "B",
        "subject": "Computer Science",
        "difficulty": "medium"
    },
    {
        "question": "What is the main gas that makes up Earth's atmosphere?",
        "choices": ["A) Oxygen", "B) Carbon Dioxide", "C) Nitrogen", "D) Hydrogen"],
        "correct_answer": "C",
        "subject": "Science",
        "difficulty": "medium"
    }
]


def format_mmlu_question(question_data: Dict[str, Any]) -> str:
    """
    Format an MMLU question for the debate system.
    
    Args:
        question_data: Dictionary containing question, choices, and metadata
        
    Returns:
        Formatted question string
    """
    lines = [
        f"Subject: {question_data['subject']}",
        f"Difficulty: {question_data['difficulty']}",
        "",
        question_data['question'],
        ""
    ]
    lines.extend(question_data['choices'])
    lines.append("")
    lines.append("Please analyze this question and determine the correct answer. Provide reasoning for your choice.")
    
    return "\n".join(lines)


def extract_answer_from_consensus(consensus_text: str) -> str:
    """
    Extract the letter answer (A, B, C, or D) from consensus text.
    
    Args:
        consensus_text: The consensus text from the debate
        
    Returns:
        Extracted answer letter or "UNKNOWN"
    """
    consensus_upper = consensus_text.upper()
    
    # Look for patterns like "the correct answer is C" or "answer: B"
    import re
    
    # Pattern 1: "answer is X" or "answer: X"
    pattern1 = r'\bANSWER\s+(?:IS\s+)?:?\s*([A-D])\b'
    match = re.search(pattern1, consensus_upper)
    if match:
        return match.group(1)
    
    # Pattern 2: "correct answer is X" or "correct: X"
    pattern2 = r'\bCORRECT\s+(?:ANSWER\s+)?(?:IS\s+)?:?\s*([A-D])\b'
    match = re.search(pattern2, consensus_upper)
    if match:
        return match.group(1)
    
    # Pattern 3: Look for standalone letter in parentheses or quotes
    pattern3 = r'[\(\"\']([A-D])[\)\"\']'
    matches = re.findall(pattern3, consensus_upper)
    if matches:
        # Return the most common answer
        from collections import Counter
        counter = Counter(matches)
        return counter.most_common(1)[0][0]
    
    # Pattern 4: Just find any mention of A, B, C, or D
    pattern4 = r'\b([A-D])\b'
    matches = re.findall(pattern4, consensus_upper)
    if matches:
        # Return the last mentioned answer (often the conclusion)
        return matches[-1]
    
    return "UNKNOWN"


class MMLUDebateTest:
    """
    Test harness for running MMLU questions through the debate system.
    """
    
    def __init__(self, num_agents: int = 3, num_rounds: int = 2, model: str = "gpt-4"):
        """
        Initialize the MMLU debate test.
        
        Args:
            num_agents: Number of agents to participate in debates
            num_rounds: Number of debate rounds per question
            model: OpenAI model to use
        """
        self.num_agents = num_agents
        self.num_rounds = num_rounds
        self.model = model
        self.results = []
    
    def run_single_question(self, question_data: Dict[str, Any], 
                          use_consensus: bool = True,
                          track_tokens: bool = True) -> Dict[str, Any]:
        """
        Run a single MMLU question through the debate system.
        
        Args:
            question_data: Dictionary containing the question and metadata
            use_consensus: Whether to generate a consensus answer
            track_tokens: Whether to track token usage
            
        Returns:
            Dictionary with test results
        """
        # Format the question
        formatted_question = format_mmlu_question(question_data)
        
        print(f"\n{'='*80}")
        print(f"Testing: {question_data['subject']} - {question_data['difficulty']}")
        print(f"{'='*80}")
        print(f"Question: {question_data['question']}")
        print(f"Correct Answer: {question_data['correct_answer']}")
        print(f"{'='*80}\n")
        
        # Run debate with tracking
        if track_tokens:
            debate_system = TokenTrackingDebateSystem(
                num_agents=self.num_agents,
                model=self.model
            )
            debate_result = debate_system.run_debate(formatted_question, self.num_rounds)
            transcript = debate_result['transcript']
            usage = debate_result['usage']
        else:
            debate_system = DebateSystem(
                num_agents=self.num_agents,
                model=self.model
            )
            transcript = debate_system.run_debate(formatted_question, self.num_rounds)
            usage = None
        
        # Generate consensus if requested
        consensus = None
        predicted_answer = "UNKNOWN"
        
        if use_consensus:
            if track_tokens:
                # Wrap the tracking debate system for consensus
                consensus_system = ConsensusSystem(debate_system)
                consensus = consensus_system._generate_consensus(formatted_question, transcript)
            else:
                consensus_system = ConsensusSystem(debate_system)
                consensus = consensus_system._generate_consensus(formatted_question, transcript)
            
            predicted_answer = extract_answer_from_consensus(consensus)
            print(f"\nConsensus Answer: {predicted_answer}")
        
        # Check if correct
        is_correct = predicted_answer == question_data['correct_answer']
        
        result = {
            "question": question_data['question'],
            "subject": question_data['subject'],
            "difficulty": question_data['difficulty'],
            "correct_answer": question_data['correct_answer'],
            "predicted_answer": predicted_answer,
            "is_correct": is_correct,
            "transcript": transcript,
            "consensus": consensus,
            "usage": usage.get_summary() if usage else None
        }
        
        self.results.append(result)
        
        print(f"Result: {'✓ CORRECT' if is_correct else '✗ INCORRECT'}")
        
        if track_tokens and usage:
            print(f"\nToken Usage: {usage.total_tokens:,} tokens "
                  f"(in: {usage.total_input_tokens:,}, out: {usage.total_output_tokens:,})")
        
        return result
    
    def run_test_suite(self, questions: List[Dict[str, Any]] = None,
                      use_consensus: bool = True,
                      track_tokens: bool = True) -> Dict[str, Any]:
        """
        Run a full test suite of MMLU questions.
        
        Args:
            questions: List of question dictionaries (uses default if None)
            use_consensus: Whether to generate consensus answers
            track_tokens: Whether to track token usage
            
        Returns:
            Dictionary with aggregate test results
        """
        if questions is None:
            questions = SAMPLE_MMLU_QUESTIONS
        
        print(f"\n{'='*80}")
        print(f"MMLU DEBATE SYSTEM TEST SUITE")
        print(f"{'='*80}")
        print(f"Total Questions: {len(questions)}")
        print(f"Agents: {self.num_agents}")
        print(f"Rounds per Question: {self.num_rounds}")
        print(f"Model: {self.model}")
        print(f"{'='*80}\n")
        
        self.results = []
        
        for i, question_data in enumerate(questions, 1):
            print(f"\n{'*'*80}")
            print(f"Question {i}/{len(questions)}")
            print(f"{'*'*80}")
            
            self.run_single_question(question_data, use_consensus, track_tokens)
        
        # Calculate aggregate statistics
        total_questions = len(self.results)
        correct_answers = sum(1 for r in self.results if r['is_correct'])
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        total_tokens = sum(r['usage']['total_tokens'] for r in self.results if r['usage'])
        
        summary = {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "incorrect_answers": total_questions - correct_answers,
            "accuracy": accuracy,
            "total_tokens": total_tokens,
            "avg_tokens_per_question": total_tokens // total_questions if total_questions > 0 else 0,
            "results": self.results
        }
        
        self._print_summary(summary)
        
        return summary
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print a formatted summary of test results."""
        print(f"\n\n{'='*80}")
        print("TEST SUITE SUMMARY")
        print(f"{'='*80}")
        print(f"Total Questions: {summary['total_questions']}")
        print(f"Correct Answers: {summary['correct_answers']}")
        print(f"Incorrect Answers: {summary['incorrect_answers']}")
        print(f"Accuracy: {summary['accuracy']:.1f}%")
        
        if summary['total_tokens'] > 0:
            print(f"\nTotal Tokens Used: {summary['total_tokens']:,}")
            print(f"Average Tokens per Question: {summary['avg_tokens_per_question']:,}")
        
        print(f"\n{'='*80}")
        print("BREAKDOWN BY SUBJECT")
        print(f"{'='*80}")
        
        # Group by subject
        by_subject = {}
        for result in summary['results']:
            subject = result['subject']
            if subject not in by_subject:
                by_subject[subject] = {"correct": 0, "total": 0}
            by_subject[subject]['total'] += 1
            if result['is_correct']:
                by_subject[subject]['correct'] += 1
        
        for subject, stats in sorted(by_subject.items()):
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"{subject}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%)")
        
        print(f"{'='*80}\n")
    
    def save_results(self, filename: str = "mmlu_debate_results.json"):
        """Save test results to a JSON file."""
        # Prepare results for JSON serialization (remove non-serializable usage objects)
        serializable_results = []
        for result in self.results:
            result_copy = result.copy()
            if 'usage' in result_copy and result_copy['usage']:
                # Usage summary is already serializable
                pass
            serializable_results.append(result_copy)
        
        with open(filename, 'w') as f:
            json.dump({
                "summary": {
                    "total_questions": len(self.results),
                    "correct_answers": sum(1 for r in self.results if r['is_correct']),
                    "accuracy": sum(1 for r in self.results if r['is_correct']) / len(self.results) * 100 if self.results else 0
                },
                "results": serializable_results
            }, f, indent=2)
        
        print(f"Results saved to {filename}")


def main():
    """Main function to run MMLU tests."""
    import os
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    
    # Create test instance
    test = MMLUDebateTest(num_agents=3, num_rounds=2, model="gpt-4o-mini")
    
    # Run on a subset of questions (first 3 for quick testing)
    # Use all questions for full test: questions=SAMPLE_MMLU_QUESTIONS
    summary = test.run_test_suite(
        questions=SAMPLE_MMLU_QUESTIONS[:3],  # Just first 3 for demo
        use_consensus=True,
        track_tokens=True
    )
    
    # Save results
    test.save_results()


if __name__ == "__main__":
    main()

