import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Salesforce AI Agent system."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Salesforce Connected App Configuration (Client Credentials Flow)
    SALESFORCE_INSTANCE_URL: Optional[str] = os.getenv("SALESFORCE_INSTANCE_URL")
    SALESFORCE_CLIENT_ID: Optional[str] = os.getenv("SALESFORCE_CLIENT_ID")
    SALESFORCE_CLIENT_SECRET: Optional[str] = os.getenv("SALESFORCE_CLIENT_SECRET")
    
    # Legacy fields (optional - for backward compatibility)
    SALESFORCE_USERNAME: Optional[str] = os.getenv("SALESFORCE_USERNAME")
    SALESFORCE_PASSWORD: Optional[str] = os.getenv("SALESFORCE_PASSWORD")
    SALESFORCE_SECURITY_TOKEN: Optional[str] = os.getenv("SALESFORCE_SECURITY_TOKEN")
    
    # Salesforce API Configuration
    SALESFORCE_API_VERSION: str = os.getenv("SALESFORCE_API_VERSION", "v58.0")
    SALESFORCE_DOMAIN: str = os.getenv("SALESFORCE_DOMAIN", "login")  # 'login' for production, 'test' for sandbox
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Test Configuration Flag
    # When True: Use environment variables from .env file (bypass UI configuration)
    # When False: Use UI configuration popup (production mode)
    USE_ENV_CONFIG: bool = os.getenv("USE_ENV_CONFIG", "False").lower() == "true"
    
    # Memory and Storage
    CONVERSATION_HISTORY_PATH: str = "data/conversation_history"
    PLANS_STORAGE_PATH: str = "data/implementation_plans"
    
    # Salesforce Connection Settings
    SALESFORCE_CONNECTION_TIMEOUT: int = int(os.getenv("SALESFORCE_CONNECTION_TIMEOUT", "30"))
    SALESFORCE_RETRY_ATTEMPTS: int = int(os.getenv("SALESFORCE_RETRY_ATTEMPTS", "3"))
    
    @classmethod
    def validate_required_keys(cls) -> bool:
        """Validate that required configuration keys are present."""
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not found. Please set it in your .env file.")
            return False
        return True
    
    @classmethod
    def validate_salesforce_config(cls) -> bool:
        """Validate Salesforce configuration for connected app."""
        # Check for Client Credentials Flow (preferred - only 3 fields needed)
        if cls.SALESFORCE_INSTANCE_URL and cls.SALESFORCE_CLIENT_ID and cls.SALESFORCE_CLIENT_SECRET:
            return True
        
        # Check for Username-Password Flow (legacy - 6 fields needed)
        legacy_complete = all([
            cls.SALESFORCE_INSTANCE_URL,
            cls.SALESFORCE_CLIENT_ID,
            cls.SALESFORCE_CLIENT_SECRET,
            cls.SALESFORCE_USERNAME,
            cls.SALESFORCE_PASSWORD,
            cls.SALESFORCE_SECURITY_TOKEN
        ])
        
        if legacy_complete:
            return True
        
        # Neither flow is properly configured
        missing_for_client_creds = []
        if not cls.SALESFORCE_INSTANCE_URL:
            missing_for_client_creds.append("SALESFORCE_INSTANCE_URL")
        if not cls.SALESFORCE_CLIENT_ID:
            missing_for_client_creds.append("SALESFORCE_CLIENT_ID")
        if not cls.SALESFORCE_CLIENT_SECRET:
            missing_for_client_creds.append("SALESFORCE_CLIENT_SECRET")
        
        print(f"Warning: Missing Salesforce configuration.")
        print(f"For Client Credentials Flow (recommended), you need: {', '.join(missing_for_client_creds)}")
        print("Salesforce org integration will be disabled.")
        return False
    
    @classmethod
    def get_salesforce_auth_type(cls) -> str:
        """Determine which authentication type to use."""
        # Prefer Client Credentials if available
        if cls.SALESFORCE_INSTANCE_URL and cls.SALESFORCE_CLIENT_ID and cls.SALESFORCE_CLIENT_SECRET:
            # Check if username/password are also provided (would use username-password flow)
            if cls.SALESFORCE_USERNAME and cls.SALESFORCE_PASSWORD and cls.SALESFORCE_SECURITY_TOKEN:
                return "username_password"  # Legacy method if all fields provided
            else:
                return "client_credentials"  # Preferred method
        
        return "none" 