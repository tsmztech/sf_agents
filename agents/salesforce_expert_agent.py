from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from config import Config

class SalesforceExpertAgent:
    """
    Expert Agent specialized in Salesforce best practices, architecture patterns,
    and intelligent requirement gap filling. This agent provides suggestions
    when requirements are incomplete or could benefit from Salesforce best practices.
    """
    
    def __init__(self):
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.2  # Lower temperature for more consistent expert advice
        )
        
        # Initialize the Crew AI expert agent
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Crew AI expert agent with Salesforce expertise."""
        self.agent = Agent(
            role="Senior Salesforce Solution Architect & Best Practices Expert",
            goal="""Provide expert guidance on Salesforce architecture, identify requirement gaps, 
                    and suggest best practices to enhance solutions. Fill missing requirements with 
                    intelligent suggestions based on industry standards and Salesforce best practices.""",
            backstory="""You are a Senior Salesforce Solution Architect with 15+ years of experience 
                        implementing enterprise Salesforce solutions. You have deep expertise in:
                        
                        TECHNICAL EXPERTISE:
                        - Salesforce platform architecture and limitations
                        - Data modeling and schema design best practices
                        - Security frameworks and permission strategies
                        - Integration patterns and API design
                        - Performance optimization and scalability
                        - Automation best practices (Flows, Apex, etc.)
                        - Lightning platform development standards
                        
                        BUSINESS EXPERTISE:
                        - Industry-specific Salesforce patterns
                        - Change management and user adoption
                        - Governance and compliance requirements
                        - ROI optimization and business value delivery
                        
                        PROBLEM SOLVING:
                        - Identifying gaps in requirements
                        - Suggesting complementary features that enhance value
                        - Recommending future-proof architectural decisions
                        - Balancing business needs with technical constraints
                        
                        You always consider scalability, maintainability, user experience, 
                        and long-term business value in your recommendations.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def analyze_requirements_and_suggest_improvements(
        self, 
        conversation_context: str, 
        current_requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze current requirements and provide expert suggestions for improvements,
        missing components, and best practices.
        
        Args:
            conversation_context: Full conversation history
            current_requirements: List of extracted requirements
            
        Returns:
            Dictionary containing analysis and suggestions
        """
        
        task = Task(
            description=f"""
            As a Senior Salesforce Solution Architect, analyze the current requirements and conversation 
            to identify gaps, improvements, and best practice recommendations.
            
            CONVERSATION CONTEXT:
            {conversation_context}
            
            CURRENT REQUIREMENTS SUMMARY:
            {self._format_requirements(current_requirements)}
            
            ANALYSIS TASKS:
            
            1. **Gap Analysis**: Identify missing but important requirements such as:
               - Security and permission considerations
               - Data governance and compliance needs
               - Integration touchpoints
               - Scalability considerations
               - User experience elements
               - Reporting and analytics needs
               - Mobile accessibility
               - Performance requirements
               - Backup and disaster recovery
               - Change management processes
            
            2. **Best Practice Suggestions**: Recommend Salesforce best practices:
               - Optimal data model design
               - Appropriate automation tools (Flow vs Apex vs Process Builder)
               - Security model recommendations
               - Integration patterns
               - UI/UX improvements
               - Performance optimizations
            
            3. **Enhancement Opportunities**: Suggest valuable additions that:
               - Increase business value
               - Improve user adoption
               - Future-proof the solution
               - Leverage Salesforce platform capabilities
               - Support business growth
            
            4. **Risk Mitigation**: Identify potential risks and suggest preventive measures:
               - Technical debt risks
               - Scalability bottlenecks
               - Security vulnerabilities
               - User adoption challenges
               - Maintenance complexities
            
            RESPONSE FORMAT:
            Provide your analysis in the following structured format:
            
            **REQUIREMENT GAPS IDENTIFIED:**
            - [List specific gaps with explanations]
            
            **SALESFORCE BEST PRACTICE RECOMMENDATIONS:**
            - [List recommendations with rationale]
            
            **SUGGESTED ENHANCEMENTS:**
            - [List valuable additions with business justification]
            
            **IMPLEMENTATION CONSIDERATIONS:**
            - [List important technical and business considerations]
            
            **RECOMMENDED NEXT STEPS:**
            - [List prioritized suggestions for user consideration]
            
            Be specific, actionable, and explain the business value of each suggestion.
            """,
            expected_output="Comprehensive analysis with structured recommendations for requirement gaps, best practices, and enhancements.",
            agent=self.agent
        )
        
        # Execute the analysis
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Parse the expert analysis
        return self._parse_expert_analysis(str(result))
    
    def suggest_missing_components(
        self, 
        requirements_type: str, 
        context: str
    ) -> Dict[str, Any]:
        """
        Suggest specific missing components for a particular area.
        
        Args:
            requirements_type: Type of requirement (e.g., 'security', 'integration', 'data_model')
            context: Relevant context for the suggestions
            
        Returns:
            Dictionary with specific suggestions
        """
        
        task = Task(
            description=f"""
            As a Salesforce expert, provide specific suggestions for the {requirements_type} area 
            based on the following context:
            
            CONTEXT:
            {context}
            
            FOCUS AREA: {requirements_type}
            
            Provide detailed, actionable recommendations that follow Salesforce best practices 
            and industry standards. Include:
            
            1. Specific components or configurations needed
            2. Rationale for each recommendation
            3. Implementation priority (High/Medium/Low)
            4. Potential business impact
            5. Technical considerations
            
            Format your response as a structured list with clear explanations.
            """,
            expected_output=f"Detailed recommendations for {requirements_type} with priorities and rationale.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        return {
            "type": requirements_type,
            "suggestions": str(result),
            "priority": self._extract_priority_suggestions(str(result))
        }
    
    def validate_solution_architecture(
        self, 
        proposed_solution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a proposed solution against Salesforce best practices.
        
        Args:
            proposed_solution: The proposed implementation plan
            
        Returns:
            Validation results with suggestions for improvement
        """
        
        task = Task(
            description=f"""
            Review the following proposed Salesforce solution and validate it against 
            best practices, identifying any issues and suggesting improvements:
            
            PROPOSED SOLUTION:
            {proposed_solution}
            
            VALIDATION AREAS:
            1. **Data Model**: Object relationships, field types, naming conventions
            2. **Security Model**: Permission sets, sharing rules, field-level security
            3. **Automation**: Appropriate tool selection (Flow vs Apex vs triggers)
            4. **Integration**: API design, error handling, security
            5. **Performance**: Query optimization, bulk processing, limits
            6. **Scalability**: Growth considerations, governor limits
            7. **Maintainability**: Code organization, documentation, testing
            8. **User Experience**: UI/UX design, mobile considerations
            
            Provide specific feedback with:
            - Issues identified (with severity: Critical/High/Medium/Low)
            - Improvement recommendations
            - Alternative approaches where applicable
            - Best practice rationale
            """,
            expected_output="Detailed validation report with issues, recommendations, and best practice guidance.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        return {
            "validation_result": str(result),
            "recommendations": self._extract_validation_recommendations(str(result))
        }
    
    def _format_requirements(self, requirements: List[Dict[str, Any]]) -> str:
        """Format requirements for analysis."""
        if not requirements:
            return "No specific requirements extracted yet."
        
        formatted = []
        for i, req in enumerate(requirements, 1):
            formatted.append(f"{i}. {req.get('description', 'No description')}")
            if req.get('details'):
                formatted.append(f"   Details: {req['details']}")
        
        return "\n".join(formatted)
    
    def _parse_expert_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the expert analysis into structured data."""
        
        sections = {
            "requirement_gaps": [],
            "best_practices": [],
            "suggested_enhancements": [],
            "implementation_considerations": [],
            "recommended_next_steps": [],
            "full_analysis": analysis_text
        }
        
        # Simple parsing logic - could be enhanced with more sophisticated NLP
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith('**REQUIREMENT GAPS'):
                current_section = "requirement_gaps"
            elif line.upper().startswith('**SALESFORCE BEST PRACTICE'):
                current_section = "best_practices"
            elif line.upper().startswith('**SUGGESTED ENHANCEMENTS'):
                current_section = "suggested_enhancements"
            elif line.upper().startswith('**IMPLEMENTATION CONSIDERATIONS'):
                current_section = "implementation_considerations"
            elif line.upper().startswith('**RECOMMENDED NEXT STEPS'):
                current_section = "recommended_next_steps"
            elif line.startswith('-') and current_section:
                sections[current_section].append(line[1:].strip())
        
        return sections
    
    def _extract_priority_suggestions(self, suggestions_text: str) -> List[Dict[str, Any]]:
        """Extract priority suggestions from the text."""
        priorities = []
        lines = suggestions_text.split('\n')
        
        for line in lines:
            if 'High' in line or 'Critical' in line:
                priorities.append({
                    "priority": "High",
                    "suggestion": line.strip()
                })
            elif 'Medium' in line:
                priorities.append({
                    "priority": "Medium", 
                    "suggestion": line.strip()
                })
        
        return priorities
    
    def _extract_validation_recommendations(self, validation_text: str) -> List[Dict[str, Any]]:
        """Extract validation recommendations from the text."""
        recommendations = []
        lines = validation_text.split('\n')
        
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('•'):
                recommendations.append({
                    "recommendation": line.strip()[1:].strip(),
                    "type": "improvement"
                })
        
        return recommendations
    
    def get_industry_best_practices(self, industry: str, use_case: str) -> Dict[str, Any]:
        """
        Get industry-specific best practices and recommendations.
        
        Args:
            industry: Industry type (e.g., 'healthcare', 'financial_services', 'manufacturing')
            use_case: Specific use case within the industry
            
        Returns:
            Industry-specific recommendations
        """
        
        task = Task(
            description=f"""
            Provide industry-specific Salesforce best practices and recommendations for:
            
            INDUSTRY: {industry}
            USE CASE: {use_case}
            
            Include:
            1. Industry-specific compliance requirements
            2. Common data models and objects for this industry
            3. Typical integration patterns
            4. Security and privacy considerations
            5. User experience patterns
            6. Reporting and analytics needs
            7. Mobile requirements
            8. Scalability considerations for this industry
            
            Provide specific, actionable recommendations that are proven to work well
            in this industry context.
            """,
            expected_output="Industry-specific best practices and recommendations with detailed explanations.",
            agent=self.agent
        )
        
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        return {
            "industry": industry,
            "use_case": use_case,
            "recommendations": str(result)
        } 