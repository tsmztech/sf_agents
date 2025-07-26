import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Salesforce AI Agent system."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Salesforce Configuration (for future phases)
    SALESFORCE_USERNAME: Optional[str] = os.getenv("SALESFORCE_USERNAME")
    SALESFORCE_PASSWORD: Optional[str] = os.getenv("SALESFORCE_PASSWORD")
    SALESFORCE_SECURITY_TOKEN: Optional[str] = os.getenv("SALESFORCE_SECURITY_TOKEN")
    SALESFORCE_SANDBOX_URL: Optional[str] = os.getenv("SALESFORCE_SANDBOX_URL")
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Memory and Storage
    CONVERSATION_HISTORY_PATH: str = "data/conversation_history"
    PLANS_STORAGE_PATH: str = "data/implementation_plans"
    
    @classmethod
    def validate_required_keys(cls) -> bool:
        """Validate that required configuration keys are present."""
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not found. Please set it in your .env file.")
            return False
        return True 