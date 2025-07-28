import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalesforceConnectionError(Exception):
    """Custom exception for Salesforce connection issues."""
    pass

class SalesforceConnector:
    """
    Handles real-time connection to Salesforce org for schema and object access.
    Uses OAuth 2.0 Username-Password flow with Connected App credentials.
    """
    
    def __init__(self):
        self.access_token = None
        self.instance_url = None
        self.token_expires_at = None
        self.session = requests.Session()
        self.session.timeout = Config.SALESFORCE_CONNECTION_TIMEOUT
        
        # Validate configuration
        if not Config.validate_salesforce_config():
            raise SalesforceConnectionError("Invalid Salesforce configuration. Please check your .env file.")
        
        # Authenticate on initialization
        self._authenticate()
    
    def _authenticate(self) -> None:
        """
        Authenticate with Salesforce using OAuth 2.0 Client Credentials or Username-Password Flow.
        """
        auth_type = Config.get_salesforce_auth_type()
        
        if auth_type == "client_credentials":
            self._authenticate_client_credentials()
        elif auth_type == "username_password":
            self._authenticate_username_password()
        else:
            raise SalesforceConnectionError("No valid Salesforce authentication configuration found")
    
    def _authenticate_client_credentials(self) -> None:
        """
        Authenticate using OAuth 2.0 Client Credentials Flow (Server-to-Server).
        Requires only: SALESFORCE_INSTANCE_URL, SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET
        """
        try:
            # Determine auth URL based on domain (production vs sandbox)
            if Config.SALESFORCE_DOMAIN == "test":
                auth_base_url = "https://test.salesforce.com"
            else:
                auth_base_url = "https://login.salesforce.com"
            
            auth_url = f"{auth_base_url}/services/oauth2/token"
            
            # Prepare authentication data for Client Credentials Flow
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': Config.SALESFORCE_CLIENT_ID,
                'client_secret': Config.SALESFORCE_CLIENT_SECRET
            }
            
            logger.info("Authenticating with Salesforce using Client Credentials Flow...")
            response = self.session.post(auth_url, data=auth_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # For client credentials, use the configured instance URL
                self.instance_url = Config.SALESFORCE_INSTANCE_URL
                
                # Calculate token expiration (Client credentials tokens typically last longer)
                self.token_expires_at = datetime.now() + timedelta(hours=1, minutes=45)
                
                logger.info(f"Successfully authenticated with Salesforce using Client Credentials. Instance: {self.instance_url}")
            else:
                error_msg = f"Client Credentials authentication failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise SalesforceConnectionError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during Client Credentials authentication: {e}"
            logger.error(error_msg)
            raise SalesforceConnectionError(error_msg)
    
    def _authenticate_username_password(self) -> None:
        """
        Authenticate using OAuth 2.0 Username-Password Flow (Legacy).
        Requires: SALESFORCE_INSTANCE_URL, SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET,
                 SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN
        """
        try:
            # Determine auth URL based on domain (production vs sandbox)
            if Config.SALESFORCE_DOMAIN == "test":
                auth_base_url = "https://test.salesforce.com"
            else:
                auth_base_url = "https://login.salesforce.com"
            
            auth_url = f"{auth_base_url}/services/oauth2/token"
            
            # Prepare authentication data for Username-Password Flow
            auth_data = {
                'grant_type': 'password',
                'client_id': Config.SALESFORCE_CLIENT_ID,
                'client_secret': Config.SALESFORCE_CLIENT_SECRET,
                'username': Config.SALESFORCE_USERNAME,
                'password': Config.SALESFORCE_PASSWORD + Config.SALESFORCE_SECURITY_TOKEN
            }
            
            logger.info("Authenticating with Salesforce using Username-Password Flow...")
            response = self.session.post(auth_url, data=auth_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.instance_url = token_data['instance_url']
                
                # Calculate token expiration
                self.token_expires_at = datetime.now() + timedelta(hours=1, minutes=45)
                
                logger.info(f"Successfully authenticated with Salesforce using Username-Password. Instance: {self.instance_url}")
            else:
                error_msg = f"Username-Password authentication failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise SalesforceConnectionError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during Username-Password authentication: {e}"
            logger.error(error_msg)
            raise SalesforceConnectionError(error_msg)
    
    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if (not self.access_token or 
            not self.token_expires_at or 
            datetime.now() >= self.token_expires_at):
            logger.info("Token expired or invalid, re-authenticating...")
            self._authenticate()
    
    def _make_api_request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> Dict:
        """
        Make authenticated API request to Salesforce with retry logic.
        """
        self._ensure_authenticated()
        
        url = f"{self.instance_url}/services/data/{Config.SALESFORCE_API_VERSION}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        for attempt in range(Config.SALESFORCE_RETRY_ATTEMPTS):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, headers=headers, params=params)
                elif method.upper() == 'POST':
                    response = self.session.post(url, headers=headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    # Token might be expired, try to re-authenticate
                    logger.warning("Received 401, attempting re-authentication...")
                    self._authenticate()
                    continue
                else:
                    error_msg = f"API request failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise SalesforceConnectionError(error_msg)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == Config.SALESFORCE_RETRY_ATTEMPTS - 1:
                    raise SalesforceConnectionError(f"All retry attempts failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise SalesforceConnectionError("Maximum retry attempts exceeded")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Salesforce connection and return org info."""
        try:
            # Get organization information
            org_info = self._make_api_request("query", params={'q': "SELECT Id, Name, OrganizationType, InstanceName FROM Organization LIMIT 1"})
            
            # Get available sobjects count
            sobjects = self._make_api_request("sobjects")
            
            return {
                'status': 'success',
                'connected': True,
                'auth_type': Config.get_salesforce_auth_type(),
                'org_info': org_info['records'][0] if org_info['records'] else {},
                'sobjects_count': len(sobjects.get('sobjects', [])),
                'instance_url': self.instance_url,
                'api_version': Config.SALESFORCE_API_VERSION
            }
        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'error': str(e)
            }
    
    def get_object_schema(self, object_name: str) -> Dict[str, Any]:
        """
        Get complete schema information for a specific Salesforce object.
        
        Args:
            object_name: API name of the Salesforce object (e.g., 'Account', 'Contact', 'CustomObject__c')
            
        Returns:
            Complete object schema including fields, relationships, and permissions
        """
        try:
            endpoint = f"sobjects/{object_name}/describe"
            schema = self._make_api_request(endpoint)
            
            # Enrich schema with additional metadata
            enriched_schema = {
                'object_name': object_name,
                'label': schema.get('label'),
                'labelPlural': schema.get('labelPlural'),
                'custom': schema.get('custom', False),
                'createable': schema.get('createable', False),
                'updateable': schema.get('updateable', False),
                'deletable': schema.get('deletable', False),
                'queryable': schema.get('queryable', False),
                'fields': self._process_fields(schema.get('fields', [])),
                'relationships': self._extract_relationships(schema.get('fields', [])),
                'record_types': schema.get('recordTypeInfos', []),
                'child_relationships': schema.get('childRelationships', []),
                'raw_schema': schema
            }
            
            return enriched_schema
            
        except Exception as e:
            logger.error(f"Failed to get schema for object {object_name}: {e}")
            raise SalesforceConnectionError(f"Failed to get schema for {object_name}: {e}")
    
    def _process_fields(self, fields: List[Dict]) -> List[Dict]:
        """Process and enrich field information."""
        processed_fields = []
        
        for field in fields:
            processed_field = {
                'name': field.get('name'),
                'label': field.get('label'),
                'type': field.get('type'),
                'length': field.get('length'),
                'custom': field.get('custom', False),
                'createable': field.get('createable', False),
                'updateable': field.get('updateable', False),
                'required': field.get('nillable', True) == False,  # nillable False means required
                'unique': field.get('unique', False),
                'default_value': field.get('defaultValue'),
                'picklist_values': [pv['value'] for pv in field.get('picklistValues', [])],
                'reference_to': field.get('referenceTo', []),
                'relationship_name': field.get('relationshipName'),
                'help_text': field.get('inlineHelpText'),
                'formula': field.get('calculatedFormula'),
                'encrypted': field.get('encrypted', False)
            }
            processed_fields.append(processed_field)
        
        return processed_fields
    
    def _extract_relationships(self, fields: List[Dict]) -> List[Dict]:
        """Extract relationship information from fields."""
        relationships = []
        
        for field in fields:
            if field.get('type') in ['reference', 'masterdetail'] and field.get('referenceTo'):
                for ref_object in field['referenceTo']:
                    relationships.append({
                        'field_name': field.get('name'),
                        'relationship_name': field.get('relationshipName'),
                        'relationship_type': field.get('type'),
                        'related_object': ref_object,
                        'cascade_delete': field.get('cascadeDelete', False)
                    })
        
        return relationships
    
    def get_all_objects(self, include_custom_only: bool = False) -> List[Dict]:
        """
        Get list of all available objects in the org.
        
        Args:
            include_custom_only: If True, return only custom objects
            
        Returns:
            List of object metadata
        """
        try:
            sobjects_data = self._make_api_request("sobjects")
            objects = sobjects_data.get('sobjects', [])
            
            if include_custom_only:
                objects = [obj for obj in objects if obj.get('custom', False)]
            
            # Add useful metadata
            processed_objects = []
            for obj in objects:
                processed_objects.append({
                    'name': obj.get('name'),
                    'label': obj.get('label'),
                    'labelPlural': obj.get('labelPlural'),
                    'custom': obj.get('custom', False),
                    'createable': obj.get('createable', False),
                    'updateable': obj.get('updateable', False),
                    'deletable': obj.get('deletable', False),
                    'queryable': obj.get('queryable', False),
                    'searchable': obj.get('searchable', False),
                    'key_prefix': obj.get('keyPrefix')
                })
            
            return processed_objects
            
        except Exception as e:
            logger.error(f"Failed to get objects list: {e}")
            raise SalesforceConnectionError(f"Failed to get objects: {e}")
    
    def search_objects_by_name(self, search_term: str, include_fields: bool = False) -> List[Dict]:
        """
        Search for objects by name pattern.
        
        Args:
            search_term: Search pattern (case-insensitive)
            include_fields: If True, include field count for each object
            
        Returns:
            List of matching objects
        """
        try:
            all_objects = self.get_all_objects()
            matching_objects = []
            
            for obj in all_objects:
                if (search_term.lower() in obj['name'].lower() or 
                    search_term.lower() in obj.get('label', '').lower()):
                    
                    if include_fields:
                        try:
                            schema = self.get_object_schema(obj['name'])
                            obj['field_count'] = len(schema.get('fields', []))
                        except:
                            obj['field_count'] = 'N/A'
                    
                    matching_objects.append(obj)
            
            return matching_objects
            
        except Exception as e:
            logger.error(f"Failed to search objects: {e}")
            raise SalesforceConnectionError(f"Failed to search objects: {e}")
    
    def get_field_details(self, object_name: str, field_name: str) -> Optional[Dict]:
        """
        Get specific field details for an object.
        
        Args:
            object_name: API name of the object
            field_name: API name of the field
            
        Returns:
            Field details or None if not found
        """
        try:
            schema = self.get_object_schema(object_name)
            
            for field in schema.get('fields', []):
                if field['name'] == field_name:
                    return field
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get field details for {object_name}.{field_name}: {e}")
            return None
    
    def get_related_objects(self, object_name: str) -> List[Dict]:
        """
        Get objects that have relationships with the specified object.
        
        Args:
            object_name: API name of the object
            
        Returns:
            List of related objects with relationship details
        """
        try:
            schema = self.get_object_schema(object_name)
            related_objects = []
            
            # Parent relationships (lookup/master-detail fields)
            for relationship in schema.get('relationships', []):
                related_objects.append({
                    'related_object': relationship['related_object'],
                    'relationship_type': relationship['relationship_type'],
                    'field_name': relationship['field_name'],
                    'relationship_name': relationship['relationship_name'],
                    'direction': 'parent'
                })
            
            # Child relationships
            for child_rel in schema.get('child_relationships', []):
                related_objects.append({
                    'related_object': child_rel.get('childSObject'),
                    'relationship_type': 'child',
                    'field_name': child_rel.get('field'),
                    'relationship_name': child_rel.get('relationshipName'),
                    'direction': 'child'
                })
            
            return related_objects
            
        except Exception as e:
            logger.error(f"Failed to get related objects for {object_name}: {e}")
            raise SalesforceConnectionError(f"Failed to get related objects for {object_name}: {e}")
    
    def execute_soql_query(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Execute SOQL query and return results.
        
        Args:
            query: SOQL query string
            limit: Maximum number of records to return
            
        Returns:
            List of query results
        """
        try:
            # Add LIMIT clause if not present
            if 'LIMIT' not in query.upper():
                query += f" LIMIT {limit}"
            
            result = self._make_api_request("query", params={'q': query})
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Failed to execute SOQL query: {e}")
            raise SalesforceConnectionError(f"Query execution failed: {e}")
    
    def analyze_data_patterns(self, object_name: str, field_name: str, limit: int = 50) -> Dict:
        """
        Analyze data patterns in a specific field.
        
        Args:
            object_name: API name of the object
            field_name: API name of the field
            limit: Maximum number of pattern examples to return
            
        Returns:
            Data pattern analysis
        """
        try:
            # Get field metadata first
            field_details = self.get_field_details(object_name, field_name)
            if not field_details:
                return {'error': f'Field {field_name} not found in {object_name}'}
            
            # Create appropriate query based on field type
            if field_details['type'] in ['picklist', 'multipicklist']:
                query = f"SELECT {field_name}, COUNT(Id) cnt FROM {object_name} WHERE {field_name} != null GROUP BY {field_name} ORDER BY COUNT(Id) DESC LIMIT {limit}"
            else:
                query = f"SELECT {field_name} FROM {object_name} WHERE {field_name} != null LIMIT {limit}"
            
            results = self.execute_soql_query(query)
            
            return {
                'field_name': field_name,
                'object_name': object_name,
                'field_type': field_details['type'],
                'data_samples': results,
                'sample_count': len(results),
                'field_metadata': field_details
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze data patterns: {e}")
            return {'error': str(e)}
    
    def get_org_limits(self) -> Dict:
        """Get current org limits and usage."""
        try:
            limits = self._make_api_request("limits")
            return limits
        except Exception as e:
            logger.error(f"Failed to get org limits: {e}")
            return {'error': str(e)} 