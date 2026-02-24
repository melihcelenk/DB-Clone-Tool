#!/bin/bash
# MySQL Schema Clone Tool - Linux/macOS Launcher
# Run this script to start the application: ./run.sh

echo "Starting MySQL Schema Clone Tool..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher:"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  - macOS: brew install python3"
    echo "  - Fedora/RHEL: sudo dnf install python3 python3-pip"
    exit 1
fi

# Display Python version
echo "Using Python: $(python3 --version)"

# Check if virtual environment exists, if not create one
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        echo "Make sure python3-venv is installed:"
        echo "  - Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Check if dependencies are installed
python -c "import flask, pymysql, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -e .
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        echo "Check your internet connection and try again"
        exit 1
    fi
fi

# Run the application
echo ""
echo "========================================"
echo "  MySQL Schema Clone Tool"
echo "========================================"
echo ""
echo "Server running at http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Use exec to replace shell process with Python (cleaner shutdown)
exec python -m src.db_clone_tool.main
