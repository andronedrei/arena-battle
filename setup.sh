#!/bin/bash

# Arena Battle - Setup Script
# Creates virtual environment and installs dependencies

set -e  # Exit on error

echo "🎮 Arena Battle - Setup"
echo "======================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Check if venv already exists
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists."
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing venv..."
        rm -rf venv
    else
        echo "Using existing venv. Installing/updating dependencies..."
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "✓ Dependencies installed!"
        echo ""
        echo "Setup complete!"
        exit 0
    fi
fi

echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed!"
echo ""

echo "======================="
echo "✓ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the game:"
echo "  0. Go to root project folder"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Go to src folder: cd src"
echo "  3. Terminal 1 - Start server: python -m server.main"
echo "  4. Repeat 0, 1, 2 => Terminal 2 - Start client 1: python -m client.main"
echo "  5. Repeat 0, 1, 2 => Terminal 3 - Start client 2: python -m client.main"
