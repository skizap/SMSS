"""
Social Media Surveillance System - Scraper Coordinator
Intelligent scheduling and coordination between different scraper types to avoid conflicts and optimize performance.
"""

import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from queue import PriorityQueue, Queue
from concurrent.futures import ThreadPoolExecutor, Future

from core.browser_engine import InstagramBrowser
from core.data_manager import data_manager
from core.error_handler import error_handler, ScrapingError

logger = logging.getLogger(__name__)

class ScraperType(Enum):
    """Types of scrapers in the system"""
    PROFILE = "profile"
    POSTS = "posts"
    STORIES = "stories"
    FOLLOWERS = "followers"
    HASHTAGS = "hashtags"
    LOCATIONS = "locations"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScrapingTask:
    """Represents a scraping task"""
    task_id: str
    scraper_type: ScraperType
    target: str  # username, hashtag, location_id, etc.
    priority: TaskPriority = TaskPriority.NORMAL
    max_items: int = 50
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

class ScraperCoordinator:
    """
    Intelligent coordinator for managing multiple scraper types with conflict avoidance,
    resource optimization, and intelligent scheduling.
    """
    
    def __init__(self, max_concurrent_tasks: int = 3, max_browser_instances: int = 2):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_browser_instances = max_browser_instances
        
        # Task management
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, ScrapingTask] = {}
        self.completed_tasks: Dict[str, ScrapingTask] = {}
        self.task_history: List[ScrapingTask] = []
        
        # Resource management
        self.browser_pool: List[InstagramBrowser] = []
        self.browser_locks: List[threading.Lock] = []
        self.available_browsers: Queue = Queue()
        
        # Coordination rules
        self.conflict_rules = self._initialize_conflict_rules()
        self.rate_limits = self._initialize_rate_limits()
        self.last_request_times: Dict[str, datetime] = {}
        
        # Execution management
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.running = False
        self.coordinator_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0,
            'conflicts_avoided': 0,
            'rate_limits_respected': 0
        }
        
        self._initialize_browser_pool()
    
    def _initialize_browser_pool(self):
        """Initialize browser pool for concurrent operations"""
        try:
            for i in range(self.max_browser_instances):
                browser = InstagramBrowser()
                self.browser_pool.append(browser)
                self.browser_locks.append(threading.Lock())
                self.available_browsers.put(i)
                
            logger.info(f"Initialized browser pool with {self.max_browser_instances} instances")
            
        except Exception as e:
            logger.error(f"Error initializing browser pool: {e}")
    
    def _initialize_conflict_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize conflict avoidance rules between scraper types"""
        return {
            # Profile scraping conflicts
            ScraperType.PROFILE.value: {
                'conflicts_with': [ScraperType.FOLLOWERS.value],
                'min_delay_after': 30,  # seconds
                'reason': 'Profile and follower scraping may trigger rate limits'
            },
            
            # Post scraping conflicts
            ScraperType.POSTS.value: {
                'conflicts_with': [ScraperType.STORIES.value],
                'min_delay_after': 15,
                'reason': 'Post and story scraping use similar navigation patterns'
            },
            
            # Follower tracking conflicts
            ScraperType.FOLLOWERS.value: {
                'conflicts_with': [ScraperType.PROFILE.value, ScraperType.POSTS.value],
                'min_delay_after': 60,
                'reason': 'Follower tracking is resource intensive'
            },
            
            # Hashtag analysis conflicts
            ScraperType.HASHTAGS.value: {
                'conflicts_with': [ScraperType.LOCATIONS.value],
                'min_delay_after': 20,
                'reason': 'Both use explore pages which may have shared rate limits'
            },
            
            # Location analysis conflicts
            ScraperType.LOCATIONS.value: {
                'conflicts_with': [ScraperType.HASHTAGS.value],
                'min_delay_after': 20,
                'reason': 'Both use explore pages which may have shared rate limits'
            }
        }
    
    def _initialize_rate_limits(self) -> Dict[str, Dict[str, Any]]:
        """Initialize rate limiting rules for each scraper type"""
        return {
            ScraperType.PROFILE.value: {
                'requests_per_minute': 10,
                'min_delay_between_requests': 6.0
            },
            ScraperType.POSTS.value: {
                'requests_per_minute': 15,
                'min_delay_between_requests': 4.0
            },
            ScraperType.STORIES.value: {
                'requests_per_minute': 8,
                'min_delay_between_requests': 7.5
            },
            ScraperType.FOLLOWERS.value: {
                'requests_per_minute': 5,
                'min_delay_between_requests': 12.0
            },
            ScraperType.HASHTAGS.value: {
                'requests_per_minute': 12,
                'min_delay_between_requests': 5.0
            },
            ScraperType.LOCATIONS.value: {
                'requests_per_minute': 12,
                'min_delay_between_requests': 5.0
            }
        }
    
    def add_task(self, scraper_type: ScraperType, target: str, 
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_items: int = 50, **parameters) -> str:
        """
        Add a new scraping task to the queue.
        
        Args:
            scraper_type: Type of scraper to use
            target: Target to scrape (username, hashtag, etc.)
            priority: Task priority
            max_items: Maximum items to scrape
            **parameters: Additional parameters for the scraper
            
        Returns:
            Task ID
        """
        task_id = f"{scraper_type.value}_{target}_{int(time.time())}"
        
        task = ScrapingTask(
            task_id=task_id,
            scraper_type=scraper_type,
            target=target,
            priority=priority,
            max_items=max_items,
            parameters=parameters
        )
        
        # Schedule task based on conflicts and rate limits
        scheduled_time = self._calculate_optimal_schedule_time(task)
        task.scheduled_at = scheduled_time
        
        self.task_queue.put(task)
        logger.info(f"Added task {task_id} scheduled for {scheduled_time}")
        
        return task_id
    
    def _calculate_optimal_schedule_time(self, task: ScrapingTask) -> datetime:
        """Calculate optimal scheduling time to avoid conflicts"""
        now = datetime.now(timezone.utc)
        earliest_time = now
        
        # Check conflict rules
        scraper_type = task.scraper_type.value
        if scraper_type in self.conflict_rules:
            rule = self.conflict_rules[scraper_type]
            conflicting_types = rule['conflicts_with']
            min_delay = rule['min_delay_after']
            
            # Find latest completion time of conflicting tasks
            for completed_task in self.task_history[-50:]:  # Check recent tasks
                if (completed_task.scraper_type.value in conflicting_types and
                    completed_task.completed_at):
                    
                    conflict_end_time = completed_task.completed_at + timedelta(seconds=min_delay)
                    if conflict_end_time > earliest_time:
                        earliest_time = conflict_end_time
                        self.stats['conflicts_avoided'] += 1
        
        # Check rate limits
        if scraper_type in self.rate_limits:
            rate_limit = self.rate_limits[scraper_type]
            min_delay = rate_limit['min_delay_between_requests']
            
            last_request_key = f"{scraper_type}_{task.target}"
            if last_request_key in self.last_request_times:
                last_time = self.last_request_times[last_request_key]
                next_allowed_time = last_time + timedelta(seconds=min_delay)
                
                if next_allowed_time > earliest_time:
                    earliest_time = next_allowed_time
                    self.stats['rate_limits_respected'] += 1
        
        return earliest_time
    
    def start(self):
        """Start the coordinator"""
        if self.running:
            logger.warning("Coordinator is already running")
            return
        
        self.running = True
        self.coordinator_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        self.coordinator_thread.start()
        logger.info("Scraper coordinator started")
    
    def stop(self):
        """Stop the coordinator"""
        self.running = False
        if self.coordinator_thread:
            self.coordinator_thread.join(timeout=10)
        
        # Cancel pending tasks
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                task.status = TaskStatus.CANCELLED
                self.completed_tasks[task.task_id] = task
            except:
                break
        
        # Cleanup browser pool
        for browser in self.browser_pool:
            try:
                browser.close()
            except:
                pass
        
        self.executor.shutdown(wait=True)
        logger.info("Scraper coordinator stopped")
    
    def _coordination_loop(self):
        """Main coordination loop"""
        while self.running:
            try:
                # Check for tasks ready to execute
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    
                    # Check if it's time to execute
                    now = datetime.now(timezone.utc)
                    if task.scheduled_at and task.scheduled_at > now:
                        # Put back in queue and wait
                        self.task_queue.put(task)
                        time.sleep(1)
                        continue
                    
                    # Check if we have capacity
                    if len(self.active_tasks) < self.max_concurrent_tasks:
                        self._execute_task(task)
                    else:
                        # Put back in queue
                        self.task_queue.put(task)
                
                time.sleep(0.5)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                time.sleep(1)
    
    def _execute_task(self, task: ScrapingTask):
        """Execute a scraping task"""
        try:
            # Get available browser
            browser_index = self.available_browsers.get(timeout=30)
            browser = self.browser_pool[browser_index]
            
            # Mark task as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            self.active_tasks[task.task_id] = task
            
            # Submit task to executor
            future = self.executor.submit(self._run_scraper_task, task, browser, browser_index)
            
            # Handle completion asynchronously
            future.add_done_callback(lambda f: self._handle_task_completion(task, f))
            
            logger.info(f"Started executing task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._complete_task(task)
    
    def _run_scraper_task(self, task: ScrapingTask, browser: InstagramBrowser, browser_index: int) -> Dict[str, Any]:
        """Run the actual scraper task"""
        try:
            # Import scrapers dynamically to avoid circular imports
            scraper_type = task.scraper_type
            
            if scraper_type == ScraperType.PROFILE:
                from scrapers.instagram_profile_scraper import scrape_single_profile
                result = scrape_single_profile(task.target, browser)
                
            elif scraper_type == ScraperType.POSTS:
                from scrapers.instagram_post_scraper import scrape_user_posts_quick
                result = scrape_user_posts_quick(task.target, task.max_items, browser)
                
            elif scraper_type == ScraperType.STORIES:
                from scrapers.instagram_story_scraper import scrape_user_stories_quick
                result = scrape_user_stories_quick(task.target, browser)
                
            elif scraper_type == ScraperType.FOLLOWERS:
                from scrapers.follower_tracker import track_followers_quick
                result = track_followers_quick(task.target, task.max_items, browser)
                
            elif scraper_type == ScraperType.HASHTAGS:
                from scrapers.instagram_hashtag_scraper import analyze_hashtag_quick
                result = analyze_hashtag_quick(task.target, task.max_items, browser)
                
            elif scraper_type == ScraperType.LOCATIONS:
                from scrapers.instagram_location_scraper import analyze_location_quick
                result = analyze_location_quick(task.target, task.max_items, browser)
                
            else:
                raise ScrapingError(f"Unknown scraper type: {scraper_type}")
            
            # Update last request time for rate limiting
            rate_limit_key = f"{scraper_type.value}_{task.target}"
            self.last_request_times[rate_limit_key] = datetime.now(timezone.utc)
            
            return result
            
        finally:
            # Return browser to pool
            self.available_browsers.put(browser_index)
    
    def _handle_task_completion(self, task: ScrapingTask, future: Future):
        """Handle task completion"""
        try:
            result = future.result()
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.stats['tasks_completed'] += 1
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            self.stats['tasks_failed'] += 1
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=30 * task.retry_count)
                self.task_queue.put(task)
                logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
                return
        
        self._complete_task(task)
    
    def _complete_task(self, task: ScrapingTask):
        """Complete a task and update statistics"""
        task.completed_at = datetime.now(timezone.utc)
        
        if task.started_at:
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.stats['total_execution_time'] += execution_time
        
        # Move from active to completed
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        self.completed_tasks[task.task_id] = task
        self.task_history.append(task)
        
        # Keep history manageable
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-500:]
        
        logger.info(f"Completed task {task.task_id} with status {task.status.value}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
        else:
            return None
        
        return {
            'task_id': task.task_id,
            'scraper_type': task.scraper_type.value,
            'target': task.target,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'retry_count': task.retry_count,
            'error': task.error,
            'result_summary': self._summarize_result(task.result) if task.result else None
        }
    
    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of task result"""
        if not result:
            return {}
        
        summary = {'status': result.get('status', 'unknown')}
        
        # Add type-specific summaries
        if 'posts_scraped' in result:
            summary['posts_scraped'] = len(result.get('posts_scraped', []))
        if 'new_followers' in result:
            summary['new_followers'] = len(result.get('new_followers', []))
        if 'post_count' in result:
            summary['post_count'] = result.get('post_count', 0)
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            **self.stats,
            'active_tasks': len(self.active_tasks),
            'pending_tasks': self.task_queue.qsize(),
            'completed_tasks': len(self.completed_tasks),
            'available_browsers': self.available_browsers.qsize(),
            'average_execution_time': (
                self.stats['total_execution_time'] / max(1, self.stats['tasks_completed'])
            )
        }


# Global coordinator instance
coordinator = ScraperCoordinator()
