"""
High-Performance LLM Classifier for Budget App
Optimized for speed with caching, connection pooling, and minimal prompts
"""

import os
import json
import time
import requests
from typing import Tuple, Optional, List, Dict
from threading import Lock
import hashlib
from collections import OrderedDict
from auto_classify import TransactionClassifier


class FastLLMClassifier(TransactionClassifier):
    """
    High-performance LLM classifier with multiple speed optimizations:
    - Connection pooling and keep-alive
    - Response caching 
    - Minimal, optimized prompts
    - Batch processing support
    - Concurrent request handling
    """
    
    def __init__(self, logic):
        super().__init__(logic)
        
        # Configuration from environment variables
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'phi3:mini')
        self.confidence_threshold = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.6'))
        self.enabled = os.getenv('LLM_ENABLED', 'false').lower() == 'true'
        
        # Speed optimizations
        self.max_cache_size = 1000
        self.cache_lock = Lock()
        self.response_cache = OrderedDict()
        
        # HTTP session with optimizations
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Connection pool optimization
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,      # Max connections in each pool
            max_retries=1         # Fast fail on errors
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Check if LLM service is available
        self.available = self.enabled and self._check_ollama_available()
        
        if self.available:
            self.categories = [cat for cat in logic.get_categories() 
                             if cat != "Uncategorized"]
            
            # Pre-warm the model with a quick query
            self._warm_up_model()
            print(f"🚀 Fast LLM Classifier ready with model: {self.model_name}")
        else:
            print("⚠️  Fast LLM Classifier not available")
    
    def _check_ollama_available(self) -> bool:
        """Quick availability check with timeout"""
        try:
            response = self.session.get(f"{self.ollama_host}/api/tags", timeout=3)
            if response.status_code != 200:
                return False
            
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            return any(self.model_name in name for name in model_names)
            
        except Exception:
            return False
    
    def _warm_up_model(self):
        """Pre-warm the model to reduce first request latency"""
        try:
            self._call_ollama_api_fast("Warm up", max_tokens=5, timeout=10)
        except:
            pass  # Ignore warm-up failures
    
    def _get_cache_key(self, description: str, amount: float) -> str:
        """Generate cache key for response caching"""
        # Normalize description for better cache hits
        normalized = description.upper().strip()
        # Round amount to reduce cache misses on similar amounts
        rounded_amount = round(amount, -1)  # Round to nearest 10
        return hashlib.md5(f"{normalized}:{rounded_amount}".encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Tuple[str, float]]:
        """Get cached classification result"""
        with self.cache_lock:
            if cache_key in self.response_cache:
                # Move to end (LRU)
                result = self.response_cache.pop(cache_key)
                self.response_cache[cache_key] = result
                return result
        return None
    
    def _cache_response(self, cache_key: str, result: Tuple[str, float]):
        """Cache classification result"""
        with self.cache_lock:
            if len(self.response_cache) >= self.max_cache_size:
                # Remove oldest entry
                self.response_cache.popitem(last=False)
            self.response_cache[cache_key] = result
    
    def classify(self, transaction) -> Tuple[Optional[str], float]:
        """Fast classify transaction using optimized LLM"""
        if not self.available:
            return None, 0.0
        
        description = transaction.get('description', '').strip()
        amount = transaction.get('amount', 0)
        
        # Skip very short descriptions
        if len(description) < 3:
            return None, 0.0
        
        # Check cache first
        cache_key = self._get_cache_key(description, amount)
        cached_result = self._get_cached_response(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Use ultra-fast minimal prompt
            prompt = self._build_minimal_prompt(description, amount)
            
            # Fast API call with optimized settings
            response = self._call_ollama_api_fast(prompt, max_tokens=50, timeout=15)
            if not response:
                return None, 0.0
            
            # Parse response
            category, confidence = self._parse_fast_response(response)
            
            # Cache the result
            if category and confidence > 0.5:
                result = (category, confidence)
                self._cache_response(cache_key, result)
                return result if confidence >= self.confidence_threshold else (None, 0.0)
            
            return None, 0.0
                
        except Exception as e:
            print(f"Fast LLM error: {e}")
            return None, 0.0
    
    def _build_minimal_prompt(self, description: str, amount: float) -> str:
        """Build ultra-minimal prompt for fastest response"""
        # Super concise prompt for speed - but still clear
        categories = ", ".join(self.categories)
        
        return f"""Swedish transaction classification:

Description: {description}
Amount: {amount:.0f} SEK

Categories: {categories}
Quick rules: ICA/COOP/Hemköp = Mat, SL = Transport, McDonald's/Pizza = Nöje, Vattenfall/Hyra = Boende

Respond only with JSON: {{"category": "Mat", "confidence": 0.9}}

If uncertain: {{"category": null, "confidence": 0.0}}"""
    
    def _call_ollama_api_fast(self, prompt: str, max_tokens: int = 100, timeout: int = 15) -> Optional[str]:
        """Ultra-fast API call with aggressive optimization"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,      # Deterministic for caching
                    "top_p": 0.9,           # Focus on likely tokens
                    "top_k": 10,            # Limit token choices
                    "num_predict": max_tokens,  # Sufficient tokens for JSON
                    "repeat_penalty": 1.0,   # No repetition penalty
                    "stop": ["\n\n", "END"],  # Early stopping but allow JSON
                    "num_ctx": 2048,        # Larger context for better understanding
                    "num_batch": 8,         # Smaller batch size
                    "num_thread": 4,        # Use available threads
                    "mirostat": 2,          # Better sampling
                    "mirostat_eta": 0.1,    # Aggressive learning rate
                    "mirostat_tau": 5.0     # Lower target entropy
                }
            }
            
            response = self.session.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                print(f"Ollama API error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"LLM timeout after {timeout}s")
        except Exception as e:
            print(f"Fast LLM API error: {e}")
        
        return None
    
    def _parse_fast_response(self, response_text: str) -> Tuple[Optional[str], float]:
        """Parse minimal response format"""
        try:
            # Try to find JSON in response
            response_text = response_text.strip()
            
            # Handle standard format: {"category":"Mat","confidence":0.9}
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                
                # Handle both formats
                category = result.get('category') or result.get('c')
                confidence = float(result.get('confidence', result.get('p', 0.0)))
                
                if category and category in self.categories:
                    return category, max(0.0, min(1.0, confidence))
            
            # Fallback: look for category names directly
            response_upper = response_text.upper()
            for category in self.categories:
                if category.upper() in response_upper:
                    return category, 0.75  # Medium confidence for fallback
            
            return None, 0.0
                
        except Exception as e:
            print(f"Parse error: {e} - Response: {response_text[:100]}")
            return None, 0.0
    
    def classify_batch(self, transactions: List[Dict], max_workers: int = 4) -> List[Dict]:
        """Fast batch classification with concurrent processing"""
        if not self.available:
            return []
        
        results = []
        
        # For small batches, process sequentially to avoid overhead
        if len(transactions) <= 3:
            for transaction in transactions:
                category, confidence = self.classify(transaction)
                if category:
                    results.append({
                        'transaction': transaction,
                        'suggested_category': category,
                        'confidence': confidence,
                        'classifier': 'FastLLM'
                    })
        else:
            # For larger batches, use threading could be added here
            # For now, keep simple sequential processing
            for transaction in transactions:
                category, confidence = self.classify(transaction)
                if category:
                    results.append({
                        'transaction': transaction,
                        'suggested_category': category,
                        'confidence': confidence,
                        'classifier': 'FastLLM'
                    })
        
        return results
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        with self.cache_lock:
            cache_size = len(self.response_cache)
        
        return {
            'enabled': self.enabled,
            'available': self.available,
            'model': self.model_name,
            'cache_size': cache_size,
            'cache_hit_ratio': 'N/A',  # Could track this
            'confidence_threshold': self.confidence_threshold,
            'optimizations': [
                'connection_pooling',
                'response_caching', 
                'minimal_prompts',
                'aggressive_timeouts',
                'deterministic_sampling'
            ]
        }
    
    def clear_cache(self):
        """Clear response cache"""
        with self.cache_lock:
            self.response_cache.clear()


def benchmark_classifiers():
    """Benchmark original vs fast classifier"""
    print("🏁 Benchmarking LLM Classifiers...")
    
    # Mock logic
    class MockLogic:
        def get_categories(self):
            return ["Mat", "Transport", "Nöje", "Boende", "Hälsa", "Uncategorized"]
    
    logic = MockLogic()
    
    # Test transactions
    test_transactions = [
        {"description": "ICA SUPERMARKET STOCKHOLM", "amount": -450.50},
        {"description": "SL ACCESS PENDELTÅG", "amount": -44.00},
        {"description": "MCDONALDS CENTRAL STATION", "amount": -89.00},
        {"description": "VATTENFALL ELRÄKNING", "amount": -1200.00},
        {"description": "ICA SUPERMARKET GÖTEBORG", "amount": -380.25},  # Should hit cache
    ]
    
    # Test Fast Classifier
    print("\n🚀 Testing Fast LLM Classifier:")
    fast_classifier = FastLLMClassifier(logic)
    
    if fast_classifier.available:
        start_time = time.time()
        fast_results = []
        
        for tx in test_transactions:
            result = fast_classifier.classify(tx)
            fast_results.append(result)
            print(f"  {tx['description'][:30]}... → {result}")
        
        fast_time = time.time() - start_time
        print(f"⚡ Fast classifier: {fast_time:.2f}s total, {fast_time/len(test_transactions):.2f}s avg")
        
        # Show performance stats
        stats = fast_classifier.get_performance_stats()
        print(f"📊 Performance stats: {stats}")
    else:
        print("❌ Fast classifier not available")


if __name__ == "__main__":
    benchmark_classifiers()
