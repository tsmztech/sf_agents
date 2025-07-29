"""
Unified Agent System - Resolves conflicts between CrewAI and Legacy agent systems.
Provides a single interface for agent operations with proper error handling and memory management.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

# Safe imports
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.crew import CrewOutput
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    CrewOutput = None

from .memory_manager import MemoryManager
from .salesforce_expert_agent import SalesforceSchemaExpertAgent
from .technical_architect_agent import SalesforceTechnicalArchitectAgent
from .dependency_resolver_agent import DependencyResolverAgent

logger = logging.getLogger(__name__)

class AgentSystemType(Enum):
    """Available agent system types."""
    CREWAI = "crewai"
    LEGACY = "legacy"
    AUTO = "auto"  # Automatically choose based on availability and complexity

class UnifiedAgentSystem:
    """
    Unified Agent System that manages both CrewAI and Legacy agent implementations.
    Provides seamless switching and error recovery between systems.
    """
    
    def __init__(self, session_id: Optional[str] = None, preferred_system: AgentSystemType = AgentSystemType.AUTO):
        """
        Initialize the unified agent system.
        
        Args:
            session_id: Unique session identifier for memory management
            preferred_system: Preferred agent system to use
        """
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_manager = MemoryManager(self.session_id)
        self.preferred_system = preferred_system
        self.active_system = None
        self.conversation_state = "initial"
        
        # Initialize systems
        self._initialize_systems()
        
        # Choose active system
        self._select_active_system()
        
        logger.info(f"Unified Agent System initialized with {self.active_system.value} system")
    
    def _initialize_systems(self):
        """Initialize both agent systems if available."""
        self.crewai_system = None
        self.legacy_system = None
        
        # Initialize CrewAI system if available
        if CREWAI_AVAILABLE:
            try:
                from salesforce_crew import SalesforceImplementationCrew
                self.crewai_system = SalesforceImplementationCrew()
                logger.info("CrewAI system initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize CrewAI system: {e}")
        
        # Initialize Legacy system
        try:
            from .master_agent import SalesforceRequirementDeconstructorAgent
            self.legacy_system = SalesforceRequirementDeconstructorAgent(self.session_id)
            logger.info("Legacy system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Legacy system: {e}")
            raise RuntimeError("No agent systems available")
    
    def _select_active_system(self):
        """Select the active agent system based on preferences and availability."""
        if self.preferred_system == AgentSystemType.CREWAI and self.crewai_system:
            self.active_system = AgentSystemType.CREWAI
        elif self.preferred_system == AgentSystemType.LEGACY and self.legacy_system:
            self.active_system = AgentSystemType.LEGACY
        elif self.preferred_system == AgentSystemType.AUTO:
            # Auto-select: prefer CrewAI if available, fallback to Legacy
            if self.crewai_system:
                self.active_system = AgentSystemType.CREWAI
            elif self.legacy_system:
                self.active_system = AgentSystemType.LEGACY
            else:
                raise RuntimeError("No agent systems available")
        else:
            # Fallback selection
            if self.legacy_system:
                self.active_system = AgentSystemType.LEGACY
            elif self.crewai_system:
                self.active_system = AgentSystemType.CREWAI
            else:
                raise RuntimeError("No agent systems available")
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input using the active agent system with error recovery.
        
        Args:
            user_input: User's requirement or question
            
        Returns:
            Dictionary containing response and metadata
        """
        if not user_input.strip():
            return {
                "success": False,
                "error": "Empty input provided",
                "suggestion": "Please provide a valid requirement or question"
            }
        
        # Store user input in memory
        self.memory_manager.add_message("user", user_input, "requirement")
        
        try:
            if self.active_system == AgentSystemType.CREWAI:
                return self._process_with_crewai(user_input)
            else:
                return self._process_with_legacy(user_input)
        except Exception as e:
            logger.error(f"Error in {self.active_system.value} system: {e}")
            return self._handle_system_error(e, user_input)
    
    def _process_with_crewai(self, user_input: str) -> Dict[str, Any]:
        """Process input using CrewAI system."""
        try:
            # Determine if this is a complex requirement
            from salesforce_crew import is_complex_requirement, analyze_salesforce_requirement
            
            if is_complex_requirement(user_input):
                # Use full crew for complex requirements
                result = self.crewai_system.execute_requirement_analysis(user_input)
            else:
                # Use simple analysis for basic requirements
                result = analyze_salesforce_requirement(user_input)
            
            # Store response in memory
            if result.get('success'):
                response_content = self._format_crewai_response(result)
                self.memory_manager.add_message("agent", response_content, "crewai_response")
                
                return {
                    "success": True,
                    "response": response_content,
                    "system": "crewai",
                    "result": result,
                    "conversation_state": "completed"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"CrewAI processing error: {e}")
            raise
    
    def _process_with_legacy(self, user_input: str) -> Dict[str, Any]:
        """Process input using Legacy system."""
        try:
            result = self.legacy_system.process_user_input(user_input)
            
            # Update conversation state
            self.conversation_state = self.legacy_system.conversation_state
            
            # Store response in memory if not already stored by legacy system
            if result.get('response') and not result.get('stored_in_memory'):
                self.memory_manager.add_message("agent", result['response'], result.get('type', 'legacy_response'))
            
            result['system'] = 'legacy'
            result['conversation_state'] = self.conversation_state
            
            return result
            
        except Exception as e:
            logger.error(f"Legacy processing error: {e}")
            raise
    
    def _handle_system_error(self, error: Exception, user_input: str) -> Dict[str, Any]:
        """Handle system errors with fallback and recovery."""
        error_type = type(error).__name__
        
        # Try to fallback to the other system
        if self.active_system == AgentSystemType.CREWAI and self.legacy_system:
            logger.info("Falling back to Legacy system due to CrewAI error")
            try:
                self.active_system = AgentSystemType.LEGACY
                return self._process_with_legacy(user_input)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
        elif self.active_system == AgentSystemType.LEGACY and self.crewai_system:
            logger.info("Falling back to CrewAI system due to Legacy error")
            try:
                self.active_system = AgentSystemType.CREWAI
                return self._process_with_crewai(user_input)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
        
        # If no fallback available or fallback failed, return error
        error_message = f"Agent system error: {str(error)}"
        self.memory_manager.add_message("agent", error_message, "system_error")
        
        return {
            "success": False,
            "error": error_message,
            "error_type": error_type,
            "suggestion": "Please try again or contact support if the issue persists"
        }
    
    def _format_crewai_response(self, result: Dict[str, Any]) -> str:
        """Format CrewAI response for display."""
        if not result.get('success'):
            return "❌ Analysis failed. Please try again."
        
        outputs = result.get('outputs', {})
        response_parts = []
        
        # Add crew collaboration summary
        response_parts.append("🤖 **Agent Collaboration Complete**")
        response_parts.append("The agent crew has analyzed your requirement:")
        
        # Add schema analysis if available
        if 'schema_analysis' in outputs:
            response_parts.append("\n📋 **Schema Analysis**")
            schema = outputs['schema_analysis']
            if isinstance(schema, dict):
                if 'recommended_objects' in schema:
                    response_parts.append(f"• Recommended {len(schema['recommended_objects'])} object(s)")
        
        # Add technical design if available
        if 'technical_design' in outputs:
            response_parts.append("\n🏗️ **Technical Design**")
            design = outputs['technical_design']
            if isinstance(design, dict):
                if 'automation_needed' in design:
                    response_parts.append(f"• {len(design['automation_needed'])} automation component(s)")
        
        # Add implementation plan if available
        if 'implementation_plan' in outputs:
            response_parts.append("\n📊 **Implementation Plan**")
            plan = outputs['implementation_plan']
            if isinstance(plan, dict):
                if 'tasks' in plan:
                    response_parts.append(f"• {len(plan['tasks'])} implementation task(s)")
                if 'project_summary' in plan:
                    summary = plan['project_summary']
                    if isinstance(summary, dict):
                        effort = summary.get('total_effort', 'Unknown')
                        duration = summary.get('duration', 'Unknown')
                        response_parts.append(f"• Estimated effort: {effort}")
                        response_parts.append(f"• Estimated duration: {duration}")
        
        response_parts.append("\n✅ **Analysis complete!** Check the detailed results above.")
        
        return "\n".join(response_parts)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self.memory_manager.get_conversation_history()
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id
    
    def switch_system(self, new_system: AgentSystemType) -> bool:
        """
        Switch to a different agent system.
        
        Args:
            new_system: The system to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        if new_system == AgentSystemType.CREWAI and self.crewai_system:
            self.active_system = AgentSystemType.CREWAI
            logger.info("Switched to CrewAI system")
            return True
        elif new_system == AgentSystemType.LEGACY and self.legacy_system:
            self.active_system = AgentSystemType.LEGACY
            logger.info("Switched to Legacy system")
            return True
        else:
            logger.warning(f"Cannot switch to {new_system.value} - system not available")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all available systems."""
        return {
            "active_system": self.active_system.value if self.active_system else "none",
            "crewai_available": self.crewai_system is not None,
            "legacy_available": self.legacy_system is not None,
            "conversation_state": self.conversation_state,
            "session_id": self.session_id
        }
    
    def clear_memory(self):
        """Clear conversation memory."""
        self.memory_manager.clear_conversation_history()
        self.conversation_state = "initial"
        if self.legacy_system:
            self.legacy_system.conversation_state = "initial"
        logger.info("Memory cleared")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate system configuration."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check OpenAI configuration
        import os
        if not os.getenv('OPENAI_API_KEY'):
            validation_results["valid"] = False
            validation_results["errors"].append("OpenAI API key not configured")
        
        # Check system availability
        if not self.crewai_system and not self.legacy_system:
            validation_results["valid"] = False
            validation_results["errors"].append("No agent systems available")
        
        if not self.crewai_system:
            validation_results["warnings"].append("CrewAI system not available - using legacy mode")
        
        return validation_results 