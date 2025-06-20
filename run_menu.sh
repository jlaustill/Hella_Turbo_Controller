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
    
    # Try to install dependencies
    pip3 install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies."
        echo "   Please run: pip3 install -r requirements.txt"
        exit 1
    fi
    
    echo "✅ Dependencies installed successfully!"
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
python3 hella_menu.py

echo ""
echo "👋 Thank you for using Hella Turbo Controller!"