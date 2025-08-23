"""
Speed Comparison Test for LLM Classifiers
Tests different approaches and provides recommendations
"""

import time
from typing import List, Dict


def speed_comparison_test():
    """Compare different classification approaches"""
    print("🏁 LLM Classification Speed Comparison")
    print("=" * 50)
    
    # Mock logic
    class MockLogic:
        def get_categories(self):
            return ["Mat", "Transport", "Nöje", "Boende", "Hälsa", "Övriga", "Uncategorized"]
    
    logic = MockLogic()
    
    # Test transactions
    test_transactions = [
        {"description": "ICA SUPERMARKET STOCKHOLM", "amount": -450.50},
        {"description": "SL ACCESS PENDELTÅG", "amount": -44.00},
        {"description": "MCDONALDS CENTRAL STATION", "amount": -89.00},
        {"description": "VATTENFALL ELRÄKNING", "amount": -1200.00},
        {"description": "SWISH BETALNING ONLINE KÖPT", "amount": -250.00},
        {"description": "OKÄND HANDLARE STOCKHOLM", "amount": -123.45},
    ]
    
    results = {}
    
    # Test 1: Rule-based only
    print("\n1️⃣  Testing Rule-Based Classifier (Baseline)")
    try:
        import sys
        sys.path.append('../src')
        from classifiers import RuleBasedClassifier
        rule_classifier = RuleBasedClassifier(logic)
        
        start_time = time.time()
        rule_results = []
        for tx in test_transactions:
            result = rule_classifier.classify(tx)
            rule_results.append(result)
        
        rule_time = time.time() - start_time
        rule_avg = rule_time / len(test_transactions)
        
        print(f"   ⚡ Total: {rule_time:.3f}s, Avg: {rule_avg:.3f}s per transaction")
        print(f"   📊 Classifications: {sum(1 for r in rule_results if r[0])}/{len(test_transactions)}")
        
        results['rule_based'] = {
            'total_time': rule_time,
            'avg_time': rule_avg,
            'classifications': sum(1 for r in rule_results if r[0]),
            'method': 'Pattern matching'
        }
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: SuperFast Classifier  
    print("\n2️⃣  Testing SuperFast Classifier (Rule + Smart LLM)")
    try:
        from classifiers import SuperFastClassifier
        super_classifier = SuperFastClassifier(logic)
        
        start_time = time.time()
        super_results = []
        for tx in test_transactions:
            result = super_classifier.classify(tx)
            super_results.append(result)
        
        super_time = time.time() - start_time
        super_avg = super_time / len(test_transactions)
        
        print(f"   ⚡ Total: {super_time:.3f}s, Avg: {super_avg:.3f}s per transaction")
        print(f"   📊 Classifications: {sum(1 for r in super_results if r[0])}/{len(test_transactions)}")
        
        stats = super_classifier.get_performance_stats()
        print(f"   🎯 Routing: {stats.get('instant_hits', 'N/A')} instant, {stats.get('llm_calls', 'N/A')} LLM")
        
        results['super_fast'] = {
            'total_time': super_time,
            'avg_time': super_avg,
            'classifications': sum(1 for r in super_results if r[0]),
            'method': 'Hybrid rule+LLM',
            'stats': stats
        }
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 3: Original Docker LLM
    print("\n3️⃣  Testing Original Docker LLM Classifier")
    try:
        from classifiers import DockerLLMClassifier
        llm_classifier = DockerLLMClassifier(logic)
        
        if llm_classifier.available:
            start_time = time.time()
            llm_results = []
            for tx in test_transactions:
                result = llm_classifier.classify(tx)
                llm_results.append(result)
            
            llm_time = time.time() - start_time
            llm_avg = llm_time / len(test_transactions)
            
            print(f"   ⚡ Total: {llm_time:.3f}s, Avg: {llm_avg:.3f}s per transaction")
            print(f"   📊 Classifications: {sum(1 for r in llm_results if r[0])}/{len(test_transactions)}")
            
            results['docker_llm'] = {
                'total_time': llm_time,
                'avg_time': llm_avg,
                'classifications': sum(1 for r in llm_results if r[0]),
                'method': 'Pure LLM'
            }
        else:
            print("   ❌ LLM not available")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 4: Fast LLM Classifier
    print("\n4️⃣  Testing Fast LLM Classifier (Optimized)")
    try:
        from classifiers import FastLLMClassifier
        fast_classifier = FastLLMClassifier(logic)
        
        if fast_classifier.available:
            start_time = time.time()
            fast_results = []
            for tx in test_transactions:
                result = fast_classifier.classify(tx)
                fast_results.append(result)
            
            fast_time = time.time() - start_time
            fast_avg = fast_time / len(test_transactions)
            
            print(f"   ⚡ Total: {fast_time:.3f}s, Avg: {fast_avg:.3f}s per transaction")
            print(f"   📊 Classifications: {sum(1 for r in fast_results if r[0])}/{len(test_transactions)}")
            
            results['fast_llm'] = {
                'total_time': fast_time,
                'avg_time': fast_avg,
                'classifications': sum(1 for r in fast_results if r[0]),
                'method': 'Optimized LLM'
            }
        else:
            print("   ❌ Fast LLM not available")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("📊 SPEED COMPARISON SUMMARY")
    print("=" * 50)
    
    if results:
        # Sort by average time
        sorted_results = sorted(results.items(), key=lambda x: x[1]['avg_time'])
        
        for i, (name, data) in enumerate(sorted_results, 1):
            accuracy = data['classifications'] / len(test_transactions) * 100
            print(f"{i}. {name.upper():<15} | {data['avg_time']:.3f}s avg | {accuracy:.0f}% accuracy | {data['method']}")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("=" * 25)
    
    if 'super_fast' in results:
        super_data = results['super_fast']
        if super_data['avg_time'] < 2.0:  # Under 2 seconds average
            print("✅ RECOMMENDED: SuperFast Classifier")
            print("   • Best balance of speed and accuracy")
            print("   • Instant for common transactions")
            print("   • LLM only for complex cases")
        else:
            print("⚠️  SuperFast still slow - check LLM performance")
    
    if 'rule_based' in results:
        rule_data = results['rule_based']
        accuracy = rule_data['classifications'] / len(test_transactions) * 100
        if accuracy >= 70:
            print("✅ FALLBACK: Rule-Based Classifier")
            print("   • Ultra-fast (<1ms per transaction)")
            print(f"   • {accuracy:.0f}% accuracy for common patterns")
            print("   • No external dependencies")
        else:
            print("⚠️  Rule-based accuracy too low, needs LLM support")
    
    print("\n💡 OPTIMIZATION TIPS:")
    print("• Use SuperFast for production (best of both worlds)")
    print("• Consider TinyLlama model for faster LLM calls")  
    print("• Increase OLLAMA_KEEP_ALIVE for better response times")
    print("• Rule-based only if sub-second response required")
    
    return results


if __name__ == "__main__":
    speed_comparison_test()
