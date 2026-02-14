#!/bin/bash

# Rakuten MLOps Control Room - Run Script

echo "🎯 Starting Rakuten MLOps Control Room..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update credentials if needed."
    echo ""
fi

# Check if venv exists
if [ ! -d "../.venv" ]; then
    echo "❌ Virtual environment not found at ../.venv"
    echo "Please create a virtual environment first:"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements-streamlit.txt"
    exit 1
fi

# Activate venv and run streamlit
echo "🚀 Launching Streamlit app..."
echo "📍 URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Run with venv python
../.venv/bin/streamlit run Home.py
