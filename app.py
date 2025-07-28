import streamlit as st
import time
from typing import Dict, Any, Optional
import json
from datetime import datetime

from agents.master_agent import SalesforceRequirementDeconstructorAgent
from config import Config

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

# Enhanced CSS for better chat styling
st.markdown("""
<style>
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f8f9fa;
    }
    
            /* Remove excessive spacing */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        /* Chat Container */
        .chat-container {
            min-height: auto;
            overflow-y: auto;
            padding: 10px 20px;
            padding-bottom: 120px;
            background: transparent;
        }

        /* User Messages - Right Aligned */
        .user-message {
            display: flex;
            justify-content: flex-end;
            margin: 12px 0;
        }

        .user-message .message-bubble {
            background: linear-gradient(135deg, #6c7293 0%, #4a4f6b 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 18px 18px 4px 18px;
            max-width: 70%;
            word-wrap: break-word;
            box-shadow: 0 2px 12px rgba(108, 114, 147, 0.3);
            animation: slideInRight 0.3s ease-out;
        }

        /* All System Messages - Left Aligned with Single Color */
        .agent-message,
        .expert-message,
        .technical-message,
        .dependency-message {
            display: flex;
            justify-content: flex-start;
            margin: 12px 0;
        }

        .agent-message .message-bubble,
        .expert-message .message-bubble,
        .technical-message .message-bubble,
        .dependency-message .message-bubble {
            background: #7c3aed;
            color: white;
            padding: 12px 16px;
            border-radius: 18px 18px 18px 4px;
            max-width: 70%;
            word-wrap: break-word;
            box-shadow: 0 2px 12px rgba(124, 58, 237, 0.3);
            animation: slideInLeft 0.3s ease-out;
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

        /* Fixed Footer Input */
        .chat-input-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-top: 2px solid #e9ecef;
            padding: 15px 20px;
            z-index: 1000;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        }

        .chat-input-container {
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }

        .chat-input-box {
            flex: 1;
            min-height: 44px;
            max-height: 120px;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 22px;
            font-size: 16px;
            resize: none;
            outline: none;
            transition: border-color 0.3s ease;
            background: #f8f9fa;
        }

        .chat-input-box:focus {
            border-color: #667eea;
            background: white;
        }

        .chat-send-button {
            min-width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 22px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s ease;
            font-weight: 600;
            padding: 0 16px;
        }

        .chat-send-button:hover {
            transform: scale(1.05);
        }

        .chat-send-button:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
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

        /* Agent Labels */
        .agent-label {
            font-size: 0.8rem;
            color: #6c757d;
            margin-bottom: 4px;
            padding-left: 16px;
        }

        .user-label {
            text-align: right;
            padding-right: 16px;
            color: #6c757d;
        }
    
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
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.02); opacity: 0.9; }
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
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
    
    # Initialize agent activity tracking
    initialize_agent_tracking()

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
    if not st.session_state.agent:
        return ""
    
    agent_state = st.session_state.agent.conversation_state
    
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
    """Display the conversation history with modern chat bubble styling."""
    if not st.session_state.conversation_history:
        # Display welcome message in system message style
        st.markdown('''
            <div class="agent-label">🤖 Master Agent • Welcome</div>
            <div class="agent-message">
                <div class="message-bubble">
                    <strong>👋 Welcome to Salesforce AI Agent System</strong><br><br>
                    I'll help you transform your business requirements into detailed Salesforce implementation plans.<br><br>
                    <strong>How it works:</strong><br>
                    • Describe your requirement in natural language<br>
                    • I'll analyze and suggest enhancements<br>
                    • You choose what to include<br>
                    • Get a comprehensive implementation plan<br><br>
                    Ready to get started? Tell me about your business requirement! 🚀
                </div>
            </div>
        ''', unsafe_allow_html=True)
        return
    
    for i, message in enumerate(st.session_state.conversation_history):
        timestamp = datetime.fromisoformat(message['timestamp']).strftime("%H:%M")
        
        if message['role'] == 'user':
            # User message - right aligned
            st.markdown(f'''
                <div class="user-label">You • {timestamp}</div>
                <div class="user-message">
                    <div class="message-bubble">
                        {message['content']}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Add agent status bubble after user message (if there's a following agent response)
            if i < len(st.session_state.conversation_history) - 1:
                next_message = st.session_state.conversation_history[i + 1]
                if next_message['role'] == 'agent':
                    # Calculate processing time
                    user_time = datetime.fromisoformat(message['timestamp'])
                    agent_time = datetime.fromisoformat(next_message['timestamp'])
                    duration = (agent_time - user_time).total_seconds()
                    
                    # Determine which agent processed this
                    agent_info = get_agent_info_from_message(next_message)
                    
                    st.markdown(f'''
                        <div class="agent-status agent-status-completed">
                            <div class="message-bubble">
                                {agent_info['icon']} {agent_info['name']} completed analysis (thought for {duration:.1f}s)
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
        
        elif message['role'] == 'agent':
            # Agent message - left aligned
            agent_info = get_agent_info_from_message(message)
            
            st.markdown(f'''
                <div class="agent-label">{agent_info['icon']} {agent_info['name']} • {timestamp}</div>
                <div class="{agent_info['css_class']}">
                    <div class="message-bubble">
                        {message['content']}
                    </div>
                </div>
            ''', unsafe_allow_html=True)

def get_agent_info_from_message(message):
    """Get agent information based on message type."""
    message_type = message.get('message_type', '')
    
    if 'expert' in message_type or 'schema' in message_type:
        return {
            'name': 'Schema Expert',
            'icon': '📋',
            'css_class': 'expert-message'
        }
    elif 'technical_design' in message_type:
        return {
            'name': 'Technical Architect',
            'icon': '🏗️',
            'css_class': 'technical-message'
        }
    elif 'task_creation' in message_type or 'dependency' in message_type:
        return {
            'name': 'Dependency Resolver',
            'icon': '📊',
            'css_class': 'dependency-message'
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
        
        # Salesforce connection status
        if st.session_state.agent and hasattr(st.session_state.agent.schema_expert, 'sf_connected'):
            if st.session_state.agent.schema_expert.sf_connected:
                st.success("🟢 Salesforce org connected")
                if st.button("🔍 Test SF Connection"):
                    with st.spinner("Testing Salesforce connection..."):
                        test_result = st.session_state.agent.schema_expert.sf_connector.test_connection()
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
            
            # Export conversation
            conversation_json = json.dumps(st.session_state.conversation_history, indent=2)
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
        
        # Quick action buttons
        st.markdown("#### Quick Actions:")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("✅ Accept All", type="primary"):
                result = st.session_state.agent.process_user_input("accept all")
                st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
                st.rerun()
        
        with col2:
            if st.button("🔧 Select Specific"):
                result = st.session_state.agent.process_user_input("select specific")
                st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
                st.rerun()
        
        with col3:
            if st.button("➡️ Proceed As-Is"):
                result = st.session_state.agent.process_user_input("proceed as-is")
                st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
                st.rerun()
        
        with col4:
            if st.button("❓ Need Details"):
                result = st.session_state.agent.process_user_input("need details")
                st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
                st.rerun()

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

def process_user_input(user_input: str):
    """Process user input through the agent."""
    import time
    
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
        # Determine which agent will be working based on conversation state
        current_state = st.session_state.agent.conversation_state
        
        if current_state == "initial" or current_state == "clarifying":
            add_agent_activity("Master Agent", "is analyzing your requirements...")
        elif current_state == "suggestions_review":
            add_agent_activity("Master Agent", "is processing your selection...")
        elif current_state == "technical_design":
            add_agent_activity("Technical Architect", "is creating detailed architecture...")
        elif current_state == "task_creation":
            add_agent_activity("Dependency Resolver", "is creating implementation tasks...")
        elif current_state == "final_review":
            add_agent_activity("Master Agent", "is processing your review...")
        elif current_state == "planning":
            add_agent_activity("Master Agent", "is creating your implementation plan...")
        else:
            add_agent_activity("Master Agent", "is processing your request...")
        
        # Process the input through the agent
        start_time = time.time()
        result = st.session_state.agent.process_user_input(user_input)
        
        # Complete the current agent activity
        complete_agent_activity("Master Agent")
        
        # Handle special cases that trigger additional agents
        if result['type'] == 'ready_for_expert_analysis':
            # Add schema expert agent activity
            add_agent_activity("Schema Expert", "is analyzing data model requirements...")
            st.info("🔍 Consulting with Salesforce Schema Expert...")
            
            # Trigger schema analysis using the dedicated method
            expert_start = time.time()
            expert_result = st.session_state.agent.trigger_expert_analysis()
            complete_agent_activity("Schema Expert")
            
            if expert_result.get('type') == 'expert_suggestions':
                st.success("📋 Schema recommendations ready for your review!")
            elif expert_result.get('type') == 'error_fallback':
                st.warning("⚠️ Schema analysis encountered issues, but we can still proceed with implementation planning.")
        
        # Update conversation history
        st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
        
        # Show success message based on result type
        if result['type'] == 'implementation_plan':
            st.success("🎉 Implementation plan created successfully!")
            st.balloons()
        elif result['type'] == 'clarification_needed':
            st.info("🤔 Agent needs more information to proceed.")
        elif result['type'] == 'expert_suggestions':
            st.success("💡 Expert suggestions ready for your review!")
        elif result['type'] == 'suggestions_accepted':
            st.success("✅ Expert suggestions incorporated!")
            # Automatically trigger technical design
            add_agent_activity("Technical Architect", "is creating detailed architecture...")
        elif result['type'] == 'original_requirements_only':
            st.info("👍 Proceeding with original requirements.")
            # Automatically trigger technical design
            add_agent_activity("Technical Architect", "is creating detailed architecture...")
        elif result['type'] == 'technical_design_complete':
            st.success("🏗️ Technical architecture completed!")
            # Automatically trigger task creation
            add_agent_activity("Dependency Resolver", "is creating implementation tasks...")
        elif result['type'] == 'task_creation_complete':
            st.success("📋 Implementation tasks created!")
        elif result['type'] == 'custom_selection_confirmed':
            st.success("🔧 Custom suggestions incorporated!")
        elif result['type'] == 'ready_for_planning':
            st.info("✅ Agent is ready to create the implementation plan.")
    
    except Exception as e:
        # Complete any active agent activities on error
        if 'agent_activities' in st.session_state:
            for activity in st.session_state.agent_activities:
                if activity.get('status') == 'active':
                    complete_agent_activity(activity['agent'])
        
        st.error(f"Error processing your request: {e}")
        if Config.DEBUG:
            st.exception(e)
    
    finally:
        st.session_state.processing = False

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

def validate_and_save_config(openai_key, sf_instance, sf_client_id, sf_client_secret, sf_domain, 
                           use_client_creds, sf_username, sf_password, sf_security_token):
    """Validate the provided configuration and save if successful."""
    
    with st.spinner("🔍 Validating configurations..."):
        # Validate OpenAI
        openai_valid = validate_openai_config(openai_key)
        
        # Validate Salesforce
        sf_valid = validate_salesforce_config(
            sf_instance, sf_client_id, sf_client_secret, sf_domain,
            use_client_creds, sf_username, sf_password, sf_security_token
        )
        
        if openai_valid and sf_valid:
            # Save to session state
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
        else:
            if not openai_valid:
                st.error("❌ OpenAI API key validation failed")
            if not sf_valid:
                st.error("❌ Salesforce configuration validation failed")
            return False

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

def main():
    """Main application function."""
    initialize_session_state()
    
    # Import config to check test flag
    from config import Config
    
    # Check if we should use environment variables (test mode)
    # Only use env config if flag is enabled AND user hasn't forced UI config
    if Config.USE_ENV_CONFIG and not st.session_state.force_ui_config:
        # Test mode: Use environment variables from .env file
        if not _validate_env_config():
            st.error("❌ Test mode enabled but environment variables are missing or invalid. Please check your .env file.")
            st.info("💡 Set USE_ENV_CONFIG=False in .env to use UI configuration instead.")
            return
        
        # Set config as complete and load from env
        st.session_state.config_complete = True
        _load_config_from_env()
        
        # Show test mode indicator in sidebar
        with st.sidebar:
            st.success("🧪 **Test Mode Active**")
            st.info("Using .env configuration")
            if st.button("🔄 Switch to UI Config"):
                # Temporarily disable test mode for this session
                st.session_state.force_ui_config = True
                st.session_state.config_complete = False
                st.rerun()
    
    # Show configuration popup if not complete (and not in test mode)
    if not st.session_state.config_complete:
        show_configuration_popup()
        return
    
    # Set environment variables from session state for the agents to use
    import os
    os.environ['OPENAI_API_KEY'] = st.session_state.openai_api_key
    os.environ['SALESFORCE_INSTANCE_URL'] = st.session_state.sf_instance_url
    os.environ['SALESFORCE_CLIENT_ID'] = st.session_state.sf_client_id
    os.environ['SALESFORCE_CLIENT_SECRET'] = st.session_state.sf_client_secret
    os.environ['SALESFORCE_DOMAIN'] = st.session_state.sf_domain
    
    # Set username-password fields if available (for legacy flow)
    if st.session_state.sf_username:
        os.environ['SALESFORCE_USERNAME'] = st.session_state.sf_username
    if st.session_state.sf_password:
        os.environ['SALESFORCE_PASSWORD'] = st.session_state.sf_password
    if st.session_state.sf_security_token:
        os.environ['SALESFORCE_SECURITY_TOKEN'] = st.session_state.sf_security_token
    
    # Display sidebar
    display_sidebar()
    
    # Display conversation history with modern chat styling
    display_conversation_history()
    
    # Display agent activities (real-time status)
    display_agent_activities()
    
    # Expert suggestions panel (when available)
    display_expert_suggestions_panel()
    
    # Fixed footer with input
    create_chat_input_footer()

def create_chat_input_footer():
    """Create the fixed footer with chat input."""
    
    # Add minimal spacing to prevent content from being hidden behind footer
    st.markdown('<div style="height: 80px;"></div>', unsafe_allow_html=True)
    
    # Show processing indicator if agents are working
    if st.session_state.processing:
        st.markdown('''
            <div style="position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%); 
                        background: rgba(255, 193, 7, 0.9); color: #856404; padding: 8px 16px; 
                        border-radius: 20px; font-size: 0.9rem; z-index: 999;">
                🤖 Agents are working on your request... Please wait.
            </div>
        ''', unsafe_allow_html=True)
    
    # Create the fixed footer with Streamlit form
    st.markdown('''
        <div class="chat-input-footer">
            <div class="chat-input-container" id="streamlit-form-container">
                <!-- Streamlit form will be inserted here -->
            </div>
        </div>
        
        <style>
        /* Override Streamlit form styling for the footer */
        .chat-input-footer .stForm {
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .chat-input-footer .stTextArea > div > div {
            border-radius: 22px !important;
            border: 2px solid #e9ecef !important;
        }
        
        .chat-input-footer .stTextArea > div > div:focus-within {
            border-color: #667eea !important;
        }
        
        .chat-input-footer .stButton > button {
            border-radius: 22px !important;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            height: 44px !important;
            min-width: 44px !important;
            font-weight: 600 !important;
        }
        
        .chat-input-footer .stButton > button:hover {
            transform: scale(1.05) !important;
        }
        
        .chat-input-footer .stForm {
            border: none !important;
        }
        </style>
    ''', unsafe_allow_html=True)
    
    # Use Streamlit's form in the footer
    with st.form("chat_input_form", clear_on_submit=True):
        col1, col2 = st.columns([0.85, 0.15])
        
        with col1:
            user_input = st.text_area(
                "Message",
                label_visibility="collapsed",
                placeholder="Describe what you need in Salesforce..." if not st.session_state.processing else "Please wait for agents to finish...",
                disabled=st.session_state.processing,
                key="chat_input",
                height=44
            )
        
        with col2:
            submit_text = "⏳" if st.session_state.processing else "📤"
            submit_button = st.form_submit_button(
                submit_text,
                disabled=st.session_state.processing,
                use_container_width=True
            )
        
        if submit_button and user_input:
            process_user_input(user_input)
            st.rerun()

if __name__ == "__main__":
    main() 