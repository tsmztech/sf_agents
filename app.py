import streamlit as st
import time
from typing import Dict, Any, Optional
import json
from datetime import datetime

from agents.master_agent import SalesforceRequirementDeconstructorAgent
from config import Config

# Configure Streamlit page
st.set_page_config(
    page_title="Salesforce AI Agent System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
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
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 10px 0;
        margin-left: 25%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    }
    
    .agent-message {
        background: white;
        color: #333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 10px 0;
        margin-right: 25%;
        border: 1px solid #e1e8ed;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    }
    
    .expert-message {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: #333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 10px 0;
        margin-right: 25%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    }
    
    .agent-status {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 15px;
        font-size: 0.9rem;
        animation: pulse 2s infinite;
        margin-right: 30%;
    }
    
    .agent-status-completed {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        animation: none;
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
    """Display the conversation history with enhanced chat bubble styling and agent status."""
    if not st.session_state.conversation_history:
        st.markdown('''
            <div style="text-align: center; padding: 2rem; color: #666;">
                <h3>👋 Welcome to Salesforce AI Agent System</h3>
                <p>Start by describing your business requirement and I'll help you create a complete Salesforce implementation plan.</p>
            </div>
        ''', unsafe_allow_html=True)
        return
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for i, message in enumerate(st.session_state.conversation_history):
        timestamp = datetime.fromisoformat(message['timestamp']).strftime("%H:%M")
        
        if message['role'] == 'user':
            st.markdown(f'''
                <div class="user-message">
                    <strong>You ({timestamp}):</strong><br>
                    {message['content']}
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
                    agent_icon = "🤖"
                    agent_name = "Master Agent"
                    if next_message.get('message_type') == 'expert_suggestions':
                        agent_icon = "🎯"
                        agent_name = "Expert Agent"
                    elif next_message.get('message_type') == 'expert_analysis':
                        agent_icon = "🔍"
                        agent_name = "Expert Agent"
                    
                    st.markdown(f'''
                        <div class="agent-status agent-status-completed">
                            {agent_icon} <strong>{agent_name}</strong> completed analysis (thought for {duration:.1f}s)
                        </div>
                    ''', unsafe_allow_html=True)
        
        elif message['role'] == 'agent':
            # Determine which agent sent this message based on message type
            message_class = "agent-message"
            agent_icon = "🤖"
            agent_name = "Master Agent"
            
            if message.get('message_type') == 'expert_suggestions':
                message_class = "expert-message"
                agent_icon = "🎯"
                agent_name = "Expert Agent"
            elif message.get('message_type') == 'expert_analysis':
                message_class = "expert-message"
                agent_icon = "🔍"
                agent_name = "Expert Agent"
            
            st.markdown(f'''
                <div class="{message_class}">
                    <strong>{agent_icon} {agent_name} ({timestamp}):</strong><br>
                    {message['content']}
                </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_agent_activities():
    """Display current agent activities with live status updates."""
    import time
    
    if 'agent_activities' not in st.session_state or not st.session_state.agent_activities:
        return
    
    # Only show active agent activities (working status)
    active_agents = [a for a in st.session_state.agent_activities if a['status'] == 'active']
    
    if active_agents:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        for activity in active_agents:
            elapsed = time.time() - activity['start_time']
            st.markdown(f'''
                <div class="agent-status">
                    🔄 <strong>{activity['agent']}</strong> {activity['activity']}
                    <span style="opacity: 0.8; font-size: 0.8rem;">(working for {elapsed:.1f}s)</span>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-refresh while agents are working
        if st.session_state.processing:
            time.sleep(0.5)
            st.rerun()

def display_sidebar():
    """Display the sidebar with session information and controls."""
    with st.sidebar:
        st.markdown('''
        <div style="text-align: center; padding: 0.5rem 0; margin-bottom: 1rem;">
            <div style="font-size: 1.2rem; font-weight: bold; color: #0176D3;">
                ⚡ Salesforce AI Agent System
            </div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 0.2rem;">
                Transforming Requirements into Solutions
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Configuration status
        st.subheader("🔧 Configuration")
        if Config.validate_required_keys():
            st.success("✅ OpenAI API configured")
        else:
            st.error("❌ OpenAI API key required")
            st.info("Please set OPENAI_API_KEY in your .env file")
        
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
            # Add expert agent activity
            add_agent_activity("Expert Agent", "is identifying gaps and enhancements...")
            st.info("🔍 Consulting with Salesforce Expert Agent...")
            
            # Trigger expert analysis
            expert_start = time.time()
            expert_result = st.session_state.agent.process_user_input("")
            complete_agent_activity("Expert Agent")
            
            if expert_result.get('type') == 'expert_suggestions':
                st.success("💡 Expert suggestions ready for your review!")
        
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

def main():
    """Main application function."""
    initialize_session_state()
    
    # Check if we have API key
    if not Config.validate_required_keys():
        st.error("⚠️ Please configure your OpenAI API key in a .env file to continue.")
        st.code("OPENAI_API_KEY=your_api_key_here")
        st.stop()
    
    # Display sidebar
    display_sidebar()
    
    # Introduction text for new users
    if not st.session_state.conversation_history:
        st.markdown("""
        ### 🎯 Welcome to the Salesforce AI Agent System
        
        This intelligent system helps you transform high-level business requirements into detailed Salesforce implementation plans.
        
        **How it works:**
        1. **Describe your requirement** - Tell us what you need in natural language
        2. **AI Expert Analysis** - Our agents identify gaps and suggest enhancements  
        3. **Choose suggestions** - Accept, modify, or skip expert recommendations
        4. **Get your plan** - Receive a comprehensive implementation plan
        
        Ready to get started? Enter your business requirement below! 👇
        """)
    
    # Display conversation history with enhanced styling
    display_conversation_history()
    
    # Display agent activities (real-time status)
    display_agent_activities()
    
    # Expert suggestions panel (when available)
    display_expert_suggestions_panel()
    
    # Input area
    st.markdown("---")
    
    # Show processing indicator if agents are working
    if st.session_state.processing:
        st.info("🤖 Agents are working on your request... Please wait.")
    
    # User input form
    with st.form("user_input_form", clear_on_submit=True):
        user_input = st.text_area(
            "💬 Enter your message or business requirement:",
            height=100,
            placeholder="Describe what you need in Salesforce..." if not st.session_state.processing else "Please wait for agents to finish...",
            disabled=st.session_state.processing
        )
        
        submit_text = "📤 Send Message" if not st.session_state.processing else "⏳ Agents Working..."
        
        submit_button = st.form_submit_button(
            submit_text,
            type="primary",
            disabled=st.session_state.processing
        )
        
        if submit_button and user_input:
            process_user_input(user_input)
            st.rerun()

if __name__ == "__main__":
    main() 