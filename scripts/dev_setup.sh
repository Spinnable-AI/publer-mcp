#!/bin/bash

# Publer MCP Development Setup Script
# Sets up the development environment for local development

set -e

echo "🚀 Setting up Publer MCP development environment..."

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -o '3\.[0-9]*')
if [[ "$python_version" < "3.11" ]]; then
    echo "❌ Python 3.11 or higher is required. Found: $python_version"
    exit 1
fi
echo "✅ Python version: $(python3 --version)"

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install -e ".[dev]"

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  Pre-commit not found, skipping hook installation"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Set up your Publer API credentials"
echo "3. Run the server: python -m publer_mcp.server"
echo "4. Run tests: pytest"
echo ""