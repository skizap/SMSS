"""
Social Media Surveillance System - Analysis Error Handler
Comprehensive error handling, logging, retry mechanisms, and fallback strategies
for the AI analysis system.
"""

import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import json

from core.config import config

# Configure logging
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories"""
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    PROCESSING_ERROR = "processing_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"

@dataclass
class ErrorInfo:
    """Container for error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'error_id': self.error_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'stack_trace': self.stack_trace
        }

class RetryConfig:
    """Configuration for retry mechanisms"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter

class AnalysisErrorHandler:
    """Comprehensive error handler for analysis operations"""
    
    def __init__(self):
        self.error_log = []
        self.error_counts = {}
        self.fallback_strategies = {}
        self.retry_configs = self._setup_retry_configs()
        
        logger.info("Analysis error handler initialized")
    
    def _setup_retry_configs(self) -> Dict[ErrorCategory, RetryConfig]:
        """Setup retry configurations for different error types"""
        return {
            ErrorCategory.API_ERROR: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.NETWORK_ERROR: RetryConfig(max_attempts=5, base_delay=1.0),
            ErrorCategory.RATE_LIMIT_ERROR: RetryConfig(max_attempts=3, base_delay=60.0),
            ErrorCategory.TIMEOUT_ERROR: RetryConfig(max_attempts=2, base_delay=5.0),
            ErrorCategory.DATABASE_ERROR: RetryConfig(max_attempts=2, base_delay=1.0),
            ErrorCategory.PROCESSING_ERROR: RetryConfig(max_attempts=1, base_delay=0.0),
            ErrorCategory.CONFIGURATION_ERROR: RetryConfig(max_attempts=1, base_delay=0.0),
            ErrorCategory.VALIDATION_ERROR: RetryConfig(max_attempts=1, base_delay=0.0)
        }
    
    def handle_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any] = None,
        details: Dict[str, Any] = None
    ) -> ErrorInfo:
        """
        Handle and log an error
        
        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity
            context: Context information
            details: Additional error details
            
        Returns:
            ErrorInfo object
        """
        error_id = self._generate_error_id()
        
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            details=details or {},
            timestamp=datetime.now(timezone.utc),
            context=context or {},
            stack_trace=traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        )
        
        # Log the error
        self._log_error(error_info)
        
        # Store error for monitoring
        self.error_log.append(error_info)
        
        # Update error counts
        category_key = category.value
        self.error_counts[category_key] = self.error_counts.get(category_key, 0) + 1
        
        # Trigger alerts for critical errors
        if severity == ErrorSeverity.CRITICAL:
            self._trigger_critical_alert(error_info)
        
        return error_info
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        import uuid
        return f"ERR_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        log_message = f"[{error_info.error_id}] {error_info.category.value}: {error_info.message}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={'error_info': error_info.to_dict()})
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={'error_info': error_info.to_dict()})
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={'error_info': error_info.to_dict()})
        else:
            logger.info(log_message, extra={'error_info': error_info.to_dict()})
    
    def _trigger_critical_alert(self, error_info: ErrorInfo):
        """Trigger alert for critical errors"""
        # This would integrate with notification system
        logger.critical(f"CRITICAL ERROR ALERT: {error_info.error_id} - {error_info.message}")
        
        # Could send email, SMS, or other notifications here
        # For now, just log the critical alert
    
    def retry_with_backoff(
        self,
        func: Callable,
        category: ErrorCategory,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry and exponential backoff
        
        Args:
            func: Function to execute
            category: Error category for retry configuration
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        retry_config = self.retry_configs.get(category, RetryConfig())
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == retry_config.max_attempts - 1:
                    # Last attempt failed
                    break
                
                # Calculate delay
                delay = retry_config.base_delay
                if retry_config.exponential_backoff:
                    delay *= (2 ** attempt)
                
                # Apply jitter
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                # Cap at max delay
                delay = min(delay, retry_config.max_delay)
                
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                time.sleep(delay)
        
        # All retries failed
        error_info = self.handle_error(
            last_exception,
            category,
            ErrorSeverity.HIGH,
            context={'function': func.__name__, 'attempts': retry_config.max_attempts}
        )
        raise last_exception
    
    def register_fallback_strategy(
        self,
        category: ErrorCategory,
        fallback_func: Callable
    ):
        """
        Register a fallback strategy for an error category
        
        Args:
            category: Error category
            fallback_func: Fallback function to execute
        """
        self.fallback_strategies[category] = fallback_func
        logger.info(f"Registered fallback strategy for {category.value}")
    
    def execute_with_fallback(
        self,
        func: Callable,
        category: ErrorCategory,
        fallback_result: Any = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with fallback strategy
        
        Args:
            func: Primary function to execute
            category: Error category
            fallback_result: Default fallback result
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_info = self.handle_error(
                e,
                category,
                ErrorSeverity.MEDIUM,
                context={'function': func.__name__, 'fallback_used': True}
            )
            
            # Try registered fallback strategy
            if category in self.fallback_strategies:
                try:
                    logger.info(f"Executing fallback strategy for {category.value}")
                    return self.fallback_strategies[category](*args, **kwargs)
                except Exception as fallback_error:
                    self.handle_error(
                        fallback_error,
                        category,
                        ErrorSeverity.HIGH,
                        context={'function': 'fallback_strategy', 'original_error': str(e)}
                    )
            
            # Return default fallback result
            logger.warning(f"Using default fallback result for {category.value}")
            return fallback_result
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.error_log)
        
        if total_errors == 0:
            return {'total_errors': 0, 'error_rate': 0.0}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        recent_errors = 0
        
        recent_threshold = datetime.now(timezone.utc).timestamp() - 3600  # Last hour
        
        for error in self.error_log:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            
            if error.timestamp.timestamp() > recent_threshold:
                recent_errors += 1
        
        return {
            'total_errors': total_errors,
            'recent_errors_1h': recent_errors,
            'error_rate_1h': recent_errors / 60.0,  # Errors per minute
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'most_common_category': max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
        }
    
    def clear_error_log(self):
        """Clear error log (for maintenance)"""
        cleared_count = len(self.error_log)
        self.error_log.clear()
        self.error_counts.clear()
        logger.info(f"Cleared {cleared_count} errors from error log")

def with_error_handling(
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    fallback_result: Any = None,
    retry: bool = False
):
    """
    Decorator for automatic error handling
    
    Args:
        category: Error category
        severity: Error severity
        fallback_result: Fallback result if function fails
        retry: Whether to retry on failure
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if retry:
                return error_handler.retry_with_backoff(func, category, *args, **kwargs)
            else:
                return error_handler.execute_with_fallback(
                    func, category, fallback_result, *args, **kwargs
                )
        return wrapper
    return decorator

# Global error handler instance
error_handler = AnalysisErrorHandler()
