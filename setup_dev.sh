#!/bin/bash
# filepath: /Users/surya/Developer/spotifytool/setup_dev.sh

set -e

echo "🚀 Setting up SpotifyTool development environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project in editable mode with all dependencies
pip install -e .

echo "✅ Development environment ready!"
echo "To activate: source venv/bin/activate"
echo "To run the server: python3 -m core.server"
echo "To run the CLI: python3 -m core.cli"