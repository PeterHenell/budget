#!/usr/bin/env python3
"""
Auto-Classification Demo and Setup Tool
Run this to test auto-classification capabilities
"""

import sys
import os
import getpass

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

from logic import BudgetLogic
from auto_classify import AutoClassificationEngine, demo_auto_classification, batch_auto_classify


def main():
    print("=== Budget App Auto-Classification Tool ===\\n")
    
    # Check for database
    db_path = "../budget.db"
    if not os.path.exists(db_path):
        print("Database not found. Please run the main app first to create a database.")
        return
    
    # Get password
    password = getpass.getpass("Enter database password: ")
    
    try:
        with BudgetLogic(db_path, password) as logic:
            print("Database connected successfully.\\n")
            
            # Show available options
            print("Available auto-classification options:")
            print("1. Demo classification suggestions")
            print("2. Batch auto-classify (confidence >= 80%)")
            print("3. Batch auto-classify (confidence >= 70%)")
            print("4. Batch auto-classify (confidence >= 60%)")
            print("5. Show classification capabilities")
            print("6. Exit")
            
            while True:
                choice = input("\\nSelect option (1-6): ").strip()
                
                if choice == "1":
                    demo_auto_classification(logic)
                
                elif choice == "2":
                    classified, suggestions = batch_auto_classify(logic, 0.8)
                    print(f"\\nClassified {classified} transactions with 80%+ confidence")
                    if suggestions:
                        print(f"{len(suggestions)} suggestions for manual review")
                
                elif choice == "3":
                    classified, suggestions = batch_auto_classify(logic, 0.7)
                    print(f"\\nClassified {classified} transactions with 70%+ confidence")
                    if suggestions:
                        print(f"{len(suggestions)} suggestions for manual review")
                
                elif choice == "4":
                    classified, suggestions = batch_auto_classify(logic, 0.6)
                    print(f"\\nClassified {classified} transactions with 60%+ confidence")
                    if suggestions:
                        print(f"{len(suggestions)} suggestions for manual review")
                
                elif choice == "5":
                    show_capabilities()
                
                elif choice == "6":
                    print("Goodbye!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-6.")
    
    except ValueError as e:
        if "password" in str(e).lower():
            print("Error: Incorrect password or corrupted database file.")
        else:
            print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def show_capabilities():
    """Show auto-classification capabilities and requirements"""
    print("\\n=== Auto-Classification Capabilities ===\\n")
    
    print("1. RULE-BASED CLASSIFICATION (Always Available)")
    print("   ✅ Swedish merchant patterns (ICA, COOP, Systembolaget, etc.)")
    print("   ✅ Transportation patterns (SL, gas stations, parking)")
    print("   ✅ Healthcare patterns (Apoteket, vårdcentral)")
    print("   ✅ Entertainment patterns (restaurants, cinema)")
    print("   ✅ Housing patterns (rent, utilities)")
    print("   ✅ Fast and reliable")
    print()
    
    print("2. LEARNING CLASSIFICATION (Always Available)")
    print("   ✅ Learns from your existing classified transactions")
    print("   ✅ Builds word frequency patterns for each category")
    print("   ✅ Analyzes amount patterns")
    print("   ✅ Improves as you classify more transactions")
    print()
    
    # Check for additional capabilities
    try:
        from advanced_classify import SKLEARN_AVAILABLE, OLLAMA_AVAILABLE
        
        print("3. MACHINE LEARNING CLASSIFICATION")
        if SKLEARN_AVAILABLE:
            print("   ✅ Available (scikit-learn installed)")
            print("   ✅ Advanced text analysis with TF-IDF")
            print("   ✅ Random Forest classifier")
            print("   ✅ Probability-based confidence scores")
        else:
            print("   ❌ Not available (install: pip install scikit-learn)")
        print()
        
        print("4. LOCAL LLM CLASSIFICATION")
        if OLLAMA_AVAILABLE:
            print("   ✅ Python client available")
            print("   ⚠️  Requires Ollama server + model")
            print("   ⚠️  Install: https://ollama.ai/")
            print("   ⚠️  Download model: ollama pull llama3.1")
            print("   ✅ Natural language understanding")
            print("   ✅ Contextual classification")
        else:
            print("   ❌ Not available (install: pip install ollama)")
        print()
        
    except ImportError:
        print("3. ADVANCED CLASSIFICATION")
        print("   ❌ Advanced classifiers not available")
        print("   💡 Create advanced_classify.py for ML and LLM options")
        print()
    
    print("RECOMMENDATIONS:")
    print("• Start with rule-based + learning (no setup required)")
    print("• Add scikit-learn for better accuracy")
    print("• Add Ollama + LLM for maximum sophistication")
    print("• Use GUI for interactive classification and review")


if __name__ == "__main__":
    main()
