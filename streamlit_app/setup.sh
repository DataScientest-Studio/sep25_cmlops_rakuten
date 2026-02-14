#!/bin/bash

# Rakuten MLOps Control Room - Setup Script

echo "🎯 Setting up Rakuten MLOps Control Room..."
echo ""

# Check if venv exists
if [ ! -d "../.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ../.venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv and install dependencies
echo ""
echo "📦 Installing dependencies..."
../.venv/bin/pip install -r ../requirements-streamlit.txt

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ Created .env file"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  source ../.venv/bin/activate"
echo "  streamlit run Home.py"
