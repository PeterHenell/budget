# Development Setup Guide

This guide explains how to set up the development environment for the Budget App with hot reloading support.

## Quick Start

### Option 1: Use the Development Script (Recommended)
```bash
# Start development environment
./dev.sh start

# View logs
./dev.sh logs

# Stop when done
./dev.sh stop
```

### Option 2: Use Make Commands
```bash
# Start development environment
make up-dev

# View logs
make logs-dev

# Stop when done
make down-dev
```

## Development Features

✅ **Hot Reloading** - Code changes are reflected immediately without rebuilding containers
✅ **Debug Mode** - Flask runs in debug mode with detailed error messages
✅ **Volume Mounting** - Source code is mounted directly from host to container
✅ **Fast Iteration** - No need to rebuild Docker images for code changes
✅ **Database Persistence** - Development database data persists between restarts

## Development vs Production

| Feature | Development (`make up-dev`) | Production (`make up`) |
|---------|----------------------------|------------------------|
| Code Changes | 🔥 Hot reload | ❄️ Requires rebuild |
| Debug Mode | ✅ Enabled | ❌ Disabled |
| Source Mounting | ✅ Live mount | ❌ Copied to image |
| Build Time | ⚡ Fast startup | 🐌 Rebuild required |
| Database | `budget_postgres_dev` | `budget_postgres` |
| Use Case | Development | Production/Testing |

## File Structure

```
src/                    # Mounted directly to /app in container
├── web_app.py         # Main Flask application
├── logic.py           # Business logic
├── budget_db_postgres.py  # Database layer
├── templates/         # HTML templates
└── uploads/           # File uploads (also mounted)

docker-compose.dev.yml  # Development configuration
Dockerfile.dev         # Development Docker image
dev.sh                 # Development helper script
```

## Available Commands

### Development Script (`./dev.sh`)
- `./dev.sh start` - Start development environment
- `./dev.sh stop` - Stop development environment
- `./dev.sh restart` - Restart development environment
- `./dev.sh logs` - Show logs (follow mode)
- `./dev.sh shell` - Open shell in web container
- `./dev.sh test` - Run integration tests
- `./dev.sh status` - Show container status
- `./dev.sh clean` - Clean up everything

### Make Commands
- `make up-dev` - Start development environment
- `make down-dev` - Stop development environment
- `make logs-dev` - Show development logs
- `make test-integration` - Run integration tests

## Testing Your Changes

1. **Start Development Environment**
   ```bash
   ./dev.sh start
   ```

2. **Make Code Changes**
   Edit any file in `src/` directory

3. **See Changes Instantly**
   Flask will automatically reload and your changes will be visible at http://localhost:5000

4. **Test Import Functionality**
   ```bash
   # Login and test CSV import
   curl -c cookies.txt http://localhost:5000/login
   curl -b cookies.txt -c cookies.txt -X POST -d "username=admin&password=admin" http://localhost:5000/login
   curl -b cookies.txt -X POST -F "file=@test_import.csv" http://localhost:5000/api/import
   ```

5. **Run Tests**
   ```bash
   ./dev.sh test
   ```

## Troubleshooting

### Container Won't Start
```bash
# Check status
./dev.sh status

# View logs
./dev.sh logs

# Clean and restart
./dev.sh clean
./dev.sh start
```

### Code Changes Not Appearing
- Ensure you're editing files in the `src/` directory
- Check that containers are running: `./dev.sh status`
- Look for Flask reload messages: `./dev.sh logs`

### Port Already in Use
```bash
# Stop any existing containers
make down
./dev.sh stop

# Or clean everything
./dev.sh clean
```

## Environment Variables (Development)

The development environment uses these settings:
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `PYTHONUNBUFFERED=1`
- Database: `budget_postgres_dev` with separate volume

## Next Steps

Once your development is complete:
1. Test with `./dev.sh test`
2. Stop development: `./dev.sh stop`  
3. Start production: `make up`
4. Run integration tests: `make test-integration`

The production environment will use the built Docker image with your changes.
