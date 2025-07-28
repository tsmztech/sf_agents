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

class SalesforceSchemaExpertAgent:
    """
    Specialized Expert Agent focused exclusively on Salesforce schema and database design.
    This agent analyzes requirements and provides guidance on:
    - Existing objects and fields that can be leveraged
    - New objects and fields that need to be created
    - Field types, relationships, and data model recommendations
    - Standard vs custom object usage optimization
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
        
        # Initialize the Crew AI schema expert agent
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
        """Initialize the Crew AI schema expert agent focused on Salesforce data model."""
        self.agent = Agent(
            role="Salesforce Schema & Database Expert",
            goal="""Analyze requirements and provide expert guidance on Salesforce object and field design. 
                    Identify existing objects/fields that can be leveraged and recommend new ones when needed. 
                    Focus exclusively on data model, schema design, and field configurations.""",
            backstory="""You are a specialized Salesforce Schema Expert with deep expertise in:
                        
                        SALESFORCE DATA MODEL EXPERTISE:
                        - Standard and Custom Objects (when to use each)
                        - Field types, lengths, and configurations
                        - Relationships (Lookup, Master-Detail, Junction Objects)
                        - Data validation rules and field dependencies
                        - Record types and picklist management
                        - Schema optimization and performance considerations
                        
                        REAL-TIME ORG ANALYSIS:
                        - Analyzing existing org schema and objects
                        - Identifying reusable standard objects and fields
                        - Mapping business requirements to Salesforce objects
                        - Recommending field types based on use cases
                        - Suggesting relationship structures
                        
                        YOUR APPROACH:
                        1. Always check existing org schema first
                        2. Prefer standard objects when possible
                        3. Recommend appropriate field types and sizes
                        4. Consider data relationships and dependencies
                        5. Provide specific object and field names
                        6. Think about data volume and performance
                        
                        You focus ONLY on schema design - no automation, security, or UI recommendations.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def analyze_schema_requirements(
        self, 
        conversation_context: str, 
        current_requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze requirements from a schema/database perspective and provide object/field recommendations.
        
        Args:
            conversation_context: Full conversation history
            current_requirements: List of extracted requirements
            
        Returns:
            Dictionary containing schema analysis and recommendations
        """
        
        task = Task(
            description=f"""
            As a Salesforce Schema Expert, analyze the requirements and provide specific object and field recommendations.
            
            CONVERSATION CONTEXT:
            {conversation_context}
            
            CURRENT REQUIREMENTS SUMMARY:
            {self._format_requirements(current_requirements)}
            
            YOUR ANALYSIS SHOULD FOCUS ON:
            
            1. **Identify Data Entities**: What business entities/concepts need to be stored?
            2. **Map to Salesforce Objects**: Which standard objects can be used? What custom objects are needed?
            3. **Define Field Requirements**: What specific fields are needed for each object?
            4. **Determine Relationships**: How should objects relate to each other?
            5. **Specify Field Types**: What field types, lengths, and configurations are appropriate?
            
            RESPONSE FORMAT (be very specific):
            
            **OBJECTS TO LEVERAGE:**
            - [List existing standard objects that can be used, e.g., "Account for companies", "Contact for people"]
            
            **NEW CUSTOM OBJECTS NEEDED:**
            - [List custom objects to create with clear business purpose, e.g., "Life_Event__c for family milestones"]
            
            **FIELD RECOMMENDATIONS:**
            For each object (existing or new), specify:
            - Field Name (API format)
            - Field Type (Text, Number, Date, Picklist, etc.)
            - Field Length/Configuration
            - Purpose/Description
            
            **RELATIONSHIP DESIGN:**
            - [Specify lookups, master-detail relationships between objects]
            
            **DATA MODEL CONSIDERATIONS:**
            - [Performance, volume, and design considerations]
            
            Be concrete and actionable - provide exact object names, field names, and types.
            """,
            expected_output="Detailed schema analysis with specific object and field recommendations.",
            agent=self.agent
        )
        
        # Execute the analysis
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Parse the schema analysis
        return self._parse_schema_analysis(str(result))
    

    
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
    
    def _parse_schema_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the schema analysis into structured data."""
        
        sections = {
            "existing_objects": [],
            "new_objects": [],
            "field_recommendations": [],
            "relationships": [],
            "schema_recommendations": [],
            "full_analysis": analysis_text
        }
        
        # Parse schema-specific sections
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith('**EXISTING OBJECTS'):
                current_section = "existing_objects"
            elif line.upper().startswith('**NEW CUSTOM OBJECTS') or line.upper().startswith('**NEW OBJECTS'):
                current_section = "new_objects"
            elif line.upper().startswith('**DETAILED FIELD') or line.upper().startswith('**FIELD RECOMMENDATIONS'):
                current_section = "field_recommendations"
            elif line.upper().startswith('**RELATIONSHIP DESIGN'):
                current_section = "relationships"
            elif line.upper().startswith('**SCHEMA RECOMMENDATIONS'):
                current_section = "schema_recommendations"
            elif line.startswith('-') and current_section:
                sections[current_section].append(line[1:].strip())
            elif line.startswith('•') and current_section:
                sections[current_section].append(line[1:].strip())
        
        return sections
    
    def _extract_potential_objects(self, conversation_context: str) -> List[str]:
        """Extract potential Salesforce objects from conversation context."""
        import re
        
        # Common business terms that might indicate objects
        business_patterns = {
            'customer|client|company|organization|business': 'Account',
            'person|people|individual|contact|user': 'Contact',
            'prospect|lead': 'Lead',
            'deal|sale|opportunity': 'Opportunity',
            'support|ticket|issue|case': 'Case',
            'product|item|merchandise': 'Product2',
            'event|appointment|meeting': 'Event',
            'task|todo|action': 'Task',
            'campaign|marketing': 'Campaign',
            'contract|agreement': 'Contract',
            'asset|equipment': 'Asset'
        }
        
        potential_objects = []
        
        # Look for explicit object mentions
        object_pattern = r'\b\w+__c\b'  # Custom objects
        custom_objects = re.findall(object_pattern, conversation_context, re.IGNORECASE)
        potential_objects.extend(custom_objects)
        
        # Map business terms to standard objects
        for pattern, obj_name in business_patterns.items():
            if re.search(pattern, conversation_context, re.IGNORECASE):
                potential_objects.append(obj_name)
        
        # Look for specific standard object names
        standard_objects = ['Account', 'Contact', 'Lead', 'Opportunity', 'Case', 'Product2', 'Campaign', 'Event', 'Task']
        for obj in standard_objects:
            if re.search(rf'\b{re.escape(obj)}\b', conversation_context, re.IGNORECASE):
                potential_objects.append(obj)
        
        return list(set(potential_objects))  # Remove duplicates
    

    
    def analyze_schema_with_org_context(
        self, 
        conversation_context: str, 
        current_requirements: List[Dict[str, Any]],
        mentioned_objects: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze requirements for schema design with real-time Salesforce org context.
        
        Args:
            conversation_context: Full conversation history
            current_requirements: List of extracted requirements
            mentioned_objects: List of object names mentioned in requirements
            
        Returns:
            Schema analysis with real org context
        """
        
        # Get real-time org data if connected
        org_context_data = self._get_org_context(mentioned_objects or [])
        
        # Auto-detect objects from conversation if not provided
        if not mentioned_objects:
            mentioned_objects = self._extract_potential_objects(conversation_context)
            if mentioned_objects:
                org_context_data.update(self._get_org_context(mentioned_objects))
        
        # Determine analysis mode
        analysis_mode = "REAL-TIME ORG SCHEMA ANALYSIS" if self.sf_connected else "SCHEMA DESIGN ANALYSIS"
        
        task = Task(
            description=f"""
            As a Salesforce Schema Expert, analyze the requirements with {analysis_mode}.
            
            CONNECTION STATUS: {"🟢 CONNECTED TO SALESFORCE ORG" if self.sf_connected else "🔴 OFFLINE MODE"}
            
            CONVERSATION CONTEXT:
            {conversation_context}
            
            CURRENT REQUIREMENTS:
            {self._format_requirements(current_requirements)}
            
            {"REAL-TIME ORG SCHEMA DATA:" if self.sf_connected else ""}
            {json.dumps(org_context_data, indent=2) if org_context_data else ""}
            
            SCHEMA ANALYSIS FOCUS:
            
            1. **Existing Object Analysis** (if connected):
               - Which mentioned objects already exist in the org?
               - What fields do they currently have?
               - Are there suitable standard objects to use instead?
               - What relationships already exist?
            
            2. **Object Strategy**:
               - Standard objects to leverage (Account, Contact, etc.)
               - Custom objects that need to be created
               - Why each object choice is optimal
            
            3. **Field Design**:
               - Specific fields needed for each object
               - Appropriate field types and configurations
               - Required vs optional fields
               - Field relationships and dependencies
            
            4. **Relationship Architecture**:
               - Lookup vs Master-Detail relationships
               - Junction objects for many-to-many relationships
               - Parent-child hierarchies
            
            RESPONSE FORMAT (be very specific):
            
            **EXISTING OBJECTS TO USE:**
            - [Object Name]: [What it will store] - [Current field count if connected]
            
            **NEW CUSTOM OBJECTS NEEDED:**
            - [Custom_Object__c]: [Purpose and why custom is needed]
            
            **DETAILED FIELD SPECIFICATIONS:**
            For [Object Name]:
            - Field_API_Name__c: [Type(Length)] - [Purpose]
            - Another_Field__c: [Type] - [Purpose]
            
            **RELATIONSHIP DESIGN:**
            - [Object A] → [Object B]: [Lookup/Master-Detail] via [Field_Name__c]
            
            **SCHEMA RECOMMENDATIONS:**
            - [Specific technical recommendations for optimal design]
            
            Focus ONLY on objects, fields, and relationships. No automation, security, or UI suggestions.
            """,
            expected_output="Detailed schema analysis with specific object, field, and relationship recommendations.",
            agent=self.agent
        )
        
        # Execute the analysis
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Parse and enhance the schema analysis
        try:
            analysis = self._parse_schema_analysis(str(result))
            analysis['org_connected'] = self.sf_connected
            analysis['org_context'] = org_context_data
            analysis['mentioned_objects'] = mentioned_objects
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing schema analysis: {e}")
            # Return basic fallback analysis focused on schema
            return {
                'existing_objects': ['Account', 'Contact'] if not org_context_data else list(org_context_data.keys()),
                'new_objects': ['Custom_Object__c'],
                'field_recommendations': ['Name (Text)', 'Description (Long Text Area)'],
                'relationships': ['Custom_Object__c → Contact (Lookup)'],
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