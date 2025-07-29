"""
Enhanced Error Handling System for SF Agents.
Provides structured error handling, recovery mechanisms, and user-friendly error messages.
"""

import logging
import traceback
import functools
from typing import Dict, Any, Callable, Optional, Union
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Standard error types for consistent error handling."""
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    VALIDATION = "validation"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SFAgentError(Exception):
    """Base exception class for SF Agent errors."""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 suggestion: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.suggestion = suggestion
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

class RateLimitError(SFAgentError):
    """Rate limit exceeded error."""
    def __init__(self, message: str = "API rate limit exceeded", suggestion: str = "Please wait a moment and try again"):
        super().__init__(message, ErrorType.RATE_LIMIT, ErrorSeverity.MEDIUM, suggestion)

class AuthenticationError(SFAgentError):
    """Authentication failure error."""
    def __init__(self, message: str = "Authentication failed", suggestion: str = "Please check your API credentials"):
        super().__init__(message, ErrorType.AUTHENTICATION, ErrorSeverity.HIGH, suggestion)

class NetworkError(SFAgentError):
    """Network connectivity error."""
    def __init__(self, message: str = "Network connectivity issue", suggestion: str = "Please check your internet connection"):
        super().__init__(message, ErrorType.NETWORK, ErrorSeverity.MEDIUM, suggestion)

class ValidationError(SFAgentError):
    """Input validation error."""
    def __init__(self, message: str = "Input validation failed", suggestion: str = "Please check your input and try again"):
        super().__init__(message, ErrorType.VALIDATION, ErrorSeverity.LOW, suggestion)

class ProcessingError(SFAgentError):
    """Processing/execution error."""
    def __init__(self, message: str = "Processing failed", suggestion: str = "Please try again or contact support"):
        super().__init__(message, ErrorType.PROCESSING, ErrorSeverity.MEDIUM, suggestion)

class ConfigurationError(SFAgentError):
    """Configuration error."""
    def __init__(self, message: str = "Configuration error", suggestion: str = "Please check your configuration settings"):
        super().__init__(message, ErrorType.CONFIGURATION, ErrorSeverity.HIGH, suggestion)

class MemoryError(SFAgentError):
    """Memory management error."""
    def __init__(self, message: str = "Memory management error", suggestion: str = "Please clear conversation history or restart"):
        super().__init__(message, ErrorType.MEMORY, ErrorSeverity.MEDIUM, suggestion)

class TimeoutError(SFAgentError):
    """Operation timeout error."""
    def __init__(self, message: str = "Operation timed out", suggestion: str = "Please try again with a simpler request"):
        super().__init__(message, ErrorType.TIMEOUT, ErrorSeverity.MEDIUM, suggestion)

class ErrorHandler:
    """Central error handling and recovery system."""
    
    def __init__(self):
        self.error_counts = {}
        self.last_errors = []
        self.max_error_history = 10
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle and format errors for consistent response.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            Standardized error response dictionary
        """
        # Log the error
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
        # Track error frequency
        error_type_str = type(error).__name__
        self.error_counts[error_type_str] = self.error_counts.get(error_type_str, 0) + 1
        
        # Store in error history
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type_str,
            "message": str(error),
            "context": context
        }
        self.last_errors.append(error_info)
        if len(self.last_errors) > self.max_error_history:
            self.last_errors = self.last_errors[-self.max_error_history:]
        
        # Handle specific error types
        if isinstance(error, SFAgentError):
            return self._format_sf_agent_error(error)
        else:
            return self._format_generic_error(error, context)
    
    def _format_sf_agent_error(self, error: SFAgentError) -> Dict[str, Any]:
        """Format SF Agent specific errors."""
        return {
            "success": False,
            "error": str(error),
            "error_type": error.error_type.value,
            "severity": error.severity.value,
            "suggestion": error.suggestion,
            "metadata": error.metadata,
            "timestamp": error.timestamp,
            "recoverable": error.severity != ErrorSeverity.CRITICAL
        }
    
    def _format_generic_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Format generic errors with best-effort classification."""
        error_message = str(error)
        error_type = ErrorType.UNKNOWN
        suggestion = "Please try again or contact support"
        severity = ErrorSeverity.MEDIUM
        
        # Classify common errors
        if "rate limit" in error_message.lower() or "429" in error_message:
            error_type = ErrorType.RATE_LIMIT
            suggestion = "Please wait a moment and try again"
        elif "authentication" in error_message.lower() or "401" in error_message:
            error_type = ErrorType.AUTHENTICATION
            suggestion = "Please check your API credentials"
            severity = ErrorSeverity.HIGH
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            error_type = ErrorType.NETWORK
            suggestion = "Please check your internet connection"
        elif "timeout" in error_message.lower():
            error_type = ErrorType.TIMEOUT
            suggestion = "Please try again with a simpler request"
        elif "memory" in error_message.lower() or "out of memory" in error_message.lower():
            error_type = ErrorType.MEMORY
            suggestion = "Please clear conversation history or restart"
        
        return {
            "success": False,
            "error": error_message,
            "error_type": error_type.value,
            "severity": severity.value,
            "suggestion": suggestion,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "recoverable": severity != ErrorSeverity.CRITICAL
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": self.error_counts,
            "recent_errors": self.last_errors,
            "total_errors": sum(self.error_counts.values())
        }
    
    def clear_error_history(self):
        """Clear error history and statistics."""
        self.error_counts.clear()
        self.last_errors.clear()

# Global error handler instance
error_handler = ErrorHandler()

def safe_execute(context: str = "", fallback_result: Any = None):
    """
    Decorator for safe execution of functions with error handling.
    
    Args:
        context: Description of the operation being performed
        fallback_result: Result to return if an error occurs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_response = error_handler.handle_error(e, context or func.__name__)
                if fallback_result is not None:
                    error_response['fallback_result'] = fallback_result
                return error_response
        return wrapper
    return decorator

def validate_input(input_data: Any, validation_rules: Dict[str, Any]) -> bool:
    """
    Validate input data against specified rules.
    
    Args:
        input_data: Data to validate
        validation_rules: Dictionary of validation rules
        
    Returns:
        True if validation passes
        
    Raises:
        ValidationError: If validation fails
    """
    if validation_rules.get('required', False) and not input_data:
        raise ValidationError("Required input is missing")
    
    if validation_rules.get('min_length') and len(str(input_data)) < validation_rules['min_length']:
        raise ValidationError(f"Input must be at least {validation_rules['min_length']} characters")
    
    if validation_rules.get('max_length') and len(str(input_data)) > validation_rules['max_length']:
        raise ValidationError(f"Input must not exceed {validation_rules['max_length']} characters")
    
    if validation_rules.get('type') and not isinstance(input_data, validation_rules['type']):
        raise ValidationError(f"Input must be of type {validation_rules['type'].__name__}")
    
    return True

def format_error_for_ui(error_dict: Dict[str, Any]) -> Dict[str, str]:
    """
    Format error dictionary for UI display.
    
    Args:
        error_dict: Error dictionary from error handler
        
    Returns:
        Dictionary with formatted error information for UI
    """
    severity = error_dict.get('severity', 'medium')
    error_type = error_dict.get('error_type', 'unknown')
    
    # Choose appropriate icons and colors
    icon_map = {
        'rate_limit': '🚦',
        'authentication': '🔐',
        'network': '🌐',
        'validation': '⚠️',
        'processing': '⚙️',
        'configuration': '🔧',
        'memory': '💾',
        'timeout': '⏰',
        'unknown': '❌'
    }
    
    severity_map = {
        'low': '💡',
        'medium': '⚠️',
        'high': '🚨',
        'critical': '🔥'
    }
    
    return {
        'icon': icon_map.get(error_type, '❌'),
        'severity_icon': severity_map.get(severity, '⚠️'),
        'title': f"{icon_map.get(error_type, '❌')} {error_type.replace('_', ' ').title()} Error",
        'message': error_dict.get('error', 'An unknown error occurred'),
        'suggestion': error_dict.get('suggestion', 'Please try again'),
        'severity': severity,
        'recoverable': error_dict.get('recoverable', True)
    } 