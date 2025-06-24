"""
Social Media Surveillance System - Instagram Profile Scraper
Comprehensive profile information extraction with change detection and anti-detection measures.
"""

import re
import time
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, StaleElementReferenceException
)

from core.browser_engine import InstagramBrowser
from core.data_manager import data_manager
from core.config import config

logger = logging.getLogger(__name__)

class ProfileExtractionError(Exception):
    """Custom exception for profile extraction errors"""
    pass

class InstagramProfileScraper:
    """
    Comprehensive Instagram profile scraper with stealth capabilities and change detection.
    Handles both private and public accounts with intelligent error recovery.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Profile selectors (may need updates as Instagram changes)
        self.selectors = {
            # Profile header elements
            'profile_header': 'header section',
            'profile_image': 'img[data-testid="user-avatar"]',
            'username': 'h2',
            'display_name': 'section h1',
            'verified_badge': 'svg[aria-label="Verified"]',
            'bio': 'section div span',
            'external_link': 'a[href*="l.instagram.com"]',
            
            # Stats elements
            'posts_count': 'a[href*="/p/"] span',
            'followers_count': 'a[href*="/followers/"] span',
            'following_count': 'a[href*="/following/"] span',
            
            # Account status elements
            'private_account': '[data-testid="private-account-icon"]',
            'blocked_message': 'span:contains("User not found")',
            'suspended_message': 'span:contains("Sorry, this page")',
            
            # Posts grid
            'posts_grid': 'article div div div a',
            'no_posts_message': 'span:contains("No posts yet")',
            
            # Story highlights
            'story_highlights': '[data-testid="highlights-tray"] button',
            
            # Additional profile elements
            'category': 'div[data-testid="user-category"]',
            'contact_button': 'button:contains("Contact")',
            'message_button': 'button:contains("Message")',
            'follow_button': 'button:contains("Follow")',
            'following_button': 'button:contains("Following")',
        }
        
        # Performance tracking
        self.extraction_stats = {
            'profiles_scraped': 0,
            'errors_encountered': 0,
            'changes_detected': 0,
            'average_extraction_time': 0.0
        }
    
    def scrape_profile(self, username: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Scrape comprehensive profile information for a given username.
        
        Args:
            username: Instagram username to scrape
            force_refresh: Force re-scraping even if recently updated
            
        Returns:
            Dictionary containing profile data or None if failed
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting profile scrape for: {username}")
            
            # Check if we need to scrape (rate limiting)
            if not force_refresh and not self._should_scrape_profile(username):
                logger.info(f"Skipping {username} - recently scraped")
                return None
            
            # Navigate to profile
            if not self._navigate_to_profile(username):
                return None
            
            # Wait for profile to load
            self._wait_for_profile_load()
            
            # Extract profile data
            profile_data = self._extract_profile_data(username)
            
            if profile_data:
                # Save to database and detect changes
                self._save_profile_data(username, profile_data)
                
                # Update stats
                self.extraction_stats['profiles_scraped'] += 1
                extraction_time = time.time() - start_time
                self._update_average_time(extraction_time)
                
                logger.info(f"Successfully scraped profile: {username} in {extraction_time:.2f}s")
                return profile_data
            else:
                self.extraction_stats['errors_encountered'] += 1
                return None
                
        except Exception as e:
            self.extraction_stats['errors_encountered'] += 1
            logger.error(f"Error scraping profile {username}: {e}")
            return None
    
    def _should_scrape_profile(self, username: str) -> bool:
        """Check if profile should be scraped based on last update time"""
        try:
            target = data_manager.get_surveillance_target(username)
            if not target:
                return True  # New target, should scrape
            
            # Check last update time
            if target.last_updated:
                time_since_update = datetime.now(timezone.utc) - target.last_updated
                # Scrape if more than 1 hour since last update
                return time_since_update.total_seconds() > 3600
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking scrape necessity for {username}: {e}")
            return True  # Default to scraping on error
    
    def _navigate_to_profile(self, username: str) -> bool:
        """Navigate to Instagram profile with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                if not self.browser.is_logged_in:
                    logger.error("Browser not logged in")
                    return False
                
                success = self.browser.navigate_to_profile(username)
                if success:
                    return True
                
                # Wait before retry
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed for {username}: {e}")
                if attempt == self.retry_attempts - 1:
                    logger.error(f"All navigation attempts failed for {username}")
                    return False
                
                time.sleep(2 ** attempt)
        
        return False
    
    def _wait_for_profile_load(self):
        """Wait for profile page to fully load"""
        try:
            # Wait for main profile header
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['profile_header']))
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
            
        except TimeoutException:
            logger.warning("Profile header not found within timeout")
            raise ProfileExtractionError("Profile page failed to load")
    
    def _extract_profile_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Extract comprehensive profile data from the current page"""
        try:
            profile_data = {
                'instagram_username': username,
                'scraped_at': datetime.now(timezone.utc),
                'is_private': False,
                'is_verified': False,
                'status': 'active'
            }
            
            # Check account status first
            account_status = self._check_account_status()
            profile_data['status'] = account_status
            
            if account_status in ['suspended', 'blocked', 'not_found']:
                logger.warning(f"Account {username} status: {account_status}")
                return profile_data
            
            # Extract basic profile information
            self._extract_basic_info(profile_data)
            
            # Extract statistics
            self._extract_statistics(profile_data)
            
            # Extract bio and links
            self._extract_bio_and_links(profile_data)
            
            # Extract additional metadata
            self._extract_additional_metadata(profile_data)
            
            # Check if account is private
            profile_data['is_private'] = self._is_private_account()
            
            # If public, extract more detailed information
            if not profile_data['is_private']:
                self._extract_public_account_details(profile_data)
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
            return None
    
    def _check_account_status(self) -> str:
        """Check if account is suspended, blocked, or not found"""
        try:
            # Check for "User not found" message
            if self._element_exists(self.selectors['blocked_message']):
                return 'not_found'
            
            # Check for "Sorry, this page isn't available" message
            if self._element_exists(self.selectors['suspended_message']):
                return 'suspended'
            
            # Check current URL for indicators
            current_url = self.browser.driver.current_url
            if 'accounts/login' in current_url:
                return 'blocked'
            
            return 'active'
            
        except Exception as e:
            logger.error(f"Error checking account status: {e}")
            return 'unknown'
    
    def _extract_basic_info(self, profile_data: Dict[str, Any]):
        """Extract basic profile information (name, username, verification)"""
        try:
            # Extract display name
            display_name_element = self._find_element(self.selectors['display_name'])
            if display_name_element:
                profile_data['display_name'] = display_name_element.text.strip()
            
            # Check verification status
            profile_data['is_verified'] = self._element_exists(self.selectors['verified_badge'])
            
            # Extract profile image URL
            profile_img_element = self._find_element(self.selectors['profile_image'])
            if profile_img_element:
                profile_data['profile_pic_url'] = profile_img_element.get_attribute('src')
            
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
    
    def _extract_statistics(self, profile_data: Dict[str, Any]):
        """Extract follower, following, and post counts"""
        try:
            # Extract posts count
            posts_element = self._find_element(self.selectors['posts_count'])
            if posts_element:
                profile_data['post_count'] = self._parse_count(posts_element.text)
            
            # Extract followers count
            followers_element = self._find_element(self.selectors['followers_count'])
            if followers_element:
                profile_data['follower_count'] = self._parse_count(followers_element.text)
            
            # Extract following count
            following_element = self._find_element(self.selectors['following_count'])
            if following_element:
                profile_data['following_count'] = self._parse_count(following_element.text)
            
        except Exception as e:
            logger.error(f"Error extracting statistics: {e}")
    
    def _extract_bio_and_links(self, profile_data: Dict[str, Any]):
        """Extract bio text and external links"""
        try:
            # Extract bio
            bio_element = self._find_element(self.selectors['bio'])
            if bio_element:
                profile_data['bio'] = bio_element.text.strip()
            
            # Extract external link
            link_element = self._find_element(self.selectors['external_link'])
            if link_element:
                profile_data['external_url'] = link_element.get_attribute('href')
            
        except Exception as e:
            logger.error(f"Error extracting bio and links: {e}")
    
    def _extract_additional_metadata(self, profile_data: Dict[str, Any]):
        """Extract additional profile metadata"""
        try:
            # Extract category if available
            category_element = self._find_element(self.selectors['category'])
            if category_element:
                profile_data['category'] = category_element.text.strip()
            
            # Check for business account indicators
            profile_data['is_business'] = (
                self._element_exists(self.selectors['contact_button']) or
                self._element_exists('[data-testid="business-category"]')
            )
            
        except Exception as e:
            logger.error(f"Error extracting additional metadata: {e}")
    
    def _is_private_account(self) -> bool:
        """Check if the account is private"""
        try:
            return self._element_exists(self.selectors['private_account'])
        except Exception:
            return False
    
    def _extract_public_account_details(self, profile_data: Dict[str, Any]):
        """Extract additional details available for public accounts"""
        try:
            # Count story highlights
            highlights = self._find_elements(self.selectors['story_highlights'])
            profile_data['highlights_count'] = len(highlights) if highlights else 0
            
            # Check if account has posts
            profile_data['has_posts'] = not self._element_exists(self.selectors['no_posts_message'])
            
        except Exception as e:
            logger.error(f"Error extracting public account details: {e}")

    def _parse_count(self, count_text: str) -> int:
        """Parse Instagram count text (e.g., '1.2K', '1M') to integer"""
        try:
            if not count_text:
                return 0

            # Remove commas and spaces
            count_text = count_text.replace(',', '').replace(' ', '').upper()

            # Handle K (thousands)
            if 'K' in count_text:
                number = float(count_text.replace('K', ''))
                return int(number * 1000)

            # Handle M (millions)
            if 'M' in count_text:
                number = float(count_text.replace('M', ''))
                return int(number * 1000000)

            # Handle B (billions)
            if 'B' in count_text:
                number = float(count_text.replace('B', ''))
                return int(number * 1000000000)

            # Regular number
            return int(count_text)

        except (ValueError, TypeError):
            logger.warning(f"Could not parse count: {count_text}")
            return 0

    def _find_element(self, selector: str, timeout: int = 5):
        """Find element with timeout and error handling"""
        try:
            return WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            return None
        except Exception as e:
            logger.debug(f"Error finding element {selector}: {e}")
            return None

    def _find_elements(self, selector: str):
        """Find multiple elements with error handling"""
        try:
            return self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.debug(f"Error finding elements {selector}: {e}")
            return []

    def _element_exists(self, selector: str, timeout: int = 2) -> bool:
        """Check if element exists without raising exceptions"""
        try:
            WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False
        except Exception:
            return False

    def _save_profile_data(self, username: str, profile_data: Dict[str, Any]):
        """Save profile data to database and detect changes"""
        try:
            # Get existing target data
            existing_target = data_manager.get_surveillance_target(username)

            if existing_target:
                # Update existing target and detect changes
                self._detect_and_log_changes(existing_target, profile_data)

                # Update the target
                update_data = {k: v for k, v in profile_data.items()
                              if k not in ['instagram_username', 'scraped_at']}

                success = data_manager.update_surveillance_target(
                    existing_target.id, **update_data
                )

                if success:
                    logger.info(f"Updated profile data for {username}")
                else:
                    logger.error(f"Failed to update profile data for {username}")
            else:
                # Create new target
                target = data_manager.add_surveillance_target(username, **profile_data)
                if target:
                    logger.info(f"Created new surveillance target: {username}")
                else:
                    logger.error(f"Failed to create surveillance target: {username}")

        except Exception as e:
            logger.error(f"Error saving profile data for {username}: {e}")

    def _detect_and_log_changes(self, existing_target, new_data: Dict[str, Any]):
        """Detect and log changes in profile data"""
        try:
            changes_detected = []

            # Fields to monitor for changes
            monitored_fields = [
                'display_name', 'bio', 'follower_count', 'following_count',
                'post_count', 'is_verified', 'is_private', 'profile_pic_url',
                'external_url', 'status'
            ]

            for field in monitored_fields:
                old_value = getattr(existing_target, field, None)
                new_value = new_data.get(field)

                if old_value != new_value and new_value is not None:
                    changes_detected.append({
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value
                    })

            # Log significant changes
            for change in changes_detected:
                self._log_profile_change(existing_target.id, change)
                self.extraction_stats['changes_detected'] += 1

            if changes_detected:
                logger.info(f"Detected {len(changes_detected)} changes for {existing_target.instagram_username}")

        except Exception as e:
            logger.error(f"Error detecting changes: {e}")

    def _log_profile_change(self, target_id: int, change: Dict[str, Any]):
        """Log a specific profile change"""
        try:
            change_type = f"{change['field']}_changed"

            # Use version manager to track the change
            from core.database import version_manager
            version_manager.track_change(
                target_id=target_id,
                change_type=change_type,
                old_value=change['old_value'],
                new_value=change['new_value']
            )

        except Exception as e:
            logger.error(f"Error logging profile change: {e}")

    def _update_average_time(self, extraction_time: float):
        """Update average extraction time statistics"""
        try:
            current_avg = self.extraction_stats['average_extraction_time']
            profiles_count = self.extraction_stats['profiles_scraped']

            if profiles_count == 1:
                self.extraction_stats['average_extraction_time'] = extraction_time
            else:
                # Calculate running average
                new_avg = ((current_avg * (profiles_count - 1)) + extraction_time) / profiles_count
                self.extraction_stats['average_extraction_time'] = new_avg

        except Exception as e:
            logger.error(f"Error updating average time: {e}")

    def scrape_multiple_profiles(self, usernames: List[str],
                                delay_range: Tuple[int, int] = (5, 15)) -> Dict[str, Any]:
        """
        Scrape multiple profiles with intelligent delays and error handling.

        Args:
            usernames: List of usernames to scrape
            delay_range: Range for random delays between scrapes

        Returns:
            Dictionary with scraping results and statistics
        """
        results = {
            'successful': [],
            'failed': [],
            'total_time': 0,
            'start_time': datetime.now(timezone.utc)
        }

        start_time = time.time()

        try:
            logger.info(f"Starting batch scrape of {len(usernames)} profiles")

            for i, username in enumerate(usernames):
                try:
                    # Scrape profile
                    profile_data = self.scrape_profile(username)

                    if profile_data:
                        results['successful'].append(username)
                    else:
                        results['failed'].append(username)

                    # Add delay between scrapes (except for last one)
                    if i < len(usernames) - 1:
                        delay = self._calculate_intelligent_delay(delay_range)
                        logger.debug(f"Waiting {delay}s before next scrape")
                        time.sleep(delay)

                except Exception as e:
                    logger.error(f"Error in batch scrape for {username}: {e}")
                    results['failed'].append(username)

            results['total_time'] = time.time() - start_time
            results['end_time'] = datetime.now(timezone.utc)

            logger.info(f"Batch scrape completed: {len(results['successful'])} successful, "
                       f"{len(results['failed'])} failed in {results['total_time']:.2f}s")

            return results

        except Exception as e:
            logger.error(f"Error in batch profile scraping: {e}")
            results['total_time'] = time.time() - start_time
            return results

    def _calculate_intelligent_delay(self, delay_range: Tuple[int, int]) -> float:
        """Calculate intelligent delay based on current performance and detection risk"""
        import random

        min_delay, max_delay = delay_range

        # Base delay
        base_delay = random.uniform(min_delay, max_delay)

        # Adjust based on error rate
        error_rate = (self.extraction_stats['errors_encountered'] /
                     max(self.extraction_stats['profiles_scraped'], 1))

        if error_rate > 0.1:  # High error rate, increase delay
            base_delay *= 1.5

        # Add some randomness to avoid patterns
        jitter = random.uniform(-0.5, 0.5)

        return max(1.0, base_delay + jitter)  # Minimum 1 second delay

    def get_profile_summary(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a quick profile summary without full scraping"""
        try:
            target = data_manager.get_surveillance_target(username)
            if not target:
                return None

            return {
                'username': target.instagram_username,
                'display_name': target.display_name,
                'follower_count': target.follower_count,
                'following_count': target.following_count,
                'post_count': target.post_count,
                'is_verified': target.is_verified,
                'is_private': target.is_private,
                'status': target.status,
                'last_updated': target.last_updated,
                'engagement_rate': target.engagement_rate
            }

        except Exception as e:
            logger.error(f"Error getting profile summary for {username}: {e}")
            return None

    def validate_profile_data(self, profile_data: Dict[str, Any]) -> bool:
        """Validate extracted profile data for completeness and accuracy"""
        try:
            required_fields = ['instagram_username', 'status']

            # Check required fields
            for field in required_fields:
                if field not in profile_data:
                    logger.warning(f"Missing required field: {field}")
                    return False

            # Validate numeric fields
            numeric_fields = ['follower_count', 'following_count', 'post_count']
            for field in numeric_fields:
                if field in profile_data:
                    value = profile_data[field]
                    if value is not None and (not isinstance(value, int) or value < 0):
                        logger.warning(f"Invalid numeric value for {field}: {value}")
                        return False

            # Validate boolean fields
            boolean_fields = ['is_verified', 'is_private']
            for field in boolean_fields:
                if field in profile_data:
                    value = profile_data[field]
                    if value is not None and not isinstance(value, bool):
                        logger.warning(f"Invalid boolean value for {field}: {value}")
                        return False

            return True

        except Exception as e:
            logger.error(f"Error validating profile data: {e}")
            return False

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics"""
        try:
            stats = self.extraction_stats.copy()

            # Calculate success rate
            total_attempts = stats['profiles_scraped'] + stats['errors_encountered']
            if total_attempts > 0:
                stats['success_rate'] = (stats['profiles_scraped'] / total_attempts) * 100
            else:
                stats['success_rate'] = 0.0

            # Add performance metrics
            stats['performance_rating'] = self._calculate_performance_rating()

            return stats

        except Exception as e:
            logger.error(f"Error getting scraping statistics: {e}")
            return {}

    def _calculate_performance_rating(self) -> str:
        """Calculate performance rating based on speed and success rate"""
        try:
            avg_time = self.extraction_stats['average_extraction_time']
            total_attempts = (self.extraction_stats['profiles_scraped'] +
                            self.extraction_stats['errors_encountered'])

            if total_attempts == 0:
                return 'No data'

            success_rate = (self.extraction_stats['profiles_scraped'] / total_attempts) * 100

            # Performance criteria
            if avg_time <= 15 and success_rate >= 95:
                return 'Excellent'
            elif avg_time <= 25 and success_rate >= 90:
                return 'Good'
            elif avg_time <= 35 and success_rate >= 80:
                return 'Fair'
            else:
                return 'Poor'

        except Exception:
            return 'Unknown'

    def reset_statistics(self):
        """Reset scraping statistics"""
        self.extraction_stats = {
            'profiles_scraped': 0,
            'errors_encountered': 0,
            'changes_detected': 0,
            'average_extraction_time': 0.0
        }
        logger.info("Scraping statistics reset")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the scraper"""
        health_status = {
            'status': 'healthy',
            'issues': [],
            'browser_status': 'unknown',
            'database_status': 'unknown',
            'last_check': datetime.now(timezone.utc)
        }

        try:
            # Check browser status
            if self.browser and self.browser.driver:
                try:
                    self.browser.driver.current_url
                    health_status['browser_status'] = 'connected'
                except Exception:
                    health_status['browser_status'] = 'disconnected'
                    health_status['issues'].append('Browser connection lost')
            else:
                health_status['browser_status'] = 'not_initialized'
                health_status['issues'].append('Browser not initialized')

            # Check database connectivity
            try:
                test_target = data_manager.get_surveillance_target('health_check_test')
                health_status['database_status'] = 'connected'
            except Exception as e:
                health_status['database_status'] = 'error'
                health_status['issues'].append(f'Database error: {str(e)[:100]}')

            # Check performance
            if self.extraction_stats['average_extraction_time'] > 30:
                health_status['issues'].append('Slow extraction performance')

            error_rate = (self.extraction_stats['errors_encountered'] /
                         max(self.extraction_stats['profiles_scraped'], 1))
            if error_rate > 0.2:
                health_status['issues'].append('High error rate detected')

            # Determine overall status
            if health_status['issues']:
                health_status['status'] = 'warning' if len(health_status['issues']) <= 2 else 'critical'

            return health_status

        except Exception as e:
            health_status['status'] = 'critical'
            health_status['issues'].append(f'Health check failed: {e}')
            return health_status

    def cleanup(self):
        """Cleanup resources and close connections"""
        try:
            if self.browser:
                self.browser.close()
            logger.info("Profile scraper cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False

# Utility functions for profile scraping
def create_profile_scraper(browser: Optional[InstagramBrowser] = None) -> InstagramProfileScraper:
    """Factory function to create a profile scraper instance"""
    return InstagramProfileScraper(browser)

def scrape_single_profile(username: str, browser: Optional[InstagramBrowser] = None) -> Optional[Dict[str, Any]]:
    """Convenience function to scrape a single profile"""
    with create_profile_scraper(browser) as scraper:
        return scraper.scrape_profile(username)

def scrape_profiles_batch(usernames: List[str],
                         browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to scrape multiple profiles"""
    with create_profile_scraper(browser) as scraper:
        return scraper.scrape_multiple_profiles(usernames)

def get_profile_changes(username: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Get recent profile changes for a specific user"""
    try:
        return data_manager.get_recent_changes(username, hours=hours)
    except Exception as e:
        logger.error(f"Error getting profile changes for {username}: {e}")
        return []

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper
