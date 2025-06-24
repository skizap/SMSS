"""
Social Media Surveillance System - Instagram Post Scraper
Infinite scroll post collection with support for all post types and comprehensive metadata extraction.
"""

import re
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple, Set
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

class PostExtractionError(Exception):
    """Custom exception for post extraction errors"""
    pass

class InstagramPostScraper:
    """
    Comprehensive Instagram post scraper with infinite scroll and metadata extraction.
    Supports all post types: photo, video, carousel, reel with anti-detection measures.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Post selectors (updated for current Instagram structure)
        self.selectors = {
            # Post grid and navigation
            'posts_grid': 'article div div div a',
            'post_modal': 'div[role="dialog"]',
            'close_modal': 'button[aria-label="Close"]',
            'next_post': 'button[aria-label="Next"]',
            'prev_post': 'button[aria-label="Go back"]',
            
            # Post content elements
            'post_image': 'article img',
            'post_video': 'article video',
            'carousel_dots': 'div[role="tablist"] button',
            'carousel_next': 'button[aria-label="Next"]',
            'carousel_prev': 'button[aria-label="Go back"]',
            
            # Post metadata
            'post_caption': 'article div span',
            'post_timestamp': 'article time',
            'like_count': 'article button span',
            'comment_count': 'article div span',
            'share_button': 'button[aria-label="Share Post"]',
            'save_button': 'button[aria-label="Save"]',
            
            # Engagement elements
            'like_button': 'button[aria-label="Like"]',
            'comment_button': 'button[aria-label="Comment"]',
            'comments_section': 'article div ul',
            'view_all_comments': 'button:contains("View all")',
            
            # Post type indicators
            'video_indicator': 'svg[aria-label="Video"]',
            'carousel_indicator': 'svg[aria-label="Carousel"]',
            'reel_indicator': 'svg[aria-label="Reel"]',
            
            # Location and tags
            'location_tag': 'article div a[href*="/locations/"]',
            'user_tags': 'article div button[aria-label*="tagged"]',
            'hashtags': 'article div a[href*="/explore/tags/"]',
            'mentions': 'article div a[href*="/"]',
            
            # Load more content
            'load_more_posts': 'button:contains("Load more")',
            'end_of_posts': 'span:contains("You\'re all caught up")',
        }
        
        # Performance tracking
        self.scraping_stats = {
            'posts_scraped': 0,
            'errors_encountered': 0,
            'duplicate_posts': 0,
            'average_scraping_time': 0.0,
            'posts_by_type': {
                'photo': 0,
                'video': 0,
                'carousel': 0,
                'reel': 0
            }
        }
        
        # Scraped post IDs to avoid duplicates
        self.scraped_post_ids: Set[str] = set()
    
    def scrape_user_posts(self, username: str, max_posts: int = 50, 
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scrape posts from a user's profile with infinite scroll.
        
        Args:
            username: Instagram username to scrape posts from
            max_posts: Maximum number of posts to scrape
            force_refresh: Force re-scraping of existing posts
            
        Returns:
            Dictionary containing scraping results and statistics
        """
        start_time = time.time()
        results = {
            'username': username,
            'posts_scraped': [],
            'posts_failed': [],
            'total_posts_found': 0,
            'scraping_time': 0,
            'status': 'started'
        }
        
        try:
            logger.info(f"Starting post scraping for {username} (max: {max_posts})")
            
            # Navigate to user profile
            if not self._navigate_to_profile(username):
                results['status'] = 'navigation_failed'
                return results
            
            # Check if profile is accessible
            if not self._check_profile_accessibility():
                results['status'] = 'profile_inaccessible'
                return results
            
            # Get post links from grid
            post_links = self._collect_post_links(max_posts)
            results['total_posts_found'] = len(post_links)
            
            if not post_links:
                results['status'] = 'no_posts_found'
                return results
            
            # Scrape individual posts
            for i, post_link in enumerate(post_links[:max_posts]):
                try:
                    post_data = self._scrape_single_post(post_link, username)
                    
                    if post_data:
                        # Check for duplicates
                        if not force_refresh and self._is_duplicate_post(post_data['instagram_post_id']):
                            self.scraping_stats['duplicate_posts'] += 1
                            logger.debug(f"Skipping duplicate post: {post_data['instagram_post_id']}")
                            continue
                        
                        # Save to database
                        if self._save_post_data(username, post_data):
                            results['posts_scraped'].append(post_data['instagram_post_id'])
                            self.scraped_post_ids.add(post_data['instagram_post_id'])
                        else:
                            results['posts_failed'].append(post_link)
                    else:
                        results['posts_failed'].append(post_link)
                    
                    # Progress logging
                    if (i + 1) % 10 == 0:
                        logger.info(f"Scraped {i + 1}/{len(post_links)} posts for {username}")
                    
                    # Add delay between posts
                    if i < len(post_links) - 1:
                        delay = self._calculate_scraping_delay()
                        time.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"Error scraping post {post_link}: {e}")
                    results['posts_failed'].append(post_link)
                    self.scraping_stats['errors_encountered'] += 1
            
            results['scraping_time'] = time.time() - start_time
            results['status'] = 'completed'
            
            logger.info(f"Post scraping completed for {username}: "
                       f"{len(results['posts_scraped'])} scraped, "
                       f"{len(results['posts_failed'])} failed in {results['scraping_time']:.2f}s")
            
            return results
            
        except Exception as e:
            results['scraping_time'] = time.time() - start_time
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error in post scraping for {username}: {e}")
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
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'article'))
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to profile {username}: {e}")
            return False
    
    def _check_profile_accessibility(self) -> bool:
        """Check if profile is accessible for post scraping"""
        try:
            # Check for private account
            if self._element_exists('[data-testid="private-account-icon"]'):
                logger.warning("Profile is private - cannot scrape posts")
                return False
            
            # Check for blocked/suspended account
            if self._element_exists('span:contains("User not found")'):
                logger.warning("Profile not found or blocked")
                return False
            
            # Check if posts section exists
            if not self._element_exists('article'):
                logger.warning("Posts section not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking profile accessibility: {e}")
            return False
    
    def _collect_post_links(self, max_posts: int) -> List[str]:
        """Collect post links using infinite scroll"""
        post_links = []
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 20
        
        try:
            while len(post_links) < max_posts and scroll_attempts < max_scroll_attempts:
                # Find all post links on current page
                current_links = self._find_elements(self.selectors['posts_grid'])
                
                for link_element in current_links:
                    try:
                        href = link_element.get_attribute('href')
                        if href and '/p/' in href and href not in post_links:
                            post_links.append(href)
                            
                        if len(post_links) >= max_posts:
                            break
                            
                    except StaleElementReferenceException:
                        continue
                
                # Check if we have enough posts
                if len(post_links) >= max_posts:
                    break
                
                # Scroll down to load more posts
                self.browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Check if new content loaded
                new_height = self.browser.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts >= 3:  # No new content after 3 attempts
                        break
                else:
                    scroll_attempts = 0
                    last_height = new_height
            
            logger.info(f"Collected {len(post_links)} post links")
            return post_links[:max_posts]
            
        except Exception as e:
            logger.error(f"Error collecting post links: {e}")
            return post_links

    def _scrape_single_post(self, post_url: str, username: str) -> Optional[Dict[str, Any]]:
        """Scrape data from a single post"""
        try:
            # Navigate to post
            self.browser.driver.get(post_url)

            # Wait for post to load
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'article'))
            )

            # Extract post ID from URL
            post_id = self._extract_post_id_from_url(post_url)
            if not post_id:
                logger.error(f"Could not extract post ID from URL: {post_url}")
                return None

            # Initialize post data
            post_data = {
                'instagram_post_id': post_id,
                'post_url': post_url,
                'scraped_at': datetime.now(timezone.utc)
            }

            # Determine post type
            post_data['post_type'] = self._determine_post_type()

            # Extract basic metadata
            self._extract_post_metadata(post_data)

            # Extract engagement metrics
            self._extract_engagement_metrics(post_data)

            # Extract media URLs
            self._extract_media_urls(post_data)

            # Extract caption and text content
            self._extract_caption_and_text(post_data)

            # Extract hashtags and mentions
            self._extract_hashtags_and_mentions(post_data)

            # Extract location if available
            self._extract_location_data(post_data)

            # Update statistics
            self.scraping_stats['posts_scraped'] += 1
            self.scraping_stats['posts_by_type'][post_data['post_type']] += 1

            return post_data

        except Exception as e:
            logger.error(f"Error scraping single post {post_url}: {e}")
            return None

    def _extract_post_id_from_url(self, url: str) -> Optional[str]:
        """Extract Instagram post ID from URL"""
        try:
            # Instagram post URLs: https://www.instagram.com/p/POST_ID/
            match = re.search(r'/p/([A-Za-z0-9_-]+)/', url)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def _determine_post_type(self) -> str:
        """Determine the type of post (photo, video, carousel, reel)"""
        try:
            # Check for reel indicator
            if self._element_exists(self.selectors['reel_indicator']):
                return 'reel'

            # Check for carousel indicator
            if self._element_exists(self.selectors['carousel_indicator']):
                return 'carousel'

            # Check for video
            if self._element_exists(self.selectors['post_video']):
                return 'video'

            # Default to photo
            return 'photo'

        except Exception as e:
            logger.error(f"Error determining post type: {e}")
            return 'photo'

    def _extract_post_metadata(self, post_data: Dict[str, Any]):
        """Extract basic post metadata"""
        try:
            # Extract timestamp
            timestamp_element = self._find_element(self.selectors['post_timestamp'])
            if timestamp_element:
                datetime_attr = timestamp_element.get_attribute('datetime')
                if datetime_attr:
                    post_data['posted_at'] = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                else:
                    # Try to parse from title attribute
                    title_attr = timestamp_element.get_attribute('title')
                    if title_attr:
                        post_data['posted_at'] = self._parse_instagram_timestamp(title_attr)

        except Exception as e:
            logger.error(f"Error extracting post metadata: {e}")

    def _extract_engagement_metrics(self, post_data: Dict[str, Any]):
        """Extract likes, comments, and other engagement metrics"""
        try:
            # Extract like count
            like_elements = self._find_elements(self.selectors['like_count'])
            for element in like_elements:
                text = element.text.strip()
                if 'like' in text.lower():
                    post_data['like_count'] = self._parse_engagement_count(text)
                    break

            # Extract comment count
            comment_elements = self._find_elements(self.selectors['comment_count'])
            for element in comment_elements:
                text = element.text.strip()
                if 'comment' in text.lower():
                    post_data['comment_count'] = self._parse_engagement_count(text)
                    break

            # For videos, try to extract view count
            if post_data.get('post_type') in ['video', 'reel']:
                view_elements = self._find_elements('span')
                for element in view_elements:
                    text = element.text.strip()
                    if 'view' in text.lower():
                        post_data['view_count'] = self._parse_engagement_count(text)
                        break

        except Exception as e:
            logger.error(f"Error extracting engagement metrics: {e}")

    def _extract_media_urls(self, post_data: Dict[str, Any]):
        """Extract media URLs (images/videos)"""
        try:
            media_urls = []

            if post_data['post_type'] == 'carousel':
                # Handle carousel posts
                media_urls = self._extract_carousel_media()
            else:
                # Handle single media posts
                if post_data['post_type'] in ['video', 'reel']:
                    video_element = self._find_element(self.selectors['post_video'])
                    if video_element:
                        video_url = video_element.get_attribute('src')
                        if video_url:
                            media_urls.append(video_url)
                else:
                    # Photo post
                    img_element = self._find_element(self.selectors['post_image'])
                    if img_element:
                        img_url = img_element.get_attribute('src')
                        if img_url:
                            media_urls.append(img_url)

            post_data['media_urls'] = media_urls

        except Exception as e:
            logger.error(f"Error extracting media URLs: {e}")
            post_data['media_urls'] = []

    def _extract_carousel_media(self) -> List[str]:
        """Extract media URLs from carousel posts"""
        media_urls = []

        try:
            # Find carousel navigation dots
            dots = self._find_elements(self.selectors['carousel_dots'])
            if not dots:
                return media_urls

            # Navigate through each carousel item
            for i in range(len(dots)):
                try:
                    # Click on the dot to navigate to this item
                    if i > 0:  # First item is already visible
                        dots[i].click()
                        time.sleep(1)  # Wait for transition

                    # Extract media from current item
                    img_element = self._find_element(self.selectors['post_image'])
                    if img_element:
                        img_url = img_element.get_attribute('src')
                        if img_url and img_url not in media_urls:
                            media_urls.append(img_url)

                    video_element = self._find_element(self.selectors['post_video'])
                    if video_element:
                        video_url = video_element.get_attribute('src')
                        if video_url and video_url not in media_urls:
                            media_urls.append(video_url)

                except Exception as e:
                    logger.warning(f"Error extracting carousel item {i}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting carousel media: {e}")

        return media_urls

    def _extract_caption_and_text(self, post_data: Dict[str, Any]):
        """Extract post caption and text content"""
        try:
            # Find caption elements
            caption_elements = self._find_elements(self.selectors['post_caption'])

            caption_text = ""
            for element in caption_elements:
                try:
                    text = element.text.strip()
                    if text and len(text) > len(caption_text):
                        caption_text = text
                except StaleElementReferenceException:
                    continue

            post_data['caption'] = caption_text if caption_text else None

        except Exception as e:
            logger.error(f"Error extracting caption: {e}")
            post_data['caption'] = None

    def _extract_hashtags_and_mentions(self, post_data: Dict[str, Any]):
        """Extract hashtags and user mentions from post"""
        try:
            hashtags = []
            mentions = []

            # Extract hashtags
            hashtag_elements = self._find_elements(self.selectors['hashtags'])
            for element in hashtag_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/explore/tags/' in href:
                        hashtag = element.text.strip()
                        if hashtag.startswith('#') and hashtag not in hashtags:
                            hashtags.append(hashtag)
                except StaleElementReferenceException:
                    continue

            # Extract mentions
            mention_elements = self._find_elements(self.selectors['mentions'])
            for element in mention_elements:
                try:
                    href = element.get_attribute('href')
                    text = element.text.strip()
                    if (href and '/' in href and not '/explore/' in href and
                        text.startswith('@') and text not in mentions):
                        mentions.append(text)
                except StaleElementReferenceException:
                    continue

            post_data['hashtags'] = hashtags
            post_data['mentions'] = mentions

        except Exception as e:
            logger.error(f"Error extracting hashtags and mentions: {e}")
            post_data['hashtags'] = []
            post_data['mentions'] = []

    def _extract_location_data(self, post_data: Dict[str, Any]):
        """Extract location information if available"""
        try:
            location_element = self._find_element(self.selectors['location_tag'])
            if location_element:
                post_data['location_name'] = location_element.text.strip()

                # Extract location ID from href
                href = location_element.get_attribute('href')
                if href and '/locations/' in href:
                    location_match = re.search(r'/locations/(\d+)/', href)
                    if location_match:
                        post_data['location_id'] = location_match.group(1)

        except Exception as e:
            logger.error(f"Error extracting location data: {e}")

    def _parse_engagement_count(self, text: str) -> int:
        """Parse engagement count from Instagram text"""
        try:
            # Remove non-numeric characters except K, M, B
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
            logger.warning(f"Could not parse engagement count: {text}")
            return 0

    def _parse_instagram_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse Instagram timestamp string to datetime"""
        try:
            # Common Instagram timestamp formats
            formats = [
                '%B %d, %Y',  # "January 1, 2023"
                '%b %d, %Y',  # "Jan 1, 2023"
                '%Y-%m-%d',   # "2023-01-01"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return None

        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
            return None

    def _is_duplicate_post(self, post_id: str) -> bool:
        """Check if post has already been scraped"""
        try:
            # Check in-memory cache first
            if post_id in self.scraped_post_ids:
                return True

            # Check database
            existing_posts = data_manager.execute_query(
                "SELECT id FROM posts WHERE instagram_post_id = ?",
                {'instagram_post_id': post_id}
            )

            return len(existing_posts) > 0

        except Exception as e:
            logger.error(f"Error checking duplicate post {post_id}: {e}")
            return False

    def _save_post_data(self, username: str, post_data: Dict[str, Any]) -> bool:
        """Save post data to database"""
        try:
            # Add post to database
            post = data_manager.add_post(
                target_username=username,
                instagram_post_id=post_data['instagram_post_id'],
                post_type=post_data['post_type'],
                caption=post_data.get('caption'),
                media_urls=post_data.get('media_urls', []),
                like_count=post_data.get('like_count', 0),
                comment_count=post_data.get('comment_count', 0),
                view_count=post_data.get('view_count'),
                posted_at=post_data.get('posted_at'),
                hashtags=post_data.get('hashtags', []),
                mentions=post_data.get('mentions', []),
                location_name=post_data.get('location_name'),
                location_id=post_data.get('location_id')
            )

            if post:
                logger.debug(f"Saved post {post_data['instagram_post_id']} to database")
                return True
            else:
                logger.error(f"Failed to save post {post_data['instagram_post_id']}")
                return False

        except Exception as e:
            logger.error(f"Error saving post data: {e}")
            return False

    def _calculate_scraping_delay(self) -> float:
        """Calculate intelligent delay between post scraping"""
        import random

        base_delay = random.uniform(1, 3)  # Base delay 1-3 seconds

        # Adjust based on error rate
        error_rate = (self.scraping_stats['errors_encountered'] /
                     max(self.scraping_stats['posts_scraped'], 1))

        if error_rate > 0.1:  # High error rate
            base_delay *= 2

        # Add jitter
        jitter = random.uniform(-0.5, 0.5)

        return max(0.5, base_delay + jitter)

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

    def scrape_recent_posts(self, username: str, hours: int = 24) -> Dict[str, Any]:
        """Scrape only recent posts from the last N hours"""
        try:
            logger.info(f"Scraping recent posts for {username} (last {hours} hours)")

            # Get cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Navigate to profile
            if not self._navigate_to_profile(username):
                return {'status': 'navigation_failed', 'posts_scraped': []}

            # Collect post links
            post_links = self._collect_post_links(50)  # Get more links to filter

            recent_posts = []
            for post_link in post_links:
                try:
                    post_data = self._scrape_single_post(post_link, username)

                    if post_data and post_data.get('posted_at'):
                        if post_data['posted_at'] >= cutoff_time:
                            if self._save_post_data(username, post_data):
                                recent_posts.append(post_data['instagram_post_id'])
                        else:
                            # Posts are chronological, so we can stop here
                            break

                    # Small delay between posts
                    time.sleep(self._calculate_scraping_delay())

                except Exception as e:
                    logger.error(f"Error scraping recent post {post_link}: {e}")
                    continue

            return {
                'status': 'completed',
                'posts_scraped': recent_posts,
                'cutoff_time': cutoff_time
            }

        except Exception as e:
            logger.error(f"Error scraping recent posts for {username}: {e}")
            return {'status': 'error', 'error': str(e), 'posts_scraped': []}

    def scrape_posts_by_hashtag(self, hashtag: str, max_posts: int = 30) -> Dict[str, Any]:
        """Scrape posts from a specific hashtag"""
        try:
            logger.info(f"Scraping posts for hashtag #{hashtag} (max: {max_posts})")

            # Navigate to hashtag page
            hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            self.browser.driver.get(hashtag_url)

            # Wait for page to load
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'article'))
            )

            # Collect post links
            post_links = self._collect_post_links(max_posts)

            scraped_posts = []
            for post_link in post_links:
                try:
                    post_data = self._scrape_single_post(post_link, None)  # No specific username

                    if post_data:
                        # Extract username from post URL or content
                        username = self._extract_username_from_post()
                        if username and self._save_post_data(username, post_data):
                            scraped_posts.append(post_data['instagram_post_id'])

                    time.sleep(self._calculate_scraping_delay())

                except Exception as e:
                    logger.error(f"Error scraping hashtag post {post_link}: {e}")
                    continue

            return {
                'status': 'completed',
                'hashtag': hashtag,
                'posts_scraped': scraped_posts
            }

        except Exception as e:
            logger.error(f"Error scraping hashtag {hashtag}: {e}")
            return {'status': 'error', 'error': str(e), 'posts_scraped': []}

    def _extract_username_from_post(self) -> Optional[str]:
        """Extract username from current post page"""
        try:
            # Look for username in post header
            username_elements = self._find_elements('article header a')
            for element in username_elements:
                href = element.get_attribute('href')
                if href and '/' in href:
                    username = href.strip('/').split('/')[-1]
                    if username and not username.startswith('explore'):
                        return username
            return None
        except Exception:
            return None

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics"""
        try:
            stats = self.scraping_stats.copy()

            # Calculate success rate
            total_attempts = stats['posts_scraped'] + stats['errors_encountered']
            if total_attempts > 0:
                stats['success_rate'] = (stats['posts_scraped'] / total_attempts) * 100
            else:
                stats['success_rate'] = 0.0

            # Calculate duplicate rate
            if stats['posts_scraped'] > 0:
                stats['duplicate_rate'] = (stats['duplicate_posts'] /
                                         (stats['posts_scraped'] + stats['duplicate_posts'])) * 100
            else:
                stats['duplicate_rate'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"Error getting scraping statistics: {e}")
            return {}

    def reset_statistics(self):
        """Reset scraping statistics"""
        self.scraping_stats = {
            'posts_scraped': 0,
            'errors_encountered': 0,
            'duplicate_posts': 0,
            'average_scraping_time': 0.0,
            'posts_by_type': {
                'photo': 0,
                'video': 0,
                'carousel': 0,
                'reel': 0
            }
        }
        self.scraped_post_ids.clear()
        logger.info("Post scraping statistics reset")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the post scraper"""
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
                data_manager.get_recent_posts(hours=1)
                health_status['database_status'] = 'connected'
            except Exception as e:
                health_status['database_status'] = 'error'
                health_status['issues'].append(f'Database error: {str(e)[:100]}')

            # Check performance
            if self.scraping_stats['average_scraping_time'] > 10:
                health_status['issues'].append('Slow scraping performance')

            error_rate = (self.scraping_stats['errors_encountered'] /
                         max(self.scraping_stats['posts_scraped'], 1))
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
            logger.info("Post scraper cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        return False

# Utility functions for post scraping
def create_post_scraper(browser: Optional[InstagramBrowser] = None) -> InstagramPostScraper:
    """Factory function to create a post scraper instance"""
    return InstagramPostScraper(browser)

def scrape_user_posts_quick(username: str, max_posts: int = 20,
                           browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to quickly scrape user posts"""
    with create_post_scraper(browser) as scraper:
        return scraper.scrape_user_posts(username, max_posts)

def scrape_recent_posts_quick(username: str, hours: int = 24,
                             browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to scrape recent posts"""
    with create_post_scraper(browser) as scraper:
        return scraper.scrape_recent_posts(username, hours)

def get_post_analytics(username: str, days: int = 7) -> Dict[str, Any]:
    """Get post analytics for a user"""
    try:
        posts = data_manager.get_posts(username, limit=100)

        # Filter posts from last N days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_posts = [p for p in posts if p.posted_at and p.posted_at >= cutoff_date]

        if not recent_posts:
            return {'error': 'No recent posts found'}

        # Calculate analytics
        total_likes = sum(p.like_count or 0 for p in recent_posts)
        total_comments = sum(p.comment_count or 0 for p in recent_posts)
        avg_likes = total_likes / len(recent_posts)
        avg_comments = total_comments / len(recent_posts)

        post_types = {}
        for post in recent_posts:
            post_types[post.post_type] = post_types.get(post.post_type, 0) + 1

        return {
            'username': username,
            'period_days': days,
            'total_posts': len(recent_posts),
            'total_likes': total_likes,
            'total_comments': total_comments,
            'average_likes': round(avg_likes, 2),
            'average_comments': round(avg_comments, 2),
            'post_types': post_types,
            'engagement_rate': round((total_likes + total_comments) /
                                   (len(recent_posts) * 1000) * 100, 2)  # Assuming 1K followers
        }

    except Exception as e:
        logger.error(f"Error getting post analytics for {username}: {e}")
        return {'error': str(e)}
