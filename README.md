# ⚡ Salesforce AI Agent System

An intelligent agentic AI system built with CrewAI that transforms high-level business requirements into detailed Salesforce implementation plans through natural language conversation.

## 🎯 Project Overview

This system uses a collaborative team of AI agents to automate the journey from business requirements to Salesforce configurations. **Phase 1** focuses on requirement gathering, clarification, and implementation planning.

### Key Features

- **🤖 Intelligent Master Agent**: Powered by CrewAI and GPT-4
- **🎯 Expert Salesforce Agent**: AI specialist for best practices and gap analysis
- **💡 Smart Requirement Enhancement**: Automatically identifies and fills gaps
- **💬 Natural Language Interface**: Streamlit-based GUI for seamless interaction
- **🧠 Persistent Memory**: Conversation history and context retention
- **📋 Automated Planning**: Structured Salesforce implementation plans
- **🔧 User Choice Workflow**: Accept, modify, or skip expert suggestions
- **📊 Session Management**: Save, load, and export conversation sessions
- **🔄 Enhanced Conversations**: Clarification → Expert Analysis → Suggestions → Planning

## 🏗️ Architecture

```
sf_agents/
├── agents/                       # AI Agent modules
│   ├── __init__.py
│   ├── memory_manager.py        # Conversation memory & persistence
│   ├── master_agent.py          # Main requirement deconstructor agent
│   └── salesforce_expert_agent.py # Expert agent for best practices
├── data/                        # Data storage
│   ├── conversation_history/    # Session conversations
│   └── implementation_plans/    # Generated plans
├── app.py                       # Streamlit GUI application
├── config.py                    # Configuration management
└── requirements.txt             # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- Virtual environment (recommended)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd sf_agents
   ```

2. **Activate your virtual environment:**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   DEBUG=True
   LOG_LEVEL=INFO
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

6. **Open your browser:**
   Navigate to `http://localhost:8501`

## 📖 Usage Guide

### Starting a Conversation

1. **Enter your business requirement** in natural language
   - Example: "We need a customer support ticketing system"
   - Example: "Create a lead management process for our sales team"

2. **Engage with clarification questions**
   - The agent will ask follow-up questions to understand your needs
   - Provide detailed responses about business goals, user roles, data requirements

3. **Confirm and generate plan**
   - Once the agent has sufficient information, confirm to proceed
   - Receive a comprehensive Salesforce implementation plan

### Enhanced Conversation Flow

```
👤 User: "We need a customer support ticketing system"

🤖 Master Agent: "I'll help you design a customer support ticketing system! 
                 Let me understand your core business needs first..."

👤 User: [Provides basic information about business goals]

🤖 Master Agent: "Great! I have the core requirements. Let me consult with 
                 our Salesforce Expert Agent to identify any gaps and 
                 suggest enhancements..."

🔍 Expert Analysis: [Identifies missing security, integration, and UX considerations]

🤖 Master Agent: "Our expert identified several valuable enhancements:
                 - Security permissions and field-level access
                 - Integration with email systems  
                 - Mobile-friendly interface design
                 - Automated escalation workflows
                 
                 Would you like to include these suggestions?"

👤 User: "Accept the security and integration suggestions"

🤖 Master Agent: [Generates comprehensive implementation plan with selected enhancements]
```

**Key Enhancement**: You no longer need to think of every detail upfront - the Expert Agent fills gaps with industry best practices!

### Implementation Plan Components

The generated plans include:

- **📋 Executive Summary**: Business requirement overview
- **🏗️ Salesforce Components**: Custom objects, fields, relationships
- **⚙️ Development Components**: Apex classes, triggers, LWC components
- **🤖 Automation**: Flows, process builders, validation rules
- **🔐 Security**: Permission sets, profiles, sharing rules
- **🔗 Integration**: External systems, APIs, data migration
- **📅 Implementation Phases**: Timeline and dependencies
- **🧪 Testing Strategy**: Unit, integration, and UAT approaches

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `DEBUG` | Enable debug mode | No (default: True) |
| `LOG_LEVEL` | Logging level | No (default: INFO) |

### Advanced Configuration

Edit `config.py` to customize:
- Data storage paths
- Model parameters
- Agent behavior settings

## 💾 Data Management

### Session Persistence

- **Automatic saving**: All conversations are automatically saved
- **Session IDs**: Unique identifiers for each conversation
- **History loading**: Resume previous conversations anytime

### Export Options

- **Conversation Export**: Download complete conversation history as JSON
- **Implementation Plans**: Export generated plans for documentation
- **Session Management**: Load, create, or switch between sessions

## 🧠 Agent Capabilities

### Master Agent Features

- **Requirement Analysis**: Understands complex business needs
- **Expert Collaboration**: Works with specialized agents for enhanced solutions
- **Intelligent Clarification**: Asks relevant follow-up questions  
- **Salesforce Expertise**: Deep knowledge of platform capabilities
- **Structured Planning**: Creates actionable implementation roadmaps
- **Context Retention**: Maintains conversation memory throughout sessions

### Expert Agent Capabilities

- **Gap Analysis**: Identifies missing requirements automatically
- **Best Practice Recommendations**: Suggests industry-standard approaches
- **Architecture Validation**: Reviews solutions for scalability and performance
- **Security Assessment**: Ensures proper permission and security models
- **Integration Guidance**: Recommends optimal integration patterns
- **Industry Expertise**: Provides sector-specific recommendations
- **Risk Mitigation**: Identifies and prevents common implementation issues

### Conversation States

1. **Initial**: First requirement submission
2. **Clarifying**: Gathering core business information
3. **Expert Analysis**: AI expert identifying gaps and enhancements
4. **Suggestions Review**: User choosing which expert recommendations to include
5. **Planning**: Ready to generate implementation plan  
6. **Completed**: Plan generated with expert enhancements, follow-up supported

## 🛠️ Development

### Project Structure

- `agents/master_agent.py`: Core AI agent logic
- `agents/memory_manager.py`: Conversation persistence
- `app.py`: Streamlit user interface
- `config.py`: Configuration management

### Extending the System

For future phases, the architecture supports:
- Additional specialized agents
- Salesforce API integration
- Automated deployment capabilities
- Multi-agent collaboration workflows

## 📝 Example Requirements

Try these sample requirements to test the system:

### Simple Requirements
- "Create a basic contact management system"
- "Set up opportunity tracking for sales"
- "Build a simple case management solution"

### Complex Requirements
- "Design a multi-stage approval process for purchase orders with budget controls and automated notifications"
- "Create an inventory management system with automated reordering, vendor integration, and cost tracking"
- "Build a customer onboarding workflow with document collection, approval stages, and integration with external systems"

## 🔍 Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   - Ensure your API key is correctly set in the `.env` file
   - Verify you have sufficient API credits

2. **Import Errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Verify you're using the correct virtual environment

3. **Streamlit Issues**
   - Clear browser cache and refresh
   - Check the terminal for detailed error messages

### Debug Mode

Enable debug mode in your `.env` file:
```
DEBUG=True
```

This provides detailed error traces and additional logging.

## 🚀 Next Phases

**Phase 2** (Planned):
- Specialized agent team (Security, Integration, UI/UX agents)
- Salesforce API integration
- Automated metadata generation

**Phase 3** (Planned):
- Automated deployment to Salesforce orgs
- Real-time collaboration between agents
- Advanced testing and validation

## 📄 License

This project is built for demonstration and educational purposes.

## 🤝 Contributing

This is a demonstration project. For questions or suggestions, please refer to the project documentation.

---

**Built with ❤️ using CrewAI, Streamlit, and OpenAI GPT-4** 