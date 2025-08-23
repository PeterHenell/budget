#!/usr/bin/env python3
"""
Test script for LLM auto-initialization validation
"""
import os
import sys
import requests
import json

def test_llm_classification():
    """Test that the auto-initialized LLM works for classification"""
    print("🧪 Testing LLM Auto-Classification")
    print("=" * 50)
    
    # Test Ollama service directly
    try:
        ollama_host = 'http://localhost:11434'
        model_name = 'llama3.2:1b'  # Our preferred model
        
        # Test classification
        test_prompt = """Classify this Swedish transaction: WILLYS 289.50 SEK. 
Categories: Mat, Transport, Nöje, Boende, Hälsa, Övrigt. 
Respond with just the category name."""
        
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            classification = result.get('response', '').strip()
            print(f"✅ LLM Classification Test Successful!")
            print(f"   Input: WILLYS 289.50 SEK")
            print(f"   Classification: {classification}")
            print(f"   Model: {model_name}")
            
            # Test web app health endpoint
            health_response = requests.get('http://localhost:5000/health', timeout=10)
            if health_response.status_code == 200:
                health_data = health_response.json()
                llm_status = health_data.get('services', {}).get('llm_classifier', 'unknown')
                print(f"   Web App LLM Status: {llm_status}")
                
                if 'available' in llm_status:
                    print("✅ Complete LLM auto-initialization test PASSED!")
                    return True
                else:
                    print(f"❌ Web app doesn't recognize LLM: {llm_status}")
                    return False
            else:
                print(f"❌ Web app health check failed: {health_response.status_code}")
                return False
        else:
            print(f"❌ LLM classification failed: {response.status_code}")
            if response.content:
                print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ LLM test error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 LLM Auto-Initialization Validation")
    print("=" * 50)
    
    success = test_llm_classification()
    
    print("=" * 50)
    if success:
        print("🎉 LLM auto-initialization validation SUCCESSFUL!")
        sys.exit(0)
    else:
        print("❌ LLM auto-initialization validation FAILED!")
        sys.exit(1)
