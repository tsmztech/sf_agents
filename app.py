import streamlit as st
import time
from typing import Dict, Any, Optional, Union, List
import json
from datetime import datetime
import logging

from config import Config
# Import unified agent system
from agents.unified_agent_system import UnifiedAgentSystem, AgentSystemType
from agents.error_handler import error_handler, format_error_for_ui, safe_execute
# Import CrewAI implementation (fallback)
from salesforce_crew import CrewExecutor, analyze_salesforce_requirement, is_complex_requirement

# Safe import of CrewOutput
try:
    from crewai.crew import CrewOutput
except ImportError:
    CrewOutput = None

# Configure Streamlit page
st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/issues',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': f"""
        ## {Config.APP_NAME}
        **Version:** {Config.APP_VERSION}  
        **Description:** {Config.APP_DESCRIPTION}
        
        Built with ❤️ using CrewAI, Streamlit, and OpenAI GPT-4
        """
    }
)

# Consolidated CSS for better UI consistency
st.markdown("""
<style>
    /* Main Layout */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 120px !important; /* Space for fixed footer */
        max-width: 1200px !important;
    }
    
    /* Chat Container */
    .chat-container {
        min-height: calc(100vh - 200px);
        overflow-y: auto;
        padding: 10px 20px;
        background: transparent;
        margin-bottom: 20px;
    }

    /* User Messages - Right Aligned */
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin: 12px 0;
        animation: slideInRight 0.3s ease-out;
    }

    .user-message .message-bubble {
        background: linear-gradient(135deg, #6c7293 0%, #4a4f6b 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 2px 12px rgba(108, 114, 147, 0.3);
        line-height: 1.5;
    }

    /* All Agent Messages - Left Aligned */
    .agent-message,
    .expert-message,
    .technical-message,
    .dependency-message,
    .orchestrator-message {
        display: flex;
        justify-content: flex-start;
        margin: 12px 0;
        animation: slideInLeft 0.3s ease-out;
    }

    .agent-message .message-bubble,
    .expert-message .message-bubble,
    .technical-message .message-bubble,
    .dependency-message .message-bubble,
    .orchestrator-message .message-bubble {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 2px 12px rgba(59, 130, 246, 0.3);
        line-height: 1.5;
    }

    /* Agent Status Messages */
    .agent-status {
        display: flex;
        justify-content: flex-start;
        margin: 8px 0;
    }

    .agent-status .message-bubble {
        background: rgba(108, 117, 125, 0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 15px;
        font-size: 0.9rem;
        animation: pulse 2s infinite;
        max-width: 60%;
    }

    .agent-status-completed .message-bubble {
        background: #10b981;
        animation: none;
    }

    /* Orchestrator-specific styling */
    .orchestrator-message .message-bubble {
        background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%) !important;
        border-left: 4px solid #42A5F5;
        box-shadow: 0 3px 15px rgba(25, 118, 210, 0.4);
    }

    /* Fixed Footer Input */
    .stForm {
        background: white !important;
        border-top: 2px solid #e9ecef !important;
        padding: 15px 20px !important;
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 1000 !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1) !important;
    }
    
    .stForm > div {
        max-width: 800px !important;
        margin: 0 auto !important;
    }
    
    .stTextArea > div > div {
        border-radius: 22px !important;
        border: 2px solid #e9ecef !important;
        background: #f8f9fa !important;
    }
    
    .stTextArea > div > div:focus-within {
        border-color: #667eea !important;
        background: white !important;
    }
    
    .stButton > button {
        border-radius: 22px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        height: 44px !important;
        min-width: 44px !important;
        font-weight: 600 !important;
        transition: transform 0.2s ease !important;
    }
    
    .stButton > button:hover {
        transform: scale(1.05) !important;
    }
    
    .stButton > button:disabled {
        background: #6c757d !important;
        cursor: not-allowed !important;
        transform: none !important;
    }

    /* Agent Labels */
    .agent-label {
        font-size: 0.8rem;
        color: #6c757d;
        margin-bottom: 4px;
        padding-left: 16px;
        font-weight: 500;
    }

    .user-label {
        text-align: right;
        padding-right: 16px;
        color: #6c757d;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Status Badges */
    .status-badge {
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
    }
    
    .status-initial { background-color: #ffc107; color: #000; }
    .status-clarifying { background-color: #17a2b8; color: white; }
    .status-expert { background-color: #6f42c1; color: white; }
    .status-suggestions { background-color: #e83e8c; color: white; }
    .status-planning { background-color: #fd7e14; color: white; }
    .status-completed { background-color: #28a745; color: white; }
    
    /* Agent Activity */
    .agent-activity-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .agent-progress-bar {
        background: linear-gradient(90deg, #0176D3 0%, #005FB8 100%);
        height: 4px;
        border-radius: 2px;
        transition: width 0.3s ease;
    }
    
    .agent-queue-item {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        margin: 0.2rem 0;
        border-radius: 4px;
        transition: all 0.3s ease;
    }
    
    .agent-queue-item:hover {
        background: rgba(0,0,0,0.05);
    }
    
    /* Processing Indicator */
    .processing-indicator {
        position: fixed;
        bottom: 90px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(255, 193, 7, 0.95);
        color: #856404;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        z-index: 999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    /* Animations */
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .processing {
        animation: pulse 2s infinite;
    }
    
    /* Error and Success Messages */
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
        border-left: 4px solid #dc3545;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        border-left: 4px solid #28a745;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    # Unified Agent System
    if 'unified_agent' not in st.session_state:
        st.session_state.unified_agent = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    # Agent system preference
    # Always use Master Orchestrator - no user selection needed
    st.session_state.preferred_agent_system = AgentSystemType.ORCHESTRATOR
    if 'crew_interactive_mode' not in st.session_state:
        st.session_state.crew_interactive_mode = 'auto'  # auto, always, never
    
    # Configuration state
    if 'config_complete' not in st.session_state:
        st.session_state.config_complete = False
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""
    if 'sf_instance_url' not in st.session_state:
        st.session_state.sf_instance_url = ""
    if 'sf_client_id' not in st.session_state:
        st.session_state.sf_client_id = ""
    if 'sf_client_secret' not in st.session_state:
        st.session_state.sf_client_secret = ""
    if 'sf_domain' not in st.session_state:
        st.session_state.sf_domain = "login"
    if 'sf_username' not in st.session_state:
        st.session_state.sf_username = ""
    if 'sf_password' not in st.session_state:
        st.session_state.sf_password = ""
    if 'sf_security_token' not in st.session_state:
        st.session_state.sf_security_token = ""
    if 'auth_method_selected' not in st.session_state:
        st.session_state.auth_method_selected = False
    if 'use_username_password' not in st.session_state:
        st.session_state.use_username_password = False
    if 'last_auth_method' not in st.session_state:
        st.session_state.last_auth_method = ""
    if 'force_ui_config' not in st.session_state:
        st.session_state.force_ui_config = False
    
    # Error tracking
    if 'error_history' not in st.session_state:
        st.session_state.error_history = []
    
    # Legacy compatibility - Master Orchestrator uses modern CrewAI flow
    st.session_state.use_crewai = True  # Always true since we're using Master Orchestrator
    
    # Legacy compatibility - initialize agent as None for old code compatibility
    if 'agent' not in st.session_state:
        st.session_state.agent = None
        
    # Initialize unified agent if configuration is complete
    if st.session_state.config_complete and not st.session_state.unified_agent:
        try:
            st.session_state.unified_agent = UnifiedAgentSystem(
                preferred_system=st.session_state.preferred_agent_system
            )
            st.session_state.conversation_history = st.session_state.unified_agent.get_conversation_history()
        except Exception as e:
            error_response = error_handler.handle_error(e, "Agent initialization")
            formatted_error = format_error_for_ui(error_response)
            st.error(f"{formatted_error['title']}: {formatted_error['message']}")
            st.session_state.unified_agent = None
    
    # Initialize agent activity tracking
    initialize_agent_tracking()
    
    # Initialize pending next phase for automatic progression
    if 'pending_next_phase' not in st.session_state:
        st.session_state.pending_next_phase = None

def get_status_badge(state: str) -> str:
    """Get HTML for status badge based on conversation state."""
    state_mapping = {
        "initial": ("Initial", "status-initial"),
        "clarifying": ("Clarifying Requirements", "status-clarifying"),
        "expert_analysis": ("Expert Analysis", "status-expert"),
        "suggestions_review": ("Reviewing Suggestions", "status-suggestions"),
        "technical_design": ("Technical Architecture", "status-planning"),
        "task_creation": ("Creating Implementation Tasks", "status-planning"),
        "final_review": ("Final Review", "status-suggestions"),
        "planning": ("Ready for Planning", "status-planning"),
        "completed": ("Implementation Plan Created", "status-completed")
    }
    
    label, css_class = state_mapping.get(state, ("Unknown", "status-initial"))
    return f'<span class="status-badge {css_class}">{label}</span>'

def initialize_agent_tracking():
    """Initialize agent activity tracking."""
    if 'agent_activities' not in st.session_state:
        st.session_state.agent_activities = []
    if 'current_agent_start_time' not in st.session_state:
        st.session_state.current_agent_start_time = None

def add_agent_activity(agent_name: str, activity: str, start_time = None):
    """Add or update agent activity tracking."""
    import time
    
    if 'agent_activities' not in st.session_state:
        st.session_state.agent_activities = []
    
    current_time = start_time or time.time()
    
    # Check if this agent is already in the list (update existing)
    for activity_record in st.session_state.agent_activities:
        if activity_record['agent'] == agent_name and activity_record['status'] == 'active':
            activity_record['activity'] = activity
            activity_record['last_update'] = current_time
            return
    
    # Add new agent activity
    st.session_state.agent_activities.append({
        'agent': agent_name,
        'activity': activity,
        'start_time': current_time,
        'last_update': current_time,
        'status': 'active'  # active, completed
    })

def complete_agent_activity(agent_name: str):
    """Mark agent activity as completed and calculate duration."""
    import time
    
    if 'agent_activities' not in st.session_state:
        return
    
    for activity_record in st.session_state.agent_activities:
        if activity_record['agent'] == agent_name and activity_record['status'] == 'active':
            duration = time.time() - activity_record['start_time']
            activity_record['status'] = 'completed'
            activity_record['duration'] = duration
            activity_record['completion_time'] = time.time()
            break
    
    # Clean up old completed activities (older than 30 seconds)
    current_time = time.time()
    st.session_state.agent_activities = [
        activity for activity in st.session_state.agent_activities
        if activity['status'] == 'active' or 
           (activity['status'] == 'completed' and 
            current_time - activity.get('completion_time', 0) < 30)
    ]

def get_agent_status_display() -> str:
    """Get current agent status for display."""
    if not st.session_state.unified_agent:
        return ""
    
    # Try to get state from unified agent system
    try:
        if hasattr(st.session_state.unified_agent, 'get_system_status'):
            status = st.session_state.unified_agent.get_system_status()
            agent_state = status.get('conversation_state', 'initial')
        else:
            agent_state = 'initial'
    except:
        agent_state = 'initial'
    
    if agent_state == "initial" or agent_state == "clarifying":
        return "🤖 **Master Agent** is analyzing your requirements..."
    elif agent_state == "expert_analysis":
        return "🎯 **Expert Agent** is identifying gaps and enhancements..."
    elif agent_state == "suggestions_review":
        return "🤝 **Master Agent** is presenting expert recommendations..."
    elif agent_state == "planning":
        return "📋 **Master Agent** is creating your implementation plan..."
    else:
        return "🤖 **Master Agent** is processing your request..."

def display_conversation_history():
    """Display the conversation history with simple chat styling."""
    if not st.session_state.conversation_history:
        st.markdown(
            '<div style="text-align: center; color: #666; margin: 50px 0;">'
            '💬 Start a conversation by describing your Salesforce requirement'
            '</div>', 
            unsafe_allow_html=True
        )
        return
    
    # Simple message display
    for message in st.session_state.conversation_history:
        if message['role'] == 'user':
            # User message - right aligned, blue background
            st.markdown(f'''
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background: #007bff; color: white; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word;">
                        {message['content']}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        elif message['role'] in ['agent', 'orchestrator']:
            # Agent message - left aligned, gray background  
            st.markdown(f'''
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background: #f1f3f4; color: #333; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word;">
                        🤖 {message['content']}
                    </div>
                </div>
            ''', unsafe_allow_html=True)

def get_agent_info_from_message(message):
    """Get agent information based on message type with improved detection."""
    message_type = message.get('message_type', '')
    message_content = message.get('content', '').lower()
    
    # Improved agent detection based on content and type
    if ('expert' in message_type or 'schema' in message_type or 
        'schema analysis' in message_content or 'object' in message_content):
        return {
            'name': 'Schema Expert',
            'icon': '📋',
            'css_class': 'expert-message'
        }
    elif ('technical_design' in message_type or 'technical' in message_type or
          'architecture' in message_content or 'automation' in message_content):
        return {
            'name': 'Technical Architect',
            'icon': '🏗️',
            'css_class': 'technical-message'
        }
    elif ('task_creation' in message_type or 'dependency' in message_type or
          'implementation' in message_content or 'tasks' in message_content):
        return {
            'name': 'Dependency Resolver',
            'icon': '📊',
            'css_class': 'dependency-message'
        }
    elif 'orchestrator' in message_type or message.get('role') == 'orchestrator':
        return {
            'name': 'Master Orchestrator',
            'icon': '🎯',
            'css_class': 'orchestrator-message'
        }
    elif 'crewai' in message_type or 'crew' in message_content:
        return {
            'name': 'CrewAI Team',
            'icon': '👥',
            'css_class': 'agent-message'
        }
    elif 'error' in message_type or message.get('role') == 'error':
        return {
            'name': 'System',
            'icon': '⚠️',
            'css_class': 'agent-message'
        }
    else:
        return {
            'name': 'Master Agent',
            'icon': '🤖',
            'css_class': 'agent-message'
        }

def display_agent_activities():
    """Display current agent activities with live status updates."""
    import time
    
    if 'agent_activities' not in st.session_state or not st.session_state.agent_activities:
        return
    
    # Only show active agent activities (working status)
    active_agents = [a for a in st.session_state.agent_activities if a['status'] == 'active']
    
    if active_agents:
        for activity in active_agents:
            elapsed = time.time() - activity['start_time']
            
            # Get agent icon
            agent_icon = "🔄"
            if "Schema" in activity['agent'] or "Expert" in activity['agent']:
                agent_icon = "📋"
            elif "Technical" in activity['agent']:
                agent_icon = "🏗️"
            elif "Dependency" in activity['agent']:
                agent_icon = "📊"
            elif "Master" in activity['agent']:
                agent_icon = "🤖"
            
            st.markdown(f'''
                <div class="agent-status">
                    <div class="message-bubble">
                        {agent_icon} <strong>{activity['agent']}</strong> {activity['activity']}
                        <span style="opacity: 0.8; font-size: 0.8rem;">(working for {elapsed:.1f}s)</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        # Auto-refresh while agents are working
        if st.session_state.processing:
            time.sleep(0.5)
            st.rerun()

def display_agent_status_indicators():
    """Display visual indicators for agent status in the sidebar."""
    
    # Define all agents and their info
    agents = [
        {"name": "Master Agent", "icon": "🎯", "key": "master"},
        {"name": "Schema Expert", "icon": "🗄️", "key": "schema"},
        {"name": "Technical Architect", "icon": "🏗️", "key": "technical"},
        {"name": "Dependency Resolver", "icon": "📋", "key": "dependency"}
    ]
    
    # Determine current active agent based on conversation state and activities
    active_agent = get_current_active_agent()
    
    # Custom CSS for agent status indicators
    st.markdown("""
    <style>
    .agent-indicator {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    
    .agent-indicator.active {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        border-color: #1e7e34;
        box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
        animation: pulse-green 2s infinite;
    }
    
    .agent-indicator.inactive {
        background: #f8f9fa;
        color: #6c757d;
        border-color: #dee2e6;
    }
    
    .agent-indicator.pending {
        background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        color: #212529;
        border-color: #e0a800;
        box-shadow: 0 2px 8px rgba(255, 193, 7, 0.3);
    }
    
    .agent-icon {
        margin-right: 8px;
        font-size: 1rem;
    }
    
    @keyframes pulse-green {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .agent-status-container {
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display agent indicators
    st.markdown('<div class="agent-status-container">', unsafe_allow_html=True)
    
    for agent in agents:
        # Determine status
        if active_agent == agent["key"]:
            status_class = "active"
            # Show working time if available
            if st.session_state.get('agent_start_time'):
                elapsed = time.time() - st.session_state.agent_start_time
                status_text = f"🟢 Working ({elapsed:.0f}s)"
            else:
                status_text = "🟢 Active"
        elif is_agent_pending(agent["key"]):
            status_class = "pending" 
            status_text = "🟡 Pending"
        else:
            status_class = "inactive"
            status_text = "⚪ Idle"
        
        # Create the indicator with status text
        indicator_html = f"""
        <div class="agent-indicator {status_class}">
            <span class="agent-icon">{agent["icon"]}</span>
            <span>{agent["name"]}</span>
            <small style="margin-left: auto; opacity: 0.8;">{status_text.split(' ', 1)[1] if ' ' in status_text else ''}</small>
        </div>
        """
        
        st.markdown(indicator_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def update_agent_status(agent_key: str, status: str = "active"):
    """Update the current active agent status for real-time display."""
    if 'current_active_agent' not in st.session_state:
        st.session_state.current_active_agent = None
    
    if 'agent_start_time' not in st.session_state:
        st.session_state.agent_start_time = None
    
    if status == "active":
        st.session_state.current_active_agent = agent_key
        st.session_state.agent_start_time = time.time()
    elif status == "completed":
        st.session_state.current_active_agent = None
        st.session_state.agent_start_time = None

def get_current_active_agent():
    """Determine which agent is currently active based on conversation state and activities."""
    
    # First check real-time CrewAI status
    if st.session_state.get('current_active_agent'):
        return st.session_state.current_active_agent
    
    # First check if any agent is actively working (from agent activities)
    if 'agent_activities' in st.session_state:
        for activity in st.session_state.agent_activities:
            if activity.get('status') == 'active':
                agent_name = activity.get('agent', '').lower()
                if 'master' in agent_name:
                    return 'master'
                elif 'schema' in agent_name or 'expert' in agent_name:
                    return 'schema'
                elif 'technical' in agent_name or 'architect' in agent_name:
                    return 'technical'
                elif 'dependency' in agent_name or 'resolver' in agent_name:
                    return 'dependency'
    
    # If no active activities, determine based on conversation state
    if st.session_state.agent:
        state = st.session_state.agent.conversation_state
        
        if state in ["initial", "clarifying", "final_review", "planning"]:
            return 'master'
        elif state in ["expert_analysis", "suggestions_review"]:
            return 'schema'
        elif state in ["technical_design"]:
            return 'technical'
        elif state in ["task_creation"]:
            return 'dependency'
    
    # Default to master agent
    return 'master'

def is_agent_pending(agent_key):
    """Check if an agent is pending to work next based on the current flow."""
    
    if not st.session_state.agent:
        return False
        
    state = st.session_state.agent.conversation_state
    
    # Define the typical flow progression
    if state == "initial" and agent_key == "schema":
        return True
    elif state == "suggestions_review" and agent_key == "technical":
        return True
    elif state == "technical_design" and agent_key == "dependency":
        return True
    
    return False

def display_sidebar():
    """Display the sidebar with session information and controls."""
    with st.sidebar:
        st.markdown(f'''
        <div style="text-align: center; padding: 0.5rem 0; margin-bottom: 1rem;">
            <div style="font-size: 1.2rem; font-weight: bold; color: #0176D3;">
                ⚡ {Config.APP_NAME}
            </div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 0.2rem;">
                {Config.APP_DESCRIPTION}
            </div>
            <div style="font-size: 0.7rem; color: #888; margin-top: 0.3rem;">
                v{Config.APP_VERSION}
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Configuration status
        st.subheader("🔧 Configuration")
        st.success("✅ OpenAI API configured")
        
        # System Status Display (Automatic - No user selection needed)
        st.subheader("🎯 AI Agent System")
        
        # Brief explanation
        st.caption("🤖 **Automatic Multi-Agent Orchestration** - The system intelligently coordinates specialist agents behind the scenes")
        
        # Display current system status
        if st.session_state.unified_agent:
            system_status = st.session_state.unified_agent.get_system_status()
            active_system = system_status.get('active_system', 'unknown')
            
            if active_system == 'orchestrator':
                st.success("🎯 **Master Orchestrator Active** - Coordinating Schema Expert, Technical Architect, and Dependency Resolver agents")
            elif active_system == 'crewai':
                st.info("🚀 **CrewAI Active** - Multi-agent collaboration system")
            elif active_system == 'legacy':
                st.info("⚙️ **Legacy System Active** - Basic agent system")
            else:
                st.warning(f"🔄 **System Status**: {active_system}")
        else:
            st.info("🔄 **Initializing Master Orchestrator...**")
        
        if st.session_state.use_crewai:
            st.caption("✨ **CrewAI Mode**: True autonomous agent collaboration")
            
            interactive_mode = st.selectbox(
                "Interactive Review",
                options=['auto', 'always', 'never'],
                index=0 if st.session_state.crew_interactive_mode == 'auto' else 
                      1 if st.session_state.crew_interactive_mode == 'always' else 2,
                help="When to enable human review of agent recommendations"
            )
            st.session_state.crew_interactive_mode = interactive_mode
            
        else:
            st.caption("⚙️ **Legacy Mode**: Manual agent orchestration")
        
        # Salesforce connection status
        if st.session_state.unified_agent and hasattr(st.session_state.unified_agent.legacy_system, 'schema_expert'):
            schema_expert = st.session_state.unified_agent.legacy_system.schema_expert
            if hasattr(schema_expert, 'sf_connected') and schema_expert.sf_connected:
                st.success("🟢 Salesforce org connected")
                if st.button("🔍 Test SF Connection"):
                    with st.spinner("Testing Salesforce connection..."):
                        test_result = schema_expert.sf_connector.test_connection()
                        if test_result.get('connected'):
                            org_info = test_result.get('org_info', {})
                            auth_type = test_result.get('auth_type', 'unknown')
                            auth_display = "🎯 Client Credentials" if auth_type == "client_credentials" else "🔄 Username-Password"
                            
                            st.success(f"✅ Connected to: {org_info.get('Name', 'Unknown Org')}")
                            st.info(f"🔐 Auth Method: {auth_display}")
                            st.info(f"📊 Available objects: {test_result.get('sobjects_count', 'Unknown')}")
                        else:
                            st.error(f"❌ Connection failed: {test_result.get('error')}")
            else:
                st.warning("🟡 Salesforce configured but not connected")
        else:
            st.info("🔵 Salesforce will connect when agent starts")
        
        # Reconfigure button
        st.markdown("---")
        if st.button("⚙️ Reconfigure Credentials", help="Change your API keys and Salesforce settings"):
            # Reset configuration
            st.session_state.config_complete = False
            st.session_state.agent = None
            st.session_state.conversation_history = []
            st.session_state.current_session_id = None
            # Reset auth method selection
            st.session_state.auth_method_selected = False
            st.session_state.use_username_password = False
            st.session_state.last_auth_method = ""
            st.rerun()
        
        # Agent Status Visual Indicator
        st.subheader("🤖 Agent Status")
        display_agent_status_indicators()
        
        # Session information
        st.subheader("📊 Session Info")
        if st.session_state.current_session_id:
            st.info(f"**Session ID:** {st.session_state.current_session_id}")
            
            if st.session_state.agent:
                state = st.session_state.agent.conversation_state
                st.markdown(f"**Status:** {get_status_badge(state)}", unsafe_allow_html=True)
                
                # Progress indicator
                progress_mapping = {
                    "initial": 0.10,
                    "clarifying": 0.25,
                    "expert_analysis": 0.40,
                    "suggestions_review": 0.55,
                    "technical_design": 0.70,
                    "task_creation": 0.85,
                    "final_review": 0.95,
                    "planning": 0.90,
                    "completed": 1.0
                }
                progress = progress_mapping.get(state, 0)
                st.progress(progress)
        
        # Session management
        st.subheader("🗂️ Session Management")
        
        if st.button("🆕 New Session", type="primary"):
            st.session_state.agent = None
            st.session_state.conversation_history = []
            st.session_state.current_session_id = None
            st.rerun()
        
        # Load existing sessions
        if st.session_state.agent:
            available_sessions = st.session_state.agent.memory_manager.get_all_sessions()
            if available_sessions:
                st.selectbox(
                    "📁 Load Previous Session",
                    options=[""] + available_sessions,
                    key="session_selector",
                    help="Select a previous session to continue"
                )
                
                if st.session_state.session_selector and st.session_state.session_selector != st.session_state.current_session_id:
                    if st.button("🔄 Load Selected Session"):
                        load_session(st.session_state.session_selector)
        
        # Export options
        if st.session_state.conversation_history:
            st.subheader("📤 Export")
            
            # Export conversation with safe serialization
            conversation_json = safe_json_serialize(st.session_state.conversation_history)
            st.download_button(
                label="💾 Download Conversation",
                data=conversation_json,
                file_name=f"conversation_{st.session_state.current_session_id}.json",
                mime="application/json"
            )
            
            # Export implementation plan if available
            if st.session_state.agent and st.session_state.agent.conversation_state == "completed":
                if hasattr(st.session_state.agent.memory_manager, 'implementation_plan') and st.session_state.agent.memory_manager.implementation_plan:
                    plan_json = json.dumps(st.session_state.agent.memory_manager.implementation_plan, indent=2)
                    st.download_button(
                        label="📋 Download Implementation Plan",
                        data=plan_json,
                        file_name=f"implementation_plan_{st.session_state.current_session_id}.json",
                        mime="application/json"
                    )

def display_expert_suggestions_panel():
    """Display expert suggestions in a special panel if available."""
    if (st.session_state.agent and 
        hasattr(st.session_state.agent, 'expert_suggestions') and 
        st.session_state.agent.expert_suggestions and
        st.session_state.agent.conversation_state == "suggestions_review"):
        
        st.markdown("### 💡 Expert Suggestions Panel")
        
        expert_analysis = st.session_state.agent.expert_suggestions
        
        # Create expandable sections for different types of suggestions
        col1, col2 = st.columns(2)
        
        with col1:
            if expert_analysis.get("requirement_gaps"):
                with st.expander("🔍 Missing Requirements", expanded=True):
                    for gap in expert_analysis["requirement_gaps"]:
                        st.markdown(f"• {gap}")
            
            if expert_analysis.get("best_practices"):
                with st.expander("⭐ Best Practices", expanded=False):
                    for practice in expert_analysis["best_practices"]:
                        st.markdown(f"• {practice}")
        
        with col2:
            if expert_analysis.get("suggested_enhancements"):
                with st.expander("🚀 Value Enhancements", expanded=True):
                    for enhancement in expert_analysis["suggested_enhancements"]:
                        st.markdown(f"• {enhancement}")
            
            if expert_analysis.get("implementation_considerations"):
                with st.expander("⚙️ Implementation Notes", expanded=False):
                    for consideration in expert_analysis["implementation_considerations"]:
                        st.markdown(f"• {consideration}")
        
        # Note: User can respond via chat instead of buttons
        st.markdown("#### 💬 **Please respond in the chat below with your preference**")

def load_session(session_id: str):
    """Load an existing session."""
    try:
        agent = SalesforceRequirementDeconstructorAgent(session_id)
        st.session_state.agent = agent
        st.session_state.current_session_id = session_id
        st.session_state.conversation_history = agent.get_conversation_history()
        st.success(f"Loaded session: {session_id}")
        st.rerun()
    except Exception as e:
        st.error(f"Error loading session: {e}")

@safe_execute("Processing user input")
def process_user_input(user_input: str):
    """
    Process user input using the unified agent system.
    Handles both CrewAI and legacy systems with error recovery.
    """
    
    if not user_input.strip():
        st.warning("Please enter a valid requirement or message.")
        return
    
    # Ensure unified agent is initialized
    if not st.session_state.unified_agent:
        try:
            st.session_state.unified_agent = UnifiedAgentSystem(
                preferred_system=st.session_state.preferred_agent_system
            )
        except Exception as e:
            error_response = error_handler.handle_error(e, "Agent initialization")
            formatted_error = format_error_for_ui(error_response)
            st.error(f"{formatted_error['title']}: {formatted_error['message']}")
            return
    
    # Show processing indicator
    st.session_state.processing = True
    
    try:
        # Process with unified agent system
        result = st.session_state.unified_agent.process_user_input(user_input)
        
        # Update conversation history
        st.session_state.conversation_history = st.session_state.unified_agent.get_conversation_history()
        
        # Handle results
        if result.get('success'):
            # Display success response based on system type
            system_type = result.get('system', 'unknown')
            
            if system_type == 'orchestrator':
                # Orchestrator responses are already in conversation history
                # Check if there's an implementation plan to display
                if result.get('implementation_plan'):
                    display_implementation_plan(result.get('implementation_plan', {}))
                elif result.get('plan_approved'):
                    st.balloons()  # Celebrate completion
                    
            elif system_type == 'crewai':
                display_crewai_results(result.get('result', {}))
            else:
                # Handle legacy system response
                pass  # Legacy responses are already in conversation history
        else:
            # Handle errors
            formatted_error = format_error_for_ui(result)
            st.markdown(f'''
                <div class="error-message">
                    {formatted_error['title']}<br>
                    <strong>Message:</strong> {formatted_error['message']}<br>
                    <strong>Suggestion:</strong> {formatted_error['suggestion']}
                </div>
            ''', unsafe_allow_html=True)
            
            # Add error to session history for tracking
            st.session_state.error_history.append(result)
            
    except Exception as e:
        # Handle unexpected errors
        error_response = error_handler.handle_error(e, "User input processing")
        formatted_error = format_error_for_ui(error_response)
        st.error(f"{formatted_error['title']}: {formatted_error['message']}")
        
    finally:
        st.session_state.processing = False

def process_user_input_crewai(user_input: str, use_interactive: bool = None):
    """
    Process user input using CrewAI crew.
    This is the new implementation with authentic agentic collaboration.
    """
    
    if not user_input.strip():
        st.warning("Please enter a valid requirement or message.")
        return
    
    # Show processing indicator
    st.session_state.processing = True
    
    try:
        # Add user message to conversation history immediately
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat(),
            'message_type': 'requirement'
        }
        
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
        
        st.session_state.conversation_history.append(user_message)
        
        # Determine if we should use interactive mode based on settings
        if use_interactive is None:
            interactive_setting = st.session_state.get('crew_interactive_mode', 'auto')
            if interactive_setting == 'always':
                use_interactive = True
            elif interactive_setting == 'never':
                use_interactive = False
            else:  # auto
                use_interactive = is_complex_requirement(user_input)
        
        # Show crew launch message
        crew_type = "Interactive" if use_interactive else "Standard"
        st.info(f"🚀 Launching {crew_type} Salesforce Implementation Crew...")
        
        if use_interactive:
            st.info("💡 Complex requirement detected - human review will be available")
        
        # Execute CrewAI analysis with progress tracking
        progress_placeholder = st.empty()
        
        with st.spinner("🤖 Agents are collaborating on your requirement..."):
            try:
                # Initialize status tracking
                update_agent_status("schema", "active")
                
                # Show initial progress
                progress_placeholder.info("🗄️ **Schema Expert** is analyzing requirements...")
                
                result = analyze_salesforce_requirement(
                    requirement=user_input,
                    interactive=use_interactive,
                    user_context=st.session_state.get('user_context', {}),
                    org_context=st.session_state.get('org_context', {})
                )
                
                # Clear progress and mark completion
                progress_placeholder.empty()
                update_agent_status("", "completed")
                
                if not result:
                    st.error("❌ CrewAI returned empty result")
                    return
                    
            except Exception as e:
                progress_placeholder.empty()
                update_agent_status("", "completed")
                st.error(f"❌ CrewAI execution failed: {str(e)}")
                import traceback
                st.error("Full error:")
                st.code(traceback.format_exc())
                return
        
        # Handle results
        if result['success']:
            # Convert result to JSON-serializable format before storing
            serializable_result = make_json_serializable(result)
            
            # Add crew result to conversation history
            crew_message = {
                'role': 'agent',
                'content': f"✅ **Implementation Plan Complete!**\n\nThe {crew_type} crew has successfully analyzed your requirement and created a comprehensive implementation plan.",
                'timestamp': datetime.now().isoformat(),
                'message_type': 'crew_result',
                'crew_data': serializable_result
            }
            st.session_state.conversation_history.append(crew_message)
            
            # Display results
            display_crewai_results(result)
            
            # Success message
            st.success("🎉 Implementation plan created successfully!")
            st.balloons()
            
        else:
            # Handle error with better messaging
            error_type = result.get('error_type', 'general')
            error_msg = result.get('error', 'Unknown error')
            suggestion = result.get('suggestion', '')
            
            if error_type == 'rate_limit':
                st.error("🚦 **Rate Limit Exceeded**")
                st.warning(error_msg)
                if suggestion:
                    st.info(f"💡 **Suggestion**: {suggestion}")
            elif error_type == 'token_limit':
                st.error("📝 **Request Too Large**") 
                st.warning(error_msg)
                if suggestion:
                    st.info(f"💡 **Suggestion**: {suggestion}")
            elif result.get('timeout'):
                st.error("⏰ **Execution Timeout**")
                st.warning(error_msg)
                if suggestion:
                    st.info(f"💡 **Suggestion**: {suggestion}")
            else:
                st.error(f"❌ **Analysis Failed**: {error_msg}")
            
            # Add error to conversation history
            error_message = {
                'role': 'agent', 
                'content': f"❌ **Analysis Failed**\n\n{error_msg}\n\n{suggestion if suggestion else ''}",
                'timestamp': datetime.now().isoformat(),
                'message_type': 'error'
            }
            st.session_state.conversation_history.append(error_message)
    
    except Exception as e:
        error_message = {
            'role': 'agent',
            'content': f"❌ **System Error**\n\nAn unexpected error occurred: {str(e)}",
            'timestamp': datetime.now().isoformat(),
            'message_type': 'system_error'
        }
        st.session_state.conversation_history.append(error_message)
        st.error(f"System error: {str(e)}")
        
    finally:
        st.session_state.processing = False

def process_user_input_legacy(user_input: str):
    """
    Process user input using the legacy agent system.
    This maintains compatibility with the old manual orchestration.
    """
    
    if not user_input.strip():
        st.warning("Please enter a valid requirement or message.")
        return
    
    # Initialize agent if not already done
    if not st.session_state.agent:
        st.session_state.agent = SalesforceRequirementDeconstructorAgent()
        st.session_state.current_session_id = st.session_state.agent.get_session_id()
    
    # Show processing indicator
    st.session_state.processing = True
    
    try:
        # Add user message to conversation history
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat(),
            'message_type': 'requirement'
        }
        
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
        
        st.session_state.conversation_history.append(user_message)
        
        # Process through legacy agent system
        st.info("⚙️ Processing with legacy agent system...")
        
        with st.spinner("Processing your requirement..."):
            result = st.session_state.agent.process_user_input(user_input)
        
        # Update conversation history from agent
        st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
        
        # Handle result
        if result.get('type') == 'implementation_plan':
            st.success("🎉 Implementation plan created successfully!")
        elif result.get('type') == 'expert_suggestions':
            st.success("💡 Expert suggestions ready for your review!")
        elif result.get('type') == 'error':
            st.error(f"Error: {result.get('message', 'Unknown error')}")
        else:
            st.info("Agent response processed.")
    
    except Exception as e:
        error_message = {
            'role': 'agent',
            'content': f"❌ **Legacy System Error**\n\nAn error occurred: {str(e)}",
            'timestamp': datetime.now().isoformat(),
            'message_type': 'system_error'
        }
        st.session_state.conversation_history.append(error_message)
        st.error(f"Legacy system error: {str(e)}")
        
    finally:
        st.session_state.processing = False

def display_implementation_plan(plan_data: Dict[str, Any]):
    """Display implementation plan from orchestrator results."""
    if not plan_data:
        return
    
    st.success("📋 **Implementation Plan Generated!**")
    
    # Show plan summary
    project_summary = plan_data.get('project_summary', {})
    if project_summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Timeline", project_summary.get('duration', 'TBD'))
        with col2:
            st.metric("Total Effort", project_summary.get('total_effort', 'TBD'))
        with col3:
            st.metric("Team Size", project_summary.get('team_size', 'TBD'))
    
    # Show tasks breakdown
    tasks = plan_data.get('tasks', [])
    if tasks:
        st.subheader(f"📊 Implementation Tasks ({len(tasks)} total)")
        
        # Group tasks by role
        admin_tasks = [t for t in tasks if t.get('role') == 'Admin']
        dev_tasks = [t for t in tasks if t.get('role') == 'Developer']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**👤 Admin Tasks: {len(admin_tasks)}**")
            for task in admin_tasks[:3]:  # Show first 3
                st.write(f"• {task.get('title', 'Untitled')} ({task.get('effort', 'TBD')})")
            if len(admin_tasks) > 3:
                st.write(f"• ... and {len(admin_tasks) - 3} more")
                
        with col2:
            st.write(f"**👨‍💻 Developer Tasks: {len(dev_tasks)}**")
            for task in dev_tasks[:3]:  # Show first 3
                st.write(f"• {task.get('title', 'Untitled')} ({task.get('effort', 'TBD')})")
            if len(dev_tasks) > 3:
                st.write(f"• ... and {len(dev_tasks) - 3} more")
    
    # Show risks and success criteria
    risks = plan_data.get('key_risks', [])
    success_criteria = plan_data.get('success_criteria', [])
    
    if risks or success_criteria:
        col1, col2 = st.columns(2)
        
        if risks:
            with col1:
                st.write("**⚠️ Key Risks:**")
                for risk in risks[:3]:
                    st.write(f"• {risk}")
                    
        if success_criteria:
            with col2:
                st.write("**✅ Success Criteria:**")
                for criterion in success_criteria[:3]:
                    st.write(f"• {criterion}")

def display_crewai_results(result: dict):
    """Display CrewAI crew results in Streamlit."""
    
    if not result.get('success'):
        st.error("Crew execution failed")
        return
    
    outputs = result.get('outputs', {})
    crew_type = result.get('crew_type', 'standard')
    
    # Show agent collaboration summary
    with st.expander("👥 Agent Collaboration Summary", expanded=True):
        st.markdown("### How the agents worked together:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🗄️ Schema Expert**")
            if 'schema_analysis' in outputs:
                st.success("✅ Analyzed schema requirements")
            else:
                st.info("⏳ Schema analysis in progress...")
        
        with col2:
            st.markdown("**🏗️ Technical Architect**") 
            if 'technical_design' in outputs:
                st.success("✅ Created technical design")
            else:
                st.info("⏳ Technical design pending...")
        
        with col3:
            st.markdown("**📋 Dependency Resolver**")
            if 'implementation_plan' in outputs:
                st.success("✅ Generated implementation plan")
            else:
                st.info("⏳ Implementation planning pending...")
    
    # Show detailed results in separate expanders (not nested)
    if 'schema_analysis' in outputs:
        with st.expander("📋 Schema Analysis Details"):
            st.json(outputs['schema_analysis'])
    
    if 'technical_design' in outputs:
        with st.expander("🔧 Technical Design Details"):
            st.json(outputs['technical_design'])
    
    if 'implementation_plan' in outputs:
        with st.expander("📊 Implementation Plan Details"):
            st.json(outputs['implementation_plan'])
    
    # Show key results
    with st.expander("🎯 Implementation Summary", expanded=True):
        if 'implementation_plan' in outputs:
            plan = outputs['implementation_plan']
            
            # Extract key metrics if available
            if isinstance(plan, dict):
                project_overview = plan.get('project_overview', {})
                
                if project_overview:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        effort = project_overview.get('total_estimated_effort', 'Not specified')
                        st.metric("Total Effort", effort)
                    
                    with col2:
                        timeline = project_overview.get('critical_path_duration', 'Not specified')
                        st.metric("Timeline", timeline)
                    
                    with col3:
                        team_size = project_overview.get('team_size_recommendation', 'Not specified')
                        st.metric("Team Size", team_size)
                
                # Show tasks summary
                tasks = plan.get('implementation_tasks', [])
                if tasks:
                    st.markdown(f"**📋 {len(tasks)} implementation tasks created**")
                    
                    # Show first few tasks as preview
                    preview_tasks = tasks[:3] if len(tasks) > 3 else tasks
                    for i, task in enumerate(preview_tasks, 1):
                        if isinstance(task, dict):
                            title = task.get('title', f'Task {i}')
                            effort = task.get('estimated_effort', 'TBD')
                            st.write(f"{i}. **{title}** - {effort}")
                    
                    if len(tasks) > 3:
                        st.write(f"... and {len(tasks) - 3} more tasks")
        else:
            st.info("Implementation plan is being generated...")
    
    # Download buttons for outputs
    if outputs:
        st.markdown("### 📥 Download Results")
        
        cols = st.columns(len(outputs))
        
        for i, (output_name, output_data) in enumerate(outputs.items()):
            with cols[i]:
                file_name = f"{output_name.replace('_', '-')}.json"
                
                if isinstance(output_data, dict):
                    data_str = json.dumps(output_data, indent=2)
                else:
                    data_str = str(output_data)
                
                st.download_button(
                    f"📄 {output_name.replace('_', ' ').title()}",
                    data=data_str,
                    file_name=file_name,
                    mime="application/json",
                    key=f"download_{output_name}_btn"
                )

def show_configuration_popup():
    """Show configuration popup to collect API keys and Salesforce credentials."""
    # Custom CSS for the configuration page
    st.markdown("""
    <style>
        .config-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            margin: 1rem 0;
            color: white;
        }
        .config-form {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .stTextInput > div > div > input {
            border-radius: 8px;
        }
        .stSelectbox > div > div > div {
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="config-container">
        <div style="text-align: center;">
            <h1>🔧 Salesforce AI Agent Configuration</h1>
            <p style="font-size: 1.1rem; opacity: 0.9;">Please provide your API credentials to get started</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("🤖 OpenAI Configuration")
            openai_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=st.session_state.openai_api_key,
                help="Your OpenAI API key for AI agent functionality",
                key="openai_key_input"
            )
            
            st.subheader("⚡ Salesforce Configuration")
            
            # Auth method selection (outside form for immediate response)
            auth_method = st.radio(
                "Authentication Method",
                options=["Client Credentials (Recommended)", "Username-Password (Legacy)"],
                index=0 if not st.session_state.get('auth_method_selected') else (1 if st.session_state.get('use_username_password', False) else 0),
                help="Client Credentials is more secure and requires only 3 fields",
                key="auth_method_radio"
            )
            
            use_client_creds = auth_method.startswith("Client Credentials")
            
            # Store auth method preference in session state
            if 'auth_method_selected' not in st.session_state:
                st.session_state.auth_method_selected = False
            if st.session_state.auth_method_radio != st.session_state.get('last_auth_method', ''):
                st.session_state.last_auth_method = st.session_state.auth_method_radio
                st.session_state.use_username_password = not use_client_creds
                st.session_state.auth_method_selected = True
            
            if use_client_creds:
                st.info("💡 Using Client Credentials Flow - only 3 fields needed!")
            else:
                st.warning("⚠️ Using Username-Password Flow - requires 6 fields")
            
            with st.form("config_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    sf_instance = st.text_input(
                        "Instance URL",
                        value=st.session_state.sf_instance_url,
                        placeholder="https://your-instance.salesforce.com",
                        help="Your Salesforce instance URL"
                    )
                    
                    sf_client_id = st.text_input(
                        "Client ID",
                        value=st.session_state.sf_client_id,
                        help="Connected App Client ID"
                    )
                    
                    sf_client_secret = st.text_input(
                        "Client Secret",
                        type="password",
                        value=st.session_state.sf_client_secret,
                        help="Connected App Client Secret"
                    )
                
                with col_b:
                    sf_domain = st.selectbox(
                        "Domain",
                        options=["login", "test"],
                        index=0 if st.session_state.sf_domain == "login" else 1,
                        help="Use 'login' for production, 'test' for sandbox"
                    )
                    
                    # Username-Password fields (only shown for legacy method)
                    if not use_client_creds:
                        st.markdown("**Username-Password Credentials:**")
                        sf_username = st.text_input(
                            "Username",
                            value=st.session_state.get('sf_username', ''),
                            help="Your Salesforce username"
                        )
                        
                        sf_password = st.text_input(
                            "Password",
                            type="password",
                            value=st.session_state.get('sf_password', ''),
                            help="Your Salesforce password"
                        )
                        
                        sf_security_token = st.text_input(
                            "Security Token",
                            type="password",
                            value=st.session_state.get('sf_security_token', ''),
                            help="Your Salesforce security token"
                        )
                    else:
                        sf_username = ""
                        sf_password = ""
                        sf_security_token = ""
                
                st.markdown("---")
                
                with st.expander("📚 Setup Instructions", expanded=False):
                    st.markdown("""
                    **OpenAI API Key:**
                    1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
                    2. Create a new API key
                    3. Copy and paste it above
                    
                    **Salesforce Connected App:**
                    1. In Salesforce: Setup → App Manager → New Connected App
                    2. Basic Information: Fill app name, email, etc.
                    3. API (Enable OAuth Settings):
                       - ✅ Enable OAuth Settings
                       - ✅ Enable Client Credentials Flow
                       - Callback URL: `http://localhost` (not used)
                       - Scopes: `api`, `refresh_token`, `web`
                    4. Save and get Client ID & Secret
                    """)
                
                submitted = st.form_submit_button("🚀 Connect & Validate", use_container_width=True, type="primary")
                
                # App information footer
                st.markdown(f"""
                <div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee;">
                    <small style="color: #666;">
                        {Config.APP_NAME} v{Config.APP_VERSION}
                    </small>
                </div>
                """, unsafe_allow_html=True)
                
                if submitted:
                    return validate_and_save_config(
                        openai_key, sf_instance, sf_client_id, sf_client_secret, sf_domain,
                        use_client_creds, sf_username, sf_password, sf_security_token
                    )
    
    return False

@safe_execute("Configuration validation and saving")
def validate_and_save_config(openai_key, sf_instance, sf_client_id, sf_client_secret, sf_domain, 
                           use_client_creds, sf_username, sf_password, sf_security_token):
    """Validate the provided configuration and save if successful with improved error handling."""
    
    validation_errors = []
    
    with st.spinner("🔍 Validating configurations..."):
        # Validate OpenAI
        try:
            openai_valid = validate_openai_config(openai_key)
            if not openai_valid:
                validation_errors.append("OpenAI API key validation failed")
        except Exception as e:
            error_response = error_handler.handle_error(e, "OpenAI validation")
            formatted_error = format_error_for_ui(error_response)
            validation_errors.append(f"OpenAI validation error: {formatted_error['message']}")
        
        # Validate Salesforce
        try:
            sf_valid = validate_salesforce_config(
                sf_instance, sf_client_id, sf_client_secret, sf_domain,
                use_client_creds, sf_username, sf_password, sf_security_token
            )
            if not sf_valid:
                validation_errors.append("Salesforce configuration validation failed")
        except Exception as e:
            error_response = error_handler.handle_error(e, "Salesforce validation")
            formatted_error = format_error_for_ui(error_response)
            validation_errors.append(f"Salesforce validation error: {formatted_error['message']}")
        
        # Display validation results
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ {error}")
            return False
        
        # Save to session state if validation successful
        try:
            st.session_state.openai_api_key = openai_key
            st.session_state.sf_instance_url = sf_instance
            st.session_state.sf_client_id = sf_client_id
            st.session_state.sf_client_secret = sf_client_secret
            st.session_state.sf_domain = sf_domain
            st.session_state.sf_username = sf_username
            st.session_state.sf_password = sf_password
            st.session_state.sf_security_token = sf_security_token
            st.session_state.config_complete = True
            
            st.success("✅ All configurations validated successfully!")
            st.balloons()
            time.sleep(1)
            st.rerun()
            return True
        except Exception as e:
            error_response = error_handler.handle_error(e, "Saving configuration")
            formatted_error = format_error_for_ui(error_response)
            st.error(f"❌ Error saving configuration: {formatted_error['message']}")
            return False

@safe_execute("Configuration validation", fallback_result=["Validation system error"])
def validate_configuration_at_startup():
    """
    Validate configuration at application startup with caching and improved error handling.
    """
    # Check cache first to avoid repeated validation
    cache_key = f"validation_{hash(str(st.session_state.get('openai_api_key', ''))[:10] + str(st.session_state.get('sf_client_id', ''))[:10])}"
    
    if hasattr(st.session_state, 'validation_cache') and cache_key in st.session_state.validation_cache:
        cached_result = st.session_state.validation_cache[cache_key]
        # Check if cache is still valid (less than 5 minutes old)
        if (datetime.now() - datetime.fromisoformat(cached_result['timestamp'])).seconds < 300:
            return cached_result['errors']
    
    validation_errors = []
    
    # Validate OpenAI configuration
    try:
        import openai
        if hasattr(st.session_state, 'openai_api_key') and st.session_state.openai_api_key:
            # Test OpenAI connection with a simple call
            try:
                client = openai.OpenAI(api_key=st.session_state.openai_api_key)
                # Make a minimal test call with timeout
                response = client.models.list()
                logging.info("✅ OpenAI API validation successful")
            except openai.AuthenticationError:
                validation_errors.append("OpenAI API key is invalid")
            except openai.RateLimitError:
                validation_errors.append("OpenAI API rate limit exceeded")
            except Exception as e:
                validation_errors.append(f"OpenAI API validation failed: {str(e)}")
        else:
            validation_errors.append("OpenAI API key not configured")
    except ImportError:
        validation_errors.append("OpenAI library not installed")
    
    # Validate Salesforce configuration
    try:
        from agents.salesforce_connector import SalesforceConnector
        if (hasattr(st.session_state, 'sf_client_id') and st.session_state.sf_client_id and
            hasattr(st.session_state, 'sf_client_secret') and st.session_state.sf_client_secret):
            
            # Test Salesforce connection with timeout
            try:
                connector = SalesforceConnector()
                test_result = connector.test_connection()
                if test_result.get('success'):
                    logging.info("✅ Salesforce connection validation successful")
                else:
                    validation_errors.append(f"Salesforce connection failed: {test_result.get('error', 'Unknown error')}")
            except Exception as e:
                validation_errors.append(f"Salesforce validation failed: {str(e)}")
        else:
            validation_errors.append("Salesforce credentials not properly configured")
    except ImportError:
        validation_errors.append("Salesforce connector not available")
    
    # Cache the results
    if not hasattr(st.session_state, 'validation_cache'):
        st.session_state.validation_cache = {}
    
    st.session_state.validation_cache[cache_key] = {
        'errors': validation_errors,
        'timestamp': datetime.now().isoformat()
    }
    
    return validation_errors

def display_startup_validation_results(validation_errors):
    """
    Display validation results in the sidebar.
    """
    with st.sidebar:
        st.subheader("🔍 Startup Validation")
        
        if validation_errors:
            st.error("❌ Configuration Issues Detected:")
            for error in validation_errors:
                st.error(f"• {error}")
            
            st.warning("⚠️ Some features may not work properly. Please check your configuration.")
            
            if st.button("🔄 Retry Validation"):
                st.rerun()
        else:
            st.success("✅ All systems validated successfully")

def _validate_env_config():
    """Validate environment variables for test mode."""
    from config import Config
    
    # Check OpenAI key
    if not Config.OPENAI_API_KEY:
        return False
    
    # Check Salesforce config (either Client Credentials or Username-Password)
    has_client_creds = all([
        Config.SALESFORCE_INSTANCE_URL,
        Config.SALESFORCE_CLIENT_ID,
        Config.SALESFORCE_CLIENT_SECRET
    ])
    
    has_username_password = all([
        Config.SALESFORCE_INSTANCE_URL,
        Config.SALESFORCE_CLIENT_ID,
        Config.SALESFORCE_CLIENT_SECRET,
        Config.SALESFORCE_USERNAME,
        Config.SALESFORCE_PASSWORD,
        Config.SALESFORCE_SECURITY_TOKEN
    ])
    
    return has_client_creds or has_username_password

def _load_config_from_env():
    """Load configuration from environment variables into session state."""
    from config import Config
    
    # Load from environment
    st.session_state.openai_api_key = Config.OPENAI_API_KEY
    st.session_state.sf_instance_url = Config.SALESFORCE_INSTANCE_URL
    st.session_state.sf_client_id = Config.SALESFORCE_CLIENT_ID
    st.session_state.sf_client_secret = Config.SALESFORCE_CLIENT_SECRET
    st.session_state.sf_domain = Config.SALESFORCE_DOMAIN
    st.session_state.sf_username = Config.SALESFORCE_USERNAME or ""
    st.session_state.sf_password = Config.SALESFORCE_PASSWORD or ""
    st.session_state.sf_security_token = Config.SALESFORCE_SECURITY_TOKEN or ""

def validate_openai_config(api_key):
    """Validate OpenAI API key."""
    if not api_key:
        st.error("OpenAI API key is required")
        return False
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        # Test with a simple API call
        response = client.models.list()
        st.success("✅ OpenAI API key is valid")
        return True
    except Exception as e:
        st.error(f"❌ OpenAI validation failed: {str(e)}")
        return False

def validate_salesforce_config(instance_url, client_id, client_secret, domain, 
                             use_client_creds, username, password, security_token):
    """Validate Salesforce configuration using direct API call."""
    
    # Check required fields based on auth method
    if use_client_creds:
        if not all([instance_url, client_id, client_secret]):
            st.error("Instance URL, Client ID, and Client Secret are required for Client Credentials Flow")
            return False
    else:
        if not all([instance_url, client_id, client_secret, username, password, security_token]):
            st.error("All fields are required for Username-Password Flow")
            return False
    
    try:
        import requests
        
        # Determine auth URL based on domain
        if domain == "test":
            auth_base_url = "https://test.salesforce.com"
        else:
            auth_base_url = "https://login.salesforce.com"
        
        auth_url = f"{auth_base_url}/services/oauth2/token"
        
        # Choose authentication method
        if use_client_creds:
            # Test Client Credentials Flow
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            auth_method_name = "Client Credentials"
        else:
            # Test Username-Password Flow
            auth_data = {
                'grant_type': 'password',
                'client_id': client_id,
                'client_secret': client_secret,
                'username': username,
                'password': password + security_token
            }
            auth_method_name = "Username-Password"
        
        # Make authentication request
        response = requests.post(auth_url, data=auth_data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            
            # For username-password flow, use the returned instance URL
            test_instance_url = token_data.get('instance_url', instance_url)
            
            # Test API access with the token
            api_url = f"{test_instance_url}/services/data/v58.0/sobjects"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            api_response = requests.get(api_url, headers=headers, timeout=30)
            
            if api_response.status_code == 200:
                # Get org info
                org_query_url = f"{test_instance_url}/services/data/v58.0/query"
                org_query = "SELECT Id, Name, OrganizationType FROM Organization LIMIT 1"
                org_response = requests.get(
                    org_query_url, 
                    headers=headers, 
                    params={'q': org_query},
                    timeout=30
                )
                
                if org_response.status_code == 200:
                    org_data = org_response.json()
                    if org_data.get('records'):
                        org_name = org_data['records'][0].get('Name', 'Unknown')
                        st.success(f"✅ Connected to Salesforce org: {org_name} (using {auth_method_name} Flow)")
                    else:
                        st.success(f"✅ Connected to Salesforce (using {auth_method_name} Flow)")
                    return True
                else:
                    st.error("❌ Connected but unable to query org information")
                    return False
            else:
                st.error(f"❌ API access failed: {api_response.status_code}")
                return False
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('error_description', error_data.get('error', response.text))
            
            if use_client_creds and "not supported" in error_msg.lower():
                st.error("❌ Client Credentials Flow is not enabled on your Connected App. Please enable it or use Username-Password Flow.")
            else:
                st.error(f"❌ {auth_method_name} authentication failed: {error_msg}")
            return False
            
    except requests.exceptions.Timeout:
        st.error("❌ Connection timeout - please check your network and Salesforce instance URL")
        return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection error - please check your network and Salesforce instance URL")
        return False
    except Exception as e:
        st.error(f"❌ Salesforce validation failed: {str(e)}")
        return False

def make_json_serializable(obj):
    """
    Convert CrewOutput and other non-serializable objects to JSON-serializable format.
    """
    # Handle CrewOutput specifically
    if CrewOutput and isinstance(obj, CrewOutput):
        return {
            'type': 'CrewOutput',
            'raw': str(obj.raw) if hasattr(obj, 'raw') and obj.raw else None,
            'pydantic': str(obj.pydantic) if hasattr(obj, 'pydantic') and obj.pydantic else None,
            'json_dict': getattr(obj, 'json_dict', None),
            'tasks_output': [make_json_serializable(task) for task in getattr(obj, 'tasks_output', [])]
        }
    elif hasattr(obj, '__dict__'):
        # Handle other objects with attributes
        if hasattr(obj, 'raw') and hasattr(obj, 'pydantic'):
            # This is likely a CrewOutput-like object
            return {
                'type': 'CrewOutput',
                'raw': str(obj.raw) if obj.raw else None,
                'pydantic': str(obj.pydantic) if obj.pydantic else None,
                'json_dict': getattr(obj, 'json_dict', None),
                'tasks_output': [make_json_serializable(task) for task in getattr(obj, 'tasks_output', [])]
            }
        else:
            # Generic object with __dict__
            return {key: make_json_serializable(value) for key, value in obj.__dict__.items()}
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Fallback: convert to string
        return str(obj)

def safe_json_serialize(data):
    """
    Safely serialize data to JSON, handling CrewOutput and other non-serializable objects.
    """
    try:
        # First try normal JSON serialization
        return json.dumps(data, indent=2)
    except TypeError:
        # If that fails, convert to serializable format first
        serializable_data = make_json_serializable(data)
        return json.dumps(serializable_data, indent=2)

def display_real_time_agent_activity():
    """Display real-time agent activity in an expandable section within chat."""
    
    # Only show if agents are processing
    if not st.session_state.processing:
        return
    
    # Create expandable section for agent activity
    with st.expander("🔍 **Live Agent Activity** (Click to see what's happening behind the scenes)", expanded=False):
        
        # Show current active agent
        if 'current_active_agent' in st.session_state and st.session_state.current_active_agent:
            agent = st.session_state.current_active_agent
            start_time = st.session_state.get('agent_start_time', time.time())
            elapsed = time.time() - start_time
            
            # Get agent details
            agent_details = {
                'schema': {'name': '🗄️ Schema Expert', 'color': '#0176D3', 'description': 'Analyzing Salesforce schema and designing data model'},
                'technical': {'name': '🏗️ Technical Architect', 'color': '#28a745', 'description': 'Creating technical architecture and automation flows'},
                'dependency': {'name': '📋 Dependency Resolver', 'color': '#ffc107', 'description': 'Generating implementation plan and task dependencies'},
                'master': {'name': '🤖 Master Agent', 'color': '#6f42c1', 'description': 'Orchestrating the overall analysis process'}
            }
            
            current_agent = agent_details.get(agent, {'name': f'🤖 {agent.title()} Agent', 'color': '#6c757d', 'description': 'Processing your request'})
            
            # Display current agent status
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {current_agent['color']} 0%, {current_agent['color']}dd 100%); 
                        color: white; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.5rem;">{current_agent['name'].split(' ')[0]}</span>
                    <div>
                        <div style="font-weight: bold; font-size: 1.1rem;">{current_agent['name']}</div>
                        <div style="font-size: 0.9rem; opacity: 0.9;">{current_agent['description']}</div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 0.9rem;">
                        ⏱️ Working for <strong>{elapsed:.1f}s</strong>
                    </div>
                    <div style="font-size: 0.8rem; opacity: 0.8;">
                        🔄 Processing...
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress bar
            progress = min(elapsed / 60, 1.0)  # 60s max
            st.progress(progress, text=f"Progress: {progress*100:.1f}%")
            
            # Show memory operations if available
            if 'agent_activities' in st.session_state:
                st.markdown("**📊 Recent Activities:**")
                for activity in st.session_state.agent_activities[-3:]:  # Show last 3 activities
                    if activity.get('status') == 'completed':
                        duration = activity.get('duration', 0)
                        st.markdown(f"✅ **{activity['agent']}** completed in {duration:.1f}s")
                    elif activity.get('status') == 'active':
                        st.markdown(f"🔄 **{activity['agent']}** is working...")
        
        # Show agent queue (what's coming next)
        st.markdown("**📋 Agent Queue:**")
        
        # Define the agent sequence
        agent_sequence = [
            {'name': '🗄️ Schema Expert', 'status': 'completed' if agent == 'schema' else 'pending' if agent in ['technical', 'dependency'] else 'waiting'},
            {'name': '🏗️ Technical Architect', 'status': 'completed' if agent == 'technical' else 'active' if agent == 'technical' else 'pending' if agent == 'dependency' else 'waiting'},
            {'name': '📋 Dependency Resolver', 'status': 'completed' if agent == 'dependency' else 'active' if agent == 'dependency' else 'waiting'}
        ]
        
        for i, agent_info in enumerate(agent_sequence):
            status_icon = {
                'completed': '✅',
                'active': '🔄',
                'pending': '⏳',
                'waiting': '⏸️'
            }.get(agent_info['status'], '⏸️')
            
            status_color = {
                'completed': '#28a745',
                'active': '#0176D3',
                'pending': '#ffc107',
                'waiting': '#6c757d'
            }.get(agent_info['status'], '#6c757d')
            
            st.markdown(f"""
            <div style="display: flex; align-items: center; padding: 0.5rem; margin: 0.2rem 0; 
                        border-left: 3px solid {status_color}; background: rgba(0,0,0,0.02); border-radius: 4px;">
                <span style="margin-right: 0.5rem; font-size: 1.2rem;">{status_icon}</span>
                <span style="color: {status_color}; font-weight: 500;">{agent_info['name']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Auto-refresh while processing
        if st.session_state.processing:
            time.sleep(1)
            st.rerun()

def main():
    """Main application function with simple chat interface."""
    
    # Initialize session state
    initialize_session_state()
    
    # Initialize unified agent system if needed
    if not st.session_state.unified_agent:
        try:
            st.session_state.unified_agent = UnifiedAgentSystem(
                preferred_system=st.session_state.preferred_agent_system
            )
            st.session_state.conversation_history = st.session_state.unified_agent.get_conversation_history()
        except Exception as e:
            st.error(f"Agent initialization error: {str(e)}")
            return
    
    # Display sidebar
    display_sidebar()
    
    # Simple CSS for the chat
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem !important;
        max-width: 800px !important;
        padding-bottom: 100px !important;
    }
    
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 20px;
        border-top: 1px solid #ddd;
        z-index: 1000;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display conversation history
    if st.session_state.conversation_history:
        for message in st.session_state.conversation_history:
            if message['role'] == 'user':
                # User message - right aligned, blue
                st.markdown(f'''
                    <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                        <div style="background: #007bff; color: white; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word;">
                            {message['content']}
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
            else:
                # Agent message - left aligned, gray
                st.markdown(f'''
                    <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                        <div style="background: #f1f3f4; color: #333; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word;">
                            🤖 {message['content']}
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align: center; color: #666; margin: 50px 0;">💬 Start a conversation by typing below</div>', unsafe_allow_html=True)
    
    # Fixed input at bottom
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)  # Spacer
    
    # Create input container
    input_container = st.container()
    with input_container:
        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                user_input = st.text_input("Your message", placeholder="Type your Salesforce requirement here...", label_visibility="collapsed")
            with col2:
                send_button = st.form_submit_button("Send")
            
            if send_button and user_input.strip():
                # Add user message immediately
                st.session_state.conversation_history.append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': datetime.now().isoformat(),
                    'message_type': 'user_input'
                })
                
                # Process with agent
                try:
                    result = st.session_state.unified_agent.process_user_input(user_input)
                    if result.get('success') and result.get('response'):
                        st.session_state.conversation_history.append({
                            'role': 'agent',
                            'content': result['response'],
                            'timestamp': datetime.now().isoformat(),
                            'message_type': 'agent_response'
                        })
                except Exception as e:
                    st.session_state.conversation_history.append({
                        'role': 'agent',
                        'content': f"Sorry, I encountered an error: {str(e)}",
                        'timestamp': datetime.now().isoformat(),
                        'message_type': 'error'
                    })
                
                # Refresh to show new messages
                st.rerun()

if __name__ == "__main__":
    main() 