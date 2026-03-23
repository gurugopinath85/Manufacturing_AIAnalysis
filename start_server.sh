#!/bin/bash

# Manufacturing AI Analysis Startup Script
echo "🏭 Starting Manufacturing AI Analysis..."

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Please run this script from the Manufacturing_AIAnalysis directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating one from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo "   Then run this script again."
    exit 1
fi

# Source environment variables (only non-comment lines)
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ No API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
    exit 1
fi

echo "✅ Environment configured"

# Start the FastAPI server
echo "🚀 Starting FastAPI server..."
cd app

# Use simple launcher
python3 run_server.py