# Database Initialization Guide

The Budget App database initialization has been moved to a separate, dedicated script for better separation of concerns.

## Quick Start

### Option 1: Simple Initialization (Recommended)
```bash
# From the project root directory
python init_db.py
```

### Option 2: Full Control Initialization
```bash
# From the project root directory  
python src/init_database.py
```

### Option 3: Using Docker
```bash
# If using docker-compose, the initialization will happen automatically
docker-compose up
```

## What Gets Created

### Database Tables
- **categories** - Budget categories (Mat, Boende, Transport, etc.)
- **budgets** - Yearly budget amounts per category  
- **transactions** - Imported financial transactions
- **users** - Application users with authentication

### Default Data
- **7 Default Categories**: Mat, Boende, Transport, Nöje, Hälsa, Övrigt, Uncategorized
- **Admin User**: username=admin, password=admin (⚠️ Change this!)
- **Performance Indexes** - For faster queries

### Database Features
- **Automatic Timestamps** - created_at and updated_at columns
- **Foreign Key Constraints** - Data integrity protection  
- **Unique Constraints** - Prevent duplicate data
- **Triggers** - Auto-update timestamps on changes

## Environment Variables

The initialization script uses these environment variables:

```bash
POSTGRES_HOST=localhost      # Database host
POSTGRES_DB=budget_db        # Database name
POSTGRES_USER=budget_user    # Database user
POSTGRES_PASSWORD=budget_password  # Database password  
POSTGRES_PORT=5432          # Database port
```

## Advanced Usage

### Custom Connection Parameters
```python
from src.init_database import DatabaseInitializer

# Custom connection
initializer = DatabaseInitializer({
    'host': 'my-db-server',
    'database': 'my_budget_db', 
    'user': 'my_user',
    'password': 'my_password',
    'port': '5432'
})

initializer.initialize_database()
```

### Skip Admin User Creation
```bash
python src/init_database.py --skip-admin
```

### Command Line Options
```bash
python src/init_database.py --help

options:
  --skip-admin          Skip admin user creation
  --host HOST          PostgreSQL host (default: localhost)
  --database DATABASE  Database name (default: budget_db)  
  --user USER          Database user (default: budget_user)
  --password PASSWORD  Database password (default: budget_password)
  --port PORT          Database port (default: 5432)
```

## Troubleshooting

### Database Connection Issues
```
Error: Failed to connect to PostgreSQL database
```
**Solutions:**
- Check if PostgreSQL is running
- Verify connection parameters
- Test with `psql` command line tool

### Permission Issues  
```
Error: permission denied for database
```
**Solutions:**
- Ensure database user has CREATE privileges
- Use database superuser for initialization
- Check pg_hba.conf configuration

### Already Initialized
The script is safe to run multiple times. It will:
- Skip existing tables
- Skip existing categories  
- Update existing admin user role
- Add any missing indexes or columns

## Integration with Application

The main `BudgetDb` class now has optional auto-initialization:

```python
from src.budget_db_postgres import BudgetDb

# Auto-check initialization (default)
db = BudgetDb()

# Skip initialization check  
db = BudgetDb(auto_init=False)
```

If tables are missing, you'll see a helpful warning:
```
⚠️  Database tables not found!
   Please run: python src/init_database.py
   Or use: from src.init_database import DatabaseInitializer
```

## File Structure
```
budget/
├── init_db.py                    # Simple initialization script
├── src/
│   ├── init_database.py         # Full initialization module  
│   ├── budget_db_postgres.py    # Main database class (no longer handles init)
│   └── ...
```

The initialization logic has been completely separated from the main database class for:
- **Better separation of concerns**
- **Easier testing and maintenance**  
- **Flexible deployment options**
- **Cleaner application startup**
