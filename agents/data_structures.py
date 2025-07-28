"""
Structured data types for agent communication.
Reduces parsing fragility by using typed dictionaries instead of strings.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BusinessRequirement:
    """Structured business requirement data."""
    original_text: str
    business_goal: str
    user_roles: List[str]
    data_entities: List[str]
    processes: List[str]
    constraints: List[str]
    success_criteria: List[str]
    timeline: Optional[str] = None

@dataclass
class SalesforceObject:
    """Salesforce object specification."""
    name: str
    api_name: str
    object_type: str  # 'standard' or 'custom'
    description: str
    fields: List['SalesforceField']
    relationships: List['SalesforceRelationship']
    record_types: List[str] = None

@dataclass 
class SalesforceField:
    """Salesforce field specification."""
    name: str
    api_name: str
    field_type: str
    length: Optional[int] = None
    required: bool = False
    unique: bool = False
    default_value: Optional[str] = None
    description: str = ""
    picklist_values: Optional[List[str]] = None

@dataclass
class SalesforceRelationship:
    """Salesforce relationship specification."""
    name: str
    relationship_type: str  # 'lookup', 'master_detail', 'junction'
    related_object: str
    description: str = ""

@dataclass
class SchemaRecommendation:
    """Schema expert recommendations."""
    recommended_objects: List[SalesforceObject]
    existing_objects_to_extend: List[Dict[str, Any]]
    field_recommendations: List[SalesforceField]
    relationship_design: List[SalesforceRelationship]
    best_practices: List[str]
    implementation_considerations: List[str]
    org_analysis: Optional[Dict[str, Any]] = None

@dataclass
class TechnicalArchitecture:
    """Technical architecture specification."""
    data_model: SchemaRecommendation
    automation_components: List[Dict[str, Any]]
    user_interface_components: List[Dict[str, Any]]
    security_configuration: List[Dict[str, Any]]
    integration_requirements: List[Dict[str, Any]]
    performance_considerations: List[str]

@dataclass
class ImplementationTask:
    """Implementation task specification."""
    task_id: str
    title: str
    description: str
    component_type: str  # 'object', 'field', 'workflow', 'apex', etc.
    dependencies: List[str]
    estimated_effort: str
    priority: int
    acceptance_criteria: List[str]
    technical_notes: List[str]

@dataclass
class ImplementationPlan:
    """Complete implementation plan."""
    business_requirement: BusinessRequirement
    schema_recommendations: SchemaRecommendation
    technical_architecture: TechnicalArchitecture
    implementation_tasks: List[ImplementationTask]
    project_timeline: Dict[str, Any]
    risk_assessment: List[str]
    success_metrics: List[str]
    generated_at: datetime

class AgentResponse:
    """Standardized agent response format."""
    
    def __init__(self, 
                 agent_name: str,
                 response_type: str,
                 data: Any,
                 success: bool = True,
                 message: str = "",
                 errors: List[str] = None):
        self.agent_name = agent_name
        self.response_type = response_type
        self.data = data
        self.success = success
        self.message = message
        self.errors = errors or []
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_name": self.agent_name,
            "response_type": self.response_type,
            "data": self.data,
            "success": self.success,
            "message": self.message,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create from dictionary."""
        return cls(
            agent_name=data["agent_name"],
            response_type=data["response_type"],
            data=data["data"],
            success=data.get("success", True),
            message=data.get("message", ""),
            errors=data.get("errors", [])
        )

def validate_schema_recommendation(data: Dict[str, Any]) -> SchemaRecommendation:
    """
    Validate and convert dictionary to SchemaRecommendation.
    Provides better error handling than heuristic parsing.
    """
    try:
        # Extract and validate objects
        objects = []
        for obj_data in data.get("recommended_objects", []):
            fields = [
                SalesforceField(**field_data) 
                for field_data in obj_data.get("fields", [])
            ]
            relationships = [
                SalesforceRelationship(**rel_data)
                for rel_data in obj_data.get("relationships", [])
            ]
            
            obj = SalesforceObject(
                name=obj_data["name"],
                api_name=obj_data["api_name"],
                object_type=obj_data.get("object_type", "custom"),
                description=obj_data.get("description", ""),
                fields=fields,
                relationships=relationships,
                record_types=obj_data.get("record_types", [])
            )
            objects.append(obj)
        
        return SchemaRecommendation(
            recommended_objects=objects,
            existing_objects_to_extend=data.get("existing_objects_to_extend", []),
            field_recommendations=[
                SalesforceField(**field_data)
                for field_data in data.get("field_recommendations", [])
            ],
            relationship_design=[
                SalesforceRelationship(**rel_data)
                for rel_data in data.get("relationship_design", [])
            ],
            best_practices=data.get("best_practices", []),
            implementation_considerations=data.get("implementation_considerations", []),
            org_analysis=data.get("org_analysis")
        )
        
    except KeyError as e:
        raise ValueError(f"Missing required field in schema recommendation: {e}")
    except Exception as e:
        raise ValueError(f"Invalid schema recommendation format: {e}") 