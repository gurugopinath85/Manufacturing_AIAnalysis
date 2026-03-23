#!/bin/bash

# Streamlit UI Startup Script
echo "🎨 Starting Streamlit UI..."

# Check if we're in the right directory
if [ ! -f "streamlit_app.py" ]; then
    echo "❌ Please run this script from the Manufacturing_AIAnalysis directory"
    exit 1
fi

# Check if API server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "⚠️  FastAPI server not detected at localhost:8000"
    echo "   Please start the server first: ./start_server.sh"
    echo "   Or start it manually: cd app && python3 main.py"
fi

echo "🚀 Starting Streamlit UI..."

# Try different ways to run streamlit
if command -v streamlit &> /dev/null; then
    streamlit run streamlit_app.py
elif command -v python3 -m streamlit &> /dev/null; then
    python3 -m streamlit run streamlit_app.py
elif [ -f "/Users/guru/Library/Python/3.13/bin/streamlit" ]; then
    /Users/guru/Library/Python/3.13/bin/streamlit run streamlit_app.py
else
    echo "❌ Streamlit not found. Installing..."
    pip install streamlit
    python3 -m streamlit run streamlit_app.py
fi