"""
Super-Fast Hybrid Classifier combining rules + fast LLM
Uses intelligent routing: simple cases use rules, complex cases use LLM
"""

import re
import time
from typing import Tuple, Optional, Dict, List
from auto_classify import RuleBasedClassifier, TransactionClassifier


class SuperFastClassifier(TransactionClassifier):
    """
    Intelligent hybrid classifier that routes transactions optimally:
    - Simple/known patterns → Rule-based (instant)
    - Complex/unknown patterns → Fast LLM (2-3 seconds)
    - Caching for repeated patterns
    """
    
    def __init__(self, logic):
        super().__init__(logic)
        
        # Initialize rule-based classifier
        self.rule_classifier = RuleBasedClassifier(logic)
        
        # Try to initialize LLM classifier
        self.llm_classifier = None
        try:
            from fast_llm_classifier import FastLLMClassifier
            self.llm_classifier = FastLLMClassifier(logic)
            if not self.llm_classifier.available:
                self.llm_classifier = None
        except:
            pass
        
        # Enhanced pattern database for instant classification
        self.instant_patterns = self._build_enhanced_patterns()
        
        # Performance tracking
        self.stats = {
            'rule_hits': 0,
            'llm_calls': 0,
            'instant_hits': 0,
            'cache_hits': 0,
            'total_calls': 0
        }
        
        print(f"🚀 SuperFast Classifier ready - LLM: {'✅' if self.llm_classifier else '❌'}")
    
    def _build_enhanced_patterns(self) -> List[Dict]:
        """Build comprehensive pattern database for instant classification"""
        return [
            # Grocery stores
            {
                "patterns": [
                    r"\bICA\b", r"\bCOOP\b", r"\bHEMKÖP\b", r"\bWILLYS\b", 
                    r"\bLIDL\b", r"\bNETTO\b", r"\bMAXI\b", r"\bSTORE\b"
                ],
                "category": "Mat",
                "confidence": 0.95
            },
            
            # Transportation
            {
                "patterns": [
                    r"\bSL\b", r"SL\s", r"PRESSBYRÅN.*SL", r"\bMTR\b",
                    r"SHELL", r"OKQ8", r"PREEM", r"CIRCLE\s*K", r"QSTAR", r"ST1",
                    r"PARKERING", r"P-HUS", r"APCOA", r"TAXI"
                ],
                "category": "Transport", 
                "confidence": 0.90
            },
            
            # Restaurants and entertainment
            {
                "patterns": [
                    r"MCDONALD", r"BURGER", r"PIZZA", r"RESTAURANG", r"CAFÉ", r"ESPRESSO",
                    r"KFC", r"MAX\s", r"SUBWAY", r"SUSHI", r"THAI", r"INDIAN"
                ],
                "category": "Nöje",
                "confidence": 0.88
            },
            
            # Alcohol
            {
                "patterns": [r"SYSTEMBOLAGET", r"SYSTEMBOLAGE"],
                "category": "Mat",
                "confidence": 0.95
            },
            
            # Healthcare
            {
                "patterns": [
                    r"APOTEKET", r"APOTEK", r"VÅRDCENTRAL", r"FOLKTANDVÅRD", 
                    r"TANDLÄKARE", r"LÄKARE"
                ],
                "category": "Hälsa",
                "confidence": 0.92
            },
            
            # Utilities and housing
            {
                "patterns": [
                    r"VATTENFALL", r"ELNÄT", r"ELHANDEL", r"HYRA", r"BREDBAND", 
                    r"TELIA", r"TELENOR", r"COMHEM", r"FÖRSÄKRING"
                ],
                "category": "Boende",
                "confidence": 0.90
            },
            
            # Common retail
            {
                "patterns": [
                    r"H&M", r"ZARA", r"KLäDER", r"IKEA", r"ELGIGANTEN", 
                    r"MEDIAMARKT", r"CLAS\s*OHLSON"
                ],
                "category": "Övriga",  # If this category exists
                "confidence": 0.85
            }
        ]
    
    def _classify_with_patterns(self, description: str) -> Tuple[Optional[str], float]:
        """Super-fast pattern-based classification"""
        description_upper = description.upper()
        
        best_match = None
        best_confidence = 0.0
        
        for pattern_group in self.instant_patterns:
            for pattern in pattern_group['patterns']:
                if re.search(pattern, description_upper):
                    if pattern_group['confidence'] > best_confidence:
                        # Check if category exists in our system
                        if pattern_group['category'] in self.rule_classifier.logic.get_categories():
                            best_match = pattern_group['category']
                            best_confidence = pattern_group['confidence']
                            break
        
        return best_match, best_confidence
    
    def _should_use_llm(self, description: str, rule_confidence: float) -> bool:
        """Decide whether to use LLM based on complexity and confidence"""
        if not self.llm_classifier:
            return False
        
        # Use LLM if rule confidence is low
        if rule_confidence < 0.7:
            return True
        
        # Use LLM for complex/ambiguous descriptions
        if len(description.split()) > 4:  # Multi-word descriptions
            return True
        
        # Check for ambiguous terms
        ambiguous_terms = ['BETALNING', 'KÖPT', 'SWISH', 'KORT', 'ONLINE']
        description_upper = description.upper()
        if any(term in description_upper for term in ambiguous_terms):
            return True
        
        return False
    
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """Intelligent classification with optimal routing"""
        self.stats['total_calls'] += 1
        
        description = transaction.get('description', '').strip()
        
        if len(description) < 3:
            return None, 0.0
        
        # Step 1: Try super-fast pattern matching
        category, confidence = self._classify_with_patterns(description)
        
        if category and confidence >= 0.85:
            self.stats['instant_hits'] += 1
            return category, confidence
        
        # Step 2: Try rule-based classifier
        rule_result = self.rule_classifier.classify(transaction)
        rule_category, rule_confidence = rule_result
        
        if rule_category and rule_confidence >= 0.8:
            self.stats['rule_hits'] += 1
            return rule_category, rule_confidence
        
        # Step 3: Use LLM for complex cases (if available)
        if self._should_use_llm(description, rule_confidence) and self.llm_classifier:
            self.stats['llm_calls'] += 1
            llm_result = self.llm_classifier.classify(transaction)
            llm_category, llm_confidence = llm_result
            
            # Prefer LLM result if significantly more confident
            if llm_category and llm_confidence > max(rule_confidence, 0.6):
                return llm_category, llm_confidence
        
        # Fallback to rule result if available
        if rule_category:
            self.stats['rule_hits'] += 1
            return rule_category, rule_confidence
        
        return None, 0.0
    
    def get_performance_stats(self) -> Dict:
        """Get detailed performance statistics"""
        total = self.stats['total_calls']
        if total == 0:
            return self.stats
        
        return {
            'total_classifications': total,
            'instant_hits': f"{self.stats['instant_hits']} ({self.stats['instant_hits']/total*100:.1f}%)",
            'rule_hits': f"{self.stats['rule_hits']} ({self.stats['rule_hits']/total*100:.1f}%)",
            'llm_calls': f"{self.stats['llm_calls']} ({self.stats['llm_calls']/total*100:.1f}%)",
            'llm_available': self.llm_classifier is not None,
            'avg_speed_estimate': 'instant' if self.stats['llm_calls'] == 0 else 'mixed'
        }


def benchmark_super_fast():
    """Benchmark the SuperFast classifier"""
    print("🚀 Benchmarking SuperFast Classifier...")
    
    # Mock logic
    class MockLogic:
        def get_categories(self):
            return ["Mat", "Transport", "Nöje", "Boende", "Hälsa", "Övriga", "Uncategorized"]
    
    logic = MockLogic()
    
    # Test transactions (mix of simple and complex)
    test_transactions = [
        {"description": "ICA SUPERMARKET STOCKHOLM", "amount": -450.50},  # Should be instant
        {"description": "SL ACCESS PENDELTÅG", "amount": -44.00},         # Should be instant  
        {"description": "SHELL BENSINSTATION", "amount": -600.00},        # Should be instant
        {"description": "MCDONALDS CENTRAL STATION", "amount": -89.00},   # Should be instant
        {"description": "VATTENFALL ELRÄKNING", "amount": -1200.00},     # Should be instant
        {"description": "SWISH BETALNING ONLINE", "amount": -250.00},     # Might need LLM
        {"description": "OKÄND BUTIK STOCKHOLM", "amount": -123.45},      # Might need LLM
        {"description": "ICA SUPERMARKET GÖTEBORG", "amount": -380.25},   # Should be instant
    ]
    
    classifier = SuperFastClassifier(logic)
    
    print(f"\nTesting with {len(test_transactions)} transactions...")
    
    start_time = time.time()
    results = []
    
    for i, tx in enumerate(test_transactions, 1):
        tx_start = time.time()
        result = classifier.classify(tx)
        tx_time = time.time() - tx_start
        
        results.append(result)
        print(f"{i:2d}. {tx['description'][:35]:<35} → {str(result[0]):<10} ({result[1]:.2f}) [{tx_time:.3f}s]")
    
    total_time = time.time() - start_time
    
    print(f"\n⚡ Total time: {total_time:.2f}s, Average: {total_time/len(test_transactions):.3f}s per transaction")
    
    # Show detailed stats
    stats = classifier.get_performance_stats()
    print(f"\n📊 Performance breakdown:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return classifier, results


if __name__ == "__main__":
    benchmark_super_fast()
