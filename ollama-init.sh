#!/bin/sh

# Ollama Model Initialization Script
# This script downloads and sets up the local LLM model

echo "🤖 Initializing Ollama with local LLM model..."
echo "Host: ${OLLAMA_HOST:-http://ollama:11434}"

# Wait for Ollama to be ready
echo "Waiting for Ollama service to be ready..."
until wget -q --spider "${OLLAMA_HOST:-http://ollama:11434}/api/tags" 2>/dev/null; do
    echo "Waiting for Ollama..."
    sleep 5
done

echo "✅ Ollama is ready!"

# List of small, efficient models to try (in order of preference)
MODELS="phi3:mini llama3.2:1b gemma2:2b qwen2:1.5b tinyllama:1.1b"

# Try to download the first available model
for model in $MODELS; do
    echo "🔄 Attempting to pull model: $model"
    
    # Use Ollama API to pull the model
    wget -q -O- --post-data="{\"name\": \"$model\"}" \
         --header="Content-Type: application/json" \
         --timeout=1800 \
         "${OLLAMA_HOST:-http://ollama:11434}/api/pull" 
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully downloaded model: $model"
        
        # Test the model with a simple query
        echo "🧪 Testing model with classification task..."
        wget -q -O- --post-data="{
                \"model\": \"$model\",
                \"prompt\": \"Classify this Swedish transaction: ICA SUPERMARKET 450.50 SEK. Categories: Mat, Transport, Nöje, Boende. Respond with just the category name.\",
                \"stream\": false
             }" \
             --header="Content-Type: application/json" \
             --timeout=60 \
             "${OLLAMA_HOST:-http://ollama:11434}/api/generate"
        
        if [ $? -eq 0 ]; then
            echo "✅ Model test successful!"
            echo "🎉 Ollama initialization complete with model: $model"
            
            # Create a status file to indicate successful initialization
            echo "$model" > /tmp/ollama_model_ready
            exit 0
        else
            echo "⚠️  Model test failed, trying next model..."
        fi
    else
        echo "❌ Failed to download model: $model, trying next..."
    fi
done

echo "❌ Failed to download any suitable model"
echo "Available models to try manually:"
echo "  - phi3:mini (recommended for classification)"
echo "  - llama3.2:1b (smallest Llama)"
echo "  - gemma2:2b (good performance/size balance)"
echo "  - qwen2:1.5b (efficient Chinese model)"
echo "  - tinyllama:1.1b (ultra-lightweight)"

echo "Manual download command:"
echo "  docker exec budget_ollama ollama pull phi3:mini"

exit 1
