#!/usr/bin/env python3
"""
LLM Initialization Module for Budget App
Handles automatic LLM service initialization during web app startup
"""

import os
import time
import requests
import json
from typing import Dict, Any, Optional, List
from logging_config import get_logger

logger = get_logger(__name__)


class LLMInitializer:
    """Handle LLM service initialization and model setup"""
    
    def __init__(self):
        """Initialize LLM initializer with configuration from environment"""
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.preferred_models = [
            'llama3.2:1b',    # Smallest and most memory-efficient
            'tinyllama:1.1b', # Ultra-lightweight fallback
            'qwen2:1.5b',     # Small efficient model
            'gemma2:2b',      # Medium size, good performance
            'phi3:mini'       # Larger model, good for classification but needs more memory
        ]
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def is_ollama_service_ready(self, timeout: int = 60) -> bool:
        """Check if Ollama service is ready to accept requests"""
        logger.info("Checking if Ollama service is ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.ollama_host}/api/tags", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Ollama service is ready")
                    return True
            except Exception as e:
                logger.debug(f"Ollama not ready yet: {e}")
                
            time.sleep(2)
            
        logger.warning(f"⚠️  Ollama service not ready after {timeout} seconds")
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of models available in Ollama"""
        try:
            response = self.session.get(f"{self.ollama_host}/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json().get('models', [])
                return [model['name'] for model in models_data]
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available"""
        available_models = self.get_available_models()
        return any(model_name in name for name in available_models)
    
    def pull_model(self, model_name: str, timeout: int = 1800) -> bool:
        """Pull/download a model to Ollama"""
        logger.info(f"🔄 Downloading model: {model_name}")
        
        try:
            pull_data = {"name": model_name}
            response = self.session.post(
                f"{self.ollama_host}/api/pull",
                json=pull_data,
                timeout=timeout,
                stream=True
            )
            
            if response.status_code == 200:
                # Process streaming response
                for line in response.iter_lines():
                    if line:
                        try:
                            status_data = json.loads(line.decode('utf-8'))
                            if status_data.get('status') == 'success':
                                logger.info(f"✅ Successfully downloaded model: {model_name}")
                                return True
                        except json.JSONDecodeError:
                            continue
                            
                logger.info(f"✅ Model download completed: {model_name}")
                return True
            else:
                logger.error(f"❌ Failed to download model {model_name}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to download model {model_name}: {e}")
            return False
    
    def test_model(self, model_name: str) -> bool:
        """Test if a model works for classification tasks"""
        logger.info(f"🧪 Testing model: {model_name}")
        
        try:
            test_prompt = """Classify this Swedish transaction: ICA SUPERMARKET 450.50 SEK. 
Categories: Mat, Transport, Nöje, Boende. 
Respond with just the category name."""
            
            generate_data = {
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            }
            
            response = self.session.post(
                f"{self.ollama_host}/api/generate",
                json=generate_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for memory or other errors
                if 'error' in result:
                    logger.warning(f"⚠️  Model test failed for {model_name}: {result['error']}")
                    return False
                
                response_text = result.get('response', '').strip()
                
                # Check if response contains a reasonable classification
                if response_text and len(response_text) < 50:  # Reasonable length
                    logger.info(f"✅ Model test successful: {model_name}")
                    logger.debug(f"Test response: {response_text}")
                    return True
            else:
                logger.warning(f"⚠️  Model test failed: {model_name} (HTTP {response.status_code})")
                    
            logger.warning(f"⚠️  Model test failed: {model_name}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Model test failed for {model_name}: {e}")
            return False
    
    def initialize_best_model(self) -> Optional[str]:
        """Initialize the best available model for classification"""
        logger.info("🤖 Starting LLM model initialization...")
        
        # First, check if any preferred model is already available
        available_models = self.get_available_models()
        logger.info(f"Currently available models: {available_models}")
        
        for model_name in self.preferred_models:
            if self.is_model_available(model_name):
                if self.test_model(model_name):
                    logger.info(f"🎉 Using existing model: {model_name}")
                    return model_name
        
        # No suitable model available, try to download one
        logger.info("No suitable model found, attempting to download...")
        
        for model_name in self.preferred_models:
            logger.info(f"Attempting to download: {model_name}")
            
            if self.pull_model(model_name):
                if self.test_model(model_name):
                    logger.info(f"🎉 Successfully initialized model: {model_name}")
                    return model_name
                else:
                    logger.warning(f"Model downloaded but test failed: {model_name}")
            else:
                logger.warning(f"Failed to download model: {model_name}")
        
        logger.error("❌ Failed to initialize any suitable model")
        return None
    
    def needs_initialization(self) -> bool:
        """Check if LLM needs initialization"""
        if not self.is_ollama_service_ready(timeout=10):
            return False  # Service not available, can't initialize
            
        # Check if any preferred model is available and working
        for model_name in self.preferred_models:
            if self.is_model_available(model_name):
                if self.test_model(model_name):
                    return False  # We have a working model
                    
        return True  # No working model found, needs initialization
    
    def auto_initialize_if_needed(self) -> Optional[str]:
        """
        Automatically initialize LLM if needed
        Returns the initialized model name or None if failed/not needed
        """
        try:
            if not self.is_ollama_service_ready(timeout=30):
                logger.info("🤖 Ollama service not available, skipping LLM initialization")
                return None
            
            if not self.needs_initialization():
                logger.info("✅ LLM already initialized and working")
                # Return the first working model
                for model_name in self.preferred_models:
                    if self.is_model_available(model_name) and self.test_model(model_name):
                        return model_name
                return None
            
            logger.info("🔧 LLM needs initialization, starting setup...")
            model_name = self.initialize_best_model()
            
            if model_name:
                logger.info(f"✅ LLM auto-initialized successfully with model: {model_name}")
                return model_name
            else:
                logger.warning("⚠️  LLM auto-initialization failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM auto-initialization error: {e}")
            return None


def auto_initialize_llm() -> Optional[str]:
    """
    Convenience function for automatic LLM initialization
    Returns the initialized model name or None if failed
    """
    initializer = LLMInitializer()
    return initializer.auto_initialize_if_needed()


if __name__ == "__main__":
    """Test the LLM initialization"""
    import sys
    
    print("🧪 Testing LLM Auto-Initialization")
    print("=" * 50)
    
    model = auto_initialize_llm()
    
    if model:
        print(f"✅ LLM initialization test successful: {model}")
        sys.exit(0)
    else:
        print("❌ LLM initialization test failed")
        sys.exit(1)
