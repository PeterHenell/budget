# Budget App Copilot Instructions
- [x] Clarify Project Requirements: Python budget app with GUI, category-based yearly budgeting (changed from monthly), editable categories, CSV import (Swedish headers, deduplication by Verifikationsnummer), transaction classification, spending vs budget report, encrypted SQLite DB, password on startup, requirements.txt, venv, unit tests, separation of GUI and logic, best practices.
- [x] Scaffold the Project: Created src/ directory with main.py, logic.py, gui.py, test_logic.py, requirements.txt, and Makefile
- [x] Customize the Project: Implemented full functionality with encryption using cryptography package. Grid-based budget interface. **CHANGED TO YEARLY BUDGETS**: Budgets are now set per year and apply to all months in that year.
- [x] Install Required Extensions: No extensions needed
- [x] Compile the Project: Dependencies installed successfully, tests pass
- [x] Create and Run Task: Makefile created with install, run, test, clean targets
- [x] Launch the Project: Successfully launched with `make run`
- [x] Ensure Documentation is Complete: README.md updated with yearly budget system documentation

## Key Changes Made:
- **Budget System**: Changed from monthly to yearly budgets
- **Database Schema**: Updated budgets table to remove month column, added unique constraint on (category_id, year)
- **GUI**: Updated budget interface to show yearly budgets, added monthly vs yearly reporting
- **Migration**: Added automatic migration from old monthly system to yearly system
- **API Changes**: `set_budget()` now takes (category, year, amount), `get_budget()` takes (category, year)
- **Reporting**: Added both monthly spending vs yearly budget and yearly spending vs yearly budget reports
