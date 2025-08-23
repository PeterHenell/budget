#!/usr/bin/env python3
"""
Test script to demonstrate the new ensure_container_is_used() decorator behavior.
This script shows how the decorator enforces container execution.
"""

import os
import sys
import subprocess

def check_container_environment():
    """Check if we're inside a Docker container"""
    return os.path.exists('/.dockerenv')

def check_containers_running():
    """Check if Docker containers are running"""
    try:
        result = subprocess.run([
            "docker", "compose", "ps", "--services", "--filter", "status=running"
        ], capture_output=True, text=True, cwd='/home/mrm/src/github/budget')
        
        running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return 'web' in running_services and 'postgres' in running_services
    except Exception as e:
        return False

def simulate_decorator_logic():
    """Simulate the logic of ensure_container_is_used() decorator"""
    print("🔍 Container Environment Check:")
    print(f"  /.dockerenv exists: {check_container_environment()}")
    
    if check_container_environment():
        print("  ✅ Inside container - test would proceed")
        return True
    else:
        print("  ❌ Not inside container - checking if containers are running...")
        containers_running = check_containers_running()
        print(f"  Docker containers running: {containers_running}")
        
        if containers_running:
            print("  ❌ FAIL: Integration tests must run inside containers.")
            print("     Use: docker compose exec -T web python -m pytest ...")
        else:
            print("  ❌ FAIL: Integration tests require containers.")
            print("     Start with: docker compose up -d")
        
        return False

if __name__ == "__main__":
    print("🧪 Testing ensure_container_is_used() decorator logic\n")
    
    result = simulate_decorator_logic()
    
    print(f"\n📊 Result: {'PASS' if result else 'SKIP/FAIL'}")
    print("\n💡 This demonstrates that integration tests will now:")
    print("   - Only run inside Docker containers")
    print("   - Fail with clear instructions if run locally")
    print("   - Force proper usage of 'docker compose exec -T web python -m pytest'")
