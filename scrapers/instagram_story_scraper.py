"""
Social Media Surveillance System - Instagram Story Scraper
Story collection with expiration tracking, highlights support, and media processing.
"""

import re
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs
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

class StoryExtractionError(Exception):
    """Custom exception for story extraction errors"""
    pass

class InstagramStoryScraper:
    """
    Comprehensive Instagram story scraper with expiration tracking and highlights support.
    Handles both regular stories and story highlights with media processing.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Story selectors (updated for current Instagram structure)
        self.selectors = {
            # Story navigation
            'story_ring': 'canvas',  # Story ring indicator
            'story_avatar': 'img[data-testid="user-avatar"]',
            'story_container': 'section[role="dialog"]',
            'story_close': 'button[aria-label="Close"]',
            'story_next': 'button[aria-label="Next"]',
            'story_prev': 'button[aria-label="Go back"]',
            
            # Story content
            'story_image': 'img[decoding="sync"]',
            'story_video': 'video',
            'story_progress_bar': 'progress',
            'story_timestamp': 'time',
            
            # Story metadata
            'story_text': 'div[data-testid="story-text"]',
            'story_stickers': 'div[data-testid="story-sticker"]',
            'story_music': 'div[data-testid="story-music"]',
            'story_location': 'div[data-testid="story-location"]',
            'story_poll': 'div[data-testid="story-poll"]',
            'story_question': 'div[data-testid="story-question"]',
            
            # Story highlights
            'highlights_tray': '[data-testid="highlights-tray"]',
            'highlight_item': '[data-testid="highlight-item"]',
            'highlight_title': 'div[data-testid="highlight-title"]',
            'highlight_cover': 'img[data-testid="highlight-cover"]',
            
            # Story viewers and interactions
            'story_viewers': 'button[aria-label*="viewer"]',
            'story_likes': 'button[aria-label*="like"]',
            'story_replies': 'button[aria-label*="reply"]',
            
            # Navigation indicators
            'has_stories': 'div[data-testid="story-ring"]',
            'no_stories': 'span:contains("No story to show")',
        }
        
        # Performance tracking
        self.scraping_stats = {
            'stories_scraped': 0,
            'highlights_scraped': 0,
            'errors_encountered': 0,
            'expired_stories': 0,
            'average_scraping_time': 0.0,
            'media_downloaded': 0
        }
        
        # Story cache to avoid duplicates
        self.scraped_story_ids = set()
    
    def scrape_user_stories(self, username: str, include_highlights: bool = True) -> Dict[str, Any]:
        """
        Scrape active stories and optionally highlights for a user.
        
        Args:
            username: Instagram username to scrape stories from
            include_highlights: Whether to include story highlights
            
        Returns:
            Dictionary containing scraping results and statistics
        """
        start_time = time.time()
        results = {
            'username': username,
            'active_stories': [],
            'highlights': [],
            'total_stories_found': 0,
            'scraping_time': 0,
            'status': 'started'
        }
        
        try:
            logger.info(f"Starting story scraping for {username}")
            
            # Navigate to user profile
            if not self._navigate_to_profile(username):
                results['status'] = 'navigation_failed'
                return results
            
            # Check if user has stories
            if not self._has_active_stories():
                logger.info(f"No active stories found for {username}")
                results['status'] = 'no_active_stories'
            else:
                # Scrape active stories
                active_stories = self._scrape_active_stories(username)
                results['active_stories'] = active_stories
                results['total_stories_found'] += len(active_stories)
            
            # Scrape highlights if requested
            if include_highlights:
                highlights = self._scrape_story_highlights(username)
                results['highlights'] = highlights
                results['total_stories_found'] += sum(len(h.get('stories', [])) for h in highlights)
            
            results['scraping_time'] = time.time() - start_time
            results['status'] = 'completed'
            
            logger.info(f"Story scraping completed for {username}: "
                       f"{len(results['active_stories'])} active stories, "
                       f"{len(results['highlights'])} highlights in {results['scraping_time']:.2f}s")
            
            return results
            
        except Exception as e:
            results['scraping_time'] = time.time() - start_time
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error in story scraping for {username}: {e}")
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
    
    def _has_active_stories(self) -> bool:
        """Check if user has active stories"""
        try:
            # Look for story ring indicator
            return self._element_exists(self.selectors['has_stories'], timeout=3)
        except Exception:
            return False
    
    def _scrape_active_stories(self, username: str) -> List[Dict[str, Any]]:
        """Scrape active stories from user profile"""
        stories = []
        
        try:
            # Click on story ring to open stories
            story_ring = self._find_element(self.selectors['story_ring'])
            if not story_ring:
                logger.warning(f"Story ring not found for {username}")
                return stories
            
            story_ring.click()
            
            # Wait for story container to load
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['story_container']))
            )
            
            # Scrape each story in the sequence
            story_index = 0
            while True:
                try:
                    story_data = self._extract_story_data(username, story_index)
                    
                    if story_data:
                        # Save to database
                        if self._save_story_data(username, story_data):
                            stories.append(story_data)
                            self.scraped_story_ids.add(story_data['story_id'])
                        
                        story_index += 1
                    
                    # Try to navigate to next story
                    if not self._navigate_to_next_story():
                        break
                    
                    # Small delay between stories
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error scraping story {story_index} for {username}: {e}")
                    break
            
            # Close story viewer
            self._close_story_viewer()
            
        except Exception as e:
            logger.error(f"Error scraping active stories for {username}: {e}")
        
        return stories
    
    def _extract_story_data(self, username: str, story_index: int) -> Optional[Dict[str, Any]]:
        """Extract data from current story"""
        try:
            # Generate story ID (Instagram doesn't expose story IDs easily)
            story_id = f"{username}_{int(time.time())}_{story_index}"
            
            story_data = {
                'story_id': story_id,
                'username': username,
                'story_index': story_index,
                'scraped_at': datetime.now(timezone.utc),
                'is_highlight': False
            }
            
            # Determine media type
            story_data['media_type'] = self._determine_story_media_type()
            
            # Extract media URL
            story_data['media_url'] = self._extract_story_media_url(story_data['media_type'])
            
            # Extract story timestamp/expiration
            self._extract_story_timing(story_data)
            
            # Extract story text overlay
            story_data['story_text'] = self._extract_story_text()
            
            # Extract stickers and interactive elements
            story_data['stickers'] = self._extract_story_stickers()
            
            # Extract music information
            story_data['music_info'] = self._extract_story_music()
            
            # Extract location if present
            story_data['location'] = self._extract_story_location()
            
            # Extract view count if available
            story_data['view_count'] = self._extract_story_view_count()
            
            self.scraping_stats['stories_scraped'] += 1
            
            return story_data
            
        except Exception as e:
            logger.error(f"Error extracting story data: {e}")
            return None
    
    def _determine_story_media_type(self) -> str:
        """Determine if story is photo or video"""
        try:
            if self._element_exists(self.selectors['story_video']):
                return 'video'
            else:
                return 'photo'
        except Exception:
            return 'photo'
    
    def _extract_story_media_url(self, media_type: str) -> Optional[str]:
        """Extract media URL from story"""
        try:
            if media_type == 'video':
                video_element = self._find_element(self.selectors['story_video'])
                if video_element:
                    return video_element.get_attribute('src')
            else:
                img_element = self._find_element(self.selectors['story_image'])
                if img_element:
                    return img_element.get_attribute('src')
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting story media URL: {e}")
            return None
    
    def _extract_story_timing(self, story_data: Dict[str, Any]):
        """Extract story posting time and expiration"""
        try:
            # Stories expire 24 hours after posting
            # Try to extract timestamp
            timestamp_element = self._find_element(self.selectors['story_timestamp'])
            if timestamp_element:
                timestamp_text = timestamp_element.get_attribute('datetime')
                if timestamp_text:
                    posted_at = datetime.fromisoformat(timestamp_text.replace('Z', '+00:00'))
                    story_data['posted_at'] = posted_at
                    story_data['expires_at'] = posted_at + timedelta(hours=24)
                    return
            
            # If no timestamp found, assume recent story
            now = datetime.now(timezone.utc)
            story_data['posted_at'] = now
            story_data['expires_at'] = now + timedelta(hours=24)
            
        except Exception as e:
            logger.error(f"Error extracting story timing: {e}")
            # Default timing
            now = datetime.now(timezone.utc)
            story_data['posted_at'] = now
            story_data['expires_at'] = now + timedelta(hours=24)

    def _extract_story_text(self) -> Optional[str]:
        """Extract text overlay from story"""
        try:
            text_elements = self._find_elements(self.selectors['story_text'])
            if text_elements:
                return ' '.join([elem.text.strip() for elem in text_elements if elem.text.strip()])
            return None
        except Exception:
            return None

    def _extract_story_stickers(self) -> List[Dict[str, Any]]:
        """Extract stickers and interactive elements from story"""
        stickers = []

        try:
            # Extract polls
            poll_elements = self._find_elements(self.selectors['story_poll'])
            for poll in poll_elements:
                try:
                    stickers.append({
                        'type': 'poll',
                        'text': poll.text.strip() if poll.text else None
                    })
                except Exception:
                    continue

            # Extract questions
            question_elements = self._find_elements(self.selectors['story_question'])
            for question in question_elements:
                try:
                    stickers.append({
                        'type': 'question',
                        'text': question.text.strip() if question.text else None
                    })
                except Exception:
                    continue

            # Extract general stickers
            sticker_elements = self._find_elements(self.selectors['story_stickers'])
            for sticker in sticker_elements:
                try:
                    stickers.append({
                        'type': 'sticker',
                        'text': sticker.text.strip() if sticker.text else None
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error extracting story stickers: {e}")

        return stickers

    def _extract_story_music(self) -> Optional[Dict[str, Any]]:
        """Extract music information from story"""
        try:
            music_element = self._find_element(self.selectors['story_music'])
            if music_element:
                return {
                    'has_music': True,
                    'music_text': music_element.text.strip() if music_element.text else None
                }
            return None
        except Exception:
            return None

    def _extract_story_location(self) -> Optional[str]:
        """Extract location tag from story"""
        try:
            location_element = self._find_element(self.selectors['story_location'])
            if location_element:
                return location_element.text.strip()
            return None
        except Exception:
            return None

    def _extract_story_view_count(self) -> Optional[int]:
        """Extract view count from story"""
        try:
            viewers_element = self._find_element(self.selectors['story_viewers'])
            if viewers_element:
                text = viewers_element.text.strip()
                # Extract number from text like "123 viewers"
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
            return None
        except Exception:
            return None

    def _navigate_to_next_story(self) -> bool:
        """Navigate to next story in sequence"""
        try:
            next_button = self._find_element(self.selectors['story_next'], timeout=2)
            if next_button:
                next_button.click()
                time.sleep(1)  # Wait for transition
                return True
            return False
        except Exception:
            return False

    def _close_story_viewer(self):
        """Close the story viewer"""
        try:
            close_button = self._find_element(self.selectors['story_close'])
            if close_button:
                close_button.click()
            else:
                # Try pressing Escape key
                ActionChains(self.browser.driver).send_keys(Keys.ESCAPE).perform()
        except Exception as e:
            logger.error(f"Error closing story viewer: {e}")

    def _scrape_story_highlights(self, username: str) -> List[Dict[str, Any]]:
        """Scrape story highlights from user profile"""
        highlights = []

        try:
            # Find highlights tray
            highlights_tray = self._find_element(self.selectors['highlights_tray'])
            if not highlights_tray:
                logger.info(f"No highlights found for {username}")
                return highlights

            # Find all highlight items
            highlight_items = self._find_elements(self.selectors['highlight_item'])

            for i, highlight_item in enumerate(highlight_items):
                try:
                    # Extract highlight metadata
                    highlight_data = self._extract_highlight_metadata(highlight_item, i)

                    # Click on highlight to open
                    highlight_item.click()

                    # Wait for highlight to load
                    WebDriverWait(self.browser.driver, self.wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['story_container']))
                    )

                    # Scrape stories in highlight
                    highlight_stories = self._scrape_highlight_stories(username, highlight_data['title'])
                    highlight_data['stories'] = highlight_stories
                    highlight_data['story_count'] = len(highlight_stories)

                    highlights.append(highlight_data)

                    # Close highlight viewer
                    self._close_story_viewer()

                    # Small delay between highlights
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error scraping highlight {i} for {username}: {e}")
                    continue

            self.scraping_stats['highlights_scraped'] += len(highlights)

        except Exception as e:
            logger.error(f"Error scraping highlights for {username}: {e}")

        return highlights

    def _extract_highlight_metadata(self, highlight_item, index: int) -> Dict[str, Any]:
        """Extract metadata from highlight item"""
        try:
            # Extract title
            title_element = highlight_item.find_element(By.CSS_SELECTOR, self.selectors['highlight_title'])
            title = title_element.text.strip() if title_element else f"Highlight {index + 1}"

            # Extract cover image
            cover_element = highlight_item.find_element(By.CSS_SELECTOR, self.selectors['highlight_cover'])
            cover_url = cover_element.get_attribute('src') if cover_element else None

            return {
                'title': title,
                'cover_url': cover_url,
                'highlight_index': index,
                'is_highlight': True,
                'scraped_at': datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.error(f"Error extracting highlight metadata: {e}")
            return {
                'title': f"Highlight {index + 1}",
                'cover_url': None,
                'highlight_index': index,
                'is_highlight': True,
                'scraped_at': datetime.now(timezone.utc)
            }

    def _scrape_highlight_stories(self, username: str, highlight_title: str) -> List[Dict[str, Any]]:
        """Scrape stories within a highlight"""
        stories = []

        try:
            story_index = 0
            while True:
                try:
                    story_data = self._extract_story_data(username, story_index)

                    if story_data:
                        # Mark as highlight story
                        story_data['is_highlight'] = True
                        story_data['highlight_title'] = highlight_title
                        story_data['story_id'] = f"{username}_{highlight_title}_{story_index}"

                        # Highlights don't expire
                        story_data['expires_at'] = None

                        # Save to database
                        if self._save_story_data(username, story_data):
                            stories.append(story_data)

                        story_index += 1

                    # Try to navigate to next story in highlight
                    if not self._navigate_to_next_story():
                        break

                    time.sleep(1)

                except Exception as e:
                    logger.error(f"Error scraping highlight story {story_index}: {e}")
                    break

        except Exception as e:
            logger.error(f"Error scraping highlight stories: {e}")

        return stories

    def _save_story_data(self, username: str, story_data: Dict[str, Any]) -> bool:
        """Save story data to database"""
        try:
            # Add story to database
            story = data_manager.add_story(
                target_username=username,
                story_id=story_data['story_id'],
                media_type=story_data['media_type'],
                media_url=story_data.get('media_url'),
                story_text=story_data.get('story_text'),
                view_count=story_data.get('view_count', 0),
                posted_at=story_data.get('posted_at'),
                expires_at=story_data.get('expires_at'),
                is_highlight=story_data.get('is_highlight', False),
                highlight_title=story_data.get('highlight_title'),
                stickers=story_data.get('stickers', []),
                music_info=story_data.get('music_info')
            )

            if story:
                logger.debug(f"Saved story {story_data['story_id']} to database")
                return True
            else:
                logger.error(f"Failed to save story {story_data['story_id']}")
                return False

        except Exception as e:
            logger.error(f"Error saving story data: {e}")
            return False

    def cleanup_expired_stories(self) -> int:
        """Clean up expired stories from database"""
        try:
            cleaned_count = data_manager.cleanup_expired_stories()
            self.scraping_stats['expired_stories'] += cleaned_count
            logger.info(f"Cleaned up {cleaned_count} expired stories")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up expired stories: {e}")
            return 0

    def get_active_stories(self, username: str) -> List[Dict[str, Any]]:
        """Get active (non-expired) stories for a user"""
        try:
            stories = data_manager.get_active_stories(username)
            return [story.to_dict() for story in stories]
        except Exception as e:
            logger.error(f"Error getting active stories for {username}: {e}")
            return []

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

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics"""
        try:
            stats = self.scraping_stats.copy()

            # Calculate success rate
            total_attempts = stats['stories_scraped'] + stats['errors_encountered']
            if total_attempts > 0:
                stats['success_rate'] = (stats['stories_scraped'] / total_attempts) * 100
            else:
                stats['success_rate'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"Error getting scraping statistics: {e}")
            return {}

    def reset_statistics(self):
        """Reset scraping statistics"""
        self.scraping_stats = {
            'stories_scraped': 0,
            'highlights_scraped': 0,
            'errors_encountered': 0,
            'expired_stories': 0,
            'average_scraping_time': 0.0,
            'media_downloaded': 0
        }
        self.scraped_story_ids.clear()
        logger.info("Story scraping statistics reset")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the story scraper"""
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
                data_manager.get_active_stories('health_check_test')
                health_status['database_status'] = 'connected'
            except Exception as e:
                health_status['database_status'] = 'error'
                health_status['issues'].append(f'Database error: {str(e)[:100]}')

            # Check performance
            if self.scraping_stats['average_scraping_time'] > 15:
                health_status['issues'].append('Slow scraping performance')

            error_rate = (self.scraping_stats['errors_encountered'] /
                         max(self.scraping_stats['stories_scraped'], 1))
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
            logger.info("Story scraper cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False

# Utility functions for story scraping
def create_story_scraper(browser: Optional[InstagramBrowser] = None) -> InstagramStoryScraper:
    """Factory function to create a story scraper instance"""
    return InstagramStoryScraper(browser)

def scrape_user_stories_quick(username: str, include_highlights: bool = True,
                             browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to quickly scrape user stories"""
    with create_story_scraper(browser) as scraper:
        return scraper.scrape_user_stories(username, include_highlights)

def get_story_analytics(username: str, days: int = 7) -> Dict[str, Any]:
    """Get story analytics for a user"""
    try:
        # Get recent stories
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # This would need to be implemented in data_manager
        # For now, return basic structure
        return {
            'username': username,
            'period_days': days,
            'total_stories': 0,
            'total_highlights': 0,
            'average_views': 0,
            'story_types': {'photo': 0, 'video': 0},
            'interactive_elements': 0
        }

    except Exception as e:
        logger.error(f"Error getting story analytics for {username}: {e}")
        return {'error': str(e)}

def monitor_story_expiration():
    """Monitor and clean up expired stories"""
    try:
        with create_story_scraper() as scraper:
            return scraper.cleanup_expired_stories()
    except Exception as e:
        logger.error(f"Error monitoring story expiration: {e}")
        return 0
