#!/bin/bash
# Environment setup script for IDP Pipeline
set -e

echo "=== IDP Pipeline Setup ==="

# Check Python version
python3 --version || { echo "Python 3.10+ required"; exit 1; }

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data/uploads data/outputs data/chroma_db logs

# Copy .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example — please edit it with your settings"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Start Ollama: ollama serve"
echo "  3. Pull Gemma: ollama pull gemma3:27b"
echo "  4. Run: uvicorn app.main:app --reload"
echo "  5. Open: http://localhost:8000/docs"
