# Budget App - PostgreSQL Version

A modern web-based personal budget management application with PostgreSQL backend and Docker support.

## 🚀 Quick Start with Docker

The easiest way to run the application is using Docker Compose:

```bash
# Clone and start the application
git clone <your-repo>
cd budget
docker-compose up -d

# Access the application
open http://localhost:5000
```

This will start both PostgreSQL database and the web application in containers.

## 📋 Prerequisites

### For Docker Setup (Recommended)
- Docker and Docker Compose installed
- Port 5000 (web) and 5432 (database) available

### For Local Development
- Python 3.11+
- PostgreSQL 15+
- pip and virtualenv

## 🐳 Docker Deployment

### Production Deployment

1. **Start the application:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f web
   docker-compose logs -f postgres
   ```

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

4. **Reset database (careful - deletes all data):**
   ```bash
   docker-compose down -v  # Removes volumes
   docker-compose up -d
   ```

### Environment Configuration

Copy and modify the environment file:
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

Key environment variables:
- `POSTGRES_PASSWORD`: Database password (change in production!)
- `FLASK_SECRET_KEY`: Session encryption key (change in production!)

## 💻 Local Development

### 1. Database Setup

Install and start PostgreSQL:
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE budget_db;
CREATE USER budget_user WITH PASSWORD 'budget_password';
GRANT ALL PRIVILEGES ON DATABASE budget_db TO budget_user;
\q
```

### 2. Application Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
cd src
pip install -r requirements.txt

# Set up environment variables
cp ../.env.example ../.env
# Edit .env with your database configuration

# Run the application
python web_app.py
```

Access the application at http://localhost:5000

## 🗄️ Database Initialization

**Important:** Database initialization is now handled by a separate script for better separation of concerns.

### Quick Initialization

```bash
# From project root (after setting up database connection)
python init_db.py
```

### Advanced Initialization

```bash
# Full control initialization
python src/init_database.py

# Skip admin user creation
python src/init_database.py --skip-admin

# Custom connection parameters
python src/init_database.py --host myhost --database mydb --user myuser
```

### What Gets Created

- **Database Tables**: categories, budgets, transactions, users
- **Indexes**: Optimized for query performance  
- **Default Categories**: Mat, Boende, Transport, Nöje, Hälsa, Övrigt, Uncategorized
- **Admin User**: username=`admin`, password=`admin` (⚠️ Change immediately!)
- **Triggers**: Automatic timestamp updates

### Docker Initialization

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d --build

# Initialize database (first time only)
docker exec -it budget_web_dev python init_database.py
```

For detailed initialization documentation, see [DATABASE_INIT.md](DATABASE_INIT.md).

## 🧪 Testing

### With Docker (Recommended)

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run tests
cd src
POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_TEST_DB=budget_test_db \
POSTGRES_USER=budget_user POSTGRES_PASSWORD=budget_password_test \
python -m pytest test_logic_postgres.py -v

# Clean up test database
docker-compose -f docker-compose.test.yml down -v
```

### Local Testing

```bash
# Create test database
sudo -u postgres psql
CREATE DATABASE budget_test_db;
\q

# Run tests with environment variables
cd src
POSTGRES_TEST_DB=budget_test_db python -m pytest test_logic_postgres.py -v
```

## 📊 Features

### Core Functionality
- **Budget Management**: Set yearly budgets by category
- **Transaction Import**: CSV file import with automatic parsing
- **Categorization**: Manual and automatic transaction categorization
- **Reporting**: Monthly and yearly spending reports with charts
- **Web Interface**: Modern, responsive Bootstrap UI

### Data Management
- **PostgreSQL Backend**: Reliable, scalable database
- **Data Import**: Supports Swedish banking CSV formats
- **Auto-Classification**: ML-based transaction categorization
- **Backup**: Database backup via PostgreSQL tools

### Security & Deployment
- **Docker Support**: Easy containerized deployment
- **Environment Configuration**: Secure credential management
- **Health Checks**: Application and database monitoring
- **Production Ready**: Proper error handling and logging

## 📁 Project Structure

```
budget/
├── docker-compose.yml          # Main deployment configuration
├── docker-compose.test.yml     # Test environment
├── Dockerfile                  # Web application container
├── .env.example               # Environment template
├── init.sql                   # Database initialization
├── src/                       # Application source code
│   ├── web_app.py            # Flask web application
│   ├── logic.py              # Business logic layer
│   ├── budget_db_postgres.py # PostgreSQL database layer
│   ├── auto_classify.py      # Auto-categorization engine
│   ├── requirements.txt      # Python dependencies
│   ├── templates/            # HTML templates
│   └── uploads/              # File upload directory
├── archive/                   # Legacy code (SQLite version)
└── tests/                     # Test files
```

## 🔧 Configuration

### Database Configuration
The application uses environment variables for database connection:

```bash
POSTGRES_HOST=localhost      # Database host
POSTGRES_DB=budget_db        # Database name
POSTGRES_USER=budget_user    # Database user
POSTGRES_PASSWORD=secret     # Database password
POSTGRES_PORT=5432          # Database port
```

### Flask Configuration
```bash
FLASK_SECRET_KEY=your-secret-key  # Session encryption
FLASK_ENV=development            # Environment mode
```

## 📈 Monitoring & Maintenance

### Health Checks
Both containers include health checks:
- Database: `pg_isready` check
- Web app: HTTP endpoint check

### Logs
View application logs:
```bash
docker-compose logs -f web      # Web application logs
docker-compose logs -f postgres # Database logs
```

### Database Backup
```bash
# Backup database
docker-compose exec postgres pg_dump -U budget_user budget_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U budget_user budget_db < backup.sql
```

### Updates
```bash
# Update application
git pull
docker-compose build web
docker-compose up -d
```

## 🚨 Troubleshooting

### Common Issues

**Database connection failed:**
- Check PostgreSQL is running: `docker-compose logs postgres`
- Verify environment variables in `.env`
- Ensure ports are not blocked by firewall

**Web app won't start:**
- Check application logs: `docker-compose logs web`
- Verify Python dependencies in requirements.txt
- Ensure database is ready (health check passes)

**Import errors:**
- Check CSV file format (semicolon-separated)
- Verify required columns: Date, Description, Amount
- Check file encoding (UTF-8 or Latin-1)

### Development Issues

**Tests failing:**
- Ensure test database exists and is accessible
- Check test environment variables
- Clean test data between runs

**Performance issues:**
- Monitor database connection pool
- Check for slow queries in PostgreSQL logs
- Consider adding database indexes for large datasets

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## 📞 Support

For issues and questions:
1. Check this README
2. Review application logs
3. Check the troubleshooting section
4. Create an issue on GitHub
