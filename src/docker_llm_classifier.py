"""
Docker-optimized LLM Classifier for Budget App
Works with Ollama running in a separate container
"""

import os
import json
import time
import requests
from typing import Tuple, Optional, List, Dict
from auto_classify import TransactionClassifier


class DockerLLMClassifier(TransactionClassifier):
    """
    LLM-based classifier optimized for Docker deployment with Ollama
    Uses HTTP API instead of ollama-python for better container networking
    """
    
    def __init__(self, logic):
        super().__init__(logic)
        
        # Configuration from environment variables
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'phi3:mini')
        self.confidence_threshold = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.6'))
        self.enabled = os.getenv('LLM_ENABLED', 'false').lower() == 'true'
        
        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Check if LLM service is available
        self.available = self.enabled and self._check_ollama_available()
        
        if self.available:
            self.categories = [cat for cat in logic.get_categories() 
                             if cat != "Uncategorized"]
            print(f"✅ LLM Classifier ready with model: {self.model_name}")
        else:
            print("⚠️  LLM Classifier not available")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama service is running and model is loaded"""
        try:
            # Check if service is running
            response = self.session.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if our model is available
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            return any(self.model_name in name for name in model_names)
            
        except Exception as e:
            print(f"LLM availability check failed: {e}")
            return False
    
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """Classify transaction using LLM via HTTP API"""
        if not self.available:
            return None, 0.0
        
        description = transaction.get('description', '')
        amount = transaction.get('amount', 0)
        date = transaction.get('date', '')
        
        # Skip very short or unclear descriptions
        if len(description.strip()) < 3:
            return None, 0.0
        
        try:
            prompt = self._build_classification_prompt(description, amount, date)
            
            # Call Ollama API
            response = self._call_ollama_api(prompt)
            if not response:
                return None, 0.0
            
            # Parse response
            category, confidence = self._parse_llm_response(response)
            
            # Only return if confidence is above threshold
            if confidence >= self.confidence_threshold:
                return category, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            print(f"LLM classification error: {e}")
            return None, 0.0
    
    def _build_classification_prompt(self, description: str, amount: float, date: str = "") -> str:
        """Build optimized classification prompt"""
        categories_str = ", ".join(self.categories)
        
        # Create context-rich but concise prompt
        prompt = f"""You are a Swedish personal finance AI. Classify this transaction:

TRANSACTION:
Description: {description}
Amount: {amount:.2f} SEK
{f"Date: {date}" if date else ""}

CATEGORIES: {categories_str}

CLASSIFICATION RULES:
• ICA, COOP, Hemköp, Willys, Lidl → Mat
• SL, Shell, OKQ8, Preem → Transport
• Restaurang, McDonald's, Pizza → Nöje
• Systembolaget → Mat
• Apotek, Vårdcentral → Hälsa
• Hyra, Elnät, Vattenfall → Boende
• H&M, Zara, clothes → Kläder (if exists)

RESPONSE FORMAT (JSON only):
{{"category": "category_name", "confidence": 0.85}}

If unsure (confidence < 0.6):
{{"category": null, "confidence": 0.0}}"""

        return prompt
    
    def _call_ollama_api(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Call Ollama API with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent classification
                        "top_p": 0.8,
                        "num_predict": 100,  # Limit response length
                        "stop": ["\n\n"]     # Stop at double newline
                    }
                }
                
                response = self.session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=30  # 30 second timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '').strip()
                else:
                    print(f"Ollama API error: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"LLM timeout on attempt {attempt + 1}")
            except Exception as e:
                print(f"LLM API error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries:
                time.sleep(1)  # Brief pause before retry
        
        return None
    
    def _parse_llm_response(self, response_text: str) -> Tuple[Optional[str], float]:
        """Parse LLM response to extract category and confidence"""
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
            else:
                # Try to parse the whole response as JSON
                result = json.loads(response_text)
            
            category = result.get('category')
            confidence = float(result.get('confidence', 0.0))
            
            # Validate category exists in our system
            if category and category in self.categories:
                # Clamp confidence to reasonable range
                confidence = max(0.0, min(1.0, confidence))
                return category, confidence
            else:
                return None, 0.0
                
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Try to extract category from free text as fallback
            return self._fallback_parse(response_text)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None, 0.0
    
    def _fallback_parse(self, response_text: str) -> Tuple[Optional[str], float]:
        """Fallback parsing for non-JSON responses"""
        response_upper = response_text.upper()
        
        # Look for category names in response
        for category in self.categories:
            if category.upper() in response_upper:
                # Assign medium confidence for fallback parsing
                return category, 0.65
        
        return None, 0.0
    
    def classify_batch(self, transactions: List[Dict]) -> List[Dict]:
        """Classify multiple transactions efficiently"""
        if not self.available:
            return []
        
        results = []
        
        for transaction in transactions:
            category, confidence = self.classify(transaction)
            if category:
                results.append({
                    'transaction': transaction,
                    'suggested_category': category,
                    'confidence': confidence,
                    'classifier': 'LLM'
                })
        
        return results
    
    def get_status(self) -> Dict:
        """Get classifier status for health checks"""
        return {
            'enabled': self.enabled,
            'available': self.available,
            'model': self.model_name,
            'host': self.ollama_host,
            'confidence_threshold': self.confidence_threshold
        }


def test_llm_classifier():
    """Test function for LLM classifier"""
    print("🧪 Testing Docker LLM Classifier...")
    
    # Mock logic object for testing
    class MockLogic:
        def get_categories(self):
            return ["Mat", "Transport", "Nöje", "Boende", "Hälsa", "Uncategorized"]
    
    classifier = DockerLLMClassifier(MockLogic())
    
    if not classifier.available:
        print("❌ LLM classifier not available for testing")
        return False
    
    # Test transactions
    test_transactions = [
        {"description": "ICA SUPERMARKET STOCKHOLM", "amount": -450.50, "date": "2025-08-23"},
        {"description": "SL ACCESS PENDELTÅG", "amount": -44.00, "date": "2025-08-23"},
        {"description": "MCDONALDS CENTRAL STATION", "amount": -89.00, "date": "2025-08-23"},
        {"description": "VATTENFALL ELRÄKNING", "amount": -1200.00, "date": "2025-08-23"},
    ]
    
    print(f"Testing with {len(test_transactions)} transactions...")
    
    for i, transaction in enumerate(test_transactions, 1):
        print(f"\n{i}. {transaction['description']} ({transaction['amount']} SEK)")
        
        category, confidence = classifier.classify(transaction)
        
        if category:
            print(f"   → {category} ({confidence:.1%} confidence)")
        else:
            print("   → No classification")
    
    # Test batch classification
    print(f"\n🔄 Testing batch classification...")
    batch_results = classifier.classify_batch(test_transactions)
    
    print(f"✅ Batch classified {len(batch_results)} transactions")
    
    # Show status
    status = classifier.get_status()
    print(f"\n📊 Classifier Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    return True


if __name__ == "__main__":
    test_llm_classifier()
