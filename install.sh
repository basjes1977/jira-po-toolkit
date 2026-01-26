#!/bin/bash
# Quick installer for Jira Presentation Tool

echo "=========================================="
echo "Jira Presentation Tool - Quick Installer"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Found Python $PYTHON_VERSION"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if pip install -r requirements.txt --quiet; then
    echo "✓ Dependencies installed"
else
    echo "⚠️  Some dependencies may have failed to install"
    echo "You can try again with: pip install -r requirements.txt"
fi

# Run setup wizard
echo ""
echo "🔧 Starting configuration wizard..."
echo ""

if [ -f ".jira_environment" ]; then
    echo "⚠️  Configuration file already exists"
    read -p "Run setup wizard anyway? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping setup wizard"
        echo ""
        echo "=========================================="
        echo "Installation Complete!"
        echo "=========================================="
        echo ""
        echo "Run the application:"
        echo "  python webapp/app.py"
        echo ""
        exit 0
    fi
fi

python3 setup_wizard.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Run the application:"
    echo "  python webapp/app.py"
    echo ""
    echo "Then visit: http://localhost:5000"
    echo ""
else
    echo ""
    echo "⚠️  Setup wizard was cancelled or failed"
    echo "You can run it again with: python setup_wizard.py"
    echo "Or use the web setup: python webapp/app.py"
    echo ""
fi
