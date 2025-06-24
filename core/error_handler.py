"""
Social Media Surveillance System - Production Error Handler
Comprehensive error handling, retry logic, and graceful degradation for all scraper components.
"""

import time
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, List, Union
from functools import wraps
from enum import Enum

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, StaleElementReferenceException,
    ElementNotInteractableException, InvalidSessionIdException
)

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better handling"""
    NETWORK = "network"
    SELENIUM = "selenium"
    INSTAGRAM = "instagram"
    DATABASE = "database"
    VALIDATION = "validation"
    SYSTEM = "system"

class ScrapingError(Exception):
    """Base exception for scraping errors"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, retry_after: int = 0):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.retry_after = retry_after
        self.timestamp = datetime.now(timezone.utc)

class NetworkError(ScrapingError):
    """Network-related errors"""
    def __init__(self, message: str, retry_after: int = 30):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.HIGH, retry_after)

class InstagramError(ScrapingError):
    """Instagram-specific errors"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message, ErrorCategory.INSTAGRAM, severity)

class RateLimitError(InstagramError):
    """Rate limiting errors"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 300):
        super().__init__(message, ErrorSeverity.HIGH)
        self.retry_after = retry_after

class ProductionErrorHandler:
    """
    Production-ready error handler with retry logic, circuit breaker pattern,
    and graceful degradation capabilities.
    """
    
    def __init__(self):
        self.error_counts = {}
        self.circuit_breakers = {}
        self.last_errors = {}
        
        # Configuration
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 60.0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        
        # Error tracking
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'retries_attempted': 0,
            'successful_retries': 0
        }
    
    def with_retry(self, max_retries: int = None, delay: float = None, 
                   backoff_multiplier: float = 2.0, exceptions: tuple = None):
        """
        Decorator for adding retry logic to functions.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries
            backoff_multiplier: Multiplier for exponential backoff
            exceptions: Tuple of exceptions to catch and retry
        """
        max_retries = max_retries or self.max_retries
        delay = delay or self.base_delay
        exceptions = exceptions or (Exception,)
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_retries:
                            break
                        
                        # Calculate delay with exponential backoff
                        retry_delay = min(delay * (backoff_multiplier ** attempt), self.max_delay)
                        
                        # Log retry attempt
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                                     f"Retrying in {retry_delay:.1f}s...")
                        
                        self.error_stats['retries_attempted'] += 1
                        time.sleep(retry_delay)
                
                # All retries failed
                self._record_error(last_exception, func.__name__)
                raise last_exception
            
            return wrapper
        return decorator
    
    def with_circuit_breaker(self, failure_threshold: int = None, timeout: int = None):
        """
        Decorator for implementing circuit breaker pattern.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting to close circuit
        """
        failure_threshold = failure_threshold or self.circuit_breaker_threshold
        timeout = timeout or self.circuit_breaker_timeout
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                func_name = func.__name__
                
                # Check circuit breaker state
                if self._is_circuit_open(func_name, failure_threshold, timeout):
                    raise ScrapingError(
                        f"Circuit breaker open for {func_name}",
                        ErrorCategory.SYSTEM,
                        ErrorSeverity.HIGH
                    )
                
                try:
                    result = func(*args, **kwargs)
                    self._record_success(func_name)
                    return result
                except Exception as e:
                    self._record_failure(func_name)
                    raise
            
            return wrapper
        return decorator
    
    def handle_selenium_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle Selenium-specific errors with appropriate responses"""
        try:
            error_info = {
                'error_type': type(error).__name__,
                'message': str(error),
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'suggested_action': 'unknown'
            }
            
            if isinstance(error, TimeoutException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.MEDIUM.value,
                    'suggested_action': 'retry_with_longer_timeout',
                    'retry_recommended': True,
                    'retry_delay': 5
                })
                
            elif isinstance(error, NoSuchElementException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.LOW.value,
                    'suggested_action': 'element_not_found_graceful_continue',
                    'retry_recommended': False
                })
                
            elif isinstance(error, StaleElementReferenceException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.LOW.value,
                    'suggested_action': 'refind_element_and_retry',
                    'retry_recommended': True,
                    'retry_delay': 1
                })
                
            elif isinstance(error, ElementClickInterceptedException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.MEDIUM.value,
                    'suggested_action': 'scroll_to_element_or_use_javascript_click',
                    'retry_recommended': True,
                    'retry_delay': 2
                })
                
            elif isinstance(error, InvalidSessionIdException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.CRITICAL.value,
                    'suggested_action': 'reinitialize_browser_session',
                    'retry_recommended': True,
                    'retry_delay': 10
                })
                
            elif isinstance(error, WebDriverException):
                error_info.update({
                    'category': ErrorCategory.SELENIUM.value,
                    'severity': ErrorSeverity.HIGH.value,
                    'suggested_action': 'check_browser_status_and_restart',
                    'retry_recommended': True,
                    'retry_delay': 15
                })
            
            self._record_error(error, context)
            return error_info
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return {
                'error_type': 'ErrorHandlerFailure',
                'message': str(e),
                'original_error': str(error)
            }
    
    def handle_instagram_error(self, response_code: int = None, 
                              response_text: str = "", context: str = "") -> Dict[str, Any]:
        """Handle Instagram-specific errors"""
        try:
            error_info = {
                'error_type': 'InstagramError',
                'response_code': response_code,
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if response_code == 429:
                error_info.update({
                    'category': ErrorCategory.INSTAGRAM.value,
                    'severity': ErrorSeverity.HIGH.value,
                    'message': 'Rate limit exceeded',
                    'suggested_action': 'wait_and_retry',
                    'retry_recommended': True,
                    'retry_delay': 300  # 5 minutes
                })
                
            elif response_code == 404:
                error_info.update({
                    'category': ErrorCategory.INSTAGRAM.value,
                    'severity': ErrorSeverity.LOW.value,
                    'message': 'Content not found',
                    'suggested_action': 'skip_and_continue',
                    'retry_recommended': False
                })
                
            elif response_code == 403:
                error_info.update({
                    'category': ErrorCategory.INSTAGRAM.value,
                    'severity': ErrorSeverity.HIGH.value,
                    'message': 'Access forbidden - possible account restriction',
                    'suggested_action': 'check_account_status',
                    'retry_recommended': False
                })
                
            elif "login" in response_text.lower():
                error_info.update({
                    'category': ErrorCategory.INSTAGRAM.value,
                    'severity': ErrorSeverity.CRITICAL.value,
                    'message': 'Authentication required',
                    'suggested_action': 'reauthenticate',
                    'retry_recommended': True,
                    'retry_delay': 60
                })
            
            return error_info
            
        except Exception as e:
            logger.error(f"Error handling Instagram error: {e}")
            return {'error_type': 'ErrorHandlerFailure', 'message': str(e)}
    
    def graceful_degradation(self, primary_func: Callable, fallback_func: Callable = None,
                           fallback_value: Any = None) -> Any:
        """
        Implement graceful degradation by trying primary function first,
        then fallback function, then returning fallback value.
        """
        try:
            return primary_func()
        except Exception as e:
            logger.warning(f"Primary function failed: {e}")
            
            if fallback_func:
                try:
                    logger.info("Attempting fallback function...")
                    return fallback_func()
                except Exception as fallback_error:
                    logger.warning(f"Fallback function also failed: {fallback_error}")
            
            logger.info(f"Using fallback value: {fallback_value}")
            return fallback_value
    
    def _record_error(self, error: Exception, context: str):
        """Record error for statistics and monitoring"""
        try:
            self.error_stats['total_errors'] += 1
            
            # Categorize error
            if isinstance(error, ScrapingError):
                category = error.category.value
                severity = error.severity.value
            else:
                category = 'unknown'
                severity = 'medium'
            
            # Update category stats
            if category not in self.error_stats['errors_by_category']:
                self.error_stats['errors_by_category'][category] = 0
            self.error_stats['errors_by_category'][category] += 1
            
            # Update severity stats
            if severity not in self.error_stats['errors_by_severity']:
                self.error_stats['errors_by_severity'][severity] = 0
            self.error_stats['errors_by_severity'][severity] += 1
            
            # Store last error for context
            self.last_errors[context] = {
                'error': str(error),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': type(error).__name__
            }
            
        except Exception as e:
            logger.error(f"Failed to record error: {e}")
    
    def _is_circuit_open(self, func_name: str, threshold: int, timeout: int) -> bool:
        """Check if circuit breaker is open for a function"""
        if func_name not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[func_name]
        
        # Check if timeout has passed
        if time.time() - breaker['opened_at'] > timeout:
            # Reset circuit breaker
            del self.circuit_breakers[func_name]
            return False
        
        return breaker['failure_count'] >= threshold
    
    def _record_failure(self, func_name: str):
        """Record a failure for circuit breaker"""
        if func_name not in self.circuit_breakers:
            self.circuit_breakers[func_name] = {
                'failure_count': 0,
                'opened_at': time.time()
            }
        
        self.circuit_breakers[func_name]['failure_count'] += 1
    
    def _record_success(self, func_name: str):
        """Record a success for circuit breaker"""
        if func_name in self.circuit_breakers:
            del self.circuit_breakers[func_name]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            **self.error_stats,
            'circuit_breakers_active': len(self.circuit_breakers),
            'last_errors': self.last_errors
        }
    
    def reset_statistics(self):
        """Reset error statistics"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'retries_attempted': 0,
            'successful_retries': 0
        }
        self.circuit_breakers.clear()
        self.last_errors.clear()


# Global error handler instance
error_handler = ProductionErrorHandler()
