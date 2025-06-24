#!/usr/bin/env python3
"""
Social Media Surveillance System - Real-time Updates
Real-time data update system using QThread for background processing,
signal-slot connections for UI updates, and automatic refresh mechanisms.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import (
    QThread, QTimer, pyqtSignal, QObject, QMutex, QMutexLocker
)

# Import project modules
from core.data_manager import DataManager
from models.instagram_models import SurveillanceTarget, Post, Follower
from ui.notification_system import Notification, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class UpdateType(Enum):
    """Types of real-time updates"""
    TARGET_STATS = "target_stats"
    NEW_POST = "new_post"
    NEW_FOLLOWER = "new_follower"
    FOLLOWER_LOST = "follower_lost"
    NEW_STORY = "new_story"
    BIO_CHANGE = "bio_change"
    PROFILE_CHANGE = "profile_change"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"

@dataclass
class UpdateData:
    """Data structure for real-time updates"""
    update_type: UpdateType
    target_id: Optional[int]
    data: Dict[str, Any]
    timestamp: datetime
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=critical

class RealTimeDataCollector(QThread):
    """Background thread for collecting real-time data updates"""
    
    update_available = pyqtSignal(UpdateData)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.is_running = False
        self.update_interval = 30  # seconds
        self.last_check_times = {}  # target_id -> last_check_time
        self.mutex = QMutex()
        
    def run(self):
        """Main data collection loop"""
        self.is_running = True
        self.status_changed.emit("Real-time data collector started")
        
        while self.is_running:
            try:
                self.collect_updates()
                self.msleep(self.update_interval * 1000)
                
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}")
                self.error_occurred.emit(str(e))
                self.msleep(10000)  # Wait 10 seconds before retry
                
        self.status_changed.emit("Real-time data collector stopped")
        
    def stop(self):
        """Stop the data collector"""
        self.is_running = False
        
    def set_update_interval(self, seconds: int):
        """Set the update interval"""
        with QMutexLocker(self.mutex):
            self.update_interval = max(10, seconds)  # Minimum 10 seconds
            
    def collect_updates(self):
        """Collect updates from all active targets"""
        try:
            # Get active targets
            targets = self.data_manager.get_active_targets()
            
            for target in targets:
                self.check_target_updates(target)
                
            # Check system status
            self.check_system_status()
            
        except Exception as e:
            logger.error(f"Error collecting updates: {e}")
            self.error_occurred.emit(f"Data collection error: {str(e)}")
            
    def check_target_updates(self, target):
        """Check for updates for a specific target"""
        try:
            target_id = target.id
            current_time = datetime.now()
            last_check = self.last_check_times.get(target_id, current_time - timedelta(hours=1))
            
            # Check for new posts
            new_posts = self.data_manager.get_posts_since(target_id, last_check)
            for post in new_posts:
                update_data = UpdateData(
                    update_type=UpdateType.NEW_POST,
                    target_id=target_id,
                    data={
                        'post_id': post.id,
                        'instagram_post_id': post.instagram_post_id,
                        'post_type': post.post_type,
                        'caption': post.caption[:100] + '...' if len(post.caption or '') > 100 else post.caption,
                        'like_count': post.like_count,
                        'target_username': target.instagram_username
                    },
                    timestamp=current_time,
                    priority=2
                )
                self.update_available.emit(update_data)
                
            # Check for follower changes
            self.check_follower_changes(target, last_check, current_time)
            
            # Check for profile changes
            self.check_profile_changes(target, last_check, current_time)
            
            # Update last check time
            self.last_check_times[target_id] = current_time
            
        except Exception as e:
            logger.error(f"Error checking target {target.id} updates: {e}")
            
    def check_follower_changes(self, target, last_check: datetime, current_time: datetime):
        """Check for follower changes"""
        try:
            # Get recent follower changes
            new_followers = self.data_manager.get_new_followers_since(target.id, last_check)
            lost_followers = self.data_manager.get_lost_followers_since(target.id, last_check)
            
            # Emit new follower updates
            for follower in new_followers:
                update_data = UpdateData(
                    update_type=UpdateType.NEW_FOLLOWER,
                    target_id=target.id,
                    data={
                        'follower_username': follower.follower_username,
                        'follower_display_name': follower.follower_display_name,
                        'is_verified': follower.is_verified,
                        'target_username': target.instagram_username
                    },
                    timestamp=current_time,
                    priority=1
                )
                self.update_available.emit(update_data)
                
            # Emit lost follower updates
            for follower in lost_followers:
                update_data = UpdateData(
                    update_type=UpdateType.FOLLOWER_LOST,
                    target_id=target.id,
                    data={
                        'follower_username': follower.follower_username,
                        'target_username': target.instagram_username
                    },
                    timestamp=current_time,
                    priority=1
                )
                self.update_available.emit(update_data)
                
        except Exception as e:
            logger.error(f"Error checking follower changes for target {target.id}: {e}")
            
    def check_profile_changes(self, target, last_check: datetime, current_time: datetime):
        """Check for profile changes"""
        try:
            # Get profile change history
            changes = self.data_manager.get_profile_changes_since(target.id, last_check)
            
            for change in changes:
                update_data = UpdateData(
                    update_type=UpdateType.PROFILE_CHANGE,
                    target_id=target.id,
                    data={
                        'change_type': change.change_type,
                        'old_value': change.old_value,
                        'new_value': change.new_value,
                        'target_username': target.instagram_username
                    },
                    timestamp=current_time,
                    priority=2
                )
                self.update_available.emit(update_data)
                
        except Exception as e:
            logger.error(f"Error checking profile changes for target {target.id}: {e}")
            
    def check_system_status(self):
        """Check system status and emit updates"""
        try:
            # Check database connection
            db_status = self.data_manager.check_connection()
            
            # Check memory usage
            import psutil
            memory_usage = psutil.virtual_memory().percent
            
            # Emit system status update
            update_data = UpdateData(
                update_type=UpdateType.SYSTEM_STATUS,
                target_id=None,
                data={
                    'database_status': 'connected' if db_status else 'disconnected',
                    'memory_usage': memory_usage,
                    'active_targets': len(self.data_manager.get_active_targets())
                },
                timestamp=datetime.now(),
                priority=1
            )
            self.update_available.emit(update_data)
            
        except Exception as e:
            logger.error(f"Error checking system status: {e}")

class RealTimeUpdateManager(QObject):
    """Manager for coordinating real-time updates across the UI"""
    
    # Signals for different types of updates
    target_stats_updated = pyqtSignal(int, dict)  # target_id, stats
    new_post_detected = pyqtSignal(dict)  # post_data
    new_follower_detected = pyqtSignal(dict)  # follower_data
    follower_lost_detected = pyqtSignal(dict)  # follower_data
    profile_changed = pyqtSignal(dict)  # change_data
    system_status_updated = pyqtSignal(dict)  # status_data
    notification_requested = pyqtSignal(Notification)  # notification
    
    def __init__(self):
        super().__init__()
        self.data_collector = RealTimeDataCollector()
        self.subscribers = {}  # update_type -> list of callbacks
        self.notification_rules = self.load_notification_rules()
        
        # Connect signals
        self.data_collector.update_available.connect(self.handle_update)
        self.data_collector.error_occurred.connect(self.handle_error)
        self.data_collector.status_changed.connect(self.handle_status_change)
        
    def start(self):
        """Start real-time updates"""
        if not self.data_collector.isRunning():
            self.data_collector.start()
            logger.info("Real-time update manager started")
            
    def stop(self):
        """Stop real-time updates"""
        if self.data_collector.isRunning():
            self.data_collector.stop()
            self.data_collector.wait(5000)  # Wait up to 5 seconds
            if self.data_collector.isRunning():
                self.data_collector.terminate()
            logger.info("Real-time update manager stopped")
            
    def set_update_interval(self, seconds: int):
        """Set the update interval"""
        self.data_collector.set_update_interval(seconds)
        
    def subscribe(self, update_type: UpdateType, callback: Callable):
        """Subscribe to specific update types"""
        if update_type not in self.subscribers:
            self.subscribers[update_type] = []
        self.subscribers[update_type].append(callback)
        
    def unsubscribe(self, update_type: UpdateType, callback: Callable):
        """Unsubscribe from specific update types"""
        if update_type in self.subscribers:
            try:
                self.subscribers[update_type].remove(callback)
            except ValueError:
                pass
                
    def handle_update(self, update_data: UpdateData):
        """Handle incoming update data"""
        try:
            # Emit appropriate signal based on update type
            if update_data.update_type == UpdateType.NEW_POST:
                self.new_post_detected.emit(update_data.data)
                self.create_notification_for_update(update_data)
                
            elif update_data.update_type == UpdateType.NEW_FOLLOWER:
                self.new_follower_detected.emit(update_data.data)
                self.create_notification_for_update(update_data)
                
            elif update_data.update_type == UpdateType.FOLLOWER_LOST:
                self.follower_lost_detected.emit(update_data.data)
                self.create_notification_for_update(update_data)
                
            elif update_data.update_type == UpdateType.PROFILE_CHANGE:
                self.profile_changed.emit(update_data.data)
                self.create_notification_for_update(update_data)
                
            elif update_data.update_type == UpdateType.SYSTEM_STATUS:
                self.system_status_updated.emit(update_data.data)
                
            # Call subscribers
            if update_data.update_type in self.subscribers:
                for callback in self.subscribers[update_data.update_type]:
                    try:
                        callback(update_data)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling update: {e}")
            
    def create_notification_for_update(self, update_data: UpdateData):
        """Create notification for update based on rules"""
        try:
            if not self.should_notify(update_data):
                return
                
            # Create notification based on update type
            if update_data.update_type == UpdateType.NEW_POST:
                notification = Notification(
                    title="New Post Detected",
                    message=f"@{update_data.data['target_username']} posted: {update_data.data.get('caption', 'No caption')}",
                    notification_type=NotificationType.INFO,
                    priority=NotificationPriority.MEDIUM,
                    target_id=update_data.target_id,
                    data=update_data.data
                )
                
            elif update_data.update_type == UpdateType.NEW_FOLLOWER:
                notification = Notification(
                    title="New Follower",
                    message=f"@{update_data.data['target_username']} gained a new follower: @{update_data.data['follower_username']}",
                    notification_type=NotificationType.SUCCESS,
                    priority=NotificationPriority.LOW,
                    target_id=update_data.target_id,
                    data=update_data.data
                )
                
            elif update_data.update_type == UpdateType.FOLLOWER_LOST:
                notification = Notification(
                    title="Follower Lost",
                    message=f"@{update_data.data['target_username']} lost a follower: @{update_data.data['follower_username']}",
                    notification_type=NotificationType.WARNING,
                    priority=NotificationPriority.LOW,
                    target_id=update_data.target_id,
                    data=update_data.data
                )
                
            elif update_data.update_type == UpdateType.PROFILE_CHANGE:
                notification = Notification(
                    title="Profile Changed",
                    message=f"@{update_data.data['target_username']} changed {update_data.data['change_type']}",
                    notification_type=NotificationType.INFO,
                    priority=NotificationPriority.MEDIUM,
                    target_id=update_data.target_id,
                    data=update_data.data
                )
                
            else:
                return
                
            self.notification_requested.emit(notification)
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            
    def should_notify(self, update_data: UpdateData) -> bool:
        """Check if notification should be sent based on rules"""
        # This would check against user-defined notification rules
        # For now, return True for all updates
        return True
        
    def load_notification_rules(self) -> dict:
        """Load notification rules from settings"""
        # This would load from settings/database
        return {
            'notify_new_posts': True,
            'notify_new_followers': True,
            'notify_follower_loss': True,
            'notify_profile_changes': True
        }
        
    def handle_error(self, error_message: str):
        """Handle errors from data collector"""
        logger.error(f"Real-time update error: {error_message}")
        
        # Create error notification
        notification = Notification(
            title="System Error",
            message=f"Real-time update error: {error_message}",
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.HIGH
        )
        self.notification_requested.emit(notification)
        
    def handle_status_change(self, status_message: str):
        """Handle status changes from data collector"""
        logger.info(f"Real-time update status: {status_message}")

# Global instance
_update_manager = None

def get_update_manager() -> RealTimeUpdateManager:
    """Get the global update manager instance"""
    global _update_manager
    if _update_manager is None:
        _update_manager = RealTimeUpdateManager()
    return _update_manager
