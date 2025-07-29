import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Import existing agent systems
from agents.unified_agent_system import UnifiedAgentSystem, AgentSystemType
from agents.error_handler import error_handler
from config import Config

# Configure logging for WebSocket events
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Salesforce AI Agent Chat",
    description="Real-time chat interface for Salesforce AI agents using WebSockets",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Manages WebSocket connections and real-time communication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, dict] = {}
        self.agent_systems: Dict[str, UnifiedAgentSystem] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Initialize agent system for this session
        try:
            self.agent_systems[session_id] = UnifiedAgentSystem(
                preferred_system=AgentSystemType.ORCHESTRATOR,
                session_id=session_id
            )
            
            # Initialize session data
            self.user_sessions[session_id] = {
                'connected_at': datetime.now(),
                'message_count': 0,
                'last_activity': datetime.now()
            }
            
            logger.info(f"Client connected: {session_id}")
            
            # Send welcome message
            await self.send_message(session_id, {
                'type': 'system',
                'message': 'Connected to Salesforce AI Assistant',
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize agent for session {session_id}: {e}")
            await websocket.close(code=1011, reason="Agent initialization failed")
    
    def disconnect(self, session_id: str):
        """Handle client disconnection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if session_id in self.user_sessions:
            del self.user_sessions[session_id]
            
        if session_id in self.agent_systems:
            del self.agent_systems[session_id]
            
        logger.info(f"Client disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)
                return False
        return False
    
    async def send_log_stream(self, session_id: str, log_entry: dict):
        """Send real-time log entry to client"""
        message = {
            'type': 'log',
            'data': log_entry,
            'timestamp': datetime.now().isoformat()
        }
        await self.send_message(session_id, message)
    
    async def send_agent_status(self, session_id: str, agent_name: str, status: str, message: str):
        """Send agent status update to client"""
        status_message = {
            'type': 'agent_status',
            'agent': agent_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        await self.send_message(session_id, status_message)
    
    async def process_user_message(self, session_id: str, user_message: str):
        """Process user message with agent system - NOW TRULY ASYNC"""
        if session_id not in self.agent_systems:
            return {
                'type': 'error',
                'message': 'Agent system not initialized for this session'
            }
        
        try:
            # Update session activity
            self.user_sessions[session_id]['last_activity'] = datetime.now()
            self.user_sessions[session_id]['message_count'] += 1
            
            # Send immediate acknowledgment
            await self.send_message(session_id, {
                'type': 'processing_started',
                'message': f'Processing: {user_message[:50]}...',
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            })
            
            # Start background processing without blocking
            asyncio.create_task(self._background_agent_processing(session_id, user_message))
            
            # Return immediately - don't wait for agent
            return {
                'type': 'acknowledged',
                'message': 'Message received and processing started',
                'session_id': session_id
            }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error starting processing for session {session_id}: {error_msg}")
            
            return {
                'type': 'error',
                'message': f'Failed to start processing: {error_msg}',
                'session_id': session_id
            }
    
    async def _background_agent_processing(self, session_id: str, user_message: str):
        """Background agent processing that sends real-time updates"""
        try:
            # Send status update
            await self.send_agent_status(session_id, 'Master Orchestrator', 'working', 'Processing your request...')
            
            # Send log entry
            await self.send_log_stream(session_id, {
                'level': 'INFO',
                'logger': 'FastAPI.WebSocket',
                'message': f'Starting agent analysis for: {user_message[:50]}...',
                'session_id': session_id
            })
            
            # Process with agent system (this is the blocking part, but now in background)
            agent_system = self.agent_systems[session_id]
            
            # Send status updates during processing
            await self.send_agent_status(session_id, 'Schema Expert', 'starting', 'Initializing...')
            await self.send_log_stream(session_id, {
                'level': 'INFO',
                'logger': 'Agent.Processing',
                'message': 'Invoking unified agent system...',
                'session_id': session_id
            })
            
            # Run the blocking agent processing in a thread pool
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the blocking operation to thread pool
                future = executor.submit(agent_system.process_user_input, user_message)
                
                # While waiting, send periodic status updates
                while not future.done():
                    await asyncio.sleep(2)  # Check every 2 seconds
                    await self.send_log_stream(session_id, {
                        'level': 'INFO',
                        'logger': 'Agent.Processing',
                        'message': 'Agent is still working...',
                        'session_id': session_id
                    })
                
                # Get the result
                result = future.result()
            
            if result.get('success'):
                # Send success status
                await self.send_agent_status(session_id, 'Master Orchestrator', 'completed', 'Response generated successfully')
                
                # Send log entry
                await self.send_log_stream(session_id, {
                    'level': 'INFO',
                    'logger': 'Agent.Processing',
                    'message': 'Agent processing completed successfully',
                    'session_id': session_id
                })
                
                # Send the actual response
                await self.send_message(session_id, {
                    'type': 'agent_response',
                    'message': result.get('response', ''),
                    'system': result.get('system', 'unknown'),
                    'conversation_state': result.get('conversation_state', 'unknown'),
                    'session_id': session_id,
                    'implementation_plan': result.get('implementation_plan'),
                    'plan_approved': result.get('plan_approved', False),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Send error status
                await self.send_agent_status(session_id, 'Master Orchestrator', 'error', 'Processing failed')
                
                error_msg = result.get('error', 'Unknown error occurred')
                await self.send_log_stream(session_id, {
                    'level': 'ERROR',
                    'logger': 'Agent.Processing',
                    'message': f'Agent processing failed: {error_msg}',
                    'session_id': session_id
                })
                
                await self.send_message(session_id, {
                    'type': 'error',
                    'message': error_msg,
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Background processing error for session {session_id}: {error_msg}")
            
            await self.send_agent_status(session_id, 'System', 'error', 'Unexpected error occurred')
            await self.send_log_stream(session_id, {
                'level': 'ERROR',
                'logger': 'Agent.Processing',
                'message': f'Background processing error: {error_msg}',
                'session_id': session_id
            })
            
            await self.send_message(session_id, {
                'type': 'error',
                'message': f'Processing error: {error_msg}',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })

# Global connection manager
manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get('type', 'unknown')
                
                if message_type == 'ping':
                    # Handle ping/pong for connection keepalive
                    await manager.send_message(session_id, {
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    })
                
                elif message_type == 'user_message':
                    # Handle user chat message
                    user_message = message.get('message', '').strip()
                    
                    if user_message:
                        # Echo user message back immediately - NO WAITING
                        await manager.send_message(session_id, {
                            'type': 'user_message_echo',
                            'message': user_message,
                            'timestamp': datetime.now().isoformat(),
                            'session_id': session_id
                        })
                        
                        # Start processing but DON'T WAIT for it - just fire and forget
                        await manager.process_user_message(session_id, user_message)
                        
                        # NO RESPONSE SENDING HERE - the background task will handle it
                        
                    else:
                        await manager.send_message(session_id, {
                            'type': 'error',
                            'message': 'Empty message received',
                            'timestamp': datetime.now().isoformat()
                        })
                
                elif message_type == 'get_status':
                    # Send current session status
                    session_info = manager.user_sessions.get(session_id, {})
                    await manager.send_message(session_id, {
                        'type': 'session_status',
                        'session_id': session_id,
                        'connected_at': session_info.get('connected_at', datetime.now()).isoformat(),
                        'message_count': session_info.get('message_count', 0),
                        'last_activity': session_info.get('last_activity', datetime.now()).isoformat()
                    })
                
                else:
                    await manager.send_message(session_id, {
                        'type': 'error',
                        'message': f'Unknown message type: {message_type}',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    'type': 'error',
                    'message': 'Invalid JSON format',
                    'timestamp': datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.user_sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sessions")
async def get_active_sessions():
    """Get information about active sessions"""
    sessions = {}
    for session_id, session_data in manager.user_sessions.items():
        sessions[session_id] = {
            'connected_at': session_data['connected_at'].isoformat(),
            'message_count': session_data['message_count'],
            'last_activity': session_data['last_activity'].isoformat(),
            'is_connected': session_id in manager.active_connections
        }
    
    return {
        "active_sessions": sessions,
        "total_sessions": len(sessions)
    }

# Serve static files for React frontend (when built)
try:
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
except:
    pass  # Frontend not built yet

@app.get("/")
async def serve_frontend():
    """Serve React frontend or fallback page"""
    try:
        with open("frontend/build/index.html") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback HTML for development
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Salesforce AI Agent Chat</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .endpoint { background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Salesforce AI Agent Chat - FastAPI Backend</h1>
                
                <div class="status">
                    <h3>✅ FastAPI WebSocket Server is Running!</h3>
                    <p>The real-time backend is ready. Connect your React frontend or test with WebSocket clients.</p>
                </div>
                
                <h3>📡 WebSocket Endpoint:</h3>
                <div class="endpoint">ws://localhost:8000/ws/{session_id}</div>
                
                <h3>🔗 API Endpoints:</h3>
                <div class="endpoint">GET /health - Health check</div>
                <div class="endpoint">GET /sessions - Active sessions info</div>
                <div class="endpoint">GET /docs - API documentation</div>
                
                <h3>💬 Message Types (WebSocket):</h3>
                <ul>
                    <li><strong>user_message</strong>: Send user chat messages</li>
                    <li><strong>ping</strong>: Connection keepalive</li>
                    <li><strong>get_status</strong>: Get session status</li>
                </ul>
                
                <h3>📨 Response Types:</h3>
                <ul>
                    <li><strong>agent_response</strong>: AI agent responses</li>
                    <li><strong>log</strong>: Real-time log entries</li>
                    <li><strong>agent_status</strong>: Agent status updates</li>
                    <li><strong>system</strong>: System messages</li>
                </ul>
                
                <p><a href="/docs">📚 View Full API Documentation</a></p>
            </div>
        </body>
        </html>
        """)

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    ) 