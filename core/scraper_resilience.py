"""
Social Media Surveillance System - Scraper Resilience
Production-ready resilience patterns for all scraper components.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable, List
from functools import wraps

from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException, ElementClickInterceptedException
)

from .error_handler import error_handler, ScrapingError, NetworkError, RateLimitError

logger = logging.getLogger(__name__)

class ScraperResilience:
    """
    Resilience patterns and utilities for scraper components.
    Provides decorators and utilities for robust scraping operations.
    """
    
    @staticmethod
    def robust_element_find(browser, selector: str, timeout: int = 10, 
                           retry_count: int = 3) -> Optional[Any]:
        """
        Robustly find an element with retry logic and error handling.
        
        Args:
            browser: Browser instance
            selector: CSS selector
            timeout: Timeout for each attempt
            retry_count: Number of retry attempts
            
        Returns:
            Element if found, None otherwise
        """
        for attempt in range(retry_count):
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                element = WebDriverWait(browser.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return element
                
            except TimeoutException:
                if attempt == retry_count - 1:
                    logger.warning(f"Element not found after {retry_count} attempts: {selector}")
                    return None
                
                logger.debug(f"Element find attempt {attempt + 1} failed, retrying...")
                time.sleep(1)
                
            except Exception as e:
                error_info = error_handler.handle_selenium_error(e, f"finding element: {selector}")
                
                if not error_info.get('retry_recommended', False):
                    return None
                
                if attempt < retry_count - 1:
                    time.sleep(error_info.get('retry_delay', 1))
                else:
                    return None
        
        return None
    
    @staticmethod
    def robust_click(element, browser=None, use_javascript: bool = False, 
                    retry_count: int = 3) -> bool:
        """
        Robustly click an element with fallback strategies.
        
        Args:
            element: Element to click
            browser: Browser instance for JavaScript fallback
            use_javascript: Whether to use JavaScript click
            retry_count: Number of retry attempts
            
        Returns:
            True if click succeeded, False otherwise
        """
        for attempt in range(retry_count):
            try:
                if use_javascript and browser:
                    browser.driver.execute_script("arguments[0].click();", element)
                else:
                    element.click()
                return True
                
            except ElementClickInterceptedException:
                if browser:
                    # Try scrolling to element
                    try:
                        browser.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            element
                        )
                        time.sleep(1)
                        
                        # Try JavaScript click as fallback
                        browser.driver.execute_script("arguments[0].click();", element)
                        return True
                        
                    except Exception as e:
                        logger.warning(f"Click fallback failed: {e}")
                
            except StaleElementReferenceException:
                logger.warning("Element became stale, cannot retry click")
                return False
                
            except Exception as e:
                error_info = error_handler.handle_selenium_error(e, "clicking element")
                
                if not error_info.get('retry_recommended', False):
                    return False
                
                if attempt < retry_count - 1:
                    time.sleep(error_info.get('retry_delay', 1))
        
        return False
    
    @staticmethod
    def robust_scroll(browser, scrolls: int = 3, delay: float = 2.0) -> bool:
        """
        Robustly scroll page with error handling.
        
        Args:
            browser: Browser instance
            scrolls: Number of scroll operations
            delay: Delay between scrolls
            
        Returns:
            True if scrolling succeeded, False otherwise
        """
        try:
            for i in range(scrolls):
                # Get current scroll position
                current_position = browser.driver.execute_script("return window.pageYOffset;")
                
                # Scroll down
                browser.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                
                # Wait for content to load
                time.sleep(delay)
                
                # Check if we actually scrolled
                new_position = browser.driver.execute_script("return window.pageYOffset;")
                if new_position == current_position:
                    logger.debug(f"Reached end of page at scroll {i + 1}")
                    break
            
            return True
            
        except Exception as e:
            error_handler.handle_selenium_error(e, "scrolling page")
            return False
    
    @staticmethod
    def with_rate_limit_handling(delay_between_requests: float = 1.0, 
                                max_requests_per_minute: int = 30):
        """
        Decorator to add rate limiting to scraping functions.
        
        Args:
            delay_between_requests: Minimum delay between requests
            max_requests_per_minute: Maximum requests per minute
        """
        def decorator(func: Callable):
            last_request_time = [0]  # Use list to make it mutable
            request_times = []
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                
                # Clean old request times (older than 1 minute)
                request_times[:] = [t for t in request_times if current_time - t < 60]
                
                # Check rate limit
                if len(request_times) >= max_requests_per_minute:
                    sleep_time = 60 - (current_time - request_times[0])
                    if sleep_time > 0:
                        logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f}s")
                        time.sleep(sleep_time)
                
                # Ensure minimum delay between requests
                time_since_last = current_time - last_request_time[0]
                if time_since_last < delay_between_requests:
                    sleep_time = delay_between_requests - time_since_last
                    time.sleep(sleep_time)
                
                # Record request time
                request_times.append(time.time())
                last_request_time[0] = time.time()
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Check if it's a rate limit error
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        raise RateLimitError("Rate limit detected")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def with_browser_recovery(browser_factory: Callable = None):
        """
        Decorator to add browser recovery capabilities.
        
        Args:
            browser_factory: Function to create new browser instance
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    error_info = error_handler.handle_selenium_error(e, func.__name__)
                    
                    # Check if browser recovery is needed
                    if error_info.get('suggested_action') == 'reinitialize_browser_session':
                        logger.warning("Browser session lost, attempting recovery...")
                        
                        try:
                            # Close current browser
                            if hasattr(self, 'browser') and self.browser:
                                self.browser.close()
                            
                            # Create new browser instance
                            if browser_factory:
                                self.browser = browser_factory()
                            elif hasattr(self, 'browser'):
                                from core.browser_engine import InstagramBrowser
                                self.browser = InstagramBrowser()
                            
                            # Retry the operation
                            logger.info("Browser recovered, retrying operation...")
                            return func(self, *args, **kwargs)
                            
                        except Exception as recovery_error:
                            logger.error(f"Browser recovery failed: {recovery_error}")
                            raise ScrapingError(
                                f"Browser recovery failed: {recovery_error}",
                                retry_after=60
                            )
                    
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def with_data_validation(validator: Callable[[Any], bool], 
                           fallback_value: Any = None):
        """
        Decorator to add data validation to scraping functions.
        
        Args:
            validator: Function to validate the returned data
            fallback_value: Value to return if validation fails
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    
                    if validator(result):
                        return result
                    else:
                        logger.warning(f"Data validation failed for {func.__name__}")
                        return fallback_value
                        
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed: {e}")
                    return fallback_value
            
            return wrapper
        return decorator
    
    @staticmethod
    def create_resilient_scraper_method(original_method: Callable, 
                                      max_retries: int = 3,
                                      rate_limit_delay: float = 1.0,
                                      enable_circuit_breaker: bool = True) -> Callable:
        """
        Create a resilient version of a scraper method with all protection patterns.
        
        Args:
            original_method: Original scraper method
            max_retries: Maximum retry attempts
            rate_limit_delay: Delay for rate limiting
            enable_circuit_breaker: Whether to enable circuit breaker
            
        Returns:
            Enhanced method with resilience patterns
        """
        # Apply decorators in order
        enhanced_method = original_method
        
        # Add retry logic
        enhanced_method = error_handler.with_retry(
            max_retries=max_retries,
            exceptions=(Exception,)
        )(enhanced_method)
        
        # Add rate limiting
        enhanced_method = ScraperResilience.with_rate_limit_handling(
            delay_between_requests=rate_limit_delay
        )(enhanced_method)
        
        # Add circuit breaker if enabled
        if enable_circuit_breaker:
            enhanced_method = error_handler.with_circuit_breaker()(enhanced_method)
        
        return enhanced_method


# Utility functions for common scraping patterns
def safe_extract_text(element, default: str = "") -> str:
    """Safely extract text from an element"""
    try:
        return element.text.strip() if element else default
    except Exception:
        return default

def safe_extract_attribute(element, attribute: str, default: str = "") -> str:
    """Safely extract attribute from an element"""
    try:
        return element.get_attribute(attribute) if element else default
    except Exception:
        return default

def safe_parse_number(text: str, default: int = 0) -> int:
    """Safely parse number from text"""
    try:
        import re
        # Extract numbers and multipliers
        clean_text = re.sub(r'[^\d.,KMB]', '', text.upper())
        
        if 'K' in clean_text:
            number = float(clean_text.replace('K', '').replace(',', ''))
            return int(number * 1000)
        elif 'M' in clean_text:
            number = float(clean_text.replace('M', '').replace(',', ''))
            return int(number * 1000000)
        elif 'B' in clean_text:
            number = float(clean_text.replace('B', '').replace(',', ''))
            return int(number * 1000000000)
        else:
            return int(clean_text.replace(',', ''))
    except Exception:
        return default

def create_fallback_chain(*functions) -> Callable:
    """Create a chain of fallback functions"""
    def fallback_chain(*args, **kwargs):
        for func in functions:
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"Fallback function {func.__name__} failed: {e}")
                continue
        return None
    
    return fallback_chain
