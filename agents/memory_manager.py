import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config import Config

@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    timestamp: str
    role: str  # 'user', 'agent', 'system'
    content: str
    message_type: str = "text"  # 'text', 'requirement', 'clarification', 'plan'
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create message from dictionary."""
        return cls(
            timestamp=data["timestamp"],
            role=data["role"],
            content=data["content"],
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {})
        )

class MemoryManager:
    """Manages conversation history and memory persistence with improved memory management."""
    
    MAX_HISTORY_SIZE = 100  # Prevent memory leaks
    MAX_FILE_SIZE_MB = 10   # Maximum file size in MB
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.conversation_history: List[ConversationMessage] = []
        self.requirements_extracted: List[Dict[str, Any]] = []
        self.implementation_plan: Optional[Dict[str, Any]] = None
        self._memory_usage = 0
        self._ensure_directories()
        self._load_existing_conversation()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(Config.CONVERSATION_HISTORY_PATH, exist_ok=True)
        os.makedirs(Config.PLANS_STORAGE_PATH, exist_ok=True)
    
    def _get_conversation_file_path(self) -> str:
        """Get the file path for conversation history."""
        return os.path.join(Config.CONVERSATION_HISTORY_PATH, f"{self.session_id}.json")
    
    def _get_plan_file_path(self) -> str:
        """Get the file path for implementation plan."""
        return os.path.join(Config.PLANS_STORAGE_PATH, f"{self.session_id}_plan.json")
    
    def _load_existing_conversation(self):
        """Load existing conversation if it exists."""
        file_path = self._get_conversation_file_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = [
                        ConversationMessage.from_dict(msg) for msg in data.get("messages", [])
                    ]
                    self.requirements_extracted = data.get("requirements_extracted", [])
            except Exception as e:
                print(f"Error loading conversation: {e}")
    
    def add_message(self, role: str, content: str, message_type: str = "text", metadata: Dict[str, Any] = None):
        """Add a new message to the conversation history with memory management."""
        # Prevent memory leaks by limiting history size
        if len(self.conversation_history) >= self.MAX_HISTORY_SIZE:
            # Keep only the most recent messages
            self.conversation_history = self.conversation_history[-(self.MAX_HISTORY_SIZE // 2):]
            self._memory_usage = len(self.conversation_history)
        
        message = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        self.conversation_history.append(message)
        self._memory_usage = len(self.conversation_history)
        self._save_conversation()
    
    def get_conversation_context(self, max_messages: int = 20) -> str:
        """Get recent conversation context as a formatted string."""
        recent_messages = self.conversation_history[-max_messages:]
        context = []
        for msg in recent_messages:
            context.append(f"[{msg.role.upper()}]: {msg.content}")
        return "\n".join(context)
    
    def get_requirements_summary(self) -> str:
        """Get a summary of extracted requirements."""
        if not self.requirements_extracted:
            return "No requirements extracted yet."
        
        summary = "Extracted Requirements:\n"
        for i, req in enumerate(self.requirements_extracted, 1):
            summary += f"{i}. {req.get('description', 'No description')}\n"
        return summary
    
    def extract_requirement(self, requirement: Dict[str, Any]):
        """Extract and store a requirement."""
        requirement["extracted_at"] = datetime.now().isoformat()
        self.requirements_extracted.append(requirement)
        self._save_conversation()
    
    def save_implementation_plan(self, plan: Dict[str, Any]):
        """Save the implementation plan."""
        self.implementation_plan = plan
        plan_file_path = self._get_plan_file_path()
        
        plan_data = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "plan": plan,
            "requirements_count": len(self.requirements_extracted)
        }
        
        try:
            with open(plan_file_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving implementation plan: {e}")
    
    def _save_conversation(self):
        """Save conversation history to file."""
        file_path = self._get_conversation_file_path()
        
        conversation_data = {
            "session_id": self.session_id,
            "last_updated": datetime.now().isoformat(),
            "messages": [msg.to_dict() for msg in self.conversation_history],
            "requirements_extracted": self.requirements_extracted
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def get_all_sessions(self) -> List[str]:
        """Get list of all available conversation sessions."""
        sessions = []
        if os.path.exists(Config.CONVERSATION_HISTORY_PATH):
            for filename in os.listdir(Config.CONVERSATION_HISTORY_PATH):
                if filename.endswith('.json'):
                    sessions.append(filename.replace('.json', ''))
        return sorted(sessions, reverse=True)  # Most recent first
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history as a list of dictionaries."""
        return [msg.to_dict() for msg in self.conversation_history]
    
    def clear_conversation_history(self):
        """Clear the conversation history and reset memory usage."""
        self.conversation_history.clear()
        self.requirements_extracted.clear()
        self.implementation_plan = None
        self._memory_usage = 0
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory usage status."""
        file_path = self._get_conversation_file_path()
        file_size_mb = 0
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        return {
            "session_id": self.session_id,
            "message_count": len(self.conversation_history),
            "max_messages": self.MAX_HISTORY_SIZE,
            "memory_usage": self._memory_usage,
            "file_size_mb": round(file_size_mb, 2),
            "max_file_size_mb": self.MAX_FILE_SIZE_MB,
            "requirements_count": len(self.requirements_extracted)
        }
    
    def optimize_memory(self):
        """Optimize memory usage by removing old messages and compacting data."""
        if len(self.conversation_history) > self.MAX_HISTORY_SIZE // 2:
            # Keep only the most recent half of messages
            keep_count = self.MAX_HISTORY_SIZE // 2
            self.conversation_history = self.conversation_history[-keep_count:]
            self._memory_usage = len(self.conversation_history)
            self._save_conversation()
        
        # Clean up old session files if they're too large
        file_path = self._get_conversation_file_path()
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                # Archive the current session and start fresh
                archive_path = file_path.replace('.json', f'_archived_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                os.rename(file_path, archive_path)
                self.clear_conversation_history() 