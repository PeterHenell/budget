VENV_DIR=venv
REQ_FILE=src/requirements.txt
SRC_DIR=src
COMPOSE_FILE=docker-compose.yml

.PHONY: up down web logs test clean import help build install-dev dev-test status test-integration test-unit dev up-dev down-dev logs-dev init-llm

help:
	@echo "Budget App - Available commands:"
	@echo ""
	@echo "Main Commands:"
	@echo "  make up        - Start the application (PostgreSQL + Web + LLM)"
	@echo "  make down      - Stop and remove all containers"
	@echo "  make status    - Show current container status"
	@echo "  make logs      - Show application logs"
	@echo "  make build     - Build/rebuild Docker images"
	@echo "  make clean     - Clean up containers, volumes, and local files"
	@echo ""
	@echo "LLM Commands:"
	@echo "  make init-llm  - Download and initialize LLM model (first-time setup)"
	@echo "  make fast-llm  - Switch to ultra-fast TinyLlama model"
	@echo "  make balanced-llm - Switch to balanced Phi3-Mini model"
	@echo ""
	@echo "Development Commands:"
	@echo "  make up-dev    - Start development environment with hot reloading"
	@echo "  make down-dev  - Stop development environment"
	@echo "  make logs-dev  - Show development logs"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test-integration - Run full integration tests"
	@echo "  make test-unit        - Run unit tests locally"
	@echo ""
	@echo "Other Commands:"
	@echo "  make import    - Import CSV files (place files in input/ folder)"
	@echo "  make install-dev - Install local development environment"
	@echo ""
	@echo "Usage: Start with 'make up' and open http://localhost:5000"

# Main Docker Compose Commands
up:
	@echo "🚀 Starting Budget App with LLM support..."
	@echo "This will start:"
	@echo "  • PostgreSQL database (localhost:5432)"
	@echo "  • Ollama LLM service (localhost:11434)" 
	@echo "  • Web application with AI classification (localhost:5000)"
	@echo ""
	@echo "Note: First run downloads LLM model (~637MB for TinyLlama)"
	docker compose up -d
	@echo "✅ Budget App started with LLM support!"
	@echo "📍 Web app: http://localhost:5000"
	@echo "💡 Use 'make init-llm' if LLM models need initialization"

down:
	@echo "🛑 Stopping Budget App..."
	docker compose down

status:
	@echo "📊 Current container status:"
	docker compose ps

logs:
	@echo "📋 Showing application logs (press Ctrl+C to exit)..."
	docker compose logs -f

build:
	@echo "🔨 Building Docker images..."
	docker compose build

# LLM Commands
init-llm:
	@echo "🤖 Initializing LLM model..."
	@echo "This will download the TinyLlama model (~637MB)"
	docker compose --profile init up ollama-init

fast-llm:
	@echo "⚡ Switching to TinyLlama (ultra-fast, 637MB model)..."
	docker exec budget_ollama ollama pull tinyllama:1.1b
	@echo "✅ TinyLlama model ready"

balanced-llm:
	@echo "⚖️ Switching to Phi3-Mini (balanced, 2.2GB model)..."
	docker exec budget_ollama ollama pull phi3:mini  
	@echo "✅ Phi3-Mini model ready"

# Development Environment Commands
up-dev:
	@echo "🚀 Starting development environment with hot reloading..."
	@echo "Code changes will be reflected immediately without rebuilding."
	@echo "PostgreSQL: localhost:5432 | Web app: http://localhost:5000"
	docker compose -f docker-compose.dev.yml up -d --build
	@echo "✅ Development environment started!"

down-dev:
	@echo "🛑 Stopping development environment..."
	docker compose -f docker-compose.dev.yml down

logs-dev:
	@echo "📋 Development environment logs (Ctrl+C to exit)..."
	docker compose -f docker-compose.dev.yml logs -f

# Import and Testing Commands
import:
	@echo "📥 Starting CSV import..."
	@echo "Place CSV files in the 'input/' folder first"
	docker compose run --rm web python import_cli.py

test-integration:
	@echo "🧪 Running integration tests..."
	./run_integration_tests.sh

test-unit:
	@echo "🧪 Running unit tests..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python -m pytest test_logic.py -v

# Local Development Commands
VENV_DIR=venv
REQ_FILE=src/requirements.txt
SRC_DIR=src

install-dev: venv
	. $(VENV_DIR)/bin/activate && pip install --upgrade pip && pip install -r $(REQ_FILE)

venv:
	python3 -m venv $(VENV_DIR)

dev-test:
	@echo "🧪 Running tests locally..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python -m pytest test_logic.py -v

clean:
	@echo "🧹 Cleaning up containers, volumes and local files..."
	docker compose down -v --remove-orphans
	docker compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f
	rm -rf $(VENV_DIR) *.db $(SRC_DIR)/__pycache__ $(SRC_DIR)/*.pyc $(SRC_DIR)/uploads
