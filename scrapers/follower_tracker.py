"""
Social Media Surveillance System - Follower Tracker
Efficient follower tracking with new/unfollowed detection and bot detection capabilities.
"""

import re
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple
from urllib.parse import urlparse
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

logger = logging.getLogger(__name__)

class FollowerTrackingError(Exception):
    """Custom exception for follower tracking errors"""
    pass

class InstagramFollowerTracker:
    """
    Comprehensive Instagram follower tracker with efficient change detection and bot analysis.
    Handles large follower counts (10K+) with performance optimization.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Follower page selectors
        self.selectors = {
            # Navigation
            'followers_link': 'a[href*="/followers/"]',
            'following_link': 'a[href*="/following/"]',
            'followers_modal': 'div[role="dialog"]',
            'close_modal': 'button[aria-label="Close"]',
            
            # Follower list elements
            'follower_list': 'div[role="dialog"] div[style*="flex-direction: column"]',
            'follower_item': 'div[role="dialog"] div[style*="flex-direction: column"] > div',
            'follower_username': 'a[role="link"]',
            'follower_display_name': 'div span',
            'follower_avatar': 'img[data-testid="user-avatar"]',
            'verified_badge': 'svg[aria-label="Verified"]',
            'follow_button': 'button:contains("Follow")',
            'following_button': 'button:contains("Following")',
            'remove_button': 'button:contains("Remove")',
            
            # Load more content
            'load_more': 'button:contains("Show more")',
            'loading_spinner': 'svg[aria-label="Loading..."]',
            
            # Profile indicators
            'private_account': '[data-testid="private-account-icon"]',
            'follower_count': 'a[href*="/followers/"] span',
            'following_count': 'a[href*="/following/"] span',
        }
        
        # Bot detection patterns
        self.bot_indicators = {
            'username_patterns': [
                r'^[a-z]+\d{4,}$',  # letters followed by many numbers
                r'^\w+_\w+_\d+$',   # word_word_number pattern
                r'^user\d+$',       # user followed by numbers
                r'^\w{1,3}\d{6,}$', # short letters + many numbers
            ],
            'suspicious_bio_keywords': [
                'follow for follow', 'f4f', 'l4l', 'like for like',
                'dm for promo', 'cheap followers', 'buy followers',
                'instagram growth', 'follow back', 'followback'
            ],
            'follower_following_ratios': {
                'min_suspicious_ratio': 10,  # Following 10x more than followers
                'max_followers_for_ratio_check': 1000
            }
        }
        
        # Performance tracking
        self.tracking_stats = {
            'followers_processed': 0,
            'new_followers_detected': 0,
            'unfollows_detected': 0,
            'bots_detected': 0,
            'errors_encountered': 0,
            'average_processing_time': 0.0,
            'last_full_scan': None
        }
        
        # Caching for performance
        self.follower_cache = {}
        self.processed_usernames = set()
    
    def track_followers(self, username: str, max_followers: int = 10000, 
                       deep_analysis: bool = False) -> Dict[str, Any]:
        """
        Track followers for a user with change detection.
        
        Args:
            username: Instagram username to track followers for
            max_followers: Maximum number of followers to process
            deep_analysis: Whether to perform deep bot analysis
            
        Returns:
            Dictionary containing tracking results and statistics
        """
        start_time = time.time()
        results = {
            'username': username,
            'new_followers': [],
            'unfollowed_users': [],
            'total_followers_found': 0,
            'bots_detected': [],
            'processing_time': 0,
            'status': 'started'
        }
        
        try:
            logger.info(f"Starting follower tracking for {username} (max: {max_followers})")
            
            # Navigate to user profile
            if not self._navigate_to_profile(username):
                results['status'] = 'navigation_failed'
                return results
            
            # Check if profile is accessible
            if not self._check_profile_accessibility():
                results['status'] = 'profile_inaccessible'
                return results
            
            # Get current follower count
            current_follower_count = self._get_follower_count()
            results['current_follower_count'] = current_follower_count
            
            # Open followers modal
            if not self._open_followers_modal():
                results['status'] = 'modal_failed'
                return results
            
            # Get existing followers from database
            existing_followers = self._get_existing_followers(username)
            existing_usernames = {f.follower_username for f in existing_followers}
            
            # Collect current followers
            current_followers = self._collect_followers(max_followers, deep_analysis)
            current_usernames = {f['username'] for f in current_followers}
            
            results['total_followers_found'] = len(current_followers)
            
            # Detect new followers
            new_followers = current_usernames - existing_usernames
            for follower_data in current_followers:
                if follower_data['username'] in new_followers:
                    if self._save_follower_data(username, follower_data):
                        results['new_followers'].append(follower_data['username'])
            
            # Detect unfollows
            unfollowed = existing_usernames - current_usernames
            for unfollowed_username in unfollowed:
                if self._mark_follower_unfollowed(username, unfollowed_username):
                    results['unfollowed_users'].append(unfollowed_username)
            
            # Collect bot detection results
            if deep_analysis:
                results['bots_detected'] = [f['username'] for f in current_followers 
                                          if f.get('bot_probability', 0) > 0.7]
            
            # Close modal
            self._close_followers_modal()
            
            # Update statistics
            self.tracking_stats['new_followers_detected'] += len(results['new_followers'])
            self.tracking_stats['unfollows_detected'] += len(results['unfollowed_users'])
            self.tracking_stats['last_full_scan'] = datetime.now(timezone.utc)
            
            results['processing_time'] = time.time() - start_time
            results['status'] = 'completed'
            
            logger.info(f"Follower tracking completed for {username}: "
                       f"{len(results['new_followers'])} new, "
                       f"{len(results['unfollowed_users'])} unfollowed, "
                       f"{len(results['bots_detected'])} bots in {results['processing_time']:.2f}s")
            
            return results
            
        except Exception as e:
            results['processing_time'] = time.time() - start_time
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error in follower tracking for {username}: {e}")
            return results
    
    def _navigate_to_profile(self, username: str) -> bool:
        """Navigate to user profile"""
        try:
            if not self.browser.is_logged_in:
                logger.error("Browser not logged in")
                return False
            
            success = self.browser.navigate_to_profile(username)
            if success:
                # Wait for profile to load
                WebDriverWait(self.browser.driver, self.wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to profile {username}: {e}")
            return False
    
    def _check_profile_accessibility(self) -> bool:
        """Check if profile is accessible for follower tracking"""
        try:
            # Check for private account
            if self._element_exists(self.selectors['private_account']):
                logger.warning("Profile is private - cannot track followers")
                return False
            
            # Check if followers link exists
            if not self._element_exists(self.selectors['followers_link']):
                logger.warning("Followers link not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking profile accessibility: {e}")
            return False
    
    def _get_follower_count(self) -> int:
        """Get current follower count from profile"""
        try:
            follower_element = self._find_element(self.selectors['follower_count'])
            if follower_element:
                count_text = follower_element.text.strip()
                return self._parse_count(count_text)
            return 0
        except Exception as e:
            logger.error(f"Error getting follower count: {e}")
            return 0
    
    def _open_followers_modal(self) -> bool:
        """Open the followers modal"""
        try:
            followers_link = self._find_element(self.selectors['followers_link'])
            if not followers_link:
                logger.error("Followers link not found")
                return False
            
            followers_link.click()
            
            # Wait for modal to open
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['followers_modal']))
            )
            
            # Additional wait for content to load
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening followers modal: {e}")
            return False
    
    def _collect_followers(self, max_followers: int, deep_analysis: bool) -> List[Dict[str, Any]]:
        """Collect follower data with infinite scroll"""
        followers = []
        processed_usernames = set()
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        try:
            while len(followers) < max_followers and scroll_attempts < max_scroll_attempts:
                # Find follower items on current page
                follower_items = self._find_elements(self.selectors['follower_item'])
                
                new_followers_found = False
                for item in follower_items:
                    try:
                        follower_data = self._extract_follower_data(item, deep_analysis)
                        
                        if (follower_data and 
                            follower_data['username'] not in processed_usernames):
                            
                            followers.append(follower_data)
                            processed_usernames.add(follower_data['username'])
                            new_followers_found = True
                            
                            if len(followers) >= max_followers:
                                break
                                
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        logger.warning(f"Error extracting follower data: {e}")
                        continue
                
                # If no new followers found, try scrolling
                if not new_followers_found:
                    scroll_attempts += 1
                    if not self._scroll_followers_list():
                        break
                else:
                    scroll_attempts = 0  # Reset if we found new followers
                
                # Progress logging
                if len(followers) % 100 == 0 and len(followers) > 0:
                    logger.info(f"Processed {len(followers)} followers...")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
            
            logger.info(f"Collected {len(followers)} followers")
            return followers
            
        except Exception as e:
            logger.error(f"Error collecting followers: {e}")
            return followers

    def _extract_follower_data(self, follower_item, deep_analysis: bool) -> Optional[Dict[str, Any]]:
        """Extract data from a single follower item"""
        try:
            # Extract username
            username_element = follower_item.find_element(By.CSS_SELECTOR, self.selectors['follower_username'])
            if not username_element:
                return None

            username = username_element.get_attribute('href').split('/')[-2] if username_element.get_attribute('href') else None
            if not username:
                return None

            follower_data = {
                'username': username,
                'scraped_at': datetime.now(timezone.utc)
            }

            # Extract display name
            try:
                display_name_element = follower_item.find_element(By.CSS_SELECTOR, self.selectors['follower_display_name'])
                follower_data['display_name'] = display_name_element.text.strip()
            except NoSuchElementException:
                follower_data['display_name'] = username

            # Extract profile picture
            try:
                avatar_element = follower_item.find_element(By.CSS_SELECTOR, self.selectors['follower_avatar'])
                follower_data['profile_pic_url'] = avatar_element.get_attribute('src')
            except NoSuchElementException:
                follower_data['profile_pic_url'] = None

            # Check verification status
            try:
                follower_item.find_element(By.CSS_SELECTOR, self.selectors['verified_badge'])
                follower_data['is_verified'] = True
            except NoSuchElementException:
                follower_data['is_verified'] = False

            # Perform bot analysis if requested
            if deep_analysis:
                follower_data.update(self._analyze_bot_probability(follower_data))

            self.tracking_stats['followers_processed'] += 1

            return follower_data

        except Exception as e:
            logger.error(f"Error extracting follower data: {e}")
            return None

    def _analyze_bot_probability(self, follower_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze probability that a follower is a bot"""
        try:
            bot_score = 0.0
            analysis_details = []

            username = follower_data['username']
            display_name = follower_data.get('display_name', '')

            # Check username patterns
            for pattern in self.bot_indicators['username_patterns']:
                if re.match(pattern, username):
                    bot_score += 0.3
                    analysis_details.append(f"Suspicious username pattern: {pattern}")
                    break

            # Check for generic display names
            if display_name.lower() in ['user', 'instagram user', ''] or display_name == username:
                bot_score += 0.2
                analysis_details.append("Generic or missing display name")

            # Check for numbers in display name
            if re.search(r'\d{3,}', display_name):
                bot_score += 0.15
                analysis_details.append("Many numbers in display name")

            # Check verification status (verified accounts less likely to be bots)
            if follower_data.get('is_verified', False):
                bot_score -= 0.3
                analysis_details.append("Verified account (less likely bot)")

            # Additional checks would require visiting the profile
            # For performance, we'll do basic checks here

            # Normalize score to 0-1 range
            bot_probability = min(1.0, max(0.0, bot_score))

            # Update bot detection stats
            if bot_probability > 0.7:
                self.tracking_stats['bots_detected'] += 1

            return {
                'bot_probability': bot_probability,
                'bot_analysis_details': analysis_details,
                'likely_bot': bot_probability > 0.7
            }

        except Exception as e:
            logger.error(f"Error analyzing bot probability: {e}")
            return {
                'bot_probability': 0.0,
                'bot_analysis_details': [],
                'likely_bot': False
            }

    def _scroll_followers_list(self) -> bool:
        """Scroll the followers list to load more content"""
        try:
            # Find the scrollable container
            modal = self._find_element(self.selectors['followers_modal'])
            if not modal:
                return False

            # Scroll down in the modal
            self.browser.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                modal
            )

            # Wait for content to load
            time.sleep(2)

            # Check if loading spinner is present
            if self._element_exists(self.selectors['loading_spinner'], timeout=1):
                # Wait for loading to complete
                WebDriverWait(self.browser.driver, 10).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['loading_spinner']))
                )

            return True

        except Exception as e:
            logger.error(f"Error scrolling followers list: {e}")
            return False

    def _close_followers_modal(self):
        """Close the followers modal"""
        try:
            close_button = self._find_element(self.selectors['close_modal'])
            if close_button:
                close_button.click()
            else:
                # Try pressing Escape key
                ActionChains(self.browser.driver).send_keys(Keys.ESCAPE).perform()

            # Wait for modal to close
            WebDriverWait(self.browser.driver, 5).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['followers_modal']))
            )

        except Exception as e:
            logger.error(f"Error closing followers modal: {e}")

    def _get_existing_followers(self, username: str) -> List:
        """Get existing followers from database"""
        try:
            return data_manager.get_followers(username, status='active')
        except Exception as e:
            logger.error(f"Error getting existing followers for {username}: {e}")
            return []

    def _save_follower_data(self, username: str, follower_data: Dict[str, Any]) -> bool:
        """Save follower data to database"""
        try:
            follower = data_manager.add_follower(
                target_username=username,
                follower_username=follower_data['username'],
                follower_display_name=follower_data.get('display_name'),
                follower_profile_pic=follower_data.get('profile_pic_url'),
                is_verified=follower_data.get('is_verified', False),
                bot_probability=follower_data.get('bot_probability', 0.0),
                influence_score=self._calculate_influence_score(follower_data)
            )

            if follower:
                logger.debug(f"Saved follower {follower_data['username']} to database")
                return True
            else:
                logger.error(f"Failed to save follower {follower_data['username']}")
                return False

        except Exception as e:
            logger.error(f"Error saving follower data: {e}")
            return False

    def _mark_follower_unfollowed(self, username: str, follower_username: str) -> bool:
        """Mark a follower as unfollowed"""
        try:
            return data_manager.mark_follower_unfollowed(username, follower_username)
        except Exception as e:
            logger.error(f"Error marking follower unfollowed: {e}")
            return False

    def _calculate_influence_score(self, follower_data: Dict[str, Any]) -> float:
        """Calculate influence score for a follower"""
        try:
            score = 5.0  # Base score

            # Verified accounts get higher score
            if follower_data.get('is_verified', False):
                score += 3.0

            # Lower score for likely bots
            if follower_data.get('likely_bot', False):
                score -= 4.0

            # Normalize to 0-10 range
            return max(0.0, min(10.0, score))

        except Exception:
            return 5.0  # Default score

    def _parse_count(self, count_text: str) -> int:
        """Parse Instagram count text to integer"""
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

            # Regular number
            return int(count_text)

        except (ValueError, TypeError):
            logger.warning(f"Could not parse count: {count_text}")
            return 0

    def track_new_followers_only(self, username: str, hours: int = 24) -> Dict[str, Any]:
        """Track only new followers from the last N hours"""
        try:
            logger.info(f"Tracking new followers for {username} (last {hours} hours)")

            # Get existing new followers from database
            existing_new_followers = data_manager.get_new_followers(username, hours)
            existing_usernames = {f.follower_username for f in existing_new_followers}

            # Get current follower count for comparison
            if not self._navigate_to_profile(username):
                return {'status': 'navigation_failed', 'new_followers': []}

            current_count = self._get_follower_count()

            # Get last known follower count
            target = data_manager.get_surveillance_target(username)
            last_known_count = target.follower_count if target else 0

            # If count increased significantly, do a partial scan
            count_increase = current_count - last_known_count
            if count_increase > 0:
                # Scan only the estimated number of new followers + buffer
                max_to_scan = min(count_increase * 2, 500)  # 2x buffer, max 500

                if self._open_followers_modal():
                    new_followers = self._collect_followers(max_to_scan, deep_analysis=True)
                    self._close_followers_modal()

                    # Filter for truly new followers
                    truly_new = []
                    for follower in new_followers:
                        if follower['username'] not in existing_usernames:
                            if self._save_follower_data(username, follower):
                                truly_new.append(follower['username'])

                    return {
                        'status': 'completed',
                        'new_followers': truly_new,
                        'count_increase': count_increase,
                        'scanned_followers': len(new_followers)
                    }

            return {
                'status': 'no_new_followers',
                'new_followers': [],
                'count_increase': count_increase
            }

        except Exception as e:
            logger.error(f"Error tracking new followers for {username}: {e}")
            return {'status': 'error', 'error': str(e), 'new_followers': []}

    def analyze_follower_quality(self, username: str, sample_size: int = 100) -> Dict[str, Any]:
        """Analyze follower quality with bot detection on a sample"""
        try:
            logger.info(f"Analyzing follower quality for {username} (sample: {sample_size})")

            if not self._navigate_to_profile(username):
                return {'status': 'navigation_failed'}

            if not self._open_followers_modal():
                return {'status': 'modal_failed'}

            # Collect sample of followers with deep analysis
            sample_followers = self._collect_followers(sample_size, deep_analysis=True)
            self._close_followers_modal()

            if not sample_followers:
                return {'status': 'no_followers_found'}

            # Analyze the sample
            total_followers = len(sample_followers)
            verified_count = sum(1 for f in sample_followers if f.get('is_verified', False))
            bot_count = sum(1 for f in sample_followers if f.get('likely_bot', False))

            avg_bot_probability = sum(f.get('bot_probability', 0) for f in sample_followers) / total_followers
            avg_influence_score = sum(self._calculate_influence_score(f) for f in sample_followers) / total_followers

            # Quality assessment
            quality_score = self._calculate_quality_score(verified_count, bot_count, total_followers)

            return {
                'status': 'completed',
                'username': username,
                'sample_size': total_followers,
                'verified_followers': verified_count,
                'verified_percentage': (verified_count / total_followers) * 100,
                'bot_followers': bot_count,
                'bot_percentage': (bot_count / total_followers) * 100,
                'average_bot_probability': round(avg_bot_probability, 3),
                'average_influence_score': round(avg_influence_score, 2),
                'quality_score': quality_score,
                'quality_rating': self._get_quality_rating(quality_score)
            }

        except Exception as e:
            logger.error(f"Error analyzing follower quality for {username}: {e}")
            return {'status': 'error', 'error': str(e)}

    def _calculate_quality_score(self, verified_count: int, bot_count: int, total_count: int) -> float:
        """Calculate overall follower quality score (0-100)"""
        try:
            if total_count == 0:
                return 0.0

            # Base score
            score = 50.0

            # Boost for verified followers
            verified_percentage = (verified_count / total_count) * 100
            score += verified_percentage * 0.5  # Up to 50 points for 100% verified

            # Penalty for bots
            bot_percentage = (bot_count / total_count) * 100
            score -= bot_percentage * 0.8  # Up to 80 points penalty for 100% bots

            return max(0.0, min(100.0, score))

        except Exception:
            return 50.0

    def _get_quality_rating(self, quality_score: float) -> str:
        """Get quality rating based on score"""
        if quality_score >= 80:
            return 'Excellent'
        elif quality_score >= 60:
            return 'Good'
        elif quality_score >= 40:
            return 'Fair'
        elif quality_score >= 20:
            return 'Poor'
        else:
            return 'Very Poor'

    def get_follower_changes(self, username: str, hours: int = 24) -> Dict[str, Any]:
        """Get follower changes (new/unfollowed) for the last N hours"""
        try:
            changes = data_manager.get_recent_changes(username, hours=hours)

            new_followers = []
            unfollowed = []

            for change in changes:
                if change.change_type == 'new_follower':
                    new_followers.append(change.new_value)
                elif change.change_type == 'follower_lost':
                    unfollowed.append(change.old_value)

            return {
                'username': username,
                'period_hours': hours,
                'new_followers': new_followers,
                'unfollowed': unfollowed,
                'net_change': len(new_followers) - len(unfollowed)
            }

        except Exception as e:
            logger.error(f"Error getting follower changes for {username}: {e}")
            return {'error': str(e)}

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

    def get_tracking_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tracking statistics"""
        try:
            stats = self.tracking_stats.copy()

            # Calculate rates
            if stats['followers_processed'] > 0:
                stats['bot_detection_rate'] = (stats['bots_detected'] / stats['followers_processed']) * 100
                stats['error_rate'] = (stats['errors_encountered'] / stats['followers_processed']) * 100
            else:
                stats['bot_detection_rate'] = 0.0
                stats['error_rate'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"Error getting tracking statistics: {e}")
            return {}

    def reset_statistics(self):
        """Reset tracking statistics"""
        self.tracking_stats = {
            'followers_processed': 0,
            'new_followers_detected': 0,
            'unfollows_detected': 0,
            'bots_detected': 0,
            'errors_encountered': 0,
            'average_processing_time': 0.0,
            'last_full_scan': None
        }
        self.follower_cache.clear()
        self.processed_usernames.clear()
        logger.info("Follower tracking statistics reset")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the follower tracker"""
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
                data_manager.get_followers('health_check_test')
                health_status['database_status'] = 'connected'
            except Exception as e:
                health_status['database_status'] = 'error'
                health_status['issues'].append(f'Database error: {str(e)[:100]}')

            # Check performance
            if self.tracking_stats['average_processing_time'] > 60:
                health_status['issues'].append('Slow processing performance')

            error_rate = (self.tracking_stats['errors_encountered'] /
                         max(self.tracking_stats['followers_processed'], 1))
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
            logger.info("Follower tracker cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False

# Utility functions for follower tracking
def create_follower_tracker(browser: Optional[InstagramBrowser] = None) -> InstagramFollowerTracker:
    """Factory function to create a follower tracker instance"""
    return InstagramFollowerTracker(browser)

def track_followers_quick(username: str, max_followers: int = 1000,
                         browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to quickly track followers"""
    with create_follower_tracker(browser) as tracker:
        return tracker.track_followers(username, max_followers)

def analyze_follower_quality_quick(username: str, sample_size: int = 100,
                                  browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to analyze follower quality"""
    with create_follower_tracker(browser) as tracker:
        return tracker.analyze_follower_quality(username, sample_size)

def get_follower_analytics(username: str, days: int = 7) -> Dict[str, Any]:
    """Get comprehensive follower analytics"""
    try:
        # Get follower changes over time
        changes = data_manager.get_recent_changes(username, hours=days*24)

        new_followers = [c for c in changes if c.change_type == 'new_follower']
        unfollowed = [c for c in changes if c.change_type == 'follower_lost']

        # Get current follower stats
        followers = data_manager.get_followers(username, limit=1000)

        bot_count = sum(1 for f in followers if f.bot_probability and f.bot_probability > 0.7)
        verified_count = sum(1 for f in followers if f.is_verified)

        return {
            'username': username,
            'period_days': days,
            'new_followers_count': len(new_followers),
            'unfollowed_count': len(unfollowed),
            'net_change': len(new_followers) - len(unfollowed),
            'total_followers': len(followers),
            'bot_followers': bot_count,
            'verified_followers': verified_count,
            'bot_percentage': (bot_count / len(followers) * 100) if followers else 0,
            'verified_percentage': (verified_count / len(followers) * 100) if followers else 0
        }

    except Exception as e:
        logger.error(f"Error getting follower analytics for {username}: {e}")
        return {'error': str(e)}
