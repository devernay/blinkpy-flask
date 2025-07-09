#!/bin/bash
# Installation script for Blink Flask Application

echo "Installing Blink Flask Application..."
echo "===================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 found"

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "Error: pip is required but not installed."
    exit 1
fi

echo "✓ pip found"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
else
    pip install -r requirements.txt
fi

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Run setup test
echo ""
echo "Testing installation..."
python3 test_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "To start the application:"
    echo "  python3 run.py"
    echo ""
    echo "Then open your browser to: http://localhost:5000"
else
    echo ""
    echo "❌ Installation test failed. Please check the error messages above."
    exit 1
fi