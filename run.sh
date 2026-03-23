#!/bin/bash

# Manufacturing AI Analysis - Quick Start Script

echo "🏭 Manufacturing AI Analysis - Quick Start"
echo "========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please copy .env.example to .env and configure your API keys."
    echo "   cp .env.example .env"
    echo "   # Edit .env file with your API keys"
    exit 1
fi

echo ""
echo "🚀 Ready to start! Run the following commands in separate terminals:"
echo ""
echo "Terminal 1 (FastAPI Backend):"
echo "   cd app && python main.py"
echo ""
echo "Terminal 2 (Streamlit UI):"
echo "   streamlit run streamlit_app.py"
echo ""
echo "Then visit:"
echo "   • Streamlit UI: http://localhost:8501"
echo "   • API Docs: http://localhost:8000/docs"
echo ""