import json
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from crewai.agent import Agent
from langchain_openai import ChatOpenAI

from agents.memory_manager import MemoryManager
from agents.salesforce_expert_agent import SalesforceExpertAgent
from config import Config

class SalesforceRequirementDeconstructorAgent:
    """
    Master Agent responsible for understanding business requirements,
    engaging in dialogue with users, and deconstructing requirements
    into structured Salesforce implementation plans.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.memory_manager = MemoryManager(session_id)
        self.conversation_state = "initial"  # initial, clarifying, expert_analysis, suggestions_review, planning, completed
        self.current_requirement = None
        self.expert_suggestions = None
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )
        
        # Initialize the Expert Agent
        self.expert_agent = SalesforceExpertAgent()
        
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
        """Incorporate all expert suggestions and proceed to planning."""
        
        response = """✅ **Excellent choice!** I'll incorporate all expert suggestions into your implementation plan.

These enhancements will make your Salesforce solution more robust, scalable, and aligned with industry best practices. 

🚀 **Ready to create your comprehensive implementation plan!**

Shall I proceed with generating the detailed implementation plan that includes both your requirements and all expert recommendations?"""

        self.memory_manager.add_message("agent", response, "suggestions_accepted")
        self.conversation_state = "planning"
        
        return {
            "response": response,
            "state": self.conversation_state,
            "type": "suggestions_accepted",
            "suggestions_included": "all",
            "session_id": self.memory_manager.session_id
        }
    
    def _proceed_with_original_requirements(self) -> Dict[str, Any]:
        """Proceed with original requirements only."""
        
        response = """👍 **Understood!** I'll create your implementation plan based on your original requirements.

The expert suggestions will be noted as optional enhancements that you can consider for future phases if needed.

🚀 **Ready to create your implementation plan!**

Shall I proceed with generating the detailed implementation plan based on your core requirements?"""

        self.memory_manager.add_message("agent", response, "original_requirements_only")
        self.conversation_state = "planning"
        
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