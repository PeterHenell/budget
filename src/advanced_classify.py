"""
Advanced auto-classification with optional local LLM integration
Requires: pip install ollama-python (optional), scikit-learn (optional)
"""

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    import joblib
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

import os
import json
from auto_classify import TransactionClassifier


class LLMClassifier(TransactionClassifier):
    """Local LLM-based classifier using Ollama"""
    
    def __init__(self, logic, model_name="llama3.1"):
        super().__init__(logic)
        self.model_name = model_name
        self.available = OLLAMA_AVAILABLE and self._check_ollama_running()
        
        if self.available:
            self.categories = [cat for cat in logic.get_categories() 
                             if cat != "Uncategorized"]
    
    def _check_ollama_running(self):
        """Check if Ollama is running and model is available"""
        try:
            models = ollama.list()
            model_names = [model['name'] for model in models['models']]
            return any(self.model_name in name for name in model_names)
        except Exception:
            return False
    
    def classify(self, transaction):
        """Classify using local LLM"""
        if not self.available:
            return None, 0.0
        
        description = transaction.get('description', '')
        amount = transaction.get('amount', 0)
        
        # Construct prompt
        prompt = self._build_classification_prompt(description, amount)
        
        try:
            response = ollama.chat(model=self.model_name, messages=[{
                'role': 'user',
                'content': prompt
            }])
            
            result = self._parse_llm_response(response['message']['content'])
            return result
            
        except Exception as e:
            print(f"LLM classification error: {e}")
            return None, 0.0
    
    def _build_classification_prompt(self, description, amount):
        """Build classification prompt for LLM"""
        categories_str = ", ".join(self.categories)
        
        return f"""You are a Swedish personal finance assistant. Classify this transaction into one of these categories: {categories_str}

Transaction details:
- Description: {description}
- Amount: {amount:.2f} SEK

Please respond with ONLY a JSON object like this:
{{"category": "category_name", "confidence": 0.85}}

Where confidence is between 0.0 and 1.0 based on how certain you are.
If you can't classify it confidently (below 0.6), respond with:
{{"category": null, "confidence": 0.0}}

Rules:
- ICA, COOP, Hemköp = Mat
- SL, gas stations = Transport  
- Restaurants, bars = Nöje
- Systembolaget = Mat
- Medical/pharmacy = Hälsa
- Rent, utilities = Boende"""

    def _parse_llm_response(self, response_text):
        """Parse LLM response to extract category and confidence"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            if not response_text.startswith('{'):
                # Find JSON in response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    response_text = response_text[start:end]
            
            result = json.loads(response_text)
            
            category = result.get('category')
            confidence = float(result.get('confidence', 0.0))
            
            # Validate category exists
            if category and category in self.categories:
                return category, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None, 0.0


class MLClassifier(TransactionClassifier):
    """Scikit-learn based machine learning classifier"""
    
    def __init__(self, logic, model_path="transaction_classifier.pkl"):
        super().__init__(logic)
        self.model_path = model_path
        self.available = SKLEARN_AVAILABLE
        self.model = None
        self.vectorizer = None
        self.categories = None
        
        if self.available:
            self._load_or_train_model()
    
    def _load_or_train_model(self):
        """Load existing model or train new one"""
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.vectorizer = data['vectorizer'] 
                self.categories = data['categories']
                print("Loaded existing ML model")
                return
            except Exception as e:
                print(f"Error loading model: {e}")
        
        # Train new model
        self._train_model()
    
    def _train_model(self):
        """Train ML model on existing classified transactions"""
        c = self.logic.conn.cursor()
        
        # Get training data
        c.execute("""
            SELECT t.description, t.amount, cat.name
            FROM transactions t
            JOIN categories cat ON t.category_id = cat.id
            WHERE cat.name != 'Uncategorized'
        """)
        
        training_data = c.fetchall()
        
        if len(training_data) < 10:
            print("Not enough training data (need at least 10 classified transactions)")
            return
        
        # Prepare features and labels
        descriptions = []
        amounts = []
        labels = []
        
        for desc, amount, category in training_data:
            descriptions.append(desc)
            amounts.append(amount)
            labels.append(category)
        
        # Create text features
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
        text_features = self.vectorizer.fit_transform(descriptions)
        
        # Combine text and numeric features
        amount_features = np.array(amounts).reshape(-1, 1)
        features = np.hstack([text_features.toarray(), amount_features])
        
        # Train model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(features, labels)
        
        self.categories = list(set(labels))
        
        # Save model
        try:
            joblib.dump({
                'model': self.model,
                'vectorizer': self.vectorizer,
                'categories': self.categories
            }, self.model_path)
            print(f"Trained and saved ML model with {len(training_data)} examples")
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def classify(self, transaction):
        """Classify using trained ML model"""
        if not self.available or not self.model or not self.vectorizer:
            return None, 0.0
        
        try:
            description = transaction.get('description', '')
            amount = transaction.get('amount', 0)
            
            # Prepare features
            text_features = self.vectorizer.transform([description])
            amount_features = np.array([[amount]])
            features = np.hstack([text_features.toarray(), amount_features])
            
            # Get prediction and probability
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            
            # Get confidence (max probability)
            max_prob = max(probabilities)
            
            return prediction, max_prob
            
        except Exception as e:
            print(f"ML classification error: {e}")
            return None, 0.0
    
    def retrain(self):
        """Retrain the model with new data"""
        if os.path.exists(self.model_path):
            os.remove(self.model_path)
        self._train_model()


def setup_auto_classification_options():
    """Show available auto-classification options"""
    print("=== Auto-Classification Options ===\n")
    
    print("1. Rule-Based Classification (Always Available)")
    print("   - Pattern matching for Swedish merchants")
    print("   - Amount-based rules")
    print("   - Fast and deterministic")
    print("   - No setup required\n")
    
    print("2. Learning Classification (Always Available)")
    print("   - Learns from your existing classified transactions")
    print("   - Adapts to your spending patterns")
    print("   - Improves over time")
    print("   - No external dependencies\n")
    
    if SKLEARN_AVAILABLE:
        print("3. Machine Learning Classification (Available)")
        print("   - Advanced ML using Random Forest")
        print("   - Text analysis with TF-IDF")
        print("   - High accuracy with enough training data")
        print("   - Requires scikit-learn\n")
    else:
        print("3. Machine Learning Classification (Not Available)")
        print("   - Install with: pip install scikit-learn")
        print("   - Provides advanced ML capabilities\n")
    
    if OLLAMA_AVAILABLE:
        print("4. Local LLM Classification (Potentially Available)")
        print("   - Uses local language models via Ollama")
        print("   - Natural language understanding")
        print("   - Contextual classification")
        print("   - Requires Ollama + model download")
        print("   - Install: https://ollama.ai/\n")
    else:
        print("4. Local LLM Classification (Not Available)")
        print("   - Install Ollama: https://ollama.ai/")
        print("   - Install Python client: pip install ollama")
        print("   - Download model: ollama pull llama3.1\n")
    
    print("Recommendation:")
    print("- Start with Rule-Based + Learning (no extra setup)")
    print("- Add ML for better accuracy (pip install scikit-learn)")
    print("- Add LLM for maximum sophistication (ollama setup)")


# Integration function for the GUI
def integrate_auto_classification(logic):
    """
    Integration function that sets up the best available auto-classification
    Returns the configured engine
    """
    from auto_classify import AutoClassificationEngine, RuleBasedClassifier, LearningClassifier
    
    # Create base engine with rule-based and learning classifiers
    engine = AutoClassificationEngine(logic)
    engine.classifiers = [
        RuleBasedClassifier(logic),
        LearningClassifier(logic)
    ]
    
    # Add ML classifier if available
    if SKLEARN_AVAILABLE:
        ml_classifier = MLClassifier(logic)
        if ml_classifier.model:
            engine.classifiers.append(ml_classifier)
            print("ML classifier loaded")
    
    # Add LLM classifier if available
    if OLLAMA_AVAILABLE:
        llm_classifier = LLMClassifier(logic)
        if llm_classifier.available:
            engine.classifiers.append(llm_classifier)
            print("LLM classifier loaded")
    
    print(f"Auto-classification engine ready with {len(engine.classifiers)} classifiers")
    return engine
