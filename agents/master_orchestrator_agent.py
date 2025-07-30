"""
Master Orchestrator Agent - Single Point of User Interaction
A hierarchical orchestrator that manages CrewAI multi-agent collaboration while
maintaining a conversational interface with users.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

# CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.crew import CrewOutput

# Local imports
from .memory_manager import MemoryManager
from salesforce_crew import SalesforceImplementationCrew, analyze_salesforce_requirement
from .error_handler import error_handler, safe_execute

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Conversation states for the orchestrator."""
    INITIAL = "initial"
    CLARIFYING = "clarifying"
    REQUIREMENTS_VALIDATED = "requirements_validated"
    CREW_PROCESSING = "crew_processing"
    PLAN_REVIEW = "plan_review"
    PLAN_REFINEMENT = "plan_refinement"
    COMPLETED = "completed"

class MasterOrchestratorAgent:
    """
    Master Orchestrator Agent - Single Point of User Interaction
    
    This agent serves as the primary interface between users and the CrewAI multi-agent system.
    It handles:
    - User conversation and requirement gathering
    - Requirement validation and clarification
    - Orchestrating the CrewAI team (Schema Expert, Technical Architect, Dependency Resolver)
    - Presenting results and managing plan refinements
    - Maintaining conversation context and memory
    
    The orchestration is hierarchical with this agent as the central coordinator.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the Master Orchestrator Agent.
        
        Args:
            session_id: Unique session identifier for memory management
        """
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_manager = MemoryManager(self.session_id)
        self.conversation_state = ConversationState.INITIAL
        
        # Current session data
        self.current_requirement = None
        self.clarified_requirement = None
        self.crew_result = None
        self.implementation_plan = None
        
        # Initialize the CrewAI system
        self.crew_system = None
        self._initialize_crew_system()
        
        # Initialize the conversational agent
        self._initialize_orchestrator_agent()
        
        logger.info(f"Master Orchestrator Agent initialized for session: {self.session_id}")
    
    def _initialize_crew_system(self):
        """Initialize the CrewAI implementation crew."""
        try:
            self.crew_system = SalesforceImplementationCrew()
            logger.info("CrewAI system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CrewAI system: {e}")
            raise RuntimeError(f"CrewAI system initialization failed: {e}")
    
    def _initialize_orchestrator_agent(self):
        """Initialize the master orchestrator conversational agent."""
        self.orchestrator_agent = Agent(
            role="Master Salesforce Solution Orchestrator",
            goal="""Act as a helpful Salesforce consultant who proactively creates technical solutions 
                    for users, regardless of their technical expertise. When users provide business needs, 
                    make intelligent assumptions and create comprehensive solutions rather than asking 
                    excessive clarifying questions. Be solution-oriented and user-friendly.""",
            backstory="""You are a proactive Salesforce Solution Orchestrator who believes in 
                        'show, don't ask'. You excel at:
                        - Making intelligent assumptions from minimal business requirements
                        - Creating comprehensive technical solutions proactively
                        - Being helpful to non-technical users by providing concrete solutions
                        - Only asking clarifying questions when absolutely critical
                        - Presenting complete implementation plans with best practices
                        - Coordinating specialized agent teams efficiently
                        
                        Your philosophy: When a user describes a business need, immediately 
                        create a practical Salesforce solution using industry best practices 
                        and common patterns. Don't interrogate users - help them!
                        
                        You work with a team of specialized agents:
                        - Schema Expert: Salesforce data model and object design
                        - Technical Architect: Complete technical architecture design  
                        - Dependency Resolver: Implementation planning and task sequencing
                        
                        Your role is to be the helpful consultant who delivers solutions, 
                        not the gatekeeper who asks endless questions.""",
            verbose=True,
            allow_delegation=False,
            memory=True
        )
    
    @safe_execute("Processing user input")
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Main entry point for user interactions.
        
        Args:
            user_input: User's message/requirement
            
        Returns:
            Dict containing response, state, and any additional data
        """
        if not user_input.strip():
            return {
                "response": "I'm here to help you create Salesforce solutions. Please share your business requirement or ask me anything about Salesforce implementation.",
                "state": self.conversation_state.value,
                "type": "prompt",
                "session_id": self.session_id
            }
        
        # Store user input
        self.memory_manager.add_message("user", user_input, "user_input")
        
        # Route to appropriate handler based on conversation state
        try:
            if self.conversation_state == ConversationState.INITIAL:
                return self._handle_initial_requirement(user_input)
            elif self.conversation_state == ConversationState.CLARIFYING:
                return self._handle_clarification_response(user_input)
            elif self.conversation_state == ConversationState.REQUIREMENTS_VALIDATED:
                return self._initiate_crew_processing()
            elif self.conversation_state == ConversationState.CREW_PROCESSING:
                return self._check_crew_progress()
            elif self.conversation_state == ConversationState.PLAN_REVIEW:
                return self._handle_plan_review_response(user_input)
            elif self.conversation_state == ConversationState.PLAN_REFINEMENT:
                return self._handle_plan_refinement(user_input)
            elif self.conversation_state == ConversationState.COMPLETED:
                return self._handle_post_completion_query(user_input)
            else:
                return self._handle_general_conversation(user_input)
                
        except Exception as e:
            error_response = error_handler.handle_error(e, "User input processing")
            return {
                "response": f"I encountered an issue while processing your request: {error_response.get('message', str(e))}. Please try again.",
                "state": self.conversation_state.value,
                "type": "error",
                "session_id": self.session_id
            }
    
    def _handle_initial_requirement(self, requirement: str) -> Dict[str, Any]:
        """Handle the initial business requirement from the user."""
        
        # Create a task for the orchestrator to analyze the requirement
        analysis_task = Task(
            description=f"""
            Analyze this business requirement and be as helpful as possible:
            
            Requirement: {requirement}
            
            Your approach should be:
            1. Assume this is a valid business need that deserves a solution
            2. Make intelligent assumptions based on industry best practices
            3. Default to proceeding with solution design unless something is genuinely unclear
            4. Only ask questions if absolutely critical information is missing
            
            PREFERRED RESPONSE: "I understand you need [summarize requirement]. Let me create 
            a comprehensive Salesforce solution for you using industry best practices. I'll 
            design [specific solution elements] and provide you with a complete implementation plan."
            
            ONLY ask clarifying questions if the requirement is genuinely ambiguous or 
            contradictory. Most business needs can be solved with standard Salesforce patterns.
            
            Be helpful, not interrogative. Show solutions, don't ask endless questions.
            
            Provide a conversational response as if speaking directly to the user.
            """,
            expected_output="A helpful, solution-oriented response that confirms understanding and offers to create a comprehensive Salesforce solution. Default to proceeding with solution design unless the requirement is genuinely unclear or contradictory.",
            agent=self.orchestrator_agent
        )
        
        # Execute the analysis
        analysis_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = analysis_crew.kickoff()
        response_text = str(result)
        
        # Store the initial requirement
        self.current_requirement = requirement
        
        # Determine next state based on response
        if self._needs_clarification(response_text):
            self.conversation_state = ConversationState.CLARIFYING
            response_type = "clarification_needed"
        else:
            self.conversation_state = ConversationState.REQUIREMENTS_VALIDATED
            response_type = "ready_to_proceed"
        
        # Store orchestrator response
        self.memory_manager.add_message("orchestrator", response_text, response_type)
        
        return {
            "response": response_text,
            "state": self.conversation_state.value,
            "type": response_type,
            "session_id": self.session_id
        }
    
    def _handle_clarification_response(self, user_response: str) -> Dict[str, Any]:
        """Handle user responses to clarification questions."""
        
        # Get conversation context for the task
        conversation_context = self._get_conversation_context()
        
        clarification_task = Task(
            description=f"""
            The user has provided additional information about their requirement:
            
            User's Additional Information: {user_response}
            
            Previous Conversation Context:
            {conversation_context}
            
            Your task:
            1. Acknowledge the user's additional information
            2. Assess if you now have sufficient information to understand the core business need
            3. If still missing essential information, ask 1-2 focused follow-up questions
            4. If you have enough information, confirm understanding and offer to proceed with creating the technical solution
            
            Be conversational and ensure the user feels heard and understood.
            """,
            expected_output="A conversational response either asking follow-up questions or confirming readiness to create the technical solution.",
            agent=self.orchestrator_agent
        )
        
        clarification_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[clarification_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = clarification_crew.kickoff()
        response_text = str(result)
        
        # Update clarified requirement
        self.clarified_requirement = f"{self.current_requirement}\n\nAdditional Details: {user_response}"
        
        # Determine next state
        if self._ready_to_proceed(response_text):
            self.conversation_state = ConversationState.REQUIREMENTS_VALIDATED
            response_type = "ready_to_proceed"
        else:
            response_type = "needs_more_clarification"
        
        self.memory_manager.add_message("orchestrator", response_text, response_type)
        
        return {
            "response": response_text,
            "state": self.conversation_state.value,
            "type": response_type,
            "session_id": self.session_id
        }
    
    def _initiate_crew_processing(self) -> Dict[str, Any]:
        """Initiate the CrewAI multi-agent processing."""
        
        self.conversation_state = ConversationState.CREW_PROCESSING
        
        # Get the final requirement (clarified if available, otherwise original)
        final_requirement = self.clarified_requirement or self.current_requirement
        
        # Start the CrewAI processing
        orchestrator_response = """🚀 **Initiating Salesforce Solution Design**

I'm now engaging our specialist team to create your comprehensive Salesforce solution:

**🔍 Schema Expert** - Analyzing your data model requirements and existing Salesforce org
**🏗️ Technical Architect** - Designing the complete technical architecture  
**📋 Dependency Resolver** - Creating the detailed implementation plan with tasks and timeline

This multi-agent collaboration will ensure we deliver a thorough, professional-grade solution that follows Salesforce best practices.

*Processing your requirement... This may take a moment as our agents collaborate.*"""

        self.memory_manager.add_message("orchestrator", orchestrator_response, "crew_initiated")
        
        # Start the crew processing in the background (async-like behavior)
        try:
            # Use the existing CrewAI integration
            crew_result = analyze_salesforce_requirement(final_requirement)
            
            if crew_result.get('success'):
                self.crew_result = crew_result
                return self._present_crew_results()
            else:
                error_msg = crew_result.get('error', 'Unknown error during processing')
                return self._handle_crew_error(error_msg)
                
        except Exception as e:
            return self._handle_crew_error(str(e))
    
    def _present_crew_results(self) -> Dict[str, Any]:
        """Present the results of the CrewAI processing to the user."""
        
        self.conversation_state = ConversationState.PLAN_REVIEW
        
        if not self.crew_result or not self.crew_result.get('result'):
            return self._handle_crew_error("No results generated from crew processing")
        
        # Extract the implementation plan from crew results
        crew_output = self.crew_result.get('result')
        
        # CrewOutput object has different ways to access data
        try:
            import json
            import re
            
            # Debug: Log what we received
            print(f"🔍 DEBUG: Crew output type: {type(crew_output)}")
            print(f"🔍 DEBUG: Crew output attributes: {dir(crew_output) if hasattr(crew_output, '__dict__') else 'No attributes'}")
            
            if hasattr(crew_output, 'raw'):
                # Try to get the raw output first
                raw_data = crew_output.raw
                print(f"🔍 DEBUG: Using raw attribute: {type(raw_data)}")
            elif hasattr(crew_output, 'result'):
                # Try to get the result attribute
                raw_data = crew_output.result
                print(f"🔍 DEBUG: Using result attribute: {type(raw_data)}")
            elif hasattr(crew_output, 'json_dict'):
                # Try to get the json_dict if available
                raw_data = crew_output.json_dict
                print(f"🔍 DEBUG: Using json_dict attribute: {type(raw_data)}")
            else:
                # Fall back to string conversion
                raw_data = str(crew_output)
                print(f"🔍 DEBUG: Using string conversion: {len(raw_data)} chars")
            
            # Ensure we have a dictionary, not a string
            if isinstance(raw_data, str):
                try:
                    implementation_data = json.loads(raw_data)
                    print(f"🔍 DEBUG: Successfully parsed JSON from string")
                except json.JSONDecodeError:
                    print(f"🔍 DEBUG: JSON parsing failed, extracting tasks manually from text")
                    # Try to extract tasks from the text manually
                    implementation_data = self._extract_tasks_from_text(raw_data)
            elif isinstance(raw_data, dict):
                implementation_data = raw_data
                print(f"🔍 DEBUG: Using dict directly")
            else:
                # Convert other types to string and try to parse
                try:
                    implementation_data = json.loads(str(raw_data))
                    print(f"🔍 DEBUG: Successfully parsed JSON from converted string")
                except:
                    print(f"🔍 DEBUG: All parsing failed, extracting from text")
                    implementation_data = self._extract_tasks_from_text(str(raw_data))
            
            # Ensure we have the required structure
            if not isinstance(implementation_data, dict):
                implementation_data = self._extract_tasks_from_text(str(raw_data))
            
            # Validate and ensure required fields exist
            if 'tasks' not in implementation_data:
                implementation_data['tasks'] = []
            if 'project_summary' not in implementation_data:
                implementation_data['project_summary'] = {"total_effort": "TBD", "team_size": "TBD", "duration": "TBD"}
            
            print(f"🔍 DEBUG: Final implementation_data has {len(implementation_data.get('tasks', []))} tasks")
                    
        except Exception as e:
            return self._handle_crew_error(f"Failed to extract results from crew output: {str(e)}")
        
        # Format the results for user presentation
        results_summary = self._format_crew_results_summary(implementation_data)
        
        response = f"""✅ **Salesforce Solution Design Complete!**

Our specialist team has completed the analysis and created your comprehensive solution:

{results_summary}

**📋 What You Have Now:**
• **Complete Technical Architecture** - Data model, automation, security, and UI specifications
• **Detailed Implementation Plan** - {implementation_data.get('tasks', []).__len__()} specific tasks with dependencies  
• **Professional Project Roadmap** - Timeline, effort estimates, and success criteria
• **Risk Assessment** - Potential challenges and mitigation strategies

**🔍 Review Options:**
• **"Show details"** - See specific components of the technical design
• **"Explain tasks"** - Review the implementation timeline and tasks
• **"Approve plan"** - Confirm the solution and receive final documentation
• **"Modify [aspect]"** - Request changes to specific parts of the solution

How would you like to proceed with your Salesforce solution?"""

        self.memory_manager.add_message("orchestrator", response, "crew_results_presented")
        
        # Store the implementation plan
        self.implementation_plan = implementation_data
        
        return {
            "response": response,
            "state": self.conversation_state.value,
            "type": "crew_results",
            "implementation_plan": implementation_data,
            "session_id": self.session_id
        }
    
    def _handle_plan_review_response(self, user_input: str) -> Dict[str, Any]:
        """Handle user responses during plan review."""
        
        user_input_lower = user_input.lower().strip()
        
        if any(keyword in user_input_lower for keyword in ["details", "show", "explain", "tell me more"]):
            return self._provide_plan_details(user_input)
        elif any(keyword in user_input_lower for keyword in ["tasks", "timeline", "implementation"]):
            return self._explain_implementation_tasks()
        elif any(keyword in user_input_lower for keyword in ["approve", "accept", "looks good", "proceed"]):
            return self._approve_final_plan()
        elif any(keyword in user_input_lower for keyword in ["modify", "change", "adjust", "different"]):
            return self._initiate_plan_modification(user_input)
        else:
            return self._clarify_review_intent(user_input)
    
    def _provide_plan_details(self, user_input: str) -> Dict[str, Any]:
        """Provide detailed information about the technical plan."""
        
        if not self.implementation_plan:
            return {
                "response": "No implementation plan available. Please restart the solution design process.",
                "state": self.conversation_state.value,
                "type": "error",
                "session_id": self.session_id
            }
        
        # Extract specific details from the implementation plan
        details_response = self._format_detailed_plan_view(self.implementation_plan)
        
        response = f"""📋 **Detailed Technical Specifications**

{details_response}

**Additional Information Available:**
• **"Show tasks"** - View the complete implementation timeline
• **"Explain [component]"** - Get details about specific technical components  
• **"Approve plan"** - Finalize the solution
• **"Modify [aspect]"** - Request changes

What specific aspect would you like to explore further?"""

        self.memory_manager.add_message("orchestrator", response, "plan_details_provided")
        
        return {
            "response": response,
            "state": self.conversation_state.value,
            "type": "plan_details",
            "session_id": self.session_id
        }
    
    def _explain_implementation_tasks(self) -> Dict[str, Any]:
        """Explain the implementation tasks and timeline."""
        
        if not self.implementation_plan:
            return {
                "response": "No implementation plan available.",
                "state": self.conversation_state.value,
                "type": "error",
                "session_id": self.session_id
            }
        
        tasks_explanation = self._format_implementation_timeline(self.implementation_plan)
        
        response = f"""📋 **Implementation Timeline & Tasks**

{tasks_explanation}

**Ready to Proceed?**
• **"Approve plan"** - Confirm this implementation approach
• **"Modify timeline"** - Adjust the task sequencing or priorities
• **"Show details"** - View technical specifications
• **"Change [aspect]"** - Request modifications to specific components

What would you like to do next?"""

        self.memory_manager.add_message("orchestrator", response, "tasks_explained")
        
        return {
            "response": response,
            "state": self.conversation_state.value,
            "type": "tasks_explanation",
            "session_id": self.session_id
        }
    
    def _approve_final_plan(self) -> Dict[str, Any]:
        """Handle final plan approval."""
        
        self.conversation_state = ConversationState.COMPLETED
        
        approval_response = """🎉 **Salesforce Solution Approved!**

Your comprehensive Salesforce implementation plan is now finalized and ready for development.

**📦 Complete Solution Package:**
✅ **Technical Architecture** - Detailed schema, automation, and UI specifications
✅ **Implementation Roadmap** - Sequenced tasks with dependencies and timelines
✅ **Project Documentation** - User stories, acceptance criteria, and testing guidelines  
✅ **Risk Management** - Identified challenges with mitigation strategies

**📈 Implementation Summary:**
• **Estimated Timeline**: {self._get_total_timeline()}
• **Total Tasks**: {self._get_total_tasks()} organized across multiple phases
• **Team Requirements**: {self._get_team_requirements()}
• **Success Metrics**: Clearly defined acceptance criteria for each component

**🚀 Next Steps:**
1. **Begin Implementation** - Start with the foundational tasks identified in Phase 1
2. **Team Coordination** - Distribute technical specifications to your development team
3. **Progress Tracking** - Use the task breakdown for project management
4. **Quality Assurance** - Follow the testing strategies outlined in the plan

**💬 Ongoing Support:**
• Ask follow-up questions about any technical component
• Request clarifications on implementation approaches  
• Seek guidance on Salesforce best practices
• Start a new requirement analysis anytime

Thank you for using the Salesforce AI Agent System! Your solution is ready for successful implementation. 🎯"""

        self.memory_manager.add_message("orchestrator", approval_response, "plan_approved")
        
        # Save the complete approved plan
        self._save_approved_plan()
        
        return {
            "response": approval_response,
            "state": self.conversation_state.value,
            "type": "plan_approved",
            "session_id": self.session_id,
            "plan_approved": True
        }
    
    def _initiate_plan_modification(self, user_input: str) -> Dict[str, Any]:
        """Handle requests to modify the plan."""
        
        self.conversation_state = ConversationState.PLAN_REFINEMENT
        
        modification_response = f"""🔧 **Plan Modification Request**

I understand you'd like to modify: "{user_input}"

To make the appropriate changes, I can work with our specialist team to:

**🔄 Available Modifications:**
• **Schema Changes** - Adjust data model, objects, or field structures
• **Architecture Updates** - Modify automation, security, or integration approaches
• **Implementation Adjustments** - Change task priorities, sequencing, or timelines
• **Scope Refinements** - Add, remove, or modify functional requirements

**🎯 Specific Examples:**
• "Add mobile app capabilities"
• "Simplify the automation to use Flows instead of Apex"
• "Include integration with our existing CRM"
• "Make the security model more restrictive"
• "Reduce the timeline by focusing on core features first"

**Next Steps:**
Please describe specifically what you'd like to change, and I'll coordinate with our technical team to update the solution accordingly.

What specific modifications would you like to make to your Salesforce solution?"""

        self.memory_manager.add_message("orchestrator", modification_response, "modification_initiated")
        
        return {
            "response": modification_response,
            "state": self.conversation_state.value,
            "type": "modification_request",
            "session_id": self.session_id
        }
    
    def _handle_plan_refinement(self, user_input: str) -> Dict[str, Any]:
        """Handle specific plan refinement requests."""
        
        # This would involve re-running parts of the CrewAI system with the modification requests
        # For now, we'll provide a structured response and potentially re-run the crew
        
        refinement_task = Task(
            description=f"""
            The user wants to modify the existing Salesforce solution plan:
            
            User's Modification Request: {user_input}
            
            Current Implementation Plan Summary:
            {self._get_current_plan_summary()}
            
            Your task:
            1. Understand the specific changes requested
            2. Assess the impact of these changes on the overall solution
            3. Provide options for implementing the requested modifications
            4. Offer to re-engage the specialist team if major changes are needed
            
            Provide a clear response about how we can accommodate their request.
            """,
            expected_output="A response explaining how the modifications can be implemented and next steps.",
            agent=self.orchestrator_agent
        )
        
        refinement_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[refinement_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = refinement_crew.kickoff()
        response_text = str(result)
        
        # Add option to re-run the crew with modifications
        enhanced_response = f"""{response_text}

**🔄 Implementation Options:**
• **"Apply changes"** - I'll update the current plan with these modifications
• **"Re-analyze with changes"** - I'll engage our full technical team to redesign the solution
• **"Show impact"** - See how these changes affect the existing plan
• **"Keep original"** - Return to the original plan without changes

How would you like to proceed with these modifications?"""

        self.memory_manager.add_message("orchestrator", enhanced_response, "refinement_options")
        
        return {
            "response": enhanced_response,
            "state": self.conversation_state.value,
            "type": "refinement_options",
            "session_id": self.session_id
        }
    
    def _handle_post_completion_query(self, user_input: str) -> Dict[str, Any]:
        """Handle questions after plan completion."""
        
        post_completion_task = Task(
            description=f"""
            The user has a follow-up question about their completed Salesforce implementation plan:
            
            User Question: {user_input}
            
            Implementation Plan Context:
            {self._get_current_plan_summary()}
            
            Your task:
            1. Provide helpful information about their approved plan
            2. Clarify any technical aspects they're asking about
            3. Offer additional guidance on implementation approaches
            4. If they want to start a new requirement, guide them appropriately
            
            Be helpful and reference their specific approved solution.
            """,
            expected_output="A helpful response to their follow-up question with relevant context from their approved plan.",
            agent=self.orchestrator_agent
        )
        
        follow_up_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[post_completion_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = follow_up_crew.kickoff()
        response_text = str(result)
        
        self.memory_manager.add_message("orchestrator", response_text, "post_completion_response")
        
        return {
            "response": response_text,
            "state": self.conversation_state.value,
            "type": "follow_up",
            "session_id": self.session_id
        }
    
    def _handle_general_conversation(self, user_input: str) -> Dict[str, Any]:
        """Handle general conversation and questions."""
        
        general_task = Task(
            description=f"""
            Respond to this general query about Salesforce or the solution process:
            
            User Input: {user_input}
            
            Conversation Context:
            {self._get_conversation_context()}
            
            Provide a helpful response while staying focused on Salesforce solutions and maintaining
            your role as a master orchestrator for Salesforce implementation planning.
            """,
            expected_output="A helpful response that addresses the user's query while maintaining context.",
            agent=self.orchestrator_agent
        )
        
        general_crew = Crew(
            agents=[self.orchestrator_agent],
            tasks=[general_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = general_crew.kickoff()
        response_text = str(result)
        
        self.memory_manager.add_message("orchestrator", response_text, "general_response")
        
        return {
            "response": response_text,
            "state": self.conversation_state.value,
            "type": "general_conversation",
            "session_id": self.session_id
        }
    
    # Helper methods
    def _needs_clarification(self, response: str) -> bool:
        """Determine if the response indicates need for clarification.
        
        Only return True for genuinely unclear or contradictory requirements.
        Default to proceeding with solution design.
        """
        # Only trigger clarification for genuinely problematic cases
        critical_clarification_indicators = [
            "completely unclear", "contradictory requirement", "impossible to determine",
            "genuinely ambiguous", "cannot proceed without", "critical information missing"
        ]
        
        # Check if response explicitly says it's ready to proceed
        proceed_indicators = [
            "let me create", "I'll design", "I'll provide", "comprehensive solution",
            "implementation plan", "ready to proceed", "move forward"
        ]
        
        # If it says it's ready to proceed, don't ask for clarification
        if any(indicator in response.lower() for indicator in proceed_indicators):
            return False
            
        # Only ask for clarification in truly critical cases
        return any(indicator in response.lower() for indicator in critical_clarification_indicators)
    
    def _ready_to_proceed(self, response: str) -> bool:
        """Determine if the response indicates readiness to proceed."""
        proceed_indicators = [
            "ready to proceed", "sufficient information", "clear understanding",
            "move forward", "create the solution", "design the solution"
        ]
        return any(indicator in response.lower() for indicator in proceed_indicators)
    
    def _handle_crew_error(self, error_message: str) -> Dict[str, Any]:
        """Handle errors from CrewAI processing."""
        
        error_response = f"""❌ **Processing Error**

I encountered an issue while our specialist team was analyzing your requirement:

**Error**: {error_message}

**Recovery Options:**
• **"Try again"** - I'll restart the analysis with our technical team
• **"Simplify requirement"** - Provide a more focused version of your requirement
• **"Manual approach"** - I'll create a solution using alternative methods

Would you like me to try processing your requirement again, or would you prefer to refine your requirement first?"""

        self.memory_manager.add_message("orchestrator", error_response, "crew_error")
        
        # Reset to clarifying state to allow recovery
        self.conversation_state = ConversationState.CLARIFYING
        
        return {
            "response": error_response,
            "state": self.conversation_state.value,
            "type": "error_recovery",
            "session_id": self.session_id
        }
    
    def _format_crew_results_summary(self, implementation_data: Dict[str, Any]) -> str:
        """Format crew results into a user-friendly summary."""
        
        if not implementation_data:
            return "No implementation data available."
        
        summary_parts = []
        
        # Add Salesforce data analysis summary first
        sf_data_summary = self._format_salesforce_data_summary(implementation_data)
        if sf_data_summary:
            summary_parts.append(sf_data_summary)
        
        # Project summary
        project_summary = implementation_data.get('project_summary', {})
        if project_summary:
            summary_parts.append(f"""**📊 Project Overview:**
• **Timeline**: {project_summary.get('duration', 'TBD')}
• **Effort**: {project_summary.get('total_effort', 'TBD')}
• **Team Size**: {project_summary.get('team_size', 'TBD')}""")
        
        # Tasks summary
        tasks = implementation_data.get('tasks', [])
        if tasks:
            summary_parts.append(f"""**📋 Implementation Tasks:**
• **Total Tasks**: {len(tasks)} organized tasks
• **Implementation Order**: Sequenced with clear dependencies
• **Roles Required**: Admin and Developer tasks identified""")
        
        # Key components
        if tasks:
            admin_tasks = [t for t in tasks if t.get('role') == 'Admin']
            dev_tasks = [t for t in tasks if t.get('role') == 'Developer']
            summary_parts.append(f"""**🔧 Task Breakdown:**
• **Admin Tasks**: {len(admin_tasks)} configuration and setup tasks
• **Developer Tasks**: {len(dev_tasks)} custom development tasks""")
        
        # Risks and success criteria
        risks = implementation_data.get('key_risks', [])
        success_criteria = implementation_data.get('success_criteria', [])
        
        if risks or success_criteria:
            summary_parts.append(f"""**⚠️ Risk Management:**
• **Identified Risks**: {len(risks)} potential challenges with mitigation strategies
• **Success Criteria**: {len(success_criteria)} measurable outcomes defined""")
        
        return "\n\n".join(summary_parts) if summary_parts else "Implementation plan generated successfully."
    
    def _format_detailed_plan_view(self, implementation_data: Dict[str, Any]) -> str:
        """Format detailed view of the implementation plan."""
        
        if not implementation_data:
            return "No detailed plan data available."
        
        details = []
        
        # Tasks details
        tasks = implementation_data.get('tasks', [])
        if tasks:
            details.append("**📋 Implementation Tasks:**")
            for i, task in enumerate(tasks[:5], 1):  # Show first 5 tasks
                details.append(f"""
{i}. **{task.get('title', 'Untitled Task')}**
   • **Description**: {task.get('description', 'No description')}
   • **Effort**: {task.get('effort', 'TBD')}
   • **Role**: {task.get('role', 'TBD')}
   • **Dependencies**: {', '.join(task.get('dependencies', [])) or 'None'}""")
            
            if len(tasks) > 5:
                details.append(f"\n   ... and {len(tasks) - 5} more tasks")
        
        # Implementation order
        impl_order = implementation_data.get('implementation_order', [])
        if impl_order:
            details.append(f"\n**🔄 Implementation Sequence:**\n{' → '.join(impl_order)}")
        
        # Key risks
        risks = implementation_data.get('key_risks', [])
        if risks:
            details.append("\n**⚠️ Key Risks:**")
            for risk in risks:
                details.append(f"• {risk}")
        
        # Success criteria
        success = implementation_data.get('success_criteria', [])
        if success:
            details.append("\n**✅ Success Criteria:**")
            for criterion in success:
                details.append(f"• {criterion}")
        
        return "\n".join(details) if details else "No detailed information available."
    
    def _format_implementation_timeline(self, implementation_data: Dict[str, Any]) -> str:
        """Format implementation timeline view."""
        
        tasks = implementation_data.get('tasks', [])
        if not tasks:
            return "No timeline data available."
        
        timeline = []
        current_phase = None
        
        # Group tasks by dependencies to show phases
        independent_tasks = [t for t in tasks if not t.get('dependencies')]
        dependent_tasks = [t for t in tasks if t.get('dependencies')]
        
        if independent_tasks:
            timeline.append("**🚀 Phase 1 - Foundation (Parallel Execution):**")
            for task in independent_tasks:
                timeline.append(f"• {task.get('title')} ({task.get('effort', 'TBD')})")
        
        if dependent_tasks:
            timeline.append("\n**🔧 Phase 2+ - Dependent Components:**")
            for task in dependent_tasks:
                deps = ', '.join(task.get('dependencies', []))
                timeline.append(f"• {task.get('title')} (depends on: {deps}) - {task.get('effort', 'TBD')}")
        
        # Add summary
        total_effort = implementation_data.get('project_summary', {}).get('total_effort', 'TBD')
        duration = implementation_data.get('project_summary', {}).get('duration', 'TBD')
        
        timeline.append(f"\n**📊 Timeline Summary:**")
        timeline.append(f"• **Total Effort**: {total_effort}")
        timeline.append(f"• **Expected Duration**: {duration}")
        timeline.append(f"• **Total Tasks**: {len(tasks)}")
        
        return "\n".join(timeline)
    
    def _get_conversation_context(self) -> str:
        """Get formatted conversation context."""
        messages = self.memory_manager.get_conversation_history()
        context_parts = []
        
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.get('role', 'unknown').title()
            content = msg.get('content', '')
            content = content[:200] + "..." if len(content) > 200 else content
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _get_current_plan_summary(self) -> str:
        """Get current plan summary for context."""
        if not self.implementation_plan:
            return "No current implementation plan."
        
        summary = []
        
        project_summary = self.implementation_plan.get('project_summary', {})
        if project_summary:
            summary.append(f"Project: {project_summary.get('duration', 'TBD')} timeline, {project_summary.get('total_effort', 'TBD')} effort")
        
        tasks = self.implementation_plan.get('tasks', [])
        if tasks:
            summary.append(f"Tasks: {len(tasks)} implementation tasks")
        
        return "; ".join(summary) if summary else "Implementation plan available."
    
    def _format_salesforce_data_summary(self, implementation_data: Dict[str, Any]) -> str:
        """Format Salesforce data access summary for user display."""
        
        # Look for salesforce_data_access in any of the implementation data
        all_data_access = {}
        
        # Check if implementation_data has salesforce_data_access directly
        if 'salesforce_data_access' in implementation_data:
            all_data_access['main'] = implementation_data['salesforce_data_access']
        
        # Check nested data structures for salesforce_data_access
        for key, value in implementation_data.items():
            if isinstance(value, dict) and 'salesforce_data_access' in value:
                all_data_access[key] = value['salesforce_data_access']
        
        if not all_data_access:
            return None
        
        # Aggregate data across all analyses
        total_api_calls = 0
        all_objects = set()
        all_fields = {}
        org_info = {}
        
        for analysis_name, data_access in all_data_access.items():
            if not isinstance(data_access, dict):
                continue
                
            total_api_calls += data_access.get('total_api_calls', 0)
            
            # Collect objects
            for obj_access in data_access.get('objects_analyzed', []):
                if isinstance(obj_access, dict):
                    all_objects.add(obj_access.get('object_name', 'Unknown'))
            
            # Collect fields
            fields_data = data_access.get('fields_analyzed', {})
            if isinstance(fields_data, dict):
                all_fields.update(fields_data)
            
            # Get org info
            if not org_info and data_access.get('org_info'):
                org_info = data_access['org_info']
        
        if not (total_api_calls or all_objects or all_fields):
            return None
        
        # Format the summary
        summary_parts = []
        
        # Connection info
        if org_info:
            instance_url = org_info.get('instance_url', 'Unknown')
            summary_parts.append(f"**🌐 Salesforce Org Analysis:** Connected to {instance_url}")
        
        # Data access metrics
        metrics = []
        if total_api_calls > 0:
            metrics.append(f"{total_api_calls} API calls")
        if all_objects:
            metrics.append(f"{len(all_objects)} objects analyzed")
        if all_fields:
            total_fields = sum(field_info.get('field_count', 0) for field_info in all_fields.values() if isinstance(field_info, dict))
            if total_fields > 0:
                metrics.append(f"{total_fields} fields examined")
        
        if metrics:
            summary_parts.append(f"**📊 Real-time Data Retrieved:** {', '.join(metrics)}")
        
        # Objects breakdown
        if all_objects:
            objects_list = sorted(list(all_objects))
            custom_objects = [obj for obj in objects_list if obj.endswith('__c')]
            standard_objects = [obj for obj in objects_list if not obj.endswith('__c')]
            
            objects_summary = []
            if custom_objects:
                objects_summary.append(f"{len(custom_objects)} custom objects")
            if standard_objects:
                objects_summary.append(f"{len(standard_objects)} standard objects")
            
            if objects_summary:
                summary_parts.append(f"**📋 Objects Analyzed:** {', '.join(objects_summary)}")
        
        return "\n• ".join(summary_parts) if summary_parts else None
    
    def _save_approved_plan(self):
        """Save the approved implementation plan."""
        if self.implementation_plan:
            approved_plan = {
                "requirement": self.clarified_requirement or self.current_requirement,
                "implementation_plan": self.implementation_plan,
                "approved_at": datetime.now().isoformat(),
                "session_id": self.session_id,
                "conversation_state": self.conversation_state.value
            }
            
            self.memory_manager.save_implementation_plan(approved_plan)
    
    def _get_total_timeline(self) -> str:
        """Get total timeline from implementation plan."""
        return self.implementation_plan.get('project_summary', {}).get('duration', 'To be determined')
    
    def _get_total_tasks(self) -> str:
        """Get total number of tasks."""
        tasks = self.implementation_plan.get('tasks', [])
        return str(len(tasks))
    
    def _get_team_requirements(self) -> str:
        """Get team requirements from plan."""
        return self.implementation_plan.get('project_summary', {}).get('team_size', 'To be determined')
    
    def _clarify_review_intent(self, user_input: str) -> Dict[str, Any]:
        """Clarify what the user wants to do during plan review."""
        
        clarification_response = f"""🤔 **I want to make sure I understand what you'd like to do:**

You said: "{user_input}"

**Available Actions:**
• **📋 "Show details"** - View technical specifications and architecture details
• **⏱️ "Explain tasks"** - See the implementation timeline and task breakdown  
• **✅ "Approve plan"** - Finalize the solution and receive documentation
• **🔧 "Modify [aspect]"** - Request changes to specific parts of the solution
• **❓ "Ask about [topic]"** - Get clarification on any aspect of the plan

**Common Examples:**
• "Show me the data model details"
• "Explain the automation approach" 
• "I want to change the security model"
• "Approve the complete plan"

What specific action would you like to take with your Salesforce solution plan?"""

        self.memory_manager.add_message("orchestrator", clarification_response, "intent_clarification")
        
        return {
            "response": clarification_response,
            "state": self.conversation_state.value,
            "type": "intent_clarification",
            "session_id": self.session_id
        }
    
    def _extract_tasks_from_text(self, text: str) -> Dict[str, Any]:
        """Extract implementation tasks from crew output text when JSON parsing fails."""
        import re
        
        print(f"🔍 DEBUG: Extracting tasks from text of length: {len(text)}")
        
        # Initialize the structure
        implementation_data = {
            "project_summary": {"total_effort": "TBD", "team_size": "TBD", "duration": "TBD"},
            "tasks": [],
            "key_risks": [],
            "success_criteria": [],
            "implementation_order": [],
            "raw_output": text
        }
        
        try:
            # Try to extract task-like patterns from the text
            # Look for numbered lists, bullet points, or task descriptions
            
            # Pattern 1: Look for numbered tasks (1., 2., etc.)
            numbered_tasks = re.findall(r'(\d+\.\s*[^\n]+(?:\n\s*[^\n\d]+)*)', text, re.MULTILINE)
            
            # Pattern 2: Look for bullet point tasks
            bullet_tasks = re.findall(r'([•\-\*]\s*[^\n]+(?:\n\s*[^\n•\-\*]+)*)', text, re.MULTILINE)
            
            # Pattern 3: Look for "Task" or "Step" keywords
            task_keywords = re.findall(r'((?:Task|Step|Phase)\s*\d*:?\s*[^\n]+(?:\n\s*[^\n]+)*)', text, re.MULTILINE | re.IGNORECASE)
            
            all_potential_tasks = numbered_tasks + bullet_tasks + task_keywords
            
            print(f"🔍 DEBUG: Found {len(all_potential_tasks)} potential tasks")
            
            # Convert to structured tasks
            for i, task_text in enumerate(all_potential_tasks[:20], 1):  # Limit to 20 tasks
                # Clean up the task text
                clean_task = re.sub(r'^[\d\.\-\*•]+\s*', '', task_text.strip())
                clean_task = re.sub(r'\s+', ' ', clean_task)
                
                if len(clean_task) > 10:  # Only include substantial tasks
                    # Determine role based on content
                    role = "Admin" if any(keyword in clean_task.lower() for keyword in 
                                       ['configure', 'setup', 'create field', 'permission', 'profile', 'workflow']) else "Developer"
                    
                    # Estimate effort based on complexity keywords
                    effort = "High" if any(keyword in clean_task.lower() for keyword in 
                                        ['custom', 'complex', 'integration', 'apex', 'trigger']) else "Medium"
                    
                    task = {
                        "id": f"T{i:03d}",
                        "title": clean_task[:100] + "..." if len(clean_task) > 100 else clean_task,
                        "description": clean_task,
                        "effort": effort,
                        "role": role,
                        "dependencies": [],
                        "acceptance_criteria": [f"Complete {clean_task.lower()}", "Test functionality", "Document changes"]
                    }
                    implementation_data["tasks"].append(task)
            
            # If no tasks found, create some default ones based on common Salesforce patterns
            if not implementation_data["tasks"]:
                print(f"🔍 DEBUG: No tasks extracted, creating default tasks")
                default_tasks = [
                    {
                        "id": "T001",
                        "title": "Analyze Current Salesforce Org",
                        "description": "Review existing objects, fields, and configurations",
                        "effort": "Medium",
                        "role": "Admin",
                        "dependencies": [],
                        "acceptance_criteria": ["Complete org analysis", "Document findings"]
                    },
                    {
                        "id": "T002",
                        "title": "Design Data Model",
                        "description": "Create custom objects and fields based on requirements",
                        "effort": "High",
                        "role": "Admin",
                        "dependencies": ["T001"],
                        "acceptance_criteria": ["Create objects", "Configure fields", "Set relationships"]
                    },
                    {
                        "id": "T003",
                        "title": "Configure Automation",
                        "description": "Set up workflows, process builder, or flows",
                        "effort": "Medium",
                        "role": "Admin",
                        "dependencies": ["T002"],
                        "acceptance_criteria": ["Configure automation", "Test processes"]
                    }
                ]
                implementation_data["tasks"] = default_tasks
            
            # Set implementation order
            implementation_data["implementation_order"] = [task["id"] for task in implementation_data["tasks"]]
            
            # Add some default risks and success criteria
            implementation_data["key_risks"] = [
                "Data migration complexity",
                "User adoption challenges", 
                "Integration dependencies"
            ]
            
            implementation_data["success_criteria"] = [
                "All requirements implemented",
                "User acceptance testing passed",
                "Performance benchmarks met"
            ]
            
            print(f"🔍 DEBUG: Final extracted data has {len(implementation_data['tasks'])} tasks")
            
        except Exception as e:
            print(f"⚠️ DEBUG: Error extracting tasks: {e}")
            # Return minimal structure on error
            pass
        
        return implementation_data
    
    # Public interface methods
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history for display."""
        return [msg.to_dict() for msg in self.memory_manager.conversation_history]
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id
    
    def get_current_state(self) -> str:
        """Get the current conversation state."""
        return self.conversation_state.value
    
    def get_implementation_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current implementation plan if available."""
        return self.implementation_plan 