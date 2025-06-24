# Production Error Handling Guide

This guide explains how to implement production-ready error handling across all scraper components in the Social Media Surveillance System.

## Overview

The error handling system provides:
- **Retry Logic**: Automatic retry with exponential backoff
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Rate Limiting**: Protects against Instagram rate limits
- **Graceful Degradation**: Fallback strategies when primary methods fail
- **Comprehensive Logging**: Detailed error tracking and statistics

## Core Components

### 1. Error Handler (`core/error_handler.py`)

The central error handling system with decorators for:
- `@error_handler.with_retry()` - Retry logic with exponential backoff
- `@error_handler.with_circuit_breaker()` - Circuit breaker pattern
- Error categorization and severity levels
- Comprehensive error statistics

### 2. Scraper Resilience (`core/scraper_resilience.py`)

Utility functions and decorators for:
- `@ScraperResilience.with_rate_limit_handling()` - Rate limiting
- `@ScraperResilience.with_browser_recovery()` - Browser session recovery
- `ScraperResilience.robust_element_find()` - Robust element finding
- `ScraperResilience.robust_click()` - Robust element clicking

### 3. Safe Utility Functions

Helper functions for safe data extraction:
- `safe_extract_text()` - Safe text extraction from elements
- `safe_extract_attribute()` - Safe attribute extraction
- `safe_parse_number()` - Safe number parsing with K/M/B support

## Implementation Examples

### Basic Method Enhancement

```python
from core.error_handler import error_handler, ScrapingError
from core.scraper_resilience import ScraperResilience, safe_extract_text

class MyInstagramScraper:
    @error_handler.with_retry(max_retries=3)
    @error_handler.with_circuit_breaker()
    @ScraperResilience.with_rate_limit_handling(delay_between_requests=2.0)
    def scrape_data(self, target: str) -> Dict[str, Any]:
        # Your scraping logic here
        pass
```

### Robust Element Finding

```python
# Instead of:
element = self.browser.driver.find_element(By.CSS_SELECTOR, selector)

# Use:
element = ScraperResilience.robust_element_find(
    self.browser, selector, timeout=10, retry_count=3
)
```

### Safe Data Extraction

```python
# Instead of:
text = element.text.strip()
count = int(element.text.replace(',', ''))

# Use:
text = safe_extract_text(element, default="")
count = safe_parse_number(element.text, default=0)
```

### Error Handling in Navigation

```python
def _navigate_to_page(self, url: str) -> bool:
    try:
        self.browser.driver.get(url)
        
        # Wait for page load with robust element finding
        main_element = ScraperResilience.robust_element_find(
            self.browser, 'main', timeout=self.wait_timeout, retry_count=3
        )
        
        if not main_element:
            raise ScrapingError("Page failed to load", retry_after=10)
        
        return True
        
    except ScrapingError:
        raise  # Re-raise scraping errors for retry logic
    except Exception as e:
        error_info = error_handler.handle_selenium_error(e, "page navigation")
        logger.error(f"Navigation error: {e}")
        return False
```

## Error Categories and Handling

### Network Errors
- **Symptoms**: Connection timeouts, DNS failures
- **Handling**: Automatic retry with exponential backoff
- **Recovery**: Wait and retry, check network connectivity

### Selenium Errors
- **TimeoutException**: Increase timeout, retry with longer wait
- **NoSuchElementException**: Graceful continue, element may not exist
- **StaleElementReferenceException**: Refind element and retry
- **ElementClickInterceptedException**: Scroll to element, use JavaScript click

### Instagram-Specific Errors
- **Rate Limiting (429)**: Wait 5+ minutes before retry
- **Not Found (404)**: Skip and continue, content doesn't exist
- **Forbidden (403)**: Check account status, may need re-authentication
- **Login Required**: Re-authenticate and retry

### Browser Session Errors
- **InvalidSessionIdException**: Reinitialize browser session
- **WebDriverException**: Check browser status and restart

## Best Practices

### 1. Layer Error Handling

Apply multiple layers of protection:
```python
@error_handler.with_retry(max_retries=3)
@error_handler.with_circuit_breaker()
@ScraperResilience.with_rate_limit_handling()
@ScraperResilience.with_browser_recovery()
def scrape_method(self):
    # Implementation
    pass
```

### 2. Use Graceful Degradation

Provide fallback strategies:
```python
def get_follower_count(self, username: str) -> int:
    # Primary method
    def primary():
        return self._extract_follower_count_from_profile()
    
    # Fallback method
    def fallback():
        return self._estimate_follower_count_from_posts()
    
    return error_handler.graceful_degradation(
        primary_func=primary,
        fallback_func=fallback,
        fallback_value=0
    )
```

### 3. Monitor Error Statistics

Regularly check error statistics:
```python
stats = error_handler.get_error_statistics()
print(f"Total errors: {stats['total_errors']}")
print(f"Success rate: {100 - (stats['total_errors'] / total_operations * 100):.2f}%")
```

### 4. Handle Rate Limits Proactively

Implement rate limiting before hitting Instagram limits:
```python
@ScraperResilience.with_rate_limit_handling(
    delay_between_requests=2.0,
    max_requests_per_minute=20
)
def scrape_posts(self):
    # Implementation
    pass
```

## Configuration

### Error Handler Settings

```python
# In core/error_handler.py
error_handler.max_retries = 3
error_handler.base_delay = 1.0
error_handler.max_delay = 60.0
error_handler.circuit_breaker_threshold = 5
error_handler.circuit_breaker_timeout = 300
```

### Rate Limiting Settings

```python
# Adjust based on your needs
delay_between_requests = 2.0  # seconds
max_requests_per_minute = 20  # requests
```

## Testing Error Handling

### Unit Tests

Test error scenarios:
```python
def test_error_handling():
    scraper = MyInstagramScraper()
    
    # Test with invalid input
    result = scraper.scrape_data("invalid_username")
    assert result is None or result.get('status') == 'error'
    
    # Test retry logic
    with mock.patch.object(scraper, '_internal_method', side_effect=TimeoutException):
        result = scraper.scrape_data("test_username")
        # Should have retried and eventually failed gracefully
```

### Integration Tests

Test complete error handling flow:
```python
def test_complete_error_flow():
    # Test network errors
    # Test rate limiting
    # Test browser recovery
    # Test graceful degradation
```

## Monitoring and Alerting

### Error Statistics Dashboard

Monitor key metrics:
- Total error count
- Error rate by category
- Circuit breaker status
- Retry success rate
- Average response times

### Alerting Thresholds

Set up alerts for:
- Error rate > 10%
- Circuit breakers open > 5 minutes
- Rate limit errors > 5 per hour
- Browser session failures > 3 per hour

## Deployment Considerations

### Production Settings

- Enable comprehensive logging
- Set conservative rate limits
- Monitor error statistics
- Implement health checks
- Set up automated recovery

### Scaling Considerations

- Distribute load across multiple browser instances
- Implement request queuing for rate limiting
- Use connection pooling for database operations
- Monitor resource usage and scale accordingly

## Troubleshooting

### Common Issues

1. **High Error Rates**: Check Instagram rate limits, verify selectors
2. **Circuit Breakers Opening**: Investigate root cause, adjust thresholds
3. **Browser Crashes**: Monitor memory usage, restart browser sessions
4. **Rate Limiting**: Reduce request frequency, implement better delays

### Debug Mode

Enable debug logging for detailed error information:
```python
import logging
logging.getLogger('core.error_handler').setLevel(logging.DEBUG)
logging.getLogger('core.scraper_resilience').setLevel(logging.DEBUG)
```

This comprehensive error handling system ensures robust, production-ready scraping operations that can handle the various challenges of web scraping at scale.
