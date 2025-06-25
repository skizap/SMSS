"""
Social Media Surveillance System - Browser Engine
Advanced Chromium automation with stealth capabilities for Instagram surveillance.
"""

import os
import time
import random
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from fake_useragent import UserAgent

from .config import config
from .credentials_manager import get_credentials_manager

logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    """Browser session data"""
    cookies: List[Dict[str, Any]]
    local_storage: Dict[str, str]
    session_storage: Dict[str, str]
    user_agent: str
    window_size: Tuple[int, int]
    created_at: float
    last_used: float

class AntiDetectionManager:
    """Manages anti-detection measures"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.viewport_sizes = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1024, 768)
        ]
        
    def get_random_user_agent(self) -> str:
        """Get random user agent string"""
        return self.ua.random
        
    def get_random_viewport(self) -> Tuple[int, int]:
        """Get random viewport size"""
        return random.choice(self.viewport_sizes)
        
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def human_like_typing(self, element, text: str):
        """Type text with human-like delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

class SessionManager:
    """Manages browser sessions and persistence"""
    
    def __init__(self, session_dir: str = "data/sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[SessionData] = None
        
    def save_session(self, driver: webdriver.Chrome, session_name: str = "default"):
        """Save current browser session"""
        try:
            session_file = self.session_dir / f"{session_name}.json"
            
            # Get session data
            cookies = driver.get_cookies()
            
            # Get local storage
            local_storage = {}
            try:
                local_storage = driver.execute_script("return window.localStorage;")
            except Exception:
                pass
                
            # Get session storage
            session_storage = {}
            try:
                session_storage = driver.execute_script("return window.sessionStorage;")
            except Exception:
                pass
                
            session_data = SessionData(
                cookies=cookies,
                local_storage=local_storage or {},
                session_storage=session_storage or {},
                user_agent=driver.execute_script("return navigator.userAgent;"),
                window_size=driver.get_window_size(),
                created_at=time.time(),
                last_used=time.time()
            )
            
            # Save to file
            with open(session_file, 'w') as f:
                json.dump({
                    'cookies': session_data.cookies,
                    'local_storage': session_data.local_storage,
                    'session_storage': session_data.session_storage,
                    'user_agent': session_data.user_agent,
                    'window_size': [session_data.window_size['width'], session_data.window_size['height']],
                    'created_at': session_data.created_at,
                    'last_used': session_data.last_used
                }, f, indent=2)
                
            self.current_session = session_data
            logger.info(f"Session saved: {session_name}")
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            
    def load_session(self, driver: webdriver.Chrome, session_name: str = "default") -> bool:
        """Load browser session"""
        try:
            session_file = self.session_dir / f"{session_name}.json"
            
            if not session_file.exists():
                logger.info(f"Session file not found: {session_name}")
                return False
                
            with open(session_file, 'r') as f:
                data = json.load(f)
                
            # Navigate to Instagram first
            driver.get("https://www.instagram.com")
            time.sleep(2)
            
            # Load cookies
            for cookie in data['cookies']:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not add cookie: {e}")
                    
            # Load local storage
            for key, value in data['local_storage'].items():
                try:
                    driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")
                except Exception:
                    pass
                    
            # Load session storage
            for key, value in data['session_storage'].items():
                try:
                    driver.execute_script(f"window.sessionStorage.setItem('{key}', '{value}');")
                except Exception:
                    pass
                    
            # Set window size
            if 'window_size' in data:
                width, height = data['window_size']
                driver.set_window_size(width, height)
                
            # Update last used time
            data['last_used'] = time.time()
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Session loaded: {session_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False

class InstagramBrowser:
    """Main browser automation class for Instagram surveillance"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.actions: Optional[ActionChains] = None
        
        self.anti_detection = AntiDetectionManager()
        self.session_manager = SessionManager()
        
        self.is_logged_in = False
        self.current_user = None
        
        # Instagram selectors (may need updates as Instagram changes)
        self.selectors = {
            'username_input': 'input[name="username"]',
            'password_input': 'input[name="password"]',
            'login_button': 'button[type="submit"]',
            'not_now_button': 'button:contains("Not Now")',
            'profile_link': 'a[href*="/{}/"]:first',
            'followers_link': 'a[href*="/followers/"]',
            'following_link': 'a[href*="/following/"]',
            'posts_container': 'article',
            'story_container': '[data-testid="story-viewer"]'
        }
        
    def setup_driver(self) -> bool:
        """Setup Chrome driver with stealth configuration"""
        try:
            # Try different Chrome versions to find compatible one
            chrome_versions = [None, 137, 136, 135, 134]  # None = auto-detect, then try specific versions

            for version in chrome_versions:
                try:
                    logger.info(f"Attempting to setup Chrome driver with version: {version or 'auto-detect'}")

                    # Create Chrome options for better compatibility
                    options = uc.ChromeOptions()
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--disable-extensions")
                    options.add_argument("--disable-plugins")
                    options.add_argument("--disable-images")
                    options.add_argument("--disable-javascript")

                    if config.browser.headless:
                        options.add_argument("--headless=new")

                    # Create driver with specific version
                    self.driver = uc.Chrome(
                        options=options,
                        headless=config.browser.headless,
                        use_subprocess=False,
                        version_main=version
                    )

                    # If we get here, the driver was created successfully
                    break

                except Exception as version_error:
                    logger.warning(f"Chrome version {version} failed: {version_error}")
                    if version == chrome_versions[-1]:  # Last version attempt
                        raise version_error
                    continue

            # Additional stealth measures
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Setup WebDriverWait and ActionChains
            self.wait = WebDriverWait(self.driver, config.browser.timeout)
            self.actions = ActionChains(self.driver)

            # Set timeouts
            self.driver.set_page_load_timeout(config.browser.page_load_timeout)
            self.driver.implicitly_wait(config.browser.implicit_wait)

            # Set window size
            width, height = config.browser.window_size
            self.driver.set_window_size(width, height)

            logger.info("Browser driver setup completed")
            return True

        except Exception as e:
            logger.error(f"Error setting up browser driver: {e}")
            return False

    def login(self, username: str, password: str, save_session: bool = True) -> bool:
        """Login to Instagram with stealth measures"""
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False

            # Try to load existing session first
            if self.session_manager.load_session(self.driver):
                # Check if already logged in
                self.driver.refresh()
                time.sleep(3)

                if self._check_login_status():
                    logger.info("Already logged in from saved session")
                    self.is_logged_in = True
                    self.current_user = username
                    return True

            # Navigate to login page
            logger.info("Navigating to Instagram login page")
            self.driver.get(config.instagram.login_url)

            # Random delay
            self.anti_detection.random_delay(2, 4)

            # Wait for login form
            username_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['username_input']))
            )

            # Human-like typing for username
            self.anti_detection.human_like_typing(username_input, username)

            # Random delay
            self.anti_detection.random_delay(1, 2)

            # Enter password
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['password_input'])
            self.anti_detection.human_like_typing(password_input, password)

            # Random delay before clicking login
            self.anti_detection.random_delay(1, 3)

            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['login_button'])
            self.actions.move_to_element(login_button).click().perform()

            # Wait for login to complete
            time.sleep(5)

            # Handle potential 2FA or suspicious login warnings
            self._handle_login_challenges()

            # Check if login was successful
            if self._check_login_status():
                logger.info("Login successful")
                self.is_logged_in = True
                self.current_user = username

                # Save session if requested
                if save_session:
                    self.session_manager.save_session(self.driver, username)

                return True
            else:
                logger.error("Login failed")
                return False

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False

    def _check_login_status(self) -> bool:
        """Check if currently logged in to Instagram"""
        try:
            # Look for elements that indicate logged-in state
            current_url = self.driver.current_url

            # If redirected to login page, not logged in
            if "accounts/login" in current_url:
                return False

            # Look for navigation elements that appear when logged in
            try:
                self.driver.find_element(By.CSS_SELECTOR, 'svg[aria-label="Home"]')
                return True
            except NoSuchElementException:
                pass

            # Alternative check - look for profile link in navigation
            try:
                self.driver.find_element(By.CSS_SELECTOR, 'a[href*="/accounts/edit/"]')
                return True
            except NoSuchElementException:
                pass

            return False

        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    def _handle_login_challenges(self):
        """Handle 2FA, suspicious login warnings, etc."""
        try:
            # Wait a bit for any challenges to appear
            time.sleep(3)

            # Check for "Not Now" buttons (save login info, notifications, etc.)
            not_now_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Not Now')]")
            for button in not_now_buttons:
                try:
                    if button.is_displayed():
                        self.actions.move_to_element(button).click().perform()
                        time.sleep(2)
                except Exception:
                    pass

            # Handle suspicious login warning
            try:
                suspicious_login = self.driver.find_element(By.XPATH, "//button[contains(text(), 'This Was Me')]")
                if suspicious_login.is_displayed():
                    logger.info("Handling suspicious login warning")
                    self.actions.move_to_element(suspicious_login).click().perform()
                    time.sleep(3)
            except NoSuchElementException:
                pass

            # TODO: Add 2FA handling if needed
            # This would require additional user input or SMS/email integration

        except Exception as e:
            logger.warning(f"Error handling login challenges: {e}")

    def auto_login(self) -> bool:
        """Automatically login using stored credentials"""
        try:
            credentials_manager = get_credentials_manager()
            creds = credentials_manager.get_instagram_credentials()

            if not creds:
                logger.error("No Instagram credentials found. Please configure credentials first.")
                return False

            logger.info("Attempting auto-login with stored credentials")
            return self.login(creds['username'], creds['password'])

        except Exception as e:
            logger.error(f"Error during auto-login: {e}")
            return False

    def navigate_to_profile(self, username: str) -> bool:
        """Navigate to a specific Instagram profile"""
        try:
            if not self.is_logged_in:
                logger.error("Must be logged in to navigate to profiles")
                return False

            profile_url = f"{config.instagram.base_url}{username}/"
            logger.info(f"Navigating to profile: {profile_url}")

            self.driver.get(profile_url)

            # Random delay
            self.anti_detection.random_delay(2, 4)

            # Check if profile exists and is accessible
            try:
                # Look for profile header
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'header'))
                )

                # Check for private account message
                private_account = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'This account is private')]")
                if private_account:
                    logger.warning(f"Profile {username} is private")
                    return True  # Still navigated successfully, just private

                # Check for user not found
                not_found = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Sorry, this page')]")
                if not_found:
                    logger.error(f"Profile {username} not found")
                    return False

                logger.info(f"Successfully navigated to profile: {username}")
                return True

            except TimeoutException:
                logger.error(f"Timeout waiting for profile page to load: {username}")
                return False

        except Exception as e:
            logger.error(f"Error navigating to profile {username}: {e}")
            return False

    def scroll_page(self, scrolls: int = 3, pause_time: Optional[float] = None) -> bool:
        """Scroll page with human-like behavior"""
        try:
            if pause_time is None:
                pause_time = config.instagram.scroll_pause_time

            for i in range(scrolls):
                # Random scroll distance
                scroll_distance = random.randint(300, 800)

                # Scroll down
                self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")

                # Random pause
                pause = random.uniform(pause_time * 0.5, pause_time * 1.5)
                time.sleep(pause)

            return True

        except Exception as e:
            logger.error(f"Error scrolling page: {e}")
            return False

    def take_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """Take screenshot of current page"""
        try:
            if not filename:
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"

            screenshot_path = config.get_data_dir() / "screenshots" / filename
            screenshot_path.parent.mkdir(exist_ok=True)

            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")

            return str(screenshot_path)

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None

    def close(self):
        """Close browser and cleanup"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False  # Don't suppress exceptions

    @contextmanager
    def temporary_window(self):
        """Context manager for temporary browser window"""
        original_window = self.driver.current_window_handle
        self.driver.execute_script("window.open('');")
        new_window = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_window)

        try:
            yield
        finally:
            self.driver.close()
            self.driver.switch_to.window(original_window)
