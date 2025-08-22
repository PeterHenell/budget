#!/bin/bash
# Development helper script for Budget App

set -e

print_help() {
    echo "Budget App Development Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start development environment with hot reloading"
    echo "  stop      - Stop development environment"
    echo "  restart   - Restart development environment" 
    echo "  logs      - Show development logs (follow)"
    echo "  shell     - Open shell in web container"
    echo "  test      - Run integration tests"
    echo "  clean     - Clean up all containers and volumes"
    echo "  status    - Show container status"
    echo ""
    echo "Development features:"
    echo "  • Hot reloading - code changes reflect immediately"
    echo "  • Debug mode enabled"
    echo "  • Source code mounted as volumes"
    echo "  • No need to rebuild containers for code changes"
}

case "${1:-}" in
    "start")
        echo "🚀 Starting development environment..."
        make up-dev
        echo ""
        echo "✅ Development environment is running!"
        echo "📍 Web app: http://localhost:5000"
        echo "📍 Database: localhost:5432"
        echo "💡 Use '$0 logs' to see output"
        ;;
    "stop")
        echo "🛑 Stopping development environment..."
        make down-dev
        ;;
    "restart")
        echo "🔄 Restarting development environment..."
        make down-dev
        sleep 2
        make up-dev
        ;;
    "logs")
        echo "📋 Showing development logs (Ctrl+C to exit)..."
        make logs-dev
        ;;
    "shell")
        echo "🐚 Opening shell in web container..."
        docker-compose -f docker-compose.dev.yml exec web bash
        ;;
    "test")
        echo "🧪 Running integration tests..."
        make test-integration
        ;;
    "clean")
        echo "🧹 Cleaning up containers and volumes..."
        make clean
        ;;
    "status")
        echo "📊 Container status:"
        docker-compose -f docker-compose.dev.yml ps
        ;;
    "help"|"")
        print_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        print_help
        exit 1
        ;;
esac
