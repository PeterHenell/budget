"""
Classification Module for Budget App

This module contains all transaction classification strategies:
- Rule-based classification for known patterns
- Machine learning classification based on historical data
- LLM-powered classification using local AI models
- Hybrid approaches combining multiple strategies

Main Components:
- AutoClassificationEngine: Main orchestrator
- RuleBasedClassifier: Pattern matching for Swedish merchants
- LearningClassifier: Learn from existing classifications
- SuperFastClassifier: Hybrid rule+LLM (highest priority)
- DockerLLMClassifier: Docker-optimized LLM classification
- FastLLMClassifier: High-performance LLM with caching

Usage:
    from classifiers import AutoClassificationEngine
    engine = AutoClassificationEngine(logic)
    suggestions = engine.classify_transaction(transaction_data)
"""

from .auto_classify import (
    AutoClassificationEngine,
    TransactionClassifier,
    RuleBasedClassifier,
    LearningClassifier
)

from .super_fast_classifier import SuperFastClassifier
from .docker_llm_classifier import DockerLLMClassifier
from .fast_llm_classifier import FastLLMClassifier

__all__ = [
    'AutoClassificationEngine',
    'TransactionClassifier',
    'RuleBasedClassifier', 
    'LearningClassifier',
    'SuperFastClassifier',
    'DockerLLMClassifier',
    'FastLLMClassifier'
]

# Version info
__version__ = "2.0.0"
__description__ = "LLM-powered transaction classification system"
