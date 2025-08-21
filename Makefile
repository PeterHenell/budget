VENV_DIR=venv
REQ_FILE=src/requirements.txt
SRC_DIR=src

.PHONY: venv install web test clean import help auto-demo

help:
	@echo "Budget App - Available commands:"
	@echo "  make install   - Create virtual environment and install dependencies"
	@echo "  make web       - Start the web application (default port 5000)"
	@echo "  make import    - Import CSV files from input/ folder"
	@echo "  make auto-demo - Demo auto-classification capabilities"
	@echo "  make test      - Run unit tests"
	@echo "  make clean     - Remove virtual environment and temporary files"
	@echo ""
	@echo "Usage: Start with 'make web' and open http://localhost:5000"

venv:
	python3 -m venv $(VENV_DIR)

install: venv
	. $(VENV_DIR)/bin/activate && pip install --upgrade pip && pip install -r $(REQ_FILE)

web:
	@echo "Starting web application on http://localhost:5000"
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python web_app.py

test:
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python -m pytest test_logic.py -v
	. $(VENV_DIR)/bin/activate && python -m unittest tests.test_import_cli -v

import:
	@echo "Starting CSV import utility..."
	@echo "Place CSV files in the 'input/' folder before running this command"
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python import_cli.py

auto-demo:
	@echo "Starting auto-classification demo..."
	. $(VENV_DIR)/bin/activate && cd $(SRC_DIR) && python auto_classify_demo.py

clean:
	rm -rf $(VENV_DIR) *.db $(SRC_DIR)/__pycache__ $(SRC_DIR)/*.pyc $(SRC_DIR)/uploads
