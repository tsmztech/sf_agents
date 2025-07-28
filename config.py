import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Salesforce AI Agent system."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Salesforce Connected App Configuration
    SALESFORCE_INSTANCE_URL: Optional[str] = os.getenv("SALESFORCE_INSTANCE_URL")
    SALESFORCE_CLIENT_ID: Optional[str] = os.getenv("SALESFORCE_CLIENT_ID")
    SALESFORCE_CLIENT_SECRET: Optional[str] = os.getenv("SALESFORCE_CLIENT_SECRET")
    SALESFORCE_USERNAME: Optional[str] = os.getenv("SALESFORCE_USERNAME")
    SALESFORCE_PASSWORD: Optional[str] = os.getenv("SALESFORCE_PASSWORD")
    SALESFORCE_SECURITY_TOKEN: Optional[str] = os.getenv("SALESFORCE_SECURITY_TOKEN")
    
    # Salesforce API Configuration
    SALESFORCE_API_VERSION: str = os.getenv("SALESFORCE_API_VERSION", "v58.0")
    SALESFORCE_DOMAIN: str = os.getenv("SALESFORCE_DOMAIN", "login")  # 'login' for production, 'test' for sandbox
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
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
        required_sf_vars = [
            cls.SALESFORCE_INSTANCE_URL,
            cls.SALESFORCE_CLIENT_ID,
            cls.SALESFORCE_CLIENT_SECRET,
            cls.SALESFORCE_USERNAME,
            cls.SALESFORCE_PASSWORD,
            cls.SALESFORCE_SECURITY_TOKEN
        ]
        
        missing_vars = []
        if not cls.SALESFORCE_INSTANCE_URL:
            missing_vars.append("SALESFORCE_INSTANCE_URL")
        if not cls.SALESFORCE_CLIENT_ID:
            missing_vars.append("SALESFORCE_CLIENT_ID")
        if not cls.SALESFORCE_CLIENT_SECRET:
            missing_vars.append("SALESFORCE_CLIENT_SECRET")
        if not cls.SALESFORCE_USERNAME:
            missing_vars.append("SALESFORCE_USERNAME")
        if not cls.SALESFORCE_PASSWORD:
            missing_vars.append("SALESFORCE_PASSWORD")
        if not cls.SALESFORCE_SECURITY_TOKEN:
            missing_vars.append("SALESFORCE_SECURITY_TOKEN")
        
        if missing_vars:
            print(f"Warning: Missing Salesforce configuration variables: {', '.join(missing_vars)}")
            print("Salesforce org integration will be disabled.")
            return False
        
        return True 