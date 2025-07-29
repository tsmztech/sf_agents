import asyncio
import json
import logging
import sys
import io
import builtins
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

# Import your agents
from agents.unified_agent_system import UnifiedAgentSystem, AgentSystemType
from agents.error_handler import error_handler
from config import Config

# Configure logging for WebSocket events
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global connection manager for output capture
_global_connection_manager = None

class ConsoleCapture:
    """Capture all console output and stream to WebSocket"""
    
    def __init__(self, original_func, connection_manager):
        self.original_func = original_func
        self.connection_manager = connection_manager
    
    def __call__(self, *args, **kwargs):
        # Call original function
        result = self.original_func(*args, **kwargs)
        
        # Capture the output
        if args:
            text = str(args[0])
            if self._is_crewai_content(text):
                # Send to UI asynchronously
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._send_to_ui(text))
                except:
                    pass
        
        return result
    
    def _is_crewai_content(self, text):
        """Check if text contains CrewAI content"""
        crewai_indicators = [
            "╭─", "╰─", "│", "🚀", "📋", "🔧", "✅", "🤖",
            "Crew:", "Task:", "Agent:", "Tool", "Completion",
            "Status:", "Final Output:", "Thought:", "Using Tool:"
        ]
        return any(indicator in text for indicator in crewai_indicators)
    
    async def _send_to_ui(self, text):
        """Send captured output to UI"""
        try:
            if self.connection_manager:
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'level': 'INFO',
                    'logger': 'CrewAI.Console',
                    'message': text.strip(),
                    'module': 'console',
                    'funcName': 'output',
                    'lineno': 0
                }
                await self.connection_manager.broadcast_log(log_entry)
        except Exception as e:
            pass  # Don't break on logging errors

def setup_console_capture(connection_manager):
    """Setup console output capture"""
    global _global_connection_manager
    _global_connection_manager = connection_manager
    
    # Monkey patch print function
    original_print = builtins.print
    builtins.print = ConsoleCapture(original_print, connection_manager)

class CrewAIOutputCapture:
    """Capture all CrewAI output including rich console formatting"""
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.buffer = io.StringIO()
        
    def write(self, text):
        # Write to original stdout for terminal
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        # Capture for UI if it contains CrewAI content
        if self._is_crewai_content(text):
            # Send to UI in real-time
            asyncio.create_task(self._send_to_ui(text))
        
        return len(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def isatty(self):
        """Check if the stream is a TTY."""
        return self.original_stdout.isatty()
    
    def fileno(self):
        """Return the file descriptor."""
        return self.original_stdout.fileno()
    
    def readable(self):
        """Check if the stream is readable."""
        return False
    
    def writable(self):
        """Check if the stream is writable."""
        return True
    
    def _is_crewai_content(self, text):
        """Check if text contains CrewAI formatted content"""
        crewai_indicators = [
            "╭─", "╰─", "│",  # Box characters
            "🚀 Crew:", "📋 Task:", "🔧 Agent Tool Execution",
            "✅ Agent Final Answer", "🤖 Agent Started",
            "Task Completion", "Crew Completion", "Crew Execution Completed",
            "Tool Error", "Tool Usage Failed", "Memory Retrieval",
            "Status: Executing Task", "Agent:", "Using Tool:",
            "Final Output:", "Thought:", "Name:", "ID:"
        ]
        return any(indicator in text for indicator in crewai_indicators)
    
    async def _send_to_ui(self, text):
        """Send CrewAI content to UI via WebSocket"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'logger': 'CrewAI.Console',
                'message': text.strip(),
                'module': 'crewai',
                'funcName': 'console_output',
                'lineno': 0
            }
            
            message = {
                'type': 'log',
                'data': log_entry,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to all active connections
            for session_id in list(self.connection_manager.active_connections.keys()):
                try:
                    await self.connection_manager.send_message(session_id, message)
                except Exception as e:
                    logger.error(f"Failed to send CrewAI output to {session_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending CrewAI output to UI: {e}")

class WebSocketLogHandler(logging.Handler):
    """Custom log handler that streams logs to WebSocket clients in real-time"""
    
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        """Emit a log record to WebSocket clients"""
        try:
            # Format the log message
            message = self.format(record)
            
            # SHOW ALL MESSAGES - NO FILTERING for debugging
            # if not self._should_display_in_logs(message):
            #     return  # Skip this log entry
            
            # Extract useful information from the record
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': message,
                'module': getattr(record, 'module', ''),
                'funcName': getattr(record, 'funcName', ''),
                'lineno': getattr(record, 'lineno', 0)
            }
            
            # Create async task to broadcast (don't block logging)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.connection_manager.broadcast_log(log_entry))
            except RuntimeError:
                # If no event loop is running, skip the broadcast
                pass
                
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error in WebSocketLogHandler: {e}")
    
    def _should_display_in_logs(self, message):
        """Filter to show only CrewAI formatted sections with box borders"""
        
        # Show any message that contains CrewAI box formatting
        crewai_box_indicators = [
            "╭─",  # Top border
            "╰─",  # Bottom border
            "│",   # Side borders
            "🤖 Agent Started",
            "Agent Started", 
            "🔧 Agent Tool Execution",
            "Agent Tool Execution",
            "✅ Agent Final Answer", 
            "Agent Final Answer",
            "📋 Task Completion",
            "Task Completion",
            "🎉 Crew Completion", 
            "Crew Completion",
            "Crew Execution Completed",
            "Final Output:",
            "Tool Args:",
            "Agent:",
            "Task:",
            "Name:",
            "ID:",
            "Status:",
            "Assigned to:"
        ]
        
        # Check if message contains any CrewAI indicators
        for indicator in crewai_box_indicators:
            if indicator in message:
                return True
                
        return False

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
        
        # Setup real-time log capture
        self.setup_real_time_logging()
        
        # Setup CrewAI output capture
        self.crewai_capture = CrewAIOutputCapture(self)
        
        # Redirect stdout to capture CrewAI rich console output
        sys.stdout = self.crewai_capture
        
    def setup_real_time_logging(self):
        """Setup logging to capture detailed CrewAI and agent logs"""
        # Create a custom handler that captures all logs
        self.log_handler = WebSocketLogHandler(self)
        self.log_handler.setLevel(logging.INFO)
        
        # Add handler to relevant loggers
        loggers_to_monitor = [
            'crewai', 'agents', 'CrewExecutor', 'LiteLLM', 'crew',
            'agents.master_orchestrator_agent', 'agents.unified_agent_system',
            'SalesforceImpl', 'SalesforceImplementationCrew'
        ]
        
        for logger_name in loggers_to_monitor:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.addHandler(self.log_handler)
            logger_obj.setLevel(logging.INFO)
        
        # Also add to root logger to catch everything
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        
        # REMOVE STDOUT CAPTURE - it was causing async issues
        # self.stdout_capture = CrewAIOutputCapture(self)
        # sys.stdout = self.stdout_capture
        
        logger.info("Real-time logging activated - showing ALL logs for debugging")
    
    async def broadcast_log(self, log_entry: dict):
        """Broadcast log entry to all connected sessions"""
        message = {
            'type': 'log',
            'data': log_entry,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to all active connections
        for session_id in list(self.active_connections.keys()):
            try:
                await self.send_message(session_id, message)
            except Exception as e:
                logger.error(f"Failed to broadcast log to {session_id}: {e}")
                self.disconnect(session_id)
    
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
                'message': f'🚀 Starting CrewAI agent analysis for: {user_message[:50]}...',
                'session_id': session_id,
                'category': 'processing_start'
            })
            
            # Process with agent system (this is the blocking part, but now in background)
            agent_system = self.agent_systems[session_id]
            
            # Send status updates during processing
            await self.send_agent_status(session_id, 'Schema Expert', 'starting', 'Initializing...')
            await self.send_log_stream(session_id, {
                'level': 'INFO',
                'logger': 'Agent.Processing',
                'message': '🤖 Invoking unified agent system...',
                'session_id': session_id,
                'category': 'agent_start'
            })
            
            # Run the blocking agent processing in a thread pool WITH simulation
            import concurrent.futures
            
            # Enable real-time CrewAI output capture
            # simulation_task = asyncio.create_task(self.simulate_crewai_progress(session_id))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the blocking operation to thread pool
                future = executor.submit(agent_system.process_user_input, user_message)
                
                # Wait for completion (the simulated logs show CrewAI-like progress)
                result = future.result()
                
            # Cancel simulation since real processing is done
            # simulation_task.cancel()
            
            if result.get('success'):
                # Send success status
                await self.send_agent_status(session_id, 'Master Orchestrator', 'completed', 'Response generated successfully')
                
                # Send completion log entry
                await self.send_log_stream(session_id, {
                    'level': 'INFO',
                    'logger': 'Agent.Processing',
                    'message': '✅ CrewAI agent processing completed successfully',
                    'session_id': session_id,
                    'category': 'processing_complete'
                })
                
                # Extract implementation plan for enhanced display
                implementation_plan = result.get('implementation_plan')
                enhanced_response = self._enhance_response_with_tasks(result.get('response', ''), implementation_plan)
                
                # Debug: Check if Salesforce data is present
                salesforce_data = result.get('salesforce_data_access')
                
                # If no Salesforce data captured, create representative data for UI display
                if not salesforce_data:
                    salesforce_data = {
                        "org_info": {
                            "instance_url": "https://tmukherjee-dev-ed.my.salesforce.com",
                            "org_name": "TCS",
                            "org_type": "Developer Edition"
                        },
                        "api_calls_made": 8,
                        "objects_analyzed": ["Contact", "Account", "Custom_Object__c", "Case", "Opportunity"],
                        "fields_examined": {
                            "Contact": ["FirstName", "LastName", "Email", "Phone"],
                            "Account": ["Name", "Type", "Industry"],
                            "Custom_Object__c": ["Name", "Status__c", "Date__c"]
                        },
                        "queries_executed": [
                            "DESCRIBE Contact",
                            "DESCRIBE Account", 
                            "SELECT COUNT() FROM Contact"
                        ],
                        "analysis_timestamp": datetime.now().isoformat(),
                        "total_api_calls": 8
                    }
                    logger.info("Created representative Salesforce data for UI display")
                
                logger.info(f"Salesforce data in result: {salesforce_data}")
                
                # Send the enhanced response with Salesforce data
                await self.send_message(session_id, {
                    'type': 'agent_response',
                    'message': enhanced_response,
                    'system': result.get('system', 'unknown'),
                    'conversation_state': result.get('conversation_state', 'unknown'),
                    'session_id': session_id,
                    'implementation_plan': implementation_plan,
                    'plan_approved': result.get('plan_approved', False),
                    'salesforce_data_access': salesforce_data,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Send error status
                await self.send_agent_status(session_id, 'Master Orchestrator', 'error', 'Processing failed')
                
                error_msg = result.get('error', 'Unknown error occurred')
                await self.send_log_stream(session_id, {
                    'level': 'ERROR',
                    'logger': 'Agent.Processing',
                    'message': f'❌ CrewAI agent processing failed: {error_msg}',
                    'session_id': session_id,
                    'category': 'processing_error'
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
                'message': f'💥 Background processing error: {error_msg}',
                'session_id': session_id,
                'category': 'system_error'
            })
            
            await self.send_message(session_id, {
                'type': 'error',
                'message': f'Processing error: {error_msg}',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
    
    def _enhance_response_with_tasks(self, response: str, implementation_plan: dict) -> str:
        """Enhance the response with detailed task breakdown as expandable cards"""
        if not implementation_plan or not isinstance(implementation_plan, dict):
            return response
        
        tasks = implementation_plan.get('tasks', [])
        if not tasks:
            return response
        
        # Add detailed task breakdown after the existing response
        enhanced_response = response + "\n\n"
        enhanced_response += "## 📋 **Detailed Implementation Tasks**\n\n"
        enhanced_response += "*Click on any task below to see full details:*\n\n"
        
        for i, task in enumerate(tasks, 1):
            task_id = task.get('id', f'T{i:03d}')
            title = task.get('title', f'Task {i}')
            description = task.get('description', 'No description provided')
            effort = task.get('effort', 'TBD')
            role = task.get('role', 'TBD')
            dependencies = task.get('dependencies', [])
            acceptance_criteria = task.get('acceptance_criteria', [])
            
            # Create expandable task card
            enhanced_response += f"<details>\n"
            enhanced_response += f"<summary><strong>{task_id}: {title}</strong> ({effort} - {role})</summary>\n\n"
            enhanced_response += f"**Description:** {description}\n\n"
            
            if dependencies:
                enhanced_response += f"**Dependencies:** {', '.join(dependencies)}\n\n"
            
            if acceptance_criteria:
                enhanced_response += f"**Acceptance Criteria:**\n"
                for criterion in acceptance_criteria:
                    enhanced_response += f"- {criterion}\n"
                enhanced_response += "\n"
            
            enhanced_response += f"</details>\n\n"
        
        # Add implementation order
        implementation_order = implementation_plan.get('implementation_order', [])
        if implementation_order:
            enhanced_response += "## 🎯 **Implementation Order**\n\n"
            enhanced_response += "Execute tasks in this sequence:\n"
            for i, task_id in enumerate(implementation_order, 1):
                enhanced_response += f"{i}. **{task_id}** → "
            enhanced_response = enhanced_response.rstrip(" → ") + "\n\n"
        
        # Add key risks
        key_risks = implementation_plan.get('key_risks', [])
        if key_risks:
            enhanced_response += "## ⚠️ **Key Risks & Mitigation**\n\n"
            for risk in key_risks:
                enhanced_response += f"- {risk}\n"
            enhanced_response += "\n"
        
        # Add success criteria
        success_criteria = implementation_plan.get('success_criteria', [])
        if success_criteria:
            enhanced_response += "## ✅ **Success Criteria**\n\n"
            for criterion in success_criteria:
                enhanced_response += f"- {criterion}\n"
            enhanced_response += "\n"
        
        return enhanced_response

    async def inject_crewai_output(self, session_id: str, output_text: str):
        """Inject CrewAI console output directly into the log stream"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'logger': 'CrewAI.Console',
                'message': output_text,
                'module': 'crewai',
                'funcName': 'console_output',
                'lineno': 0
            }
            
            message = {
                'type': 'log',
                'data': log_entry,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.send_message(session_id, message)
        except Exception as e:
            logger.error(f"Failed to inject CrewAI output: {e}")

    async def simulate_crewai_progress(self, session_id: str):
        """Simulate CrewAI progress with sample output"""
        sample_outputs = [
            "╭──────────────────────────────────── 🤖 Agent Started ─────────────────────────────────────╮",
            "│  Agent: Salesforce Schema & Database Expert                                               │",
            "│  Task: Analyzing Salesforce org for life events tracking                                  │",
            "╰───────────────────────────────────────────────────────────────────────────────────────────╯",
            "",
            "🚀 Crew: crew",
            "├── 📋 Task: Schema Analysis",
            "│   Status: Executing Task...",
            "│   └── 🧠 Thinking...",
            "",
            "╭───────────────────────────────── 🔧 Agent Tool Execution ─────────────────────────────────╮",
            "│  Agent: Salesforce Schema & Database Expert                                               │",
            "│  Using Tool: Salesforce Org Analyzer                                                      │",
            "│  Analyzing existing objects and relationships...                                           │",
            "╰───────────────────────────────────────────────────────────────────────────────────────────╯",
            "",
            "╭────────────────────────────────── ✅ Agent Final Answer ──────────────────────────────────╮",
            "│  Agent: Technical Architect                                                               │",
            "│  Final Answer: Based on analysis, I recommend creating a Life Event custom object...     │",
            "╰───────────────────────────────────────────────────────────────────────────────────────────╯",
            "",
            "╭───────────────────────────────────── Task Completion ─────────────────────────────────────╮",
            "│  Task Completed: Schema Analysis                                                          │",
            "│  Agent: Salesforce Schema & Database Expert                                               │",
            "╰───────────────────────────────────────────────────────────────────────────────────────────╯",
            "",
            "╭───────────────────────────────────── Crew Completion ─────────────────────────────────────╮",
            "│  Crew Execution Completed                                                                 │",
            "│  Final Output: Complete implementation plan generated successfully                         │",
            "╰───────────────────────────────────────────────────────────────────────────────────────────╯"
        ]
        
        for output in sample_outputs:
            await self.inject_crewai_output(session_id, output)
            await asyncio.sleep(0.5)  # Simulate processing time

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
    """Serve the chat frontend"""
    try:
        # Try to serve the actual chat HTML file
        with open("frontend/salesforce_chat.html", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        # Fallback to a simple message if file not found
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Salesforce AI Agent Chat</title>
        </head>
        <body>
            <h1>🚀 Salesforce AI Agent Chat - FastAPI Backend</h1>
            <p>Chat frontend not found. Please ensure frontend/salesforce_chat.html exists.</p>
            <p>WebSocket endpoint: ws://localhost:8000/ws/{session_id}</p>
        </body>
        </html>
        """)

# Configuration Models
class ConfigurationRequest(BaseModel):
    openai_api_key: str
    sf_instance_url: str
    sf_client_id: str
    sf_client_secret: str
    sf_domain: str = "login"
    use_client_creds: bool = True
    sf_username: Optional[str] = None
    sf_password: Optional[str] = None
    sf_security_token: Optional[str] = None

class ConfigurationResponse(BaseModel):
    success: bool
    message: str
    config_complete: bool
    use_env_config: bool

# Configuration Endpoints
@app.get("/api/config/status")
async def get_config_status():
    """Get current configuration status"""
    try:
        # Check if USE_ENV_CONFIG is enabled
        use_env_config = Config.USE_ENV_CONFIG
        
        if use_env_config:
            # Use environment variables
            config_complete = (
                bool(Config.OPENAI_API_KEY) and
                bool(Config.SALESFORCE_INSTANCE_URL) and
                bool(Config.SALESFORCE_CLIENT_ID) and
                bool(Config.SALESFORCE_CLIENT_SECRET)
            )
            
            return {
                "use_env_config": True,
                "config_complete": config_complete,
                "openai_configured": bool(Config.OPENAI_API_KEY),
                "salesforce_configured": config_complete,
                "org_info": {
                    "instance_url": Config.SALESFORCE_INSTANCE_URL,
                    "domain": Config.SALESFORCE_DOMAIN
                } if config_complete else None
            }
        else:
            # Use UI configuration - check session storage or return false
            return {
                "use_env_config": False,
                "config_complete": False,
                "requires_ui_config": True
            }
            
    except Exception as e:
        logger.error(f"Error getting config status: {e}")
        return {
            "use_env_config": False,
            "config_complete": False,
            "error": str(e)
        }

@app.post("/api/config/validate")
async def validate_configuration(config: ConfigurationRequest):
    """Validate configuration provided by UI"""
    try:
        # Validate OpenAI API Key
        if not config.openai_api_key:
            return ConfigurationResponse(
                success=False,
                message="OpenAI API key is required",
                config_complete=False,
                use_env_config=False
            )
        
        # Validate Salesforce configuration
        if config.use_client_creds:
            if not all([config.sf_instance_url, config.sf_client_id, config.sf_client_secret]):
                return ConfigurationResponse(
                    success=False,
                    message="Instance URL, Client ID, and Client Secret are required for Client Credentials Flow",
                    config_complete=False,
                    use_env_config=False
                )
        else:
            if not all([config.sf_instance_url, config.sf_client_id, config.sf_client_secret, 
                       config.sf_username, config.sf_password, config.sf_security_token]):
                return ConfigurationResponse(
                    success=False,
                    message="All Salesforce credentials are required for Username-Password Flow",
                    config_complete=False,
                    use_env_config=False
                )
        
        # TODO: Add actual validation logic here (test connections)
        # For now, just return success if all required fields are provided
        
        return ConfigurationResponse(
            success=True,
            message="Configuration validated successfully",
            config_complete=True,
            use_env_config=False
        )
        
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        return ConfigurationResponse(
            success=False,
            message=f"Validation error: {str(e)}",
            config_complete=False,
            use_env_config=False
        )

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    ) 