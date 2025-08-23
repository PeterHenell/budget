"""
Auto-classification module for the Budget App
Provides various strategies for automatically classifying transactions
while running completely local.
"""

import os
import re
import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logging_config import get_logger


class TransactionClassifier:
    """Base class for transaction classification strategies"""
    
    def __init__(self, logic):
        self.logic = logic
        
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """
        Classify a transaction and return (category, confidence_score)
        Returns (None, 0.0) if no classification found
        """
        raise NotImplementedError


class RuleBasedClassifier(TransactionClassifier):
    """Rule-based classifier using patterns and merchant databases"""
    
    def __init__(self, logic):
        super().__init__(logic)
        self.rules = self._load_default_rules()
        
    def _load_default_rules(self):
        """Load default classification rules for Swedish merchants"""
        return [
            # Food & Groceries
            {
                "patterns": [r"ICA", r"COOP", r"HEMKÖP", r"WILLYS", r"LIDL", r"NETTO"],
                "category": "Mat",
                "confidence": 0.9
            },
            {
                "patterns": [r"SYSTEMBOLAGET", r"SYSTEMBOLAGE"],
                "category": "Mat",  # or create "Alkohol" category
                "confidence": 0.95
            },
            
            # Transportation
            {
                "patterns": [r"SL\s", r"^SL$", r"PRESSBYRÅN.*SL"],  # Stockholm public transport
                "category": "Transport", 
                "confidence": 0.9
            },
            {
                "patterns": [r"SHELL", r"OKQ8", r"PREEM", r"CIRCLE K", r"QSTAR"],
                "category": "Transport",
                "confidence": 0.85
            },
            {
                "patterns": [r"PARKERING", r"P-HUS", r"APCOA"],
                "category": "Transport",
                "confidence": 0.8
            },
            
            # Healthcare
            {
                "patterns": [r"APOTEKET", r"APOTEK", r"VÅRDCENTRAL", r"FOLKTANDVÅRD"],
                "category": "Hälsa",
                "confidence": 0.9
            },
            
            # Entertainment & Dining
            {
                "patterns": [r"RESTAURANG", r"CAFÉ", r"PIZZERIA", r"SUSHI"],
                "category": "Nöje",
                "confidence": 0.8
            },
            {
                "patterns": [r"CINEMA", r"FILMSTADEN", r"SF BIO"],
                "category": "Nöje",
                "confidence": 0.9
            },
            
            # Housing (rent, utilities, etc.)
            {
                "patterns": [r"HYRA", r"ELNÄT", r"VATTENFALL", r"TELIA", r"BREDBAND"],
                "category": "Boende",
                "confidence": 0.85
            },
            
            # Income (usually positive amounts)
            {
                "patterns": [r"LÖN", r"SALARY", r"PENSION"],
                "category": "Inkomst",  # Would need to add this category
                "confidence": 0.95,
                "amount_filter": "positive"  # Only apply to positive amounts
            }
        ]
    
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """Classify based on description patterns"""
        description = transaction.get('description', '').upper()
        amount = transaction.get('amount', 0)
        
        best_match = None
        best_confidence = 0.0
        
        for rule in self.rules:
            # Check amount filter if specified
            if 'amount_filter' in rule:
                if rule['amount_filter'] == 'positive' and amount <= 0:
                    continue
                elif rule['amount_filter'] == 'negative' and amount >= 0:
                    continue
                    
            # Check if any pattern matches
            for pattern in rule['patterns']:
                if re.search(pattern, description):
                    if rule['confidence'] > best_confidence:
                        best_match = rule['category']
                        best_confidence = rule['confidence']
                        break
        
        return best_match, best_confidence


class LearningClassifier(TransactionClassifier):
    """Machine learning classifier that learns from existing classifications"""
    
    def __init__(self, logic):
        super().__init__(logic)
        self.features_cache = {}
        self.category_patterns = {}
        self._build_patterns()
    
    def _build_patterns(self):
        """Build classification patterns from existing classified transactions"""
        # Get classified transactions through proper abstraction layer
        classified_transactions = self.logic.get_classified_transactions_for_patterns()
        
        if not classified_transactions:
            return
        
        # Build patterns for each category
        category_data = {}
        for desc, amount, category, year, month in classified_transactions:
            if category not in category_data:
                category_data[category] = {
                    'descriptions': [],
                    'amounts': [],
                    'word_freq': Counter()
                }
            
            category_data[category]['descriptions'].append(desc.upper())
            category_data[category]['amounts'].append(amount)
            
            # Extract words for frequency analysis
            words = re.findall(r'\b[A-ZÅÄÖ]{3,}\b', desc.upper())
            category_data[category]['word_freq'].update(words)
        
        # Build classification patterns
        for category, data in category_data.items():
            # Get most common words for this category
            common_words = data['word_freq'].most_common(10)
            
            # Calculate amount statistics
            amounts = data['amounts']
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            
            self.category_patterns[category] = {
                'common_words': [word for word, freq in common_words if freq > 1],
                'avg_amount': avg_amount,
                'amount_std': self._calculate_std(amounts) if len(amounts) > 1 else 0,
                'transaction_count': len(data['descriptions'])
            }
    
    def _calculate_std(self, values):
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
    
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """Classify based on learned patterns"""
        description = transaction.get('description', '').upper()
        amount = transaction.get('amount', 0)
        
        if not self.category_patterns:
            return None, 0.0
        
        best_category = None
        best_score = 0.0
        
        # Extract words from description
        words = set(re.findall(r'\b[A-ZÅÄÖ]{3,}\b', description))
        
        for category, pattern in self.category_patterns.items():
            score = 0.0
            
            # Word matching score
            word_matches = len(words.intersection(set(pattern['common_words'])))
            if pattern['common_words']:
                word_score = word_matches / len(pattern['common_words'])
                score += word_score * 0.7  # 70% weight for word matching
            
            # Amount similarity score (if we have amount data)
            if pattern['amount_std'] > 0:
                amount_diff = abs(float(amount) - float(pattern['avg_amount']))
                amount_score = max(0, 1 - (amount_diff / (float(pattern['amount_std']) * 2)))
                score += amount_score * 0.3  # 30% weight for amount similarity
            
            # Boost score based on training data volume
            confidence_boost = min(0.1, pattern['transaction_count'] / 100)
            score += confidence_boost
            
            if score > best_score:
                best_category = category
                best_score = score
        
        # Only return if confidence is reasonable
        if best_score > 0.4:  # Threshold for suggestion
            return best_category, min(best_score, 0.95)  # Cap at 95%
        
        return None, 0.0


class AutoClassificationEngine:
    """Main engine that combines multiple classification strategies, prioritizing LLM classifiers"""
    
    def __init__(self, logic):
        self.logic = logic
        self.logger = get_logger(f'{__name__}.AutoClassificationEngine')
        # Initialize with empty list - will be populated in priority order
        self.classifiers = []
        
        # Check if LLM priority is enabled (default: true)
        llm_priority = os.getenv('LLM_PRIORITY', 'true').lower() == 'true'
        
        if llm_priority:
            # Add LLM classifiers first (highest priority)
            self._add_llm_classifiers()
            
            # Add traditional classifiers as fallback
            self.classifiers.extend([
                RuleBasedClassifier(logic),
                LearningClassifier(logic)
            ])
        else:
            # Traditional order: rules, learning, then LLM
            self.classifiers.extend([
                RuleBasedClassifier(logic),
                LearningClassifier(logic)
            ])
            self._add_llm_classifiers()
        
        self.logger.info(f"Auto-classification engine initialized with {len(self.classifiers)} classifiers")
        if llm_priority:
            self.logger.info("LLM classifiers have PRIORITY")
        else:
            self.logger.info("Traditional classifiers have priority")
    
    def _add_llm_classifiers(self):
        """Add LLM classifiers in priority order (most capable first)"""
        llm_added = False
        
        # Priority 1: SuperFast classifier (hybrid rule+LLM, best of both worlds)
        try:
            from .super_fast_classifier import SuperFastClassifier
            super_fast = SuperFastClassifier(self.logic)
            self.classifiers.append(super_fast)
            self.logger.info("SuperFast Classifier (Rule+LLM hybrid) - PRIORITY #1")
            llm_added = True
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"SuperFast Classifier failed: {e}")
        
        # Priority 2: Docker LLM classifier (pure LLM with Docker optimization)
        try:
            from docker_llm_classifier import DockerLLMClassifier
            llm_classifier = DockerLLMClassifier(self.logic)
            if llm_classifier.available:
                self.classifiers.append(llm_classifier)
                self.logger.info("Docker LLM Classifier - PRIORITY #2")
                llm_added = True
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"Docker LLM Classifier failed: {e}")
        
        # Priority 3: Fast LLM classifier (fallback pure LLM)
        if not llm_added:
            try:
                from .fast_llm_classifier import FastLLMClassifier
                fast_llm = FastLLMClassifier(self.logic)
                if fast_llm.available:
                    self.classifiers.append(fast_llm)
                    self.logger.info("Fast LLM Classifier - PRIORITY #3")
                    llm_added = True
            except ImportError:
                pass
            except Exception as e:
                self.logger.warning(f"Fast LLM Classifier failed: {e}")
        
        if not llm_added:
            self.logger.info("No LLM classifiers available - falling back to rule-based classification")
        else:
            self.logger.info("LLM-supported classification is now DEFAULT")
    
    def classify_transaction(self, transaction_data) -> List[Dict]:
        """
        Get classification suggestions from all classifiers, prioritizing LLM results
        Returns list of suggestions sorted by priority and confidence
        """
        suggestions = []
        llm_suggestions = []
        traditional_suggestions = []
        
        for classifier in self.classifiers:
            category, confidence = classifier.classify(transaction_data)
            
            # Different confidence thresholds for different classifier types
            classifier_name = classifier.__class__.__name__
            
            if classifier_name in ['SuperFastClassifier', 'DockerLLMClassifier', 'FastLLMClassifier']:
                # Lower threshold for LLM classifiers (they're generally more accurate)
                min_confidence = 0.4
                suggestion_type = 'llm'
            else:
                # Higher threshold for traditional classifiers
                min_confidence = 0.6
                suggestion_type = 'traditional'
            
            if category and confidence > min_confidence:
                suggestion = {
                    'category': category,
                    'confidence': confidence,
                    'classifier': classifier_name,
                    'type': suggestion_type
                }
                
                if suggestion_type == 'llm':
                    llm_suggestions.append(suggestion)
                else:
                    traditional_suggestions.append(suggestion)
        
        # Sort LLM suggestions by confidence (highest first)
        llm_suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Sort traditional suggestions by confidence
        traditional_suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Prioritize LLM suggestions, then traditional ones
        suggestions = llm_suggestions + traditional_suggestions
        
        # Remove duplicates, keeping the highest confidence version of each category
        seen_categories = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            if suggestion['category'] not in seen_categories:
                unique_suggestions.append(suggestion)
                seen_categories.add(suggestion['category'])
        
        return unique_suggestions
    
    def auto_classify_uncategorized(self, confidence_threshold=0.7, max_suggestions=100):
        """
        Automatically classify uncategorized transactions, prioritizing LLM results
        Uses lower confidence threshold to leverage LLM capabilities
        Returns (classified_count, suggestions_for_review)
        """
        uncategorized = self.logic.get_uncategorized_transactions(limit=max_suggestions)
        
        classified_count = 0
        suggestions_for_review = []
        llm_classifications = 0
        traditional_classifications = 0
        
        for tx in uncategorized:
            tx_id, verif_num, date, description, amount, year, month = tx
            
            transaction_data = {
                'description': description,
                'amount': amount,
                'date': date,
                'year': year,
                'month': month
            }
            
            suggestions = self.classify_transaction(transaction_data)
            
            if suggestions:
                best_suggestion = suggestions[0]
                
                # Auto-classify if confidence meets threshold
                if best_suggestion['confidence'] >= confidence_threshold:
                    try:
                        # Map classifier to method name for tracking
                        classifier_to_method = {
                            'SuperFastClassifier': 'hybrid-llm',
                            'DockerLLMClassifier': 'docker-llm', 
                            'FastLLMClassifier': 'fast-llm',
                            'RuleBasedClassifier': 'rules',
                            'LearningClassifier': 'learning'
                        }
                        method = classifier_to_method.get(best_suggestion.get('classifier'), 'auto')
                        
                        self.logic.reclassify_transaction(
                            tx_id, 
                            best_suggestion['category'],
                            confidence=best_suggestion['confidence'],
                            classification_method=method
                        )
                        classified_count += 1
                        
                        # Track classification type for reporting
                        if best_suggestion.get('type') == 'llm':
                            llm_classifications += 1
                        else:
                            traditional_classifications += 1
                            
                    except Exception as e:
                        self.logger.error(f"Error classifying transaction {tx_id}: {e}")
                
                # Add to review queue if confidence is moderate (0.4-threshold)
                elif best_suggestion['confidence'] >= 0.4:
                    suggestions_for_review.append({
                        'transaction_id': tx_id,
                        'description': description,
                        'amount': amount,
                        'date': date,
                        'suggestions': suggestions[:3],  # Top 3 suggestions
                        'needs_review': True
                    })
        
        # Log summary of classification results
        if classified_count > 0:
            self.logger.info(f"Classification Summary:")
            self.logger.info(f"   LLM Classifications: {llm_classifications}")
            self.logger.info(f"   Traditional Classifications: {traditional_classifications}")
            self.logger.info(f"   Total Auto-classified: {classified_count}")
            if suggestions_for_review:
                self.logger.info(f"   Requiring Review: {len(suggestions_for_review)}")
        
        return classified_count, suggestions_for_review


# Example usage functions that could be integrated into the GUI or CLI

def demo_auto_classification(logic):
    """Demo function showing auto-classification capabilities"""
    engine = AutoClassificationEngine(logic)
    
    print("=== Auto-Classification Demo ===")
    
    # Show some uncategorized transactions and their suggestions
    uncategorized = logic.get_uncategorized_transactions(limit=5)
    
    for tx in uncategorized:
        tx_id, verif_num, date, description, amount, year, month = tx
        
        transaction_data = {
            'description': description,
            'amount': amount,
            'date': date,
            'year': year,
            'month': month
        }
        
        suggestions = engine.classify_transaction(transaction_data)
        
        print(f"\nTransaction: {date} | {amount:,.2f} | {description}")
        if suggestions:
            print("Suggestions:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"  {i}. {suggestion['category']} "
                      f"({suggestion['confidence']:.1%} confidence, "
                      f"{suggestion['classifier']})")
        else:
            print("  No suggestions found")


def batch_auto_classify(logic, confidence_threshold=0.8):
    """Batch classify transactions with high confidence"""
    engine = AutoClassificationEngine(logic)
    
    classified_count, suggestions = engine.auto_classify_uncategorized(
        confidence_threshold=confidence_threshold
    )
    
    print(f"Auto-classified {classified_count} transactions")
    
    if suggestions:
        print(f"\n{len(suggestions)} transactions need manual review:")
        for item in suggestions[:5]:  # Show first 5
            print(f"  {item['description']} -> Suggested: {item['suggestions'][0]['category']} "
                  f"({item['suggestions'][0]['confidence']:.1%})")
    
    return classified_count, suggestions
