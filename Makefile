VENV_DIR=venv
REQ_FILE=src/requirements.txt
SRC_DIR=src
COMPOSE_FILE=docker-compose.yml

.PHONY: up down web logs test clean import help auto-demo build install-dev dev-test status test-integration test-unit dev up-dev down-dev logs-dev

help:
	@echo "Budget App - Available commands:"
	@echo ""
	@echo "Docker Commands (Recommended):"
	@echo "  make up        - Start the application with Docker Compose (PostgreSQL + Web)"
	@echo "  make down      - Stop and remove all containers"
	@echo "  make status    - Show current container status"
	@echo "  make web       - Start web app only (requires 'make db' first)"
	@echo "  make db        - Start PostgreSQL database only"
	@echo "  make logs      - Show application logs"
	@echo "  make build     - Build/rebuild Docker images"
	@echo "  make import    - Import CSV files using Docker (place files in input/ folder)"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test-integration - Run full integration tests with separate test database"
	@echo "  make test-unit        - Run unit tests locally"
	@echo ""
	@echo "Development Commands:"
	@echo "  make install-dev - Install local development environment"
	@echo "  make dev-test   - Run tests locally (for development)"
	@echo "  make auto-demo  - Demo auto-classification (requires local setup)"
	@echo "  make up-dev     - Start development environment with hot reloading"
	@echo "  make down-dev   - Stop development environment"
	@echo "  make logs-dev   - Show development logs"
	@echo "  make clean      - Clean up containers, volumes, and local files"
	@echo ""
	@echo "Usage: Start with 'make up' and open http://localhost:5000"

# Docker Compose Commands
up:
	@echo "Starting Budget App with Docker Compose..."
	@echo "PostgreSQL will be available on localhost:5432"
	@echo "Web app will be available on http://localhost:5000"
	docker compose up -d
	@echo "Containers started. Use 'make logs' to see output."

down:
	@echo "Stopping Budget App containers..."
	docker compose down

status:
	@echo "Current container status:"
	docker compose ps

web:
	@echo "Starting web application only..."
	docker compose up -d web

db:
	@echo "Starting PostgreSQL database only..."
	docker compose up -d postgres

logs:
	@echo "Showing application logs (press Ctrl+C to exit)..."
	docker compose logs -f

build:
	@echo "Building Docker images..."
	docker compose build

import:
	@echo "Starting CSV import using Docker..."
	@echo "Make sure your CSV files are in the 'input/' folder"
	@echo "The container will process files and exit"
	docker compose run --rm web python import_cli.py

# Testing Commands
test-integration:
	@echo "Running comprehensive integration tests..."
	@echo "This will start separate test containers with isolated test database"
	./run_integration_tests.sh

test-unit:
	@echo "Running unit tests..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python -m pytest test_logic.py -v
	. $(VENV_DIR)/bin/activate && python -m unittest tests.test_import_cli -v

# Development Commands  
install-dev: venv
	. $(VENV_DIR)/bin/activate && pip install --upgrade pip && pip install -r $(REQ_FILE)

venv:
	python3 -m venv $(VENV_DIR)

dev-test:
	@echo "Running tests locally (requires PostgreSQL running via 'make db')..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python -m pytest test_logic.py -v
	. $(VENV_DIR)/bin/activate && python -m unittest tests.test_import_cli -v

auto-demo:
	@echo "Starting auto-classification demo (local development)..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python auto_classify_demo.py

clean:
	@echo "Cleaning up containers, volumes and local files..."
	docker compose down -v --remove-orphans
	docker compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f
	rm -rf $(VENV_DIR) *.db $(SRC_DIR)/__pycache__ $(SRC_DIR)/*.pyc $(SRC_DIR)/uploads

# Development Environment Commands (Hot Reloading)
up-dev:
	@echo "Starting Budget App in DEVELOPMENT mode with hot reloading..."
	@echo "Code changes will be reflected immediately without rebuilding."
	@echo "PostgreSQL will be available on localhost:5432"
	@echo "Web app will be available on http://localhost:5000"
	@echo ""
	@echo "Note: This mounts your source code directly for development."
	docker compose -f docker-compose.dev.yml up -d --build
	@echo ""
	@echo "Development environment started!"
	@echo "• Files in src/ are mounted and will reload automatically"
	@echo "• Use 'make logs-dev' to see output"
	@echo "• Use 'make down-dev' to stop"

down-dev:
	@echo "Stopping development environment..."
	docker compose -f docker-compose.dev.yml down

logs-dev:
	@echo "Showing development environment logs (Ctrl+C to exit)..."
	docker compose -f docker-compose.dev.yml logs -f
