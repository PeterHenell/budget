# Budget App

A Python budget app with a GUI for managing monthly budgets by category, importing transactions from CSV, classifying transactions, and reporting spending vs budget. Data is stored in an encrypted SQLite database. Unit tests and best practices are followed.

## Features
- **Yearly budget system**: Set budgets per category per year (applies to all months in that year)
- Category-based budgeting (default and editable categories)
- **Grid-based budget interface**: Easy-to-use table view where categories are rows and yearly budget amounts can be edited by double-clicking
- **CSV Import**: Import transactions from Swedish CSV format with automatic archiving
- **Auto-Classification**: Multiple local strategies for automatic transaction classification
- **Uncategorized Queue**: Batch process and classify imported transactions
- **Command Line Tools**: Import and classify transactions from the terminal
- **Dual reporting**: Monthly spending vs yearly budget, and yearly spending vs yearly budget
- Encrypted SQLite database (password required on startup)
- GUI separated from business logic
- Comprehensive unit tests

## Usage

### Web Interface
1. Start the web application: `make web`
2. Open http://localhost:5000 in your browser
3. Enter your database password to login
4. Use the modern web interface with left-side navigation:
   - **Dashboard**: Overview and quick stats
   - **Budgets**: Set yearly budgets with interactive grid
   - **Import CSV**: Upload transaction files with drag & drop
   - **Uncategorized Queue**: Batch classify transactions with auto-classification
   - **All Transactions**: View and filter transaction history
   - **Reports**: Generate detailed spending reports with charts

### CSV Import & Auto-Classification
1. **Command Line**: `python src/import_cli.py path/to/file.csv` (with optional interactive classification)
2. **GUI**: Imported transactions go to "Uncategorized Queue" tab
3. Use **Auto Classify** feature with multiple local strategies:
   - **Rule-Based**: Swedish merchant patterns (ICA→Mat, SL→Transport, etc.)
   - **Learning**: Learns from your existing classified transactions  
   - **ML** (optional): Advanced classification with scikit-learn
   - **Local LLM** (optional): AI-powered classification with Ollama

See `AUTO_CLASSIFY_OPTIONS.md` for detailed auto-classification setup and usage.

### Legacy GUI (Tkinter)
1. Go to the "Budgets" tab
2. Select the year you want to set budgets for
3. Click "Load Budgets" to see the grid
4. Double-click on any yearly budget amount to edit it
5. Enter the new amount and confirm - changes are saved immediately
6. **Note**: Budgets are set per year and apply to all 12 months in that year

### Reporting
1. Go to the "Report" tab
2. Enter year and optionally month
3. Click "Monthly Report" to see spending for a specific month vs yearly budget
4. Click "Yearly Report" to see total spending for the entire year vs yearly budget
5. Reports show spending amount, budget, difference, and percentage used

## Setup
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python src/main.py
   ```

## Command Line Tools
- **Start Web App**: `make web`
- **Import CSV**: `python src/import_cli.py path/to/file.csv`
- **Auto-Classification Demo**: `make auto-demo`
- **Run Tests**: `make test`
- **All Options**: `make help`

## Testing
Run unit tests with:
```bash
pytest
```

## Project Structure
- `src/` - Application source code
- `tests/` - Unit tests
- `requirements.txt` - Python dependencies
- `.github/copilot-instructions.md` - Copilot instructions
- `README.md` - Project documentation
