#!/bin/bash

# Salesforce AI Agent Chat - FastAPI WebSocket Server Startup Script

echo "🚀 Starting Salesforce AI Agent Chat with FastAPI + WebSockets..."
echo "=================================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -q fastapi uvicorn websockets python-multipart aiofiles uvloop httptools

# Stop any existing server on port 8000
echo "🔄 Stopping any existing servers on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment
sleep 2

# Start FastAPI server
echo "🌟 Starting FastAPI WebSocket server on http://localhost:8000"
echo ""
echo "📡 WebSocket endpoint: ws://localhost:8000/ws/{session_id}"
echo "🔗 API documentation: http://localhost:8000/docs"
echo "🧪 Test client: http://localhost:8000/"
echo "❤️  Health check: http://localhost:8000/health"
echo ""
echo "💬 Features enabled:"
echo "   ✅ Real-time WebSocket chat"
echo "   ✅ Agent status updates"
echo "   ✅ Live log streaming"
echo "   ✅ Master Orchestrator integration"
echo "   ✅ Multi-session support"
echo ""
echo "🔥 Press Ctrl+C to stop the server"
echo "=================================================================="

# Start the server
uvicorn fastapi_app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    --loop uvloop \
    --access-log 