"""
Biography Evaluation Metrics

Evaluates generated biographies against reference biographies and attributes.
"""

from typing import List, Dict, Any, Set
import re
from collections import Counter


class BiographyEvaluator:
    """Evaluator for biographical generation quality."""
    
    def __init__(self):
        """Initialize the evaluator."""
        pass
    
    def evaluate(self, 
                 generated: str, 
                 attributes: Dict[str, Any], 
                 references: List[str]) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a generated biography.
        
        Args:
            generated: Generated biography text
            attributes: Original attributes (infobox)
            references: List of reference biographies
            
        Returns:
            Dictionary of evaluation metrics
        """
        results = {
            'rouge_l': self.compute_rouge_l(generated, references),
            'faithfulness': self.compute_faithfulness(generated, attributes),
            'hallucination_score': self.detect_hallucinations(generated, attributes),
            'attribute_coverage': self.compute_attribute_coverage(generated, attributes),
        }
        
        return results
    
    def compute_rouge_l(self, generated: str, references: List[str]) -> float:
        """
        Compute ROUGE-L score (Longest Common Subsequence).
        
        Simplified implementation - for production, use rouge-score library.
        
        Args:
            generated: Generated text
            references: List of reference texts
            
        Returns:
            Average ROUGE-L F1 score across references
        """
        if not generated or not references:
            return 0.0
        
        def lcs_length(s1: str, s2: str) -> int:
            """Compute length of longest common subsequence."""
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        def rouge_l_score(candidate: str, reference: str) -> float:
            """Compute ROUGE-L score between candidate and reference."""
            # Tokenize (simple whitespace split)
            cand_tokens = candidate.lower().split()
            ref_tokens = reference.lower().split()
            
            if not cand_tokens or not ref_tokens:
                return 0.0
            
            lcs = lcs_length(cand_tokens, ref_tokens)
            
            precision = lcs / len(cand_tokens) if cand_tokens else 0.0
            recall = lcs / len(ref_tokens) if ref_tokens else 0.0
            
            if precision + recall == 0:
                return 0.0
            
            f1 = 2 * precision * recall / (precision + recall)
            return f1
        
        # Average ROUGE-L across all references
        scores = [rouge_l_score(generated, ref) for ref in references]
        return sum(scores) / len(scores) if scores else 0.0
    
    def compute_faithfulness(self, generated: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute faithfulness score - how well the biography reflects the attributes.
        
        Args:
            generated: Generated biography
            attributes: Original attributes
            
        Returns:
            Dictionary with faithfulness metrics
        """
        generated_lower = generated.lower()
        
        # Extract key attribute values
        key_attributes = {}
        for key, value in attributes.items():
            if value and isinstance(value, str):
                # Normalize value for comparison
                value_normalized = str(value).lower().strip()
                if len(value_normalized) > 2:  # Skip very short values
                    key_attributes[key] = value_normalized
        
        # Check which attributes appear in the biography
        found_attributes = {}
        for key, value in key_attributes.items():
            # Check if the value (or key parts) appear in generated text
            if self._attribute_in_text(value, generated_lower):
                found_attributes[key] = True
            else:
                found_attributes[key] = False
        
        # Compute scores
        total_attributes = len(key_attributes)
        found_count = sum(1 for v in found_attributes.values() if v)
        
        faithfulness_score = found_count / total_attributes if total_attributes > 0 else 0.0
        
        return {
            'score': faithfulness_score,
            'found_attributes': found_count,
            'total_attributes': total_attributes,
            'details': found_attributes
        }
    
    def _attribute_in_text(self, attribute_value: str, text: str) -> bool:
        """
        Check if an attribute value appears in the text.
        
        Uses fuzzy matching to handle variations.
        
        Args:
            attribute_value: The attribute value to search for
            text: Text to search in
            
        Returns:
            True if attribute value is found
        """
        if not attribute_value or not text:
            return False
        
        # Simple substring matching
        if attribute_value.lower() in text.lower():
            return True
        
        # Check for key words/phrases (for longer attributes)
        words = attribute_value.lower().split()
        if len(words) > 1:
            # Check if most words appear
            found_words = sum(1 for word in words if len(word) > 3 and word in text.lower())
            if found_words >= len(words) * 0.7:  # 70% of words found
                return True
        
        return False
    
    def detect_hallucinations(self, generated: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential hallucinations - facts mentioned that aren't in attributes.
        
        This is a simplified heuristic-based approach.
        
        Args:
            generated: Generated biography
            attributes: Original attributes
            
        Returns:
            Dictionary with hallucination metrics
        """
        # Extract all attribute values
        attribute_values = set()
        for key, value in attributes.items():
            if value:
                if isinstance(value, str):
                    # Add individual words
                    words = value.lower().split()
                    attribute_values.update(words)
                    # Add full value
                    attribute_values.add(value.lower().strip())
                else:
                    attribute_values.add(str(value).lower().strip())
        
        # Extract sentences from generated text
        sentences = re.split(r'[.!?]+', generated)
        
        # Check each sentence for potential hallucinations
        # This is a simplified heuristic - in practice, would need NLP
        potential_hallucinations = []
        
        # Common patterns that might indicate hallucinations
        # (This is a basic implementation - could be improved with NER)
        
        hallucination_score = 0.0  # Lower is better
        
        # Simple heuristic: count sentences that don't contain any attribute values
        sentences_with_attributes = 0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            contains_attribute = any(
                attr in sentence_lower for attr in attribute_values 
                if len(attr) > 3  # Only check longer attributes
            )
            if contains_attribute:
                sentences_with_attributes += 1
        
        total_sentences = len([s for s in sentences if s.strip()])
        if total_sentences > 0:
            # Score: percentage of sentences that reference attributes
            hallucination_score = 1.0 - (sentences_with_attributes / total_sentences)
        
        return {
            'score': hallucination_score,  # 0 = no hallucinations, 1 = many hallucinations
            'sentences_with_attributes': sentences_with_attributes,
            'total_sentences': total_sentences,
            'potential_hallucinations': potential_hallucinations
        }
    
    def compute_attribute_coverage(self, generated: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute how many attributes are covered in the generated biography.
        
        Args:
            generated: Generated biography
            attributes: Original attributes
            
        Returns:
            Dictionary with coverage metrics
        """
        faithfulness = self.compute_faithfulness(generated, attributes)
        
        return {
            'coverage_ratio': faithfulness['score'],
            'covered_attributes': faithfulness['found_attributes'],
            'total_attributes': faithfulness['total_attributes'],
            'missing_attributes': [
                key for key, found in faithfulness['details'].items() 
                if not found
            ]
        }


if __name__ == "__main__":
    # Test the evaluator
    evaluator = BiographyEvaluator()
    
    # Example
    generated = "John Smith was born in 1980 in New York. He is a software engineer."
    attributes = {
        "name": "John Smith",
        "birth_date": "1980",
        "birth_place": "New York",
        "occupation": "software engineer"
    }
    references = [
        "John Smith (born 1980) is a software engineer from New York.",
        "John Smith, born in New York in 1980, works as a software engineer."
    ]
    
    results = evaluator.evaluate(generated, attributes, references)
    print("Evaluation Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")

