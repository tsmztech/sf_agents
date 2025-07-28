from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from config import Config
import json
import logging

# Import the new Salesforce connector
try:
    from .salesforce_connector import SalesforceConnector, SalesforceConnectionError
except ImportError:
    # Fallback if connector not available
    SalesforceConnector = None
    SalesforceConnectionError = Exception

logger = logging.getLogger(__name__)

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
        
        # Initialize Salesforce connector if configuration is available
        self.sf_connector = None
        self.sf_connected = False
        self._initialize_salesforce_connection()
        
        # Initialize the Crew AI expert agent
        self._initialize_agent()
    
    def _initialize_salesforce_connection(self):
        """Initialize Salesforce connection if credentials are available."""
        if SalesforceConnector is None:
            logger.warning("SalesforceConnector not available")
            return
        
        if not Config.validate_salesforce_config():
            logger.info("Salesforce configuration not complete - operating in offline mode")
            return
        
        try:
            self.sf_connector = SalesforceConnector()
            connection_test = self.sf_connector.test_connection()
            
            if connection_test.get('connected'):
                self.sf_connected = True
                org_info = connection_test.get('org_info', {})
                logger.info(f"Successfully connected to Salesforce org: {org_info.get('Name', 'Unknown')}")
                logger.info(f"Instance: {connection_test.get('instance_url')}")
                logger.info(f"Available objects: {connection_test.get('sobjects_count', 'Unknown')}")
            else:
                logger.error(f"Failed to connect to Salesforce: {connection_test.get('error')}")
                
        except Exception as e:
            logger.error(f"Error initializing Salesforce connection: {e}")
            self.sf_connector = None
            self.sf_connected = False
    
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
    
    def analyze_with_org_context(
        self, 
        conversation_context: str, 
        current_requirements: List[Dict[str, Any]],
        mentioned_objects: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze requirements with real-time Salesforce org context.
        
        Args:
            conversation_context: Full conversation history
            current_requirements: List of extracted requirements
            mentioned_objects: List of object names mentioned in requirements
            
        Returns:
            Enhanced analysis with real org context
        """
        
        # Get real-time org data if connected
        org_context_data = self._get_org_context(mentioned_objects or [])
        
        # Determine analysis mode
        analysis_mode = "REAL-TIME ORG ANALYSIS" if self.sf_connected else "BEST PRACTICE ANALYSIS"
        
        task = Task(
            description=f"""
            As a Senior Salesforce Solution Architect, analyze the requirements with {analysis_mode}.
            
            CONNECTION STATUS: {"🟢 CONNECTED TO SALESFORCE ORG" if self.sf_connected else "🔴 OFFLINE MODE"}
            
            CONVERSATION CONTEXT:
            {conversation_context}
            
            CURRENT REQUIREMENTS:
            {self._format_requirements(current_requirements)}
            
            {"REAL-TIME ORG SCHEMA DATA:" if self.sf_connected else ""}
            {json.dumps(org_context_data, indent=2) if org_context_data else ""}
            
            ENHANCED ANALYSIS TASKS:
            
            1. **Real-Time Object Analysis** (if connected):
               - Verify which objects/fields already exist in the org
               - Identify existing relationships and dependencies
               - Check current field types and constraints
               - Analyze existing data patterns and usage
            
            2. **Gap Analysis with Org Context**:
               - What needs to be created vs. what exists
               - Missing relationships and data connections
               - Security and permission gaps based on current setup
               - Data migration and integration requirements
            
            3. **Optimization Opportunities**:
               - Leverage existing org infrastructure
               - Optimize based on current data volumes and patterns
               - Suggest improvements to existing schema
               - Identify unused or underutilized objects/fields
            
            4. **Implementation Feasibility**:
               - Assess complexity based on current org state
               - Identify potential conflicts with existing setup
               - Recommend phased implementation approach
               - Highlight technical risks and mitigation strategies
            
            RESPONSE FORMAT:
            Provide analysis in structured format:
            
            **ORG ANALYSIS SUMMARY:**
            - [Summary of current org state and readiness]
            
            **EXISTING INFRASTRUCTURE:**
            - [List what already exists and can be leveraged]
            
            **REQUIRED NEW COMPONENTS:**
            - [List what needs to be created]
            
            **OPTIMIZATION RECOMMENDATIONS:**
            - [Suggestions to improve existing setup]
            
            **IMPLEMENTATION STRATEGY:**
            - [Phased approach with priorities and dependencies]
            
            **RISK ASSESSMENT:**
            - [Potential issues and mitigation strategies]
            
            Be specific about object names, field types, and relationships.
            Include business justification for each recommendation.
            """,
            expected_output="Comprehensive org-aware analysis with specific recommendations based on real Salesforce data.",
            agent=self.agent
        )
        
        # Execute the analysis
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Parse and enhance the expert analysis
        try:
            analysis = self._parse_expert_analysis(str(result))
            analysis['org_connected'] = self.sf_connected
            analysis['org_context'] = org_context_data
            
            # Ensure we have at least some basic content
            if not any(analysis.get(key) for key in ['requirement_gaps', 'best_practices', 'suggested_enhancements']):
                # Create some basic suggestions if parsing failed
                analysis = {
                    'requirement_gaps': ['Consider data validation rules', 'Define user access permissions', 'Plan for data backup and recovery'],
                    'best_practices': ['Use standard Salesforce naming conventions', 'Implement proper field-level security', 'Create comprehensive test data'],
                    'suggested_enhancements': ['Add workflow automation', 'Include reporting dashboards', 'Consider mobile optimization'],
                    'org_connected': self.sf_connected,
                    'org_context': org_context_data,
                    'full_analysis': str(result)
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing expert analysis: {e}")
            # Return basic fallback analysis
            return {
                'requirement_gaps': ['Review data model completeness', 'Validate security requirements'],
                'best_practices': ['Follow Salesforce development best practices', 'Implement proper testing'],
                'suggested_enhancements': ['Consider automation opportunities', 'Plan for user training'],
                'org_connected': self.sf_connected,
                'org_context': org_context_data,
                'full_analysis': str(result),
                'parsing_error': str(e)
            }
    
    def validate_objects_in_org(self, object_names: List[str]) -> Dict[str, Any]:
        """
        Validate if specified objects exist in the connected org.
        
        Args:
            object_names: List of object API names to validate
            
        Returns:
            Validation results with details about each object
        """
        if not self.sf_connected:
            return {
                'connected': False,
                'message': 'Not connected to Salesforce org - validation unavailable'
            }
        
        validation_results = {
            'connected': True,
            'validated_objects': {},
            'summary': {
                'total_checked': len(object_names),
                'existing': 0,
                'missing': 0,
                'errors': 0
            }
        }
        
        for obj_name in object_names:
            try:
                # Try to get object schema
                schema = self.sf_connector.get_object_schema(obj_name)
                validation_results['validated_objects'][obj_name] = {
                    'exists': True,
                    'label': schema.get('label'),
                    'custom': schema.get('custom', False),
                    'fields_count': len(schema.get('fields', [])),
                    'relationships_count': len(schema.get('relationships', [])),
                    'permissions': {
                        'createable': schema.get('createable', False),
                        'updateable': schema.get('updateable', False),
                        'deletable': schema.get('deletable', False)
                    }
                }
                validation_results['summary']['existing'] += 1
                
            except SalesforceConnectionError as e:
                if "NOT_FOUND" in str(e) or "INVALID_TYPE" in str(e):
                    validation_results['validated_objects'][obj_name] = {
                        'exists': False,
                        'error': 'Object not found in org'
                    }
                    validation_results['summary']['missing'] += 1
                else:
                    validation_results['validated_objects'][obj_name] = {
                        'exists': None,
                        'error': str(e)
                    }
                    validation_results['summary']['errors'] += 1
        
        return validation_results
    
    def get_field_recommendations(self, object_name: str, field_requirements: List[Dict]) -> Dict[str, Any]:
        """
        Get field recommendations based on existing object schema.
        
        Args:
            object_name: API name of the object
            field_requirements: List of required field specifications
            
        Returns:
            Field recommendations with org context
        """
        if not self.sf_connected:
            return {
                'connected': False,
                'message': 'Not connected to org - providing generic recommendations'
            }
        
        try:
            # Get current object schema
            schema = self.sf_connector.get_object_schema(object_name)
            existing_fields = {field['name']: field for field in schema.get('fields', [])}
            
            recommendations = {
                'object_name': object_name,
                'connected': True,
                'existing_fields_count': len(existing_fields),
                'field_recommendations': []
            }
            
            for req_field in field_requirements:
                field_name = req_field.get('name', '')
                
                if field_name in existing_fields:
                    # Field exists - analyze compatibility
                    existing_field = existing_fields[field_name]
                    recommendation = {
                        'field_name': field_name,
                        'status': 'exists',
                        'current_type': existing_field.get('type'),
                        'required_type': req_field.get('type'),
                        'compatible': existing_field.get('type') == req_field.get('type'),
                        'existing_metadata': existing_field,
                        'action': 'use_existing' if existing_field.get('type') == req_field.get('type') else 'review_compatibility'
                    }
                else:
                    # Field doesn't exist - recommend creation
                    recommendation = {
                        'field_name': field_name,
                        'status': 'new',
                        'recommended_type': req_field.get('type'),
                        'action': 'create_new',
                        'suggestions': self._get_field_type_suggestions(req_field, existing_fields)
                    }
                
                recommendations['field_recommendations'].append(recommendation)
            
            return recommendations
            
        except Exception as e:
            return {
                'connected': True,
                'error': str(e),
                'object_name': object_name
            }
    
    def _get_org_context(self, mentioned_objects: List[str]) -> Dict[str, Any]:
        """Get relevant org context for mentioned objects."""
        if not self.sf_connected or not mentioned_objects:
            return {}
        
        org_context = {}
        
        for obj_name in mentioned_objects:
            try:
                # Get object schema
                schema = self.sf_connector.get_object_schema(obj_name)
                
                # Get related objects
                related_objects = self.sf_connector.get_related_objects(obj_name)
                
                org_context[obj_name] = {
                    'exists': True,
                    'schema_summary': {
                        'label': schema.get('label'),
                        'custom': schema.get('custom', False),
                        'fields_count': len(schema.get('fields', [])),
                        'key_fields': [f['name'] for f in schema.get('fields', [])[:10]],  # First 10 fields
                        'relationships_count': len(schema.get('relationships', [])),
                        'related_objects': [rel['related_object'] for rel in related_objects[:5]]  # Top 5 related
                    }
                }
                
            except Exception as e:
                org_context[obj_name] = {
                    'exists': False,
                    'error': str(e)
                }
        
        return org_context
    
    def _get_field_type_suggestions(self, field_req: Dict, existing_fields: Dict) -> List[str]:
        """Get field type suggestions based on existing org patterns."""
        suggestions = []
        
        # Analyze similar fields in the object
        req_type = field_req.get('type', '').lower()
        field_name = field_req.get('name', '').lower()
        
        # Find similar fields by name pattern
        similar_fields = []
        for existing_name, existing_field in existing_fields.items():
            if any(keyword in existing_name.lower() for keyword in field_name.split('_')):
                similar_fields.append(existing_field)
        
        if similar_fields:
            common_types = list(set(f.get('type') for f in similar_fields))
            suggestions.append(f"Similar fields in this object use types: {', '.join(common_types)}")
        
        # Type-specific suggestions
        if 'email' in field_name:
            suggestions.append("Consider using Email type with built-in validation")
        elif 'phone' in field_name:
            suggestions.append("Consider using Phone type for proper formatting")
        elif 'date' in field_name and req_type != 'date':
            suggestions.append("Consider using Date or DateTime type for date fields")
        elif 'amount' in field_name or 'price' in field_name:
            suggestions.append("Consider using Currency type for monetary values")
        
        return suggestions
    
    def get_org_statistics(self) -> Dict[str, Any]:
        """Get helpful org statistics for analysis."""
        if not self.sf_connected:
            return {'connected': False}
        
        try:
            # Get org limits
            limits = self.sf_connector.get_org_limits()
            
            # Get custom objects count
            custom_objects = self.sf_connector.get_all_objects(include_custom_only=True)
            
            return {
                'connected': True,
                'custom_objects_count': len(custom_objects),
                'data_storage_used': limits.get('DataStorageMB', {}).get('Remaining', 'Unknown'),
                'file_storage_used': limits.get('FileStorageMB', {}).get('Remaining', 'Unknown'),
                'api_requests_used': limits.get('DailyApiRequests', {}).get('Remaining', 'Unknown'),
                'sample_custom_objects': [obj['name'] for obj in custom_objects[:10]]
            }
            
        except Exception as e:
            return {
                'connected': True,
                'error': str(e)
            } 