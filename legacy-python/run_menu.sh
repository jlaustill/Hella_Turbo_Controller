#!/bin/bash
#
# Hella Turbo Controller - Interactive Menu Launcher
#
# This script provides an easy way to launch the interactive menu system
# with proper error handling and dependency checking.
#

echo "🔧 Hella Turbo Controller - Interactive Menu System"
echo "=================================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Please install Python 3 and try again."
    exit 1
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."

python3 -c "import inquirer, rich" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required dependencies."
    echo "   Installing dependencies..."
    
    # Try to install dependencies with pip3 first
    pip3 install -r requirements.txt 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "⚠️  System-wide installation failed. Creating virtual environment..."
        
        # Create virtual environment if it doesn't exist
        if [ ! -d ".venv" ]; then
            python3 -m venv .venv
            if [ $? -ne 0 ]; then
                echo "❌ Failed to create virtual environment."
                echo "   Please install python3-venv: sudo apt install python3-venv"
                exit 1
            fi
        fi
        
        # Activate virtual environment and install
        source .venv/bin/activate
        pip install -r requirements.txt
        
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies in virtual environment."
            echo "   Please check your internet connection and try again."
            exit 1
        fi
        
        echo "✅ Dependencies installed in virtual environment!"
        echo "   Note: Virtual environment will be used automatically."
    else
        echo "✅ Dependencies installed successfully!"
    fi
fi

# Check if python-can is available (might need separate installation)
python3 -c "import can" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  python-can library not found."
    echo "   This is required for CAN communication."
    echo "   Installing python-can..."
    
    pip3 install python-can
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install python-can."
        echo "   Please run: pip3 install python-can"
        exit 1
    fi
fi

echo "✅ All dependencies are available!"
echo ""

# Launch the menu system
echo "🚀 Launching interactive menu..."

# Use virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    python3 hella_menu.py
else
    python3 hella_menu.py
fi

echo ""
echo "👋 Thank you for using Hella Turbo Controller!"