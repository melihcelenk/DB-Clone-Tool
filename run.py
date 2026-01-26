#!/usr/bin/env python
"""
MySQL Schema Clone Tool - Cross-platform Launcher
Double-click this file to start the application (Windows)
Or run: python run.py (Linux/Mac)
"""
import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        input("Press Enter to exit...")
        sys.exit(1)

def setup_venv():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

def activate_venv():
    """Activate virtual environment and return Python executable"""
    if sys.platform == "win32":
        python_exe = Path("venv/Scripts/python.exe")
    else:
        python_exe = Path("venv/bin/python")
    
    if python_exe.exists():
        return str(python_exe)
    return sys.executable

def install_dependencies(python_exe):
    """Install dependencies if not already installed"""
    missing = []

    try:
        import flask
    except ImportError:
        missing.append("Flask")

    try:
        import pymysql
    except ImportError:
        missing.append("pymysql")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing:
        print("=" * 70)
        print("  MISSING DEPENDENCIES")
        print("=" * 70)
        print(f"\nRequired packages are not installed: {', '.join(missing)}\n")
        print("Please run the following command to install dependencies:")
        print("\n  pip install -e .")
        print("\nOr for development mode:")
        print("\n  pip install -e .[dev]")
        print("\n" + "=" * 70)
        input("\nPress Enter after installing dependencies...")
        return False

    return True

def open_browser():
    """Open browser after a short delay"""
    import time
    import webbrowser
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://localhost:5000")

def main():
    """Main launcher function"""
    print("=" * 70)
    print("  MySQL Schema Clone Tool")
    print("=" * 70)
    print()
    
    # Check Python version
    check_python_version()
    
    # Setup virtual environment
    setup_venv()
    
    # Get Python executable
    python_exe = activate_venv()
    
    # Install dependencies
    install_dependencies(python_exe)
    
    # Print instructions
    print()
    print("=" * 70)
    print("  Starting application...")
    print("=" * 70)
    print()
    print("  The web interface will open automatically in your browser")
    print("  URL: http://localhost:5000")
    print()
    print("  Press Ctrl+C to stop the server")
    print()
    print("=" * 70)
    print()
    
    # Open browser in background (Windows)
    if sys.platform == "win32":
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    # Run the application
    try:
        subprocess.run([python_exe, "-m", "src.db_clone_tool.main"], check=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Application failed to start: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
