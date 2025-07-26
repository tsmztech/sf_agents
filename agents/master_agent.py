import json
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from crewai.agent import Agent
from langchain_openai import ChatOpenAI

from agents.memory_manager import MemoryManager
from agents.salesforce_expert_agent import SalesforceExpertAgent
from agents.technical_architect_agent import SalesforceTechnicalArchitectAgent
from agents.dependency_resolver_agent import DependencyResolverAgent
from config import Config

class SalesforceRequirementDeconstructorAgent:
    """
    Master Agent responsible for understanding business requirements,
    engaging in dialogue with users, and deconstructing requirements
    into structured Salesforce implementation plans.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.memory_manager = MemoryManager(session_id)
        self.conversation_state = "initial"  # initial, clarifying, expert_analysis, suggestions_review, technical_design, task_creation, final_review, completed
        self.current_requirement = None
        self.expert_suggestions = None
        self.technical_design = None
        self.implementation_tasks = None
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )
        
        # Initialize all specialized agents
        self.expert_agent = SalesforceExpertAgent()
        self.technical_architect = SalesforceTechnicalArchitectAgent()
        self.dependency_resolver = DependencyResolverAgent()
        
        # Initialize the Crew AI agent
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Crew AI agent with Salesforce expertise."""
        self.agent = Agent(
            role="Salesforce Solution Architect",
            goal="""Understand business requirements and deconstruct them into detailed 
                    Salesforce implementation plans. Engage with users to clarify requirements 
                    and ensure comprehensive understanding before creating implementation strategies.""",
            backstory="""You are an expert Salesforce Solution Architect with extensive experience 
                        in translating business requirements into technical Salesforce solutions. 
                        You understand all aspects of the Salesforce platform including:
                        - Custom and Standard Objects
                        - Fields, Relationships, and Schema Design
                        - Apex Classes and Triggers
                        - Lightning Web Components (LWC)
                        - Flows and Process Automation
                        - Security and Permission Sets
                        - Integration patterns
                        
                        You are collaborative and work with expert agents to enhance solutions.
                        You gather the core requirements from users and then consult with expert 
                        agents to identify gaps and suggest improvements. You present expert 
                        recommendations to users in a clear, non-overwhelming way, allowing them 
                        to choose which suggestions to include. You focus on getting enough 
                        information to create a solid foundation, then enhance it with expert insights.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and determine the appropriate response based on conversation state.
        
        Args:
            user_input: The user's message/requirement
            
        Returns:
            Dictionary containing agent response, state, and any actions taken
        """
        # Store user message
        self.memory_manager.add_message("user", user_input, "requirement")
        
        # Determine conversation state and generate appropriate response
        if self.conversation_state == "initial":
            return self._handle_initial_requirement(user_input)
        elif self.conversation_state == "clarifying":
            return self._handle_clarification(user_input)
        elif self.conversation_state == "expert_analysis":
            return self._handle_expert_analysis()
        elif self.conversation_state == "suggestions_review":
            return self._handle_suggestions_review(user_input)
        elif self.conversation_state == "technical_design":
            return self._handle_technical_design()
        elif self.conversation_state == "task_creation":
            return self._handle_task_creation()
        elif self.conversation_state == "final_review":
            return self._handle_final_review(user_input)
        elif self.conversation_state == "planning":
            return self._handle_planning_confirmation(user_input)
        else:
            return self._handle_general_conversation(user_input)
    
    def _handle_initial_requirement(self, requirement: str) -> Dict[str, Any]:
        """Handle the initial business requirement submission."""
        
        # Create task for understanding and clarifying the requirement
        task = Task(
            description=f"""
            Analyze the following business requirement and determine if you need more information:
            
            Requirement: {requirement}
            
            Your tasks:
            1. Assess if the requirement is clear and complete enough to proceed with implementation planning
            2. If not clear, identify specific questions you need to ask to understand:
               - Business objectives and goals
               - User roles and personas involved
               - Data structures and relationships needed
               - Business processes and workflows
               - Integration requirements
               - Security and permission requirements
            3. If clear enough, acknowledge understanding and ask for confirmation to proceed with planning
            
            Conversation Context:
            {self.memory_manager.get_conversation_context()}
            
            Provide your response in a conversational manner, as if speaking directly to the user.
            """,
            expected_output="A conversational response either asking clarifying questions or confirming understanding to proceed.",
            agent=self.agent
        )
        
        # Execute the task
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Determine next state based on response
        if self._needs_clarification(str(result)):
            self.conversation_state = "clarifying"
            response_type = "clarification_needed"
        else:
            self.conversation_state = "planning"
            response_type = "ready_for_planning"
        
        # Store agent response
        self.memory_manager.add_message("agent", str(result), response_type)
        
        return {
            "response": str(result),
            "state": self.conversation_state,
            "type": response_type,
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_clarification(self, user_response: str) -> Dict[str, Any]:
        """Handle user responses during the clarification phase."""
        
        task = Task(
            description=f"""
            The user has provided additional information about their requirement:
            
            User Response: {user_response}
            
            Previous Conversation:
            {self.memory_manager.get_conversation_context()}
            
            Your tasks:
            1. Acknowledge the user's additional information
            2. Determine if you have enough CORE information to understand the basic business need
            3. If you still need essential information, ask 1-2 specific follow-up questions
            4. If you have the basic understanding of what they want to achieve, suggest consulting 
               with expert agents to identify potential gaps and enhancements before creating the plan
            
            Be conversational and ensure the user feels heard and understood.
            """,
            expected_output="A conversational response either asking more questions or confirming readiness to create implementation plan.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Check if we're ready to move to expert analysis
        if self._ready_for_expert_analysis(str(result)):
            self.conversation_state = "expert_analysis"
            response_type = "ready_for_expert_analysis"
        else:
            response_type = "needs_more_clarification"
        
        self.memory_manager.add_message("agent", str(result), response_type)
        
        return {
            "response": str(result),
            "state": self.conversation_state,
            "type": response_type,
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_planning_confirmation(self, user_input: str) -> Dict[str, Any]:
        """Handle user confirmation to proceed with planning."""
        
        if user_input.lower().strip() in ['yes', 'y', 'proceed', 'go ahead', 'continue', 'ok', 'okay']:
            return self._create_implementation_plan()
        else:
            # User wants to add more information or has concerns
            self.conversation_state = "clarifying"
            return self._handle_clarification(user_input)
    
    def _create_implementation_plan(self) -> Dict[str, Any]:
        """Create the detailed implementation plan."""
        
        task = Task(
            description=f"""
            Based on the complete conversation and requirements gathered, create a comprehensive 
            Salesforce implementation plan.
            
            Conversation History:
            {self.memory_manager.get_conversation_context()}
            
            Expert Suggestions Incorporated:
            {self._format_expert_suggestions_for_plan()}
            
            Create a detailed implementation plan that includes:
            
            1. **Executive Summary**
               - Brief overview of the business requirement
               - High-level solution approach
               
            2. **Salesforce Components Required**
               - Custom Objects (with field specifications)
               - Standard Objects to be modified
               - Custom Fields and their types
               - Relationships between objects
               
            3. **Development Components**
               - Apex Classes needed (with purpose)
               - Apex Triggers required
               - Lightning Web Components (LWC)
               - Aura Components (if needed)
               
            4. **Automation and Workflow**
               - Process Builders/Flows
               - Workflow Rules
               - Validation Rules
               - Formula Fields
               
            5. **Security and Permissions**
               - Permission Sets required
               - Profiles to be modified
               - Field-level security considerations
               - Sharing rules
               
            6. **Integration Requirements**
               - External system integrations
               - API requirements
               - Data migration needs
               
            7. **Implementation Phases**
               - Break down into logical phases
               - Dependencies between components
               - Estimated timeline for each phase
               
            8. **Testing Strategy**
               - Unit testing requirements
               - Integration testing approach
               - User acceptance testing plan
               
            Format the response as a detailed, structured plan that could be used by development teams.
            """,
            expected_output="A comprehensive, structured Salesforce implementation plan with all technical details.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Parse and structure the plan
        plan_data = self._parse_implementation_plan(str(result))
        
        # Save to memory
        self.memory_manager.save_implementation_plan(plan_data)
        self.memory_manager.add_message("agent", str(result), "implementation_plan")
        
        self.conversation_state = "completed"
        
        return {
            "response": str(result),
            "state": self.conversation_state,
            "type": "implementation_plan",
            "plan_data": plan_data,
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_general_conversation(self, user_input: str) -> Dict[str, Any]:
        """Handle general conversation after plan is created."""
        
        task = Task(
            description=f"""
            The user has a follow-up question or comment about the implementation plan:
            
            User Input: {user_input}
            
            Previous Conversation:
            {self.memory_manager.get_conversation_context()}
            
            Respond helpfully to their question or comment. You can:
            - Clarify aspects of the implementation plan
            - Suggest modifications if requested
            - Provide additional technical details
            - Explain Salesforce concepts
            
            Be helpful and knowledgeable.
            """,
            expected_output="A helpful response to the user's follow-up question or comment.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        self.memory_manager.add_message("agent", str(result), "follow_up")
        
        return {
            "response": str(result),
            "state": self.conversation_state,
            "type": "follow_up",
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_expert_analysis(self) -> Dict[str, Any]:
        """Handle expert analysis of requirements and generate suggestions."""
        
        # Get the conversation context and requirements
        conversation_context = self.memory_manager.get_conversation_context()
        current_requirements = self.memory_manager.requirements_extracted
        
        # Consult with the expert agent
        self.memory_manager.add_message("system", "🔍 Consulting with Salesforce Expert Agent to identify gaps and enhancements...", "expert_analysis")
        
        try:
            # Get expert analysis
            expert_analysis = self.expert_agent.analyze_requirements_and_suggest_improvements(
                conversation_context, 
                current_requirements
            )
            
            self.expert_suggestions = expert_analysis
            
            # Create a user-friendly presentation of the expert suggestions
            suggestions_summary = self._format_expert_suggestions(expert_analysis)
            
            response = f"""🎯 **Expert Analysis Complete!**

I've consulted with our Salesforce Expert Agent to analyze your requirements and identify potential enhancements. Here's what we found:

{suggestions_summary}

**These are expert recommendations to enhance your solution.** You can choose to:

✅ **Accept All** - Include all expert suggestions in your implementation plan
🔧 **Select Specific** - Tell me which suggestions you'd like to include  
➡️ **Proceed As-Is** - Continue with your original requirements only
❓ **Need Details** - Ask me to explain any specific recommendation

What would you like to do with these expert suggestions?"""

            # Store the expert response
            self.memory_manager.add_message("agent", response, "expert_suggestions")
            
            # Move to suggestions review state
            self.conversation_state = "suggestions_review"
            
            return {
                "response": response,
                "state": self.conversation_state,
                "type": "expert_suggestions",
                "expert_analysis": expert_analysis,
                "session_id": self.memory_manager.session_id
            }
            
        except Exception as e:
            error_response = f"I encountered an issue while consulting with the expert agent: {e}. Let me proceed with creating a plan based on your current requirements."
            self.memory_manager.add_message("agent", error_response, "error")
            self.conversation_state = "planning"
            return {
                "response": error_response,
                "state": self.conversation_state,
                "type": "error_fallback",
                "session_id": self.memory_manager.session_id
            }
    
    def _handle_suggestions_review(self, user_input: str) -> Dict[str, Any]:
        """Handle user response to expert suggestions."""
        
        user_choice = user_input.lower().strip()
        
        if any(phrase in user_choice for phrase in ['accept all', 'include all', 'yes to all', 'all suggestions']):
            # User accepts all suggestions
            return self._incorporate_all_suggestions()
            
        elif any(phrase in user_choice for phrase in ['proceed as-is', 'original only', 'no suggestions', 'skip suggestions']):
            # User wants to proceed with original requirements only
            return self._proceed_with_original_requirements()
            
        elif any(phrase in user_choice for phrase in ['select specific', 'choose some', 'partial']):
            # User wants to select specific suggestions
            return self._handle_selective_suggestions()
            
        elif any(phrase in user_choice for phrase in ['need details', 'explain', 'tell me more']):
            # User wants more details about suggestions
            return self._provide_suggestion_details(user_input)
            
        else:
            # User provided specific feedback or selections
            return self._process_custom_selection(user_input)
    
    def _incorporate_all_suggestions(self) -> Dict[str, Any]:
        """Incorporate all expert suggestions and proceed to technical design."""
        
        response = """✅ **Excellent choice!** I'll incorporate all expert suggestions into your solution.

These enhancements will make your Salesforce solution more robust, scalable, and aligned with industry best practices. 

🚀 **Ready to create your technical architecture!**

Now I'll work with our Technical Architect to design the detailed solution architecture including data models, automation, security, and all technical components."""

        self.memory_manager.add_message("agent", response, "suggestions_accepted")
        self.conversation_state = "technical_design"
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "suggestions_accepted",
            "suggestions_included": "all",
            "session_id": self.memory_manager.session_id
        }
    
    def _proceed_with_original_requirements(self) -> Dict[str, Any]:
        """Proceed with original requirements only."""
        
        response = """👍 **Understood!** I'll create your solution based on your original requirements.

The expert suggestions will be noted as optional enhancements that you can consider for future phases if needed.

🚀 **Ready to create your technical architecture!**

Now I'll work with our Technical Architect to design the detailed solution architecture based on your core requirements."""

        self.memory_manager.add_message("agent", response, "original_requirements_only")
        self.conversation_state = "technical_design"
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "original_requirements_only",
            "suggestions_included": "none",
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_selective_suggestions(self) -> Dict[str, Any]:
        """Handle selective suggestion inclusion."""
        
        if not self.expert_suggestions:
            return self._proceed_with_original_requirements()
        
        # Create a numbered list of suggestions for easy selection
        suggestions_list = self._create_numbered_suggestions_list()
        
        response = f"""🔧 **Great! Let's select specific suggestions:**

{suggestions_list}

Please tell me which suggestions you'd like to include by:
- **Listing numbers**: "Include suggestions 1, 3, and 5"
- **Describing areas**: "Include security and integration suggestions"
- **Being specific**: "I want the permission sets and API recommendations"

Which expert suggestions would you like to include in your implementation plan?"""

        self.memory_manager.add_message("agent", response, "selective_suggestions")
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "selective_suggestions",
            "session_id": self.memory_manager.session_id
        }
    
    def _provide_suggestion_details(self, user_input: str) -> Dict[str, Any]:
        """Provide detailed explanations of suggestions."""
        
        if not self.expert_suggestions:
            return self._proceed_with_original_requirements()
        
        # Extract which details the user wants
        details_response = f"""📋 **Detailed Expert Recommendations:**

{self.expert_suggestions.get('full_analysis', 'No detailed analysis available')}

Would you like to:
✅ **Accept specific suggestions** after reviewing these details
➡️ **Proceed with original requirements** only
❓ **Ask about specific recommendations** for more clarification

What would you like to do next?"""

        self.memory_manager.add_message("agent", details_response, "suggestion_details")
        
        return {
            "response": details_response,
            "state": self.conversation_state,
            "type": "suggestion_details",
            "session_id": self.memory_manager.session_id
        }
    
    def _process_custom_selection(self, user_input: str) -> Dict[str, Any]:
        """Process custom user selection of suggestions."""
        
        # Store user's custom selection
        self.memory_manager.add_message("user", user_input, "custom_selection")
        
        response = f"""✅ **Perfect!** I've noted your selections:

"{user_input}"

I'll incorporate your chosen expert recommendations into the implementation plan while keeping your original requirements as the foundation.

🚀 **Ready to create your customized implementation plan!**

Shall I proceed with generating the detailed implementation plan that includes your requirements plus your selected expert recommendations?"""

        self.memory_manager.add_message("agent", response, "custom_selection_confirmed")
        self.conversation_state = "planning"
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "custom_selection_confirmed",
            "suggestions_included": "custom",
            "session_id": self.memory_manager.session_id
        }
    
    def _needs_clarification(self, response: str) -> bool:
        """Determine if the agent response indicates need for clarification."""
        clarification_indicators = [
            "need more information",
            "can you clarify",
            "tell me more about",
            "what do you mean",
            "could you elaborate",
            "I need to understand",
            "questions about"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in clarification_indicators)
    
    def _ready_for_expert_analysis(self, response: str) -> bool:
        """Determine if the agent response indicates readiness for expert analysis."""
        analysis_indicators = [
            "consulting with expert",
            "expert agents",
            "identify potential gaps",
            "basic understanding",
            "core information",
            "expert consultation"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in analysis_indicators)
    
    def _ready_for_planning(self, response: str) -> bool:
        """Determine if the agent response indicates readiness for planning."""
        planning_indicators = [
            "ready to proceed",
            "create the implementation plan",
            "move forward with planning",
            "sufficient information",
            "clear understanding"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in planning_indicators)
    
    def _parse_implementation_plan(self, plan_text: str) -> Dict[str, Any]:
        """Parse the implementation plan text into structured data."""
        
        # This is a simplified parser - could be enhanced with more sophisticated NLP
        plan_data = {
            "raw_plan": plan_text,
            "created_at": self.memory_manager.conversation_history[-1].timestamp,
            "session_id": self.memory_manager.session_id,
            "components": {
                "custom_objects": [],
                "apex_classes": [],
                "lwc_components": [],
                "flows": [],
                "permission_sets": [],
                "integrations": []
            },
            "phases": [],
            "estimated_timeline": "To be determined based on detailed analysis"
        }
        
        # Simple extraction logic - this could be enhanced with more sophisticated parsing
        lines = plan_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('##') or line.startswith('**'):
                current_section = line.replace('#', '').replace('*', '').strip().lower()
            elif line and current_section:
                if 'custom object' in current_section:
                    if line.startswith('-') or line.startswith('•'):
                        plan_data["components"]["custom_objects"].append(line[1:].strip())
                elif 'apex' in current_section and 'class' in current_section:
                    if line.startswith('-') or line.startswith('•'):
                        plan_data["components"]["apex_classes"].append(line[1:].strip())
                elif 'lightning' in current_section or 'lwc' in current_section:
                    if line.startswith('-') or line.startswith('•'):
                        plan_data["components"]["lwc_components"].append(line[1:].strip())
        
        return plan_data
    
    def _handle_technical_design(self) -> Dict[str, Any]:
        """Handle technical architecture design creation."""
        
        # Prepare requirements context
        requirements_context = self._get_consolidated_requirements()
        
        response = """🏗️ **Creating Detailed Technical Architecture...**

Our Technical Architect is now designing the complete Salesforce solution architecture including:

• **Data Model Design** - Custom objects, fields, relationships, and schema
• **Automation Architecture** - Triggers, flows, apex classes, and business logic  
• **User Interface Design** - Lightning components, page layouts, and user experience
• **Security Framework** - Profiles, permission sets, and field-level security
• **Integration Strategy** - External systems, APIs, and data synchronization
• **Performance Optimization** - Scalability, governor limits, and best practices

This will provide the blueprint for your entire Salesforce implementation."""

        self.memory_manager.add_message("agent", response, "technical_design_start")
        
        # Create technical architecture using the Technical Architect agent
        try:
            self.technical_design = self.technical_architect.create_technical_architecture(
                requirements_context, 
                self.expert_suggestions
            )
            
            # Format the technical design for user display
            design_summary = self._format_technical_design_summary()
            
            final_response = f"""{response}

✅ **Technical Architecture Complete!**

{design_summary}

The detailed technical architecture has been created. Would you like me to proceed with creating the implementation tasks and project plan?

**Options:**
• **Continue** - "Yes, create the implementation tasks"  
• **Review Details** - "Show me more details about [specific area]"
• **Modify** - "I'd like to change [specific aspect]" """

            self.memory_manager.add_message("agent", final_response, "technical_design_complete")
            
            # Move to task creation state
            self.conversation_state = "task_creation"
            
            return {
                "response": final_response,
                "state": self.conversation_state,
                "type": "technical_design_complete",
                "technical_design": self.technical_design,
                "session_id": self.memory_manager.session_id
            }
            
        except Exception as e:
            error_response = f"❌ **Error creating technical design**: {str(e)}\n\nPlease try again or contact support."
            self.memory_manager.add_message("agent", error_response, "technical_design_error")
            
            return {
                "response": error_response,
                "state": self.conversation_state,
                "type": "error",
                "session_id": self.memory_manager.session_id
            }
    
    def _handle_task_creation(self) -> Dict[str, Any]:
        """Handle implementation task creation and dependency resolution."""
        
        if not self.technical_design:
            return {
                "response": "❌ No technical design available. Please create technical architecture first.",
                "state": self.conversation_state,
                "type": "error",
                "session_id": self.memory_manager.session_id
            }
        
        response = """📋 **Creating Implementation Tasks and Dependencies...**

Our Dependency Resolver is now analyzing the technical design to create:

• **Phased Implementation Plan** - Logical phases with proper sequencing
• **Task Dependencies** - What must be built before other components
• **User Stories** - Agile-ready stories with acceptance criteria
• **Effort Estimates** - Time and resource requirements for each task
• **Risk Assessment** - Potential blockers and mitigation strategies
• **Critical Path Analysis** - Identifying the most important tasks for timeline

This will give you a complete project roadmap for implementation."""

        self.memory_manager.add_message("agent", response, "task_creation_start")
        
        try:
            # Get consolidated requirements for context
            requirements_context = self._get_consolidated_requirements()
            
            # Create implementation tasks using the Dependency Resolver agent
            self.implementation_tasks = self.dependency_resolver.create_implementation_tasks(
                self.technical_design,
                requirements_context
            )
            
            # Format the task summary for user display
            task_summary = self._format_task_summary()
            
            final_response = f"""{response}

✅ **Implementation Plan Complete!**

{task_summary}

**Ready for Final Review**

I've created your complete technical architecture and implementation plan. Here's what you have:

🏗️ **Technical Design**: Detailed schema, automation, UI, and security specifications
📋 **Implementation Tasks**: {self.implementation_tasks.get('total_tasks', 'Multiple')} organized tasks across {len(self.implementation_tasks.get('phases', []))} phases
⚡ **Dependencies Resolved**: Proper task sequencing for efficient implementation
📊 **Project Ready**: Effort estimates, risk assessments, and acceptance criteria

Would you like to review and approve this plan?

**Options:**
• **Approve Plan** - "Yes, approve the complete plan"
• **Review Details** - "Show me details about [phase/task/area]"  
• **Request Changes** - "I'd like to modify [specific aspect]" """

            self.memory_manager.add_message("agent", final_response, "task_creation_complete")
            
            # Move to final review state
            self.conversation_state = "final_review"
            
            return {
                "response": final_response,
                "state": self.conversation_state,
                "type": "task_creation_complete",
                "implementation_tasks": self.implementation_tasks,
                "session_id": self.memory_manager.session_id
            }
            
        except Exception as e:
            error_response = f"❌ **Error creating implementation tasks**: {str(e)}\n\nPlease try again or contact support."
            self.memory_manager.add_message("agent", error_response, "task_creation_error")
            
            return {
                "response": error_response,
                "state": self.conversation_state,
                "type": "error",
                "session_id": self.memory_manager.session_id
            }
    
    def _handle_final_review(self, user_input: str) -> Dict[str, Any]:
        """Handle final review and approval of the complete plan."""
        
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ["approve", "yes", "looks good", "proceed", "accept"]):
            return self._approve_final_plan()
        elif any(keyword in user_input_lower for keyword in ["details", "show", "review", "explain"]):
            return self._provide_plan_details(user_input)
        elif any(keyword in user_input_lower for keyword in ["modify", "change", "update", "different"]):
            return self._handle_plan_modifications(user_input)
        else:
            return self._clarify_final_review_intent(user_input)
    
    def _approve_final_plan(self) -> Dict[str, Any]:
        """Approve and finalize the complete implementation plan."""
        
        response = """🎉 **Implementation Plan Approved!**

Your complete Salesforce solution design is now ready for development.

**What You Have:**
✅ **Detailed Technical Architecture** - Complete schema, automation, and UI specifications
✅ **Ordered Implementation Tasks** - Ready-to-execute project plan with dependencies
✅ **Resource Requirements** - Effort estimates and skill requirements
✅ **Risk Mitigation** - Identified challenges and mitigation strategies

**Your Implementation Plan Includes:**
• Technical specifications ready for development teams
• User stories and acceptance criteria for Agile development  
• Dependency mapping for efficient project execution
• Testing strategies and quality assurance guidelines

**Next Steps:**
1. **Download Your Plan** - Use the sidebar to export technical documents
2. **Share with Team** - Distribute to developers, architects, and stakeholders
3. **Start Development** - Begin with Phase 1 foundation setup
4. **Track Progress** - Use the task breakdown for project management

Thank you for using the Salesforce AI Agent System! 🚀

You can ask follow-up questions or start a new requirement anytime."""

        self.memory_manager.add_message("agent", response, "plan_approved")
        
        # Mark conversation as completed
        self.conversation_state = "completed"
        
        # Save the complete plan
        self._save_complete_plan()
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "implementation_plan",
            "plan_approved": True,
            "session_id": self.memory_manager.session_id
        }
    
    def _get_consolidated_requirements(self) -> str:
        """Get all requirements including expert suggestions."""
        base_requirement = ""
        
        # Get the original requirement
        for msg in self.memory_manager.messages:
            if msg.role == "user" and msg.message_type == "requirement":
                base_requirement = msg.content
                break
        
        # Add expert suggestions if incorporated
        expert_context = ""
        if self.expert_suggestions:
            expert_context = f"""

EXPERT ENHANCEMENTS INCLUDED:
{self._format_expert_suggestions_for_plan()}"""
        
        return base_requirement + expert_context
    
    def _format_technical_design_summary(self) -> str:
        """Format technical design for user display."""
        if not self.technical_design:
            return "Technical design not available."
        
        # Extract key components for summary
        summary = "**Architecture Overview:**\n"
        
        if "data_model" in self.technical_design:
            data_model = self.technical_design["data_model"]
            if isinstance(data_model, dict):
                custom_objects = len(data_model.get("custom_objects", []))
                custom_fields = len(data_model.get("custom_fields", []))
                summary += f"• Data Model: {custom_objects} custom objects, {custom_fields} custom fields\n"
        
        if "automation" in self.technical_design:
            automation = self.technical_design["automation"]
            if isinstance(automation, dict):
                triggers = len(automation.get("triggers", []))
                classes = len(automation.get("apex_classes", []))
                summary += f"• Automation: {triggers} triggers, {classes} Apex classes\n"
        
        if "user_interface" in self.technical_design:
            ui = self.technical_design["user_interface"]
            if isinstance(ui, dict):
                lwc = len(ui.get("lightning_components", []))
                layouts = len(ui.get("page_layouts", []))
                summary += f"• User Interface: {lwc} Lightning components, {layouts} page layouts\n"
        
        if "security" in self.technical_design:
            security = self.technical_design["security"]
            if isinstance(security, dict):
                profiles = len(security.get("profiles", []))
                permission_sets = len(security.get("permission_sets", []))
                summary += f"• Security: {profiles} profile modifications, {permission_sets} permission sets\n"
        
        return summary
    
    def _format_task_summary(self) -> str:
        """Format implementation tasks for user display."""
        if not self.implementation_tasks:
            return "Implementation tasks not available."
        
        summary = "**Implementation Overview:**\n"
        
        total_tasks = self.implementation_tasks.get("total_tasks", 0)
        phases = self.implementation_tasks.get("phases", [])
        
        summary += f"• **Total Tasks**: {total_tasks} implementation tasks\n"
        summary += f"• **Phases**: {len(phases)} organized phases\n"
        
        for i, phase in enumerate(phases[:3], 1):  # Show first 3 phases
            if isinstance(phase, dict):
                phase_name = phase.get("name", f"Phase {i}")
                phase_tasks = len(phase.get("tasks", []))
                summary += f"• **{phase_name}**: {phase_tasks} tasks\n"
        
        if len(phases) > 3:
            summary += f"• ... and {len(phases) - 3} more phases\n"
        
        return summary
    
    def _save_complete_plan(self):
        """Save the complete implementation plan."""
        if self.technical_design and self.implementation_tasks:
            complete_plan = {
                "technical_architecture": self.technical_design,
                "implementation_tasks": self.implementation_tasks,
                "expert_suggestions": self.expert_suggestions,
                "approved_at": datetime.now().isoformat(),
                "session_id": self.memory_manager.session_id
            }
            
            self.memory_manager.save_implementation_plan(complete_plan)
    
    def _provide_plan_details(self, user_input: str) -> Dict[str, Any]:
        """Provide detailed information about specific aspects of the plan."""
        
        response = f"""📋 **Plan Details:**

**Technical Architecture:**
{self._format_technical_design_summary()}

**Implementation Tasks:**
{self._format_task_summary()}

**Expert Suggestions Included:**
{self._format_expert_suggestions_for_plan()}

Would you like more specific details about any particular area, or are you ready to approve the plan?

**Options:**
• **Approve Plan** - "Yes, approve the complete plan"
• **Specific Area** - "Tell me more about [data model/automation/security/etc.]"
• **Request Changes** - "I'd like to modify [specific aspect]" """

        self.memory_manager.add_message("agent", response, "plan_details")
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "plan_details",
            "session_id": self.memory_manager.session_id
        }
    
    def _handle_plan_modifications(self, user_input: str) -> Dict[str, Any]:
        """Handle requests to modify the implementation plan."""
        
        response = f"""🔧 **Plan Modification Request:**

I understand you'd like to modify: {user_input}

To help you make the changes, I can:

• **Regenerate Technical Design** - If you want changes to the architecture
• **Adjust Implementation Tasks** - If you want different task prioritization
• **Update Expert Suggestions** - If you want to include/exclude different recommendations
• **Revise Specific Components** - Focus on particular areas like data model, automation, etc.

Please specify what you'd like to change:

**Examples:**
• "I want to add a mobile app component"
• "Change the security model to be more restrictive"
• "Add integration with our existing CRM system"
• "Simplify the automation to use flows instead of Apex"

What specific changes would you like to make?"""

        self.memory_manager.add_message("agent", response, "plan_modifications")
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "plan_modifications",
            "session_id": self.memory_manager.session_id
        }
    
    def _clarify_final_review_intent(self, user_input: str) -> Dict[str, Any]:
        """Clarify what the user wants to do in the final review stage."""
        
        response = f"""🤔 **Let me clarify what you'd like to do:**

You said: "{user_input}"

At this stage, you can:

• **✅ Approve the Plan** - If you're satisfied with the technical design and implementation tasks
• **📋 Review Details** - If you want to see more specifics about any component
• **🔧 Request Changes** - If you want to modify any aspect of the solution
• **❓ Ask Questions** - If you need clarification about the implementation

**Common Actions:**
• "Yes, approve the plan" - to finalize everything
• "Show me the data model details" - to review specific components  
• "I want to change the security approach" - to request modifications
• "How long will implementation take?" - to ask questions

What would you like to do with your implementation plan?"""

        self.memory_manager.add_message("agent", response, "clarify_intent")
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "clarify_intent",
            "session_id": self.memory_manager.session_id
        }
    
    def _format_expert_suggestions(self, expert_analysis: Dict[str, Any]) -> str:
        """Format expert suggestions in a user-friendly way."""
        
        if not expert_analysis:
            return "No specific suggestions available."
        
        formatted = []
        
        # Format requirement gaps
        if expert_analysis.get("requirement_gaps"):
            formatted.append("🔍 **Missing Requirements Identified:**")
            for gap in expert_analysis["requirement_gaps"][:3]:  # Show top 3
                formatted.append(f"   • {gap}")
            if len(expert_analysis["requirement_gaps"]) > 3:
                formatted.append(f"   • ...and {len(expert_analysis['requirement_gaps']) - 3} more")
        
        # Format best practices
        if expert_analysis.get("best_practices"):
            formatted.append("\n⭐ **Best Practice Recommendations:**")
            for practice in expert_analysis["best_practices"][:3]:  # Show top 3
                formatted.append(f"   • {practice}")
            if len(expert_analysis["best_practices"]) > 3:
                formatted.append(f"   • ...and {len(expert_analysis['best_practices']) - 3} more")
        
        # Format enhancements
        if expert_analysis.get("suggested_enhancements"):
            formatted.append("\n🚀 **Value-Adding Enhancements:**")
            for enhancement in expert_analysis["suggested_enhancements"][:3]:  # Show top 3
                formatted.append(f"   • {enhancement}")
            if len(expert_analysis["suggested_enhancements"]) > 3:
                formatted.append(f"   • ...and {len(expert_analysis['suggested_enhancements']) - 3} more")
        
        return "\n".join(formatted) if formatted else "The expert analysis is still processing. Please try again."
    
    def _create_numbered_suggestions_list(self) -> str:
        """Create a numbered list of suggestions for easy selection."""
        
        if not self.expert_suggestions:
            return "No suggestions available."
        
        numbered_suggestions = []
        counter = 1
        
        # Add gaps
        for gap in self.expert_suggestions.get("requirement_gaps", []):
            numbered_suggestions.append(f"{counter}. **Gap**: {gap}")
            counter += 1
        
        # Add best practices
        for practice in self.expert_suggestions.get("best_practices", []):
            numbered_suggestions.append(f"{counter}. **Best Practice**: {practice}")
            counter += 1
        
        # Add enhancements
        for enhancement in self.expert_suggestions.get("suggested_enhancements", []):
            numbered_suggestions.append(f"{counter}. **Enhancement**: {enhancement}")
            counter += 1
        
        return "\n".join(numbered_suggestions) if numbered_suggestions else "No numbered suggestions available."
    
    def _format_expert_suggestions_for_plan(self) -> str:
        """Format expert suggestions for inclusion in the implementation plan."""
        
        if not self.expert_suggestions:
            return "No expert suggestions were incorporated into this plan."
        
        # Check user's choice from conversation history
        recent_messages = self.memory_manager.conversation_history[-5:]
        suggestions_included = "none"
        
        for msg in recent_messages:
            if msg.role == "agent":
                if "suggestions_accepted" in msg.message_type:
                    suggestions_included = "all"
                    break
                elif "original_requirements_only" in msg.message_type:
                    suggestions_included = "none"
                    break
                elif "custom_selection" in msg.message_type:
                    suggestions_included = "custom"
                    break
        
        if suggestions_included == "none":
            return "User chose to proceed with original requirements only. Expert suggestions are noted as optional future enhancements."
        elif suggestions_included == "all":
            return f"""All expert suggestions have been incorporated into this plan:

REQUIREMENT GAPS ADDRESSED:
{chr(10).join(f"- {gap}" for gap in self.expert_suggestions.get('requirement_gaps', []))}

BEST PRACTICES INCLUDED:
{chr(10).join(f"- {practice}" for practice in self.expert_suggestions.get('best_practices', []))}

VALUE ENHANCEMENTS ADDED:
{chr(10).join(f"- {enhancement}" for enhancement in self.expert_suggestions.get('suggested_enhancements', []))}"""
        else:
            return "User selected specific expert suggestions. Custom selections have been incorporated into this plan."
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history for display."""
        return [msg.to_dict() for msg in self.memory_manager.conversation_history]
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.memory_manager.session_id 