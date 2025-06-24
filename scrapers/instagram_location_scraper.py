"""
Social Media Surveillance System - Instagram Location Scraper
Comprehensive location-based post collection and geographic analysis.
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

logger = logging.getLogger(__name__)

class LocationScrapingError(Exception):
    """Custom exception for location scraping errors"""
    pass

class InstagramLocationScraper:
    """
    Comprehensive Instagram location scraper for geographic analysis and location-based post collection.
    Provides detailed location metrics and nearby location discovery.
    """
    
    def __init__(self, browser: Optional[InstagramBrowser] = None):
        self.browser = browser or InstagramBrowser()
        self.wait_timeout = config.browser.timeout
        self.retry_attempts = config.instagram.max_retries
        
        # Location page selectors
        self.selectors = {
            # Location page elements
            'location_header': 'header section',
            'location_name': 'h1',
            'location_address': 'div[data-testid="location-address"]',
            'location_coordinates': 'div[data-testid="location-coordinates"]',
            'post_count': 'span:contains("posts")',
            'location_description': 'div[data-testid="location-description"]',
            
            # Posts grid
            'posts_grid': 'article div div div a[href*="/p/"]',
            'top_posts': 'div[data-testid="top-posts"] article a',
            'recent_posts': 'div[data-testid="recent-posts"] article a',
            
            # Related locations
            'related_locations': 'div[data-testid="related-locations"] a',
            'nearby_locations': 'div[data-testid="nearby-locations"] a',
            
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
            
            # Map elements
            'location_map': 'div[data-testid="location-map"]',
            'map_marker': 'div[data-testid="map-marker"]',
        }
        
        # Performance tracking
        self.scraping_stats = {
            'locations_analyzed': 0,
            'posts_collected': 0,
            'related_locations_found': 0,
            'errors_encountered': 0,
            'average_analysis_time': 0.0,
            'popular_locations_detected': 0
        }
        
        # Caching for performance
        self.location_cache = {}
        self.analyzed_locations = set()
    
    def analyze_location(self, location_id: str, max_posts: int = 50, 
                        include_nearby: bool = True) -> Dict[str, Any]:
        """
        Comprehensive location analysis with metrics and post collection.
        
        Args:
            location_id: Instagram location ID to analyze
            max_posts: Maximum number of posts to collect
            include_nearby: Whether to find nearby locations
            
        Returns:
            Dictionary containing location analysis results
        """
        start_time = time.time()
        results = {
            'location_id': location_id,
            'location_name': '',
            'address': '',
            'coordinates': None,
            'post_count': 0,
            'top_posts': [],
            'recent_posts': [],
            'nearby_locations': [],
            'popularity_score': 0.0,
            'analysis_time': 0,
            'status': 'started'
        }
        
        try:
            logger.info(f"Starting location analysis for location ID: {location_id}")
            
            # Navigate to location page
            if not self._navigate_to_location(location_id):
                results['status'] = 'navigation_failed'
                return results
            
            # Extract location metadata
            location_metadata = self._extract_location_metadata()
            results.update(location_metadata)
            
            # Collect top posts
            if max_posts > 0:
                results['top_posts'] = self._collect_top_posts(min(max_posts // 2, 25))
                results['recent_posts'] = self._collect_recent_posts(min(max_posts // 2, 25))
            
            # Find nearby locations
            if include_nearby:
                results['nearby_locations'] = self._find_nearby_locations()
            
            # Calculate popularity score
            results['popularity_score'] = self._calculate_popularity_score(results)
            
            # Save location data
            self._save_location_data(location_id, results)
            
            # Update statistics
            self.scraping_stats['locations_analyzed'] += 1
            self.scraping_stats['posts_collected'] += len(results['top_posts']) + len(results['recent_posts'])
            self.scraping_stats['related_locations_found'] += len(results['nearby_locations'])
            
            results['analysis_time'] = time.time() - start_time
            results['status'] = 'completed'
            
            logger.info(f"Location analysis completed for {location_id}: "
                       f"{results['post_count']} posts, "
                       f"{len(results['nearby_locations'])} nearby locations, "
                       f"popularity score: {results['popularity_score']:.2f}")
            
            return results
            
        except Exception as e:
            results['analysis_time'] = time.time() - start_time
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error analyzing location {location_id}: {e}")
            return results
    
    def search_locations_by_name(self, location_name: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for locations by name.
        
        Args:
            location_name: Name of location to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of location dictionaries with basic info
        """
        try:
            logger.info(f"Searching for locations matching: {location_name}")
            
            # Navigate to Instagram search
            search_url = f"https://www.instagram.com/explore/locations/"
            self.browser.driver.get(search_url)
            
            # Wait for page to load
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
            )
            
            # This would implement location search functionality
            # For now, return empty list as placeholder
            logger.info(f"Location search for '{location_name}' completed")
            return []
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return []
    
    def _navigate_to_location(self, location_id: str) -> bool:
        """Navigate to location page"""
        try:
            if not self.browser.is_logged_in:
                logger.error("Browser not logged in")
                return False
            
            location_url = f"https://www.instagram.com/explore/locations/{location_id}/"
            self.browser.driver.get(location_url)
            
            # Wait for page to load
            WebDriverWait(self.browser.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
            )
            
            # Check if location exists
            if "Page Not Found" in self.browser.driver.title:
                logger.warning(f"Location {location_id} not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to location {location_id}: {e}")
            return False
    
    def _extract_location_metadata(self) -> Dict[str, Any]:
        """Extract basic location metadata from page"""
        try:
            metadata = {}
            
            # Extract location name
            name_element = self._find_element(self.selectors['location_name'])
            if name_element:
                metadata['location_name'] = name_element.text.strip()
            
            # Extract address
            address_element = self._find_element(self.selectors['location_address'])
            if address_element:
                metadata['address'] = address_element.text.strip()
            
            # Extract post count
            post_count_element = self._find_element(self.selectors['post_count'])
            if post_count_element:
                count_text = post_count_element.text
                metadata['post_count'] = self._parse_count(count_text)
            else:
                metadata['post_count'] = 0
            
            # Extract coordinates if available
            coords_element = self._find_element(self.selectors['location_coordinates'])
            if coords_element:
                coords_text = coords_element.text.strip()
                metadata['coordinates'] = self._parse_coordinates(coords_text)
            
            # Extract description if available
            desc_element = self._find_element(self.selectors['location_description'])
            if desc_element:
                metadata['description'] = desc_element.text.strip()
            else:
                metadata['description'] = ''
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting location metadata: {e}")
            return {
                'location_name': '',
                'address': '',
                'post_count': 0,
                'coordinates': None,
                'description': ''
            }
    
    def _collect_top_posts(self, max_posts: int) -> List[Dict[str, Any]]:
        """Collect top posts for location"""
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
        """Collect recent posts for location"""
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
            try:
                likes_element = post_element.find_element(By.CSS_SELECTOR, self.selectors['post_likes'])
                if likes_element:
                    post_data['likes'] = self._parse_count(likes_element.get_attribute('aria-label'))
            except NoSuchElementException:
                post_data['likes'] = 0

            try:
                comments_element = post_element.find_element(By.CSS_SELECTOR, self.selectors['post_comments'])
                if comments_element:
                    post_data['comments'] = self._parse_count(comments_element.get_attribute('aria-label'))
            except NoSuchElementException:
                post_data['comments'] = 0

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

    def _find_nearby_locations(self) -> List[Dict[str, Any]]:
        """Find nearby locations"""
        try:
            nearby_locations = []

            # Look for nearby locations section
            nearby_elements = self._find_elements(self.selectors['nearby_locations'])
            for element in nearby_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/explore/locations/' in href:
                        location_id = href.split('/explore/locations/')[-1].rstrip('/')
                        location_name = element.text.strip()

                        if location_id and location_name:
                            nearby_locations.append({
                                'location_id': location_id,
                                'location_name': location_name,
                                'url': href
                            })

                except StaleElementReferenceException:
                    continue

            # Look for related locations
            related_elements = self._find_elements(self.selectors['related_locations'])
            for element in related_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/explore/locations/' in href:
                        location_id = href.split('/explore/locations/')[-1].rstrip('/')
                        location_name = element.text.strip()

                        if location_id and location_name:
                            # Avoid duplicates
                            if not any(loc['location_id'] == location_id for loc in nearby_locations):
                                nearby_locations.append({
                                    'location_id': location_id,
                                    'location_name': location_name,
                                    'url': href
                                })

                except StaleElementReferenceException:
                    continue

            return nearby_locations[:15]  # Limit to top 15

        except Exception as e:
            logger.error(f"Error finding nearby locations: {e}")
            return []

    def _calculate_popularity_score(self, location_data: Dict[str, Any]) -> float:
        """Calculate popularity score based on various metrics"""
        try:
            score = 0.0

            # Base score from post count (normalized)
            post_count = location_data.get('post_count', 0)
            if post_count > 0:
                # Logarithmic scaling for post count
                score += min(60.0, 15 * (post_count / 100000))  # Max 60 points

            # Engagement score from top posts
            top_posts = location_data.get('top_posts', [])
            if top_posts:
                avg_engagement = sum(
                    (post.get('likes', 0) + post.get('comments', 0) * 5)
                    for post in top_posts
                ) / len(top_posts)
                score += min(25.0, avg_engagement / 5000)  # Max 25 points

            # Nearby locations bonus (indicates popular area)
            nearby_count = len(location_data.get('nearby_locations', []))
            score += min(15.0, nearby_count)  # Max 15 points

            return min(100.0, score)  # Cap at 100

        except Exception as e:
            logger.error(f"Error calculating popularity score: {e}")
            return 0.0

    def _parse_coordinates(self, coords_text: str) -> Optional[Dict[str, float]]:
        """Parse coordinates from text"""
        try:
            # Look for latitude, longitude pattern
            coord_match = re.search(r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)', coords_text)
            if coord_match:
                return {
                    'latitude': float(coord_match.group(1)),
                    'longitude': float(coord_match.group(2))
                }
            return None
        except Exception:
            return None

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

    def _find_elements(self, selector: str) -> List[Any]:
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

    def _save_location_data(self, location_id: str, location_data: Dict[str, Any]) -> bool:
        """Save location analysis data to database"""
        try:
            # This would integrate with the data manager
            # For now, we'll log the save operation
            logger.info(f"Saving location data for {location_id} with {len(location_data)} fields")
            return True
        except Exception as e:
            logger.error(f"Error saving location data: {e}")
            return False

    def get_popular_locations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular locations based on analysis"""
        try:
            # This would query the database for locations with high popularity scores
            # For now, return empty list as placeholder
            logger.info(f"Getting top {limit} popular locations")
            return []
        except Exception as e:
            logger.error(f"Error getting popular locations: {e}")
            return []

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get scraping performance statistics"""
        return {
            'locations_analyzed': self.scraping_stats['locations_analyzed'],
            'posts_collected': self.scraping_stats['posts_collected'],
            'related_locations_found': self.scraping_stats['related_locations_found'],
            'errors_encountered': self.scraping_stats['errors_encountered'],
            'average_analysis_time': self.scraping_stats['average_analysis_time'],
            'popular_locations_detected': self.scraping_stats['popular_locations_detected'],
            'success_rate': (
                (self.scraping_stats['locations_analyzed'] - self.scraping_stats['errors_encountered']) /
                max(1, self.scraping_stats['locations_analyzed'])
            ) * 100
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on scraper"""
        try:
            return {
                'status': 'healthy',
                'browser_connected': self.browser.driver is not None,
                'last_analysis': datetime.now(timezone.utc).isoformat(),
                'cache_size': len(self.location_cache),
                'analyzed_locations': len(self.analyzed_locations)
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
            logger.error(f"Error closing location scraper: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Context manager for location scraper
def create_location_scraper(browser: Optional[InstagramBrowser] = None) -> InstagramLocationScraper:
    """Create location scraper with context management"""
    return InstagramLocationScraper(browser)


# Convenience functions
def analyze_location_quick(location_id: str, max_posts: int = 30,
                          browser: Optional[InstagramBrowser] = None) -> Dict[str, Any]:
    """Convenience function to quickly analyze a location"""
    with create_location_scraper(browser) as scraper:
        return scraper.analyze_location(location_id, max_posts)


def search_locations_quick(location_name: str, max_results: int = 20,
                          browser: Optional[InstagramBrowser] = None) -> List[Dict[str, Any]]:
    """Convenience function to search locations by name"""
    with create_location_scraper(browser) as scraper:
        return scraper.search_locations_by_name(location_name, max_results)


def get_popular_locations_quick(limit: int = 20,
                               browser: Optional[InstagramBrowser] = None) -> List[Dict[str, Any]]:
    """Convenience function to get popular locations"""
    with create_location_scraper(browser) as scraper:
        return scraper.get_popular_locations(limit)
