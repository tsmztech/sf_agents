import json
from typing import Dict, Any, List
from datetime import datetime
from agents.simple_agent import Agent, Task, Crew
import openai
import os
from config import Config

class SalesforceTechnicalArchitectAgent:
    """
    Advanced Technical Architect Agent for Salesforce solutions.
    Creates detailed technical designs, schema definitions, and architecture plans.
    """
    
    def __init__(self):
        # OpenAI is handled by the simple agent implementation
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Technical Architect agent with comprehensive capabilities."""
        self.agent = Agent(
            role="Senior Salesforce Technical Architect & Solution Designer",
            goal="""Create comprehensive, detailed technical architecture and implementation 
                    plans for Salesforce solutions. Design complete schemas, automation 
                    strategies, and technical components with precise specifications.""",
            backstory="""You are a highly experienced Salesforce Technical Architect with 20+ years 
                        of enterprise solution design experience. You have deep expertise in:
                        
                        • Data Model Design: Custom/Standard Objects, Field Types, Relationships, Schema Design
                        • Automation Architecture: Process Builder, Flows, Triggers, Apex, Schedulable Classes
                        • User Interface Design: Lightning Web Components, Aura Components, Page Layouts, Record Types
                        • Security Framework: Profiles, Permission Sets, Field-Level Security, Sharing Rules
                        • Integration Patterns: APIs, External Systems, Data Sync, ETL Processes
                        • Performance Optimization: Governor Limits, Bulk Processing, Async Patterns
                        • Deployment Strategy: Change Sets, DevOps, CI/CD, Environment Management
                        
                        You think systematically about:
                        - Scalability and performance implications
                        - Security and compliance requirements  
                        - Maintainability and technical debt
                        - Integration touchpoints and dependencies
                        - User experience and adoption considerations
                        
                        You create detailed technical specifications that development teams 
                        can directly implement without ambiguity.""",
        )
    
    def create_technical_architecture(self, requirements: str, expert_suggestions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create comprehensive technical architecture and design."""
        
        # Prepare context with requirements and expert input
        context = self._prepare_technical_context(requirements, expert_suggestions)
        
        # Create technical analysis task
        technical_task = Task(
            description=f"""
            Based on the confirmed business requirements and expert recommendations, create a 
            comprehensive technical architecture and implementation design.
            
            REQUIREMENTS CONTEXT:
            {context}
            
            YOUR TASK:
            Create a detailed technical design document that includes:
            
            1. **DATA MODEL DESIGN**:
               - Custom Objects needed (API names, labels, descriptions)
               - Standard Objects to be extended
               - Field specifications (Name, API Name, Type, Length, Required, Default Values)
               - Relationship design (Lookup, Master-Detail, Junction Objects)
               - Record Types and Picklist Values
               - Validation Rules
            
            2. **AUTOMATION ARCHITECTURE**:
               - Process flows and their triggers
               - Apex Triggers (Object, Events, Logic Description)
               - Apex Classes (Purpose, Methods, Key Logic)
               - Scheduled Jobs and Batch Classes
               - Email Alerts and Workflow Rules
            
            3. **USER INTERFACE DESIGN**:
               - Lightning Web Components needed
               - Page Layout modifications
               - Custom Lightning Pages
               - Record Type assignments
               - List Views and Report requirements
            
            4. **SECURITY & ACCESS DESIGN**:
               - Profile modifications needed
               - Permission Sets required
               - Field-Level Security settings
               - Sharing Rules and Criteria
               - Role Hierarchy considerations
            
            5. **INTEGRATION REQUIREMENTS**:
               - External system connections
               - API endpoints needed
               - Data sync requirements
               - Real-time vs batch processing
            
            6. **PERFORMANCE CONSIDERATIONS**:
               - Governor limit implications
               - Bulk processing requirements
               - Indexing strategy
               - Archive/Purge considerations
            
            Format your response as a structured JSON with detailed specifications 
            that can be directly used for implementation.
            """,
            agent=self.agent,
            expected_output="""A comprehensive JSON technical architecture document with detailed 
                              specifications for all Salesforce components needed."""
        )
        
        # Execute the technical analysis
        crew = Crew(
            agents=[self.agent],
            tasks=[technical_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse and structure the technical design
        return self._parse_technical_design(result)
    
    def _prepare_technical_context(self, requirements: str, expert_suggestions: Dict[str, Any] = None) -> str:
        """Prepare comprehensive context for technical analysis."""
        context = f"""
        BUSINESS REQUIREMENTS:
        {requirements}
        
        """
        
        if expert_suggestions:
            context += f"""
        EXPERT RECOMMENDATIONS INCORPORATED:
        """
            
            if expert_suggestions.get('missing_requirements'):
                context += f"""
        Missing Requirements Identified:
        {json.dumps(expert_suggestions['missing_requirements'], indent=2)}
        """
            
            if expert_suggestions.get('best_practices'):
                context += f"""
        Best Practices to Implement:
        {json.dumps(expert_suggestions['best_practices'], indent=2)}
        """
            
            if expert_suggestions.get('value_enhancements'):
                context += f"""
        Value Enhancements to Include:
        {json.dumps(expert_suggestions['value_enhancements'], indent=2)}
        """
        
        return context
    
    def _parse_technical_design(self, raw_result) -> Dict[str, Any]:
        """Parse and structure the technical design result."""
        try:
            # Try to extract JSON from the result
            result_str = str(raw_result)
            
            # Find JSON content in the response
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = result_str[start_idx:end_idx]
                technical_design = json.loads(json_str)
            else:
                # If no JSON found, structure the response
                technical_design = {
                    "overview": result_str,
                    "data_model": {},
                    "automation": {},
                    "user_interface": {},
                    "security": {},
                    "integration": {},
                    "performance": {}
                }
        
        except (json.JSONDecodeError, Exception) as e:
            # Fallback structure
            technical_design = {
                "overview": str(raw_result),
                "parsing_note": f"Could not parse as JSON: {str(e)}",
                "data_model": {"note": "See overview for data model details"},
                "automation": {"note": "See overview for automation details"},
                "user_interface": {"note": "See overview for UI details"},
                "security": {"note": "See overview for security details"},
                "integration": {"note": "See overview for integration details"},
                "performance": {"note": "See overview for performance details"}
            }
        
        # Add metadata
        technical_design["created_at"] = datetime.now().isoformat()
        technical_design["created_by"] = "Technical Architect Agent"
        technical_design["version"] = "1.0"
        
        return technical_design
    
    def validate_technical_design(self, technical_design: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the technical design for completeness and feasibility."""
        
        validation_task = Task(
            description=f"""
            Review and validate the following technical design for completeness, 
            feasibility, and Salesforce best practices:
            
            TECHNICAL DESIGN:
            {json.dumps(technical_design, indent=2)}
            
            Validate:
            1. Design completeness and coverage
            2. Salesforce governor limit considerations
            3. Security and best practice compliance
            4. Implementation feasibility
            5. Potential risks or gaps
            
            Provide validation results with any recommended improvements.
            """,
            agent=self.agent,
            expected_output="Detailed validation report with recommendations"
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[validation_task],
            verbose=True
        )
        
        validation_result = crew.kickoff()
        
        return {
            "validation_status": "completed",
            "validation_report": str(validation_result),
            "validated_at": datetime.now().isoformat()
        } 