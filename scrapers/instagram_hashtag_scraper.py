"""
Social Media Surveillance System - Instagram Hashtag Scraper
Comprehensive hashtag analysis and trending detection with performance optimization.
"""

import re
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple
from urllib.parse import urlparse, quote
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, StaleElementReferenceException
)

from core.browser_engine import InstagramBrowser
from core.data_manager import data_manager
from core.config import config
from core.error_handler import error_handler, ScrapingError, RateLimitError
from core.scraper_resilience import ScraperResilience, safe_extract_text, safe_parse_number

logger = logging.getLogger(__name__)

class HashtagScrapingError(Exception):
    """Custom exception for hashtag scraping errors"""
    pass

class InstagramHashtagScraper:
    """
    Comprehensive Instagram hashtag scraper with trending analysis and post collection.
    Provides detailed hashtag metrics and related hashtag discovery.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Hashtag page selectors
        self.selectors = {
            # Hashtag page elements
            'hashtag_header': 'header section',
            'hashtag_title': 'h1',
            'post_count': 'span:contains("posts")',
            'hashtag_description': 'div[data-testid="hashtag-description"]',
            
            # Posts grid
            'posts_grid': 'article div div div a[href*="/p/"]',
            'top_posts': 'div[data-testid="top-posts"] article a',
            'recent_posts': 'div[data-testid="recent-posts"] article a',
            
            # Related hashtags
            'related_hashtags': 'div[data-testid="related-hashtags"] a',
            'suggested_hashtags': 'div[data-testid="suggested-hashtags"] a',
            
            # Navigation elements
            'top_posts_tab': 'div[role="tablist"] div:contains("Top")',
            'recent_posts_tab': 'div[role="tablist"] div:contains("Recent")',
            
            # Load more content
            'load_more': 'button:contains("Show more")',
            'loading_spinner': 'svg[aria-label="Loading..."]',
            
            # Post preview elements
            'post_likes': 'span[aria-label*="likes"]',
            'post_comments': 'span[aria-label*="comments"]',
            'post_video_indicator': 'svg[aria-label="Video"]',
            'post_carousel_indicator': 'svg[aria-label="Carousel"]',
        }
        
        # Performance tracking
        self.scraping_stats = {
            'hashtags_analyzed': 0,
            'posts_collected': 0,
            'related_hashtags_found': 0,
            'errors_encountered': 0,
            'average_analysis_time': 0.0,
            'trending_hashtags_detected': 0
        }
        
        # Caching for performance
        self.hashtag_cache = {}
        self.analyzed_hashtags = set()
    
    @error_handler.with_retry(max_retries=3, exceptions=(ScrapingError, RateLimitError))
    @error_handler.with_circuit_breaker(failure_threshold=5, timeout=300)
    @ScraperResilience.with_rate_limit_handling(delay_between_requests=2.0, max_requests_per_minute=20)
    def analyze_hashtag(self, hashtag: str, max_posts: int = 50,
                       include_related: bool = True) -> Dict[str, Any]:
        """
        Comprehensive hashtag analysis with metrics and post collection.
        
        Args:
            hashtag: Hashtag to analyze (without # symbol)
            max_posts: Maximum number of posts to collect
            include_related: Whether to find related hashtags
            
        Returns:
            Dictionary containing hashtag analysis results
        """
        start_time = time.time()
        results = {
            'hashtag': hashtag,
            'post_count': 0,
            'top_posts': [],
            'recent_posts': [],
            'related_hashtags': [],
            'trending_score': 0.0,
            'analysis_time': 0,
            'status': 'started'
        }
        
        try:
            logger.info(f"Starting hashtag analysis for #{hashtag}")
            
            # Navigate to hashtag page
            if not self._navigate_to_hashtag(hashtag):
                results['status'] = 'navigation_failed'
                return results
            
            # Extract hashtag metrics
            hashtag_metrics = self._extract_hashtag_metrics()
            results.update(hashtag_metrics)
            
            # Collect top posts
            if max_posts > 0:
                results['top_posts'] = self._collect_top_posts(min(max_posts // 2, 25))
                results['recent_posts'] = self._collect_recent_posts(min(max_posts // 2, 25))
            
            # Find related hashtags
            if include_related:
                results['related_hashtags'] = self._find_related_hashtags()
            
            # Calculate trending score
            results['trending_score'] = self._calculate_trending_score(results)
            
            # Save hashtag data
            self._save_hashtag_data(hashtag, results)
            
            # Update statistics
            self.scraping_stats['hashtags_analyzed'] += 1
            self.scraping_stats['posts_collected'] += len(results['top_posts']) + len(results['recent_posts'])
            self.scraping_stats['related_hashtags_found'] += len(results['related_hashtags'])
            
            results['analysis_time'] = time.time() - start_time
            results['status'] = 'completed'
            
            logger.info(f"Hashtag analysis completed for #{hashtag}: "
                       f"{results['post_count']} posts, "
                       f"{len(results['related_hashtags'])} related hashtags, "
                       f"trending score: {results['trending_score']:.2f}")
            
            return results
            
        except Exception as e:
            results['analysis_time'] = time.time() - start_time
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error analyzing hashtag #{hashtag}: {e}")
            return results
    
    def _navigate_to_hashtag(self, hashtag: str) -> bool:
        """Navigate to hashtag page with robust error handling"""
        try:
            if not self.browser.is_logged_in:
                raise ScrapingError("Browser not logged in", retry_after=30)

            # Clean hashtag (remove # if present)
            clean_hashtag = hashtag.lstrip('#')
            hashtag_url = f"https://www.instagram.com/explore/tags/{quote(clean_hashtag)}/"

            # Navigate with error handling
            try:
                self.browser.driver.get(hashtag_url)
            except Exception as e:
                error_info = error_handler.handle_selenium_error(e, f"navigating to {hashtag_url}")
                if error_info.get('retry_recommended'):
                    raise ScrapingError(f"Navigation failed: {e}", retry_after=error_info.get('retry_delay', 5))
                return False

            # Wait for page to load with robust element finding
            main_element = ScraperResilience.robust_element_find(
                self.browser, 'main', timeout=self.wait_timeout, retry_count=3
            )

            if not main_element:
                raise ScrapingError(f"Page failed to load for hashtag #{hashtag}", retry_after=10)

            # Check if hashtag exists
            page_title = safe_extract_text(self.browser.driver.find_element(By.TAG_NAME, 'title'))
            if "Page Not Found" in page_title or "not found" in page_title.lower():
                logger.warning(f"Hashtag #{hashtag} not found")
                return False

            return True

        except ScrapingError:
            raise  # Re-raise scraping errors
        except Exception as e:
            error_info = error_handler.handle_selenium_error(e, f"navigating to hashtag #{hashtag}")
            logger.error(f"Error navigating to hashtag #{hashtag}: {e}")
            return False
    
    def _extract_hashtag_metrics(self) -> Dict[str, Any]:
        """Extract basic hashtag metrics from page with robust error handling"""
        try:
            metrics = {}

            # Extract post count with robust element finding
            post_count_element = ScraperResilience.robust_element_find(
                self.browser, self.selectors['post_count'], timeout=5, retry_count=2
            )

            if post_count_element:
                count_text = safe_extract_text(post_count_element)
                metrics['post_count'] = safe_parse_number(count_text, default=0)
            else:
                metrics['post_count'] = 0

            # Extract hashtag description with fallback
            desc_element = ScraperResilience.robust_element_find(
                self.browser, self.selectors['hashtag_description'], timeout=3, retry_count=1
            )
            metrics['description'] = safe_extract_text(desc_element, default='')

            # Extract hashtag title with fallback
            title_element = ScraperResilience.robust_element_find(
                self.browser, self.selectors['hashtag_title'], timeout=3, retry_count=1
            )
            metrics['display_name'] = safe_extract_text(title_element, default='')

            return metrics

        except Exception as e:
            error_handler.handle_selenium_error(e, "extracting hashtag metrics")
            logger.error(f"Error extracting hashtag metrics: {e}")
            return {'post_count': 0, 'description': '', 'display_name': ''}
    
    def _collect_top_posts(self, max_posts: int) -> List[Dict[str, Any]]:
        """Collect top posts for hashtag"""
        try:
            # Click on top posts tab if available
            top_tab = self._find_element(self.selectors['top_posts_tab'])
            if top_tab:
                top_tab.click()
                time.sleep(2)
            
            return self._collect_posts_from_grid(self.selectors['top_posts'], max_posts, 'top')
            
        except Exception as e:
            logger.error(f"Error collecting top posts: {e}")
            return []
    
    def _collect_recent_posts(self, max_posts: int) -> List[Dict[str, Any]]:
        """Collect recent posts for hashtag"""
        try:
            # Click on recent posts tab if available
            recent_tab = self._find_element(self.selectors['recent_posts_tab'])
            if recent_tab:
                recent_tab.click()
                time.sleep(2)
            
            return self._collect_posts_from_grid(self.selectors['recent_posts'], max_posts, 'recent')
            
        except Exception as e:
            logger.error(f"Error collecting recent posts: {e}")
            return []
    
    def _collect_posts_from_grid(self, grid_selector: str, max_posts: int, post_type: str) -> List[Dict[str, Any]]:
        """Collect posts from a specific grid"""
        posts = []
        processed_urls = set()
        
        try:
            # Use fallback selector if specific one doesn't work
            if not self._element_exists(grid_selector):
                grid_selector = self.selectors['posts_grid']
            
            post_elements = self._find_elements(grid_selector)[:max_posts]
            
            for element in post_elements:
                try:
                    post_data = self._extract_post_preview_data(element, post_type)
                    if post_data and post_data['url'] not in processed_urls:
                        posts.append(post_data)
                        processed_urls.add(post_data['url'])
                        
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    logger.warning(f"Error extracting post preview: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"Error collecting posts from grid: {e}")
            return posts
    
    def _extract_post_preview_data(self, post_element, post_type: str) -> Optional[Dict[str, Any]]:
        """Extract preview data from post element"""
        try:
            # Get post URL
            post_url = post_element.get_attribute('href')
            if not post_url:
                return None
            
            post_data = {
                'url': post_url,
                'post_id': self._extract_post_id_from_url(post_url),
                'type': post_type,
                'scraped_at': datetime.now(timezone.utc)
            }
            
            # Extract engagement metrics from preview
            likes_element = post_element.find_element(By.CSS_SELECTOR, self.selectors['post_likes'])
            if likes_element:
                post_data['likes'] = self._parse_count(likes_element.get_attribute('aria-label'))
            
            comments_element = post_element.find_element(By.CSS_SELECTOR, self.selectors['post_comments'])
            if comments_element:
                post_data['comments'] = self._parse_count(comments_element.get_attribute('aria-label'))
            
            # Determine media type
            if post_element.find_elements(By.CSS_SELECTOR, self.selectors['post_video_indicator']):
                post_data['media_type'] = 'video'
            elif post_element.find_elements(By.CSS_SELECTOR, self.selectors['post_carousel_indicator']):
                post_data['media_type'] = 'carousel'
            else:
                post_data['media_type'] = 'photo'
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting post preview data: {e}")
            return None
    
    def _find_related_hashtags(self) -> List[str]:
        """Find related hashtags"""
        try:
            related_hashtags = []
            
            # Look for related hashtags section
            related_elements = self._find_elements(self.selectors['related_hashtags'])
            for element in related_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/explore/tags/' in href:
                        hashtag = href.split('/explore/tags/')[-1].rstrip('/')
                        if hashtag and hashtag not in related_hashtags:
                            related_hashtags.append(hashtag)
                except StaleElementReferenceException:
                    continue
            
            # Look for suggested hashtags
            suggested_elements = self._find_elements(self.selectors['suggested_hashtags'])
            for element in suggested_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/explore/tags/' in href:
                        hashtag = href.split('/explore/tags/')[-1].rstrip('/')
                        if hashtag and hashtag not in related_hashtags:
                            related_hashtags.append(hashtag)
                except StaleElementReferenceException:
                    continue
            
            return related_hashtags[:20]  # Limit to top 20

        except Exception as e:
            logger.error(f"Error finding related hashtags: {e}")
            return []

    def _calculate_trending_score(self, hashtag_data: Dict[str, Any]) -> float:
        """Calculate trending score based on various metrics"""
        try:
            score = 0.0

            # Base score from post count (normalized)
            post_count = hashtag_data.get('post_count', 0)
            if post_count > 0:
                # Logarithmic scaling for post count
                score += min(50.0, 10 * (post_count / 1000000))  # Max 50 points

            # Engagement score from top posts
            top_posts = hashtag_data.get('top_posts', [])
            if top_posts:
                avg_engagement = sum(
                    (post.get('likes', 0) + post.get('comments', 0) * 5)
                    for post in top_posts
                ) / len(top_posts)
                score += min(30.0, avg_engagement / 10000)  # Max 30 points

            # Related hashtags bonus
            related_count = len(hashtag_data.get('related_hashtags', []))
            score += min(20.0, related_count)  # Max 20 points

            return min(100.0, score)  # Cap at 100

        except Exception as e:
            logger.error(f"Error calculating trending score: {e}")
            return 0.0

    def _parse_count(self, text: str) -> int:
        """Parse count from Instagram text"""
        try:
            if not text:
                return 0

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

        except (ValueError, TypeError):
            logger.warning(f"Could not parse count: {text}")
            return 0

    def _extract_post_id_from_url(self, url: str) -> Optional[str]:
        """Extract Instagram post ID from URL"""
        try:
            match = re.search(r'/p/([A-Za-z0-9_-]+)/', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _find_element(self, selector: str, timeout: int = None) -> Optional[Any]:
        """Find single element with timeout"""
        try:
            timeout = timeout or self.wait_timeout
            return WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            return None
        except Exception:
            return None

    def _find_elements(self, selector: str) -> List:
        """Find multiple elements"""
        try:
            return self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            return []

    def _element_exists(self, selector: str, timeout: int = 2) -> bool:
        """Check if element exists"""
        try:
            WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False
        except Exception:
            return False

    def _save_hashtag_data(self, hashtag: str, hashtag_data: Dict[str, Any]) -> bool:
        """Save hashtag analysis data to database"""
        try:
            # This would integrate with the data manager
            # For now, we'll log the save operation
            logger.info(f"Saving hashtag data for #{hashtag} with {len(hashtag_data)} fields")
            return True
        except Exception as e:
            logger.error(f"Error saving hashtag data: {e}")
            return False

    def get_trending_hashtags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending hashtags based on analysis"""
        try:
            # This would query the database for hashtags with high trending scores
            # For now, return empty list as placeholder
            logger.info(f"Getting top {limit} trending hashtags")
            return []
        except Exception as e:
            logger.error(f"Error getting trending hashtags: {e}")
            return []

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get scraping performance statistics"""
        return {
            'hashtags_analyzed': self.scraping_stats['hashtags_analyzed'],
            'posts_collected': self.scraping_stats['posts_collected'],
            'related_hashtags_found': self.scraping_stats['related_hashtags_found'],
            'errors_encountered': self.scraping_stats['errors_encountered'],
            'average_analysis_time': self.scraping_stats['average_analysis_time'],
            'trending_hashtags_detected': self.scraping_stats['trending_hashtags_detected'],
            'success_rate': (
                (self.scraping_stats['hashtags_analyzed'] - self.scraping_stats['errors_encountered']) /
                max(1, self.scraping_stats['hashtags_analyzed'])
            ) * 100
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on scraper"""
        try:
            return {
                'status': 'healthy',
                'browser_connected': self.browser.driver is not None,
                'last_analysis': datetime.now(timezone.utc).isoformat(),
                'cache_size': len(self.hashtag_cache),
                'analyzed_hashtags': len(self.analyzed_hashtags)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'browser_connected': False
            }

    def close(self):
        """Clean up resources"""
        try:
            if self.browser:
                self.browser.close()
        except Exception as e:
            logger.error(f"Error closing hashtag scraper: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Context manager for hashtag scraper
def create_hashtag_scraper(browser: Optional[InstagramBrowser] = None) -> InstagramHashtagScraper:
    """Create hashtag scraper with context management"""
    return InstagramHashtagScraper(browser)


# Convenience functions
def analyze_hashtag_quick(hashtag: str, max_posts: int = 30,
                         browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to quickly analyze a hashtag"""
    with create_hashtag_scraper(browser) as scraper:
        return scraper.analyze_hashtag(hashtag, max_posts)


def get_trending_hashtags_quick(limit: int = 20,
                               browser: Optional[InstagramBrowser] = None) -> List[Dict[str, Any]]:
    """Convenience function to get trending hashtags"""
    with create_hashtag_scraper(browser) as scraper:
        return scraper.get_trending_hashtags(limit)
