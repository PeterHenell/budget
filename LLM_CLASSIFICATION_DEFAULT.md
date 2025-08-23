# LLM-Supported Classification (Default)

## Overview

The Budget App now uses **LLM-supported classification by default** for all transaction imports and manual classification operations. This provides more accurate and intelligent categorization of your financial transactions.

## How It Works

### 1. **Automatic Classification During Import**
- When you import CSV files, transactions are automatically classified using AI
- Uses a hybrid approach combining rule-based patterns with LLM intelligence
- Transactions are classified immediately upon import with high confidence

### 2. **Classification Priority Order**
1. **SuperFast Classifier** (Hybrid Rule+LLM) - *Highest Priority*
2. **Docker LLM Classifier** (Pure LLM with Docker optimization)  
3. **Fast LLM Classifier** (Fallback pure LLM)
4. **Rule-Based Classifier** (Pattern matching for Swedish merchants)
5. **Learning Classifier** (Learns from your existing classifications)

### 3. **Confidence Thresholds**
- **LLM Classifiers**: Minimum 40% confidence (they're generally more accurate)
- **Traditional Classifiers**: Minimum 60% confidence  
- **Auto-Classification**: 75% confidence threshold for automatic processing
- **Manual Review**: 40-75% confidence suggestions are flagged for review

## Configuration Options

All LLM classification behavior can be controlled via environment variables in `docker-compose.yml`:

### Core LLM Settings
```yaml
LLM_ENABLED: "true"                          # Enable/disable LLM features
OLLAMA_HOST: http://ollama:11434             # Ollama service endpoint
OLLAMA_MODEL: tinyllama:1.1b                 # AI model to use
LLM_CONFIDENCE_THRESHOLD: "0.6"             # General LLM confidence threshold
```

### Auto-Classification Settings  
```yaml
AUTO_CLASSIFY_ON_IMPORT: "true"              # Auto-classify during CSV import
AUTO_CLASSIFY_CONFIDENCE_THRESHOLD: "0.75"   # Threshold for automatic classification
LLM_PRIORITY: "true"                         # Prioritize LLM over traditional methods
```

## Benefits of LLM Classification

### ✅ **More Accurate**
- Understands context and nuance in transaction descriptions
- Learns from patterns beyond simple keyword matching
- Handles variations in merchant names and descriptions

### ✅ **Automatic Processing**
- New transactions are classified immediately upon import
- Reduces manual categorization work significantly
- Provides intelligent suggestions for review

### ✅ **Swedish Market Optimized**
- Recognizes Swedish merchants and banking formats
- Understands local transaction patterns (ICA, SL, Systembolaget, etc.)
- Handles Swedish currency and date formats

### ✅ **Hybrid Intelligence**
- Combines fast rule-based matching with AI analysis
- Falls back gracefully if AI services are unavailable
- Provides confidence scores for transparency

## Usage Examples

### Import with Automatic Classification
```python
# Simply import your CSV - classification happens automatically
logic = BudgetLogic(connection_params)
imported_count = logic.import_csv('transactions.csv')
# Transactions are automatically classified using LLM
```

### Manual Classification API
```bash
# API automatically uses best available classifier
POST /api/classify
{
  "transaction_id": 123,
  "category": "Mat"
}
```

### Batch Auto-Classification
```bash
# Trigger classification of uncategorized transactions
POST /api/auto-classify
{
  "confidence_threshold": 0.8
}
```

## Performance

- **SuperFast Classifier**: Instant rule-based for known patterns, 2-3s LLM for complex cases
- **Docker LLM Classifier**: 3-5 seconds per transaction with caching
- **Batch Processing**: Efficient handling of multiple transactions
- **Caching**: Repeated patterns are cached for instant classification

## Troubleshooting

### If LLM classification isn't working:
1. Check that Ollama container is running: `docker logs budget_ollama`
2. Verify model is loaded: `docker compose exec ollama ollama list`
3. Check web app logs: `docker logs budget_web`
4. Verify environment variables in `docker-compose.yml`

### To disable LLM classification:
Set `LLM_ENABLED: "false"` in docker-compose.yml and restart:
```bash
docker compose restart web
```

### To disable auto-classification on import:
Set `AUTO_CLASSIFY_ON_IMPORT: "false"` in docker-compose.yml.

## Migration from Previous Versions

If you're upgrading from a version without LLM classification:

1. **Your existing data is safe** - no changes to classified transactions
2. **New imports will be auto-classified** - using the new LLM system
3. **Manual classification gets smarter** - better suggestions and accuracy
4. **Configuration is optional** - works out of the box with sensible defaults

---

**🎯 LLM-supported classification is now the default experience** - making your budget management more intelligent and automated!
