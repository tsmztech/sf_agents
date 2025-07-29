"""
CrewAI tool wrapper for Salesforce org analysis.
Enables agents to access real-time Salesforce data and schema information.
"""

from crewai.tools.base_tool import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import json
import logging

# Import our existing Salesforce connector
try:
    from agents.salesforce_connector import SalesforceConnector, SalesforceConnectionError
except ImportError:
    # Fallback for development
    SalesforceConnector = None
    SalesforceConnectionError = Exception

logger = logging.getLogger(__name__)

class SalesforceAnalysisInput(BaseModel):
    """Input schema for Salesforce analysis tool."""
    query: str = Field(description="What to analyze in the Salesforce org (objects, fields, relationships, etc.)")
    analysis_type: str = Field(
        description="Type of analysis: 'schema', 'objects', 'fields', 'relationships', 'limits', 'data_patterns'",
        default="schema"
    )

class SalesforceAnalysisTool(BaseTool):
    """
    Tool for analyzing Salesforce org schema and data.
    Provides real-time access to Salesforce org information for agents.
    """
    
    name: str = "Salesforce Org Analyzer"
    description: str = """
    Analyze Salesforce org schema, objects, fields, and relationships in real-time.
    
    Use this tool to:
    - Get existing object and field information
    - Analyze schema for reusable components
    - Check org limits and constraints
    - Understand data patterns and relationships
    
    Input should be a clear description of what you want to analyze.
    Example: "Get all custom objects and their fields" or "Analyze Contact object relationships"
    """
    args_schema: Type[BaseModel] = SalesforceAnalysisInput
    
    def _run(self, query: str, analysis_type: str = "schema") -> str:
        """
        Execute Salesforce org analysis.
        
        Args:
            query: What to analyze in the Salesforce org
            analysis_type: Type of analysis to perform
            
        Returns:
            JSON string with analysis results
        """
        
        if not SalesforceConnector:
            logger.warning("SalesforceConnector not available")
            return json.dumps({
                "error": "Salesforce connector not available",
                "message": "Operating in offline mode - no real-time org data",
                "recommendations": [
                    "Consider standard Salesforce objects like Contact, Account, Case, Opportunity",
                    "Use appropriate field types: Text, Number, Date, Lookup, Picklist",
                    "Follow Salesforce naming conventions for API names"
                ]
            })
        
        try:
            connector = SalesforceConnector()
            
            # Route to appropriate analysis method based on type
            if analysis_type == "schema":
                result = self._analyze_schema(connector, query)
            elif analysis_type == "objects":
                result = self._analyze_objects(connector, query)
            elif analysis_type == "fields":
                result = self._analyze_fields(connector, query)
            elif analysis_type == "relationships":
                result = self._analyze_relationships(connector, query)
            elif analysis_type == "limits":
                result = self._analyze_limits(connector, query)
            elif analysis_type == "data_patterns":
                result = self._analyze_data_patterns(connector, query)
            else:
                result = self._general_analysis(connector, query)
            
            return json.dumps(result, indent=2)
            
        except SalesforceConnectionError as e:
            logger.error(f"Salesforce connection error: {e}")
            return json.dumps({
                "error": "Salesforce connection failed",
                "message": str(e),
                "fallback_mode": True,
                "recommendations": [
                    "Verify Salesforce credentials are configured correctly",
                    "Check network connectivity",
                    "Consider using standard Salesforce objects as fallback"
                ]
            })
            
        except Exception as e:
            logger.error(f"Unexpected error in Salesforce analysis: {e}")
            return json.dumps({
                "error": "Analysis failed",
                "message": str(e),
                "query": query,
                "analysis_type": analysis_type
            })
    
    def _analyze_schema(self, connector: Any, query: str) -> dict:
        """Analyze overall schema and objects."""
        try:
            # Get all objects
            all_objects = connector.get_all_objects()
            
            # Get org limits for context
            org_limits = connector.get_org_limits()
            
            # Test connection and get basic org info
            connection_test = connector.test_connection()
            
            # Limit objects to prevent token overflow
            custom_objects = [obj for obj in all_objects if obj.get('name', '').endswith('__c')][:20]
            standard_objects = [obj for obj in all_objects if not obj.get('name', '').endswith('__c')][:20]
            
            return {
                "org_info": connection_test,
                "total_objects": len(all_objects),
                "custom_objects": custom_objects,
                "standard_objects": standard_objects,
                "org_limits": org_limits,
                "schema_summary": {
                    "objects_analyzed": len(all_objects),
                    "objects_returned": len(custom_objects) + len(standard_objects),
                    "note": "Limited to top 20 custom and 20 standard objects for performance",
                    "connection_status": "connected" if connection_test.get('success') else "failed",
                    "analysis_timestamp": connector._get_current_timestamp() if hasattr(connector, '_get_current_timestamp') else "unknown"
                }
            }
            
        except Exception as e:
            return {"error": f"Schema analysis failed: {str(e)}"}
    
    def _analyze_objects(self, connector: Any, query: str) -> dict:
        """Analyze specific objects or object patterns."""
        try:
            # Search for objects based on query
            search_results = connector.search_objects_by_name(query)
            
            detailed_objects = []
            for obj in search_results[:5]:  # Limit to first 5 for performance
                try:
                    obj_details = connector.get_object_schema(obj['name'])
                    detailed_objects.append(obj_details)
                except Exception as e:
                    logger.warning(f"Could not get details for object {obj['name']}: {e}")
            
            return {
                "search_query": query,
                "objects_found": len(search_results),
                "detailed_objects": detailed_objects,
                "object_summary": [
                    {
                        "name": obj['name'],
                        "label": obj.get('label', 'Unknown'),
                        "custom": obj['name'].endswith('__c'),
                        "creatable": obj.get('createable', False),
                        "queryable": obj.get('queryable', False)
                    }
                    for obj in search_results
                ]
            }
            
        except Exception as e:
            return {"error": f"Object analysis failed: {str(e)}"}
    
    def _analyze_fields(self, connector: Any, query: str) -> dict:
        """Analyze fields for specific objects."""
        try:
            # Extract object name from query if possible
            object_name = self._extract_object_name(query)
            
            if object_name:
                field_details = connector.get_field_details(object_name)
                return {
                    "object_name": object_name,
                    "field_analysis": field_details,
                    "field_count": len(field_details.get('fields', [])),
                    "custom_fields": [f for f in field_details.get('fields', []) if f.get('name', '').endswith('__c')],
                    "required_fields": [f for f in field_details.get('fields', []) if f.get('nillable') == False]
                }
            else:
                return {"error": "Could not determine object name from query", "query": query}
                
        except Exception as e:
            return {"error": f"Field analysis failed: {str(e)}"}
    
    def _analyze_relationships(self, connector: Any, query: str) -> dict:
        """Analyze object relationships."""
        try:
            object_name = self._extract_object_name(query)
            
            if object_name:
                relationships = connector.get_related_objects(object_name)
                return {
                    "object_name": object_name,
                    "relationship_analysis": relationships,
                    "relationship_types": {
                        "lookup": [r for r in relationships if r.get('relationshipName')],
                        "master_detail": [r for r in relationships if r.get('cascadeDelete') == True],
                        "child_relationships": [r for r in relationships if r.get('childSObject')]
                    }
                }
            else:
                return {"error": "Could not determine object name for relationship analysis"}
                
        except Exception as e:
            return {"error": f"Relationship analysis failed: {str(e)}"}
    
    def _analyze_limits(self, connector: Any, query: str) -> dict:
        """Analyze org limits and constraints."""
        try:
            limits = connector.get_org_limits()
            return {
                "org_limits": limits,
                "critical_limits": {
                    "api_calls": limits.get('DailyApiRequests', {}),
                    "storage": limits.get('DataStorageMB', {}),
                    "file_storage": limits.get('FileStorageMB', {}),
                    "custom_objects": limits.get('CustomObjects', {})
                },
                "recommendations": [
                    "Monitor API call usage during implementation",
                    "Consider data archival strategies if approaching storage limits",
                    "Plan for governor limits in automation design"
                ]
            }
            
        except Exception as e:
            return {"error": f"Limits analysis failed: {str(e)}"}
    
    def _analyze_data_patterns(self, connector: Any, query: str) -> dict:
        """Analyze data patterns and usage."""
        try:
            # This is a placeholder for data pattern analysis
            # In a real implementation, you might run SOQL queries to analyze data
            return {
                "analysis_type": "data_patterns",
                "query": query,
                "message": "Data pattern analysis requires specific SOQL queries",
                "recommendations": [
                    "Use SOQL queries to analyze record counts and data distribution",
                    "Check for duplicate data patterns",
                    "Analyze field usage and data quality"
                ]
            }
            
        except Exception as e:
            return {"error": f"Data pattern analysis failed: {str(e)}"}
    
    def _general_analysis(self, connector: Any, query: str) -> dict:
        """General analysis for unspecified queries."""
        try:
            # Try to provide helpful analysis based on the query
            if 'object' in query.lower():
                return self._analyze_objects(connector, query)
            elif 'field' in query.lower():
                return self._analyze_fields(connector, query)
            elif 'relationship' in query.lower():
                return self._analyze_relationships(connector, query)
            else:
                return self._analyze_schema(connector, query)
                
        except Exception as e:
            return {"error": f"General analysis failed: {str(e)}"}
    
    def _extract_object_name(self, query: str) -> str:
        """Extract object name from query string."""
        # Simple extraction logic - can be improved
        words = query.split()
        
        # Look for common Salesforce object patterns
        for word in words:
            if word.endswith('__c') or word in ['Contact', 'Account', 'Case', 'Opportunity', 'Lead', 'User']:
                return word
        
        # Look for words that might be object names (capitalized)
        for word in words:
            if word[0].isupper() and len(word) > 2:
                return word
                
        return None

# Export the tool for use in crews
__all__ = ['SalesforceAnalysisTool'] 