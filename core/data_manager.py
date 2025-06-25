"""
Social Media Surveillance System - Data Manager
High-level data operations, change detection, and efficient data persistence.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, desc, func

from .database import db_manager, version_manager
from models.instagram_models import (
    SurveillanceTarget, Post, Follower, Story, ChangeLog,
    create_surveillance_target, create_post, create_follower, 
    create_story, create_change_log
)

logger = logging.getLogger(__name__)

class DataManager:
    """High-level data management operations"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.version_manager = version_manager
        
    # Surveillance Target Operations
    def add_surveillance_target(self, username: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Add a new surveillance target and return as dictionary to avoid session binding issues"""
        try:
            with self.db_manager.get_session() as session:
                # Check if target already exists
                existing = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == username.lower()
                ).first()

                if existing:
                    logger.warning(f"Target {username} already exists")
                    return self._target_to_dict(existing)

                # Create new target
                target = create_surveillance_target(username, **kwargs)
                session.add(target)
                session.flush()  # Get the ID

                # Log the addition
                version_manager.track_change(
                    target.id, 'target_added', None, username, session
                )

                # Convert to dict before returning to avoid session binding issues
                target_dict = self._target_to_dict(target)

                logger.info(f"Added surveillance target: {username}")
                return target_dict

        except Exception as e:
            logger.error(f"Error adding surveillance target {username}: {e}")
            return None
    
    def update_surveillance_target(self, target_id: int, **updates) -> bool:
        """Update surveillance target with change tracking"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.id == target_id
                ).first()
                
                if not target:
                    logger.error(f"Target {target_id} not found")
                    return False
                
                # Track changes
                for field, new_value in updates.items():
                    if hasattr(target, field):
                        old_value = getattr(target, field)
                        if old_value != new_value:
                            # Track the change
                            change_type = f"{field}_changed"
                            version_manager.track_change(
                                target_id, change_type, old_value, new_value, session
                            )
                            
                            # Update the field
                            setattr(target, field, new_value)
                
                target.last_updated = datetime.now(timezone.utc)
                logger.info(f"Updated surveillance target: {target.instagram_username}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating surveillance target {target_id}: {e}")
            return False
    
    def get_surveillance_target(self, username: str) -> Optional[SurveillanceTarget]:
        """Get surveillance target by username"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == username.lower()
                ).first()
        except Exception as e:
            logger.error(f"Error getting surveillance target {username}: {e}")
            return None
    
    def get_all_surveillance_targets(self, status: Optional[str] = None) -> List[SurveillanceTarget]:
        """Get all surveillance targets, optionally filtered by status"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(SurveillanceTarget)
                if status:
                    query = query.filter(SurveillanceTarget.status == status)
                return query.order_by(SurveillanceTarget.instagram_username).all()
        except Exception as e:
            logger.error(f"Error getting surveillance targets: {e}")
            return []
    
    # Post Operations
    def add_post(self, target_username: str, instagram_post_id: str, 
                post_type: str, **kwargs) -> Optional[Post]:
        """Add a new post with duplicate detection"""
        try:
            with self.db_manager.get_session() as session:
                # Get target
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()
                
                if not target:
                    logger.error(f"Target {target_username} not found")
                    return None
                
                # Check for duplicate
                existing = session.query(Post).filter(
                    Post.instagram_post_id == instagram_post_id
                ).first()
                
                if existing:
                    logger.debug(f"Post {instagram_post_id} already exists")
                    return existing
                
                # Create new post
                post = create_post(target.id, instagram_post_id, post_type, **kwargs)
                session.add(post)
                session.flush()
                
                # Track the change
                version_manager.track_change(
                    target.id, 'new_post', None, {
                        'post_id': instagram_post_id,
                        'post_type': post_type,
                        'caption': kwargs.get('caption', '')[:100] + '...' if kwargs.get('caption', '') else ''
                    }, session
                )
                
                # Update target post count
                target.post_count = session.query(Post).filter(
                    Post.target_id == target.id
                ).count()
                
                logger.info(f"Added post {instagram_post_id} for {target_username}")
                return post
                
        except IntegrityError:
            logger.debug(f"Post {instagram_post_id} already exists (integrity constraint)")
            return None
        except Exception as e:
            logger.error(f"Error adding post {instagram_post_id}: {e}")
            return None
    
    def get_posts(self, target_username: str, limit: int = 50, 
                 post_type: Optional[str] = None) -> List[Post]:
        """Get posts for a target"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()
                
                if not target:
                    return []
                
                query = session.query(Post).filter(Post.target_id == target.id)
                if post_type:
                    query = query.filter(Post.post_type == post_type)
                
                return query.order_by(desc(Post.posted_at)).limit(limit).all()
                
        except Exception as e:
            logger.error(f"Error getting posts for {target_username}: {e}")
            return []
    
    def get_recent_posts(self, hours: int = 24) -> List[Post]:
        """Get recent posts across all targets"""
        try:
            with self.db_manager.get_session() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                return session.query(Post).filter(
                    Post.posted_at >= cutoff_time
                ).order_by(desc(Post.posted_at)).all()
        except Exception as e:
            logger.error(f"Error getting recent posts: {e}")
            return []
    
    # Follower Operations
    def add_follower(self, target_username: str, follower_username: str, 
                    **kwargs) -> Optional[Follower]:
        """Add a new follower with duplicate detection"""
        try:
            with self.db_manager.get_session() as session:
                # Get target
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()
                
                if not target:
                    logger.error(f"Target {target_username} not found")
                    return None
                
                # Check for existing follower
                existing = session.query(Follower).filter(
                    and_(
                        Follower.target_id == target.id,
                        Follower.follower_username == follower_username.lower()
                    )
                ).first()
                
                if existing:
                    # Update last seen
                    existing.last_seen = datetime.now(timezone.utc)
                    if existing.status == 'unfollowed':
                        existing.status = 'active'
                        # Track re-follow
                        version_manager.track_change(
                            target.id, 'follower_returned', None, follower_username, session
                        )
                    return existing
                
                # Create new follower
                follower = create_follower(target.id, follower_username, **kwargs)
                session.add(follower)
                session.flush()
                
                # Track the change
                version_manager.track_change(
                    target.id, 'new_follower', None, follower_username, session
                )
                
                # Update target follower count
                target.follower_count = session.query(Follower).filter(
                    and_(Follower.target_id == target.id, Follower.status == 'active')
                ).count()
                
                logger.info(f"Added follower {follower_username} for {target_username}")
                return follower
                
        except Exception as e:
            logger.error(f"Error adding follower {follower_username}: {e}")
            return None
    
    def mark_follower_unfollowed(self, target_username: str, follower_username: str) -> bool:
        """Mark a follower as unfollowed"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()
                
                if not target:
                    return False
                
                follower = session.query(Follower).filter(
                    and_(
                        Follower.target_id == target.id,
                        Follower.follower_username == follower_username.lower(),
                        Follower.status == 'active'
                    )
                ).first()
                
                if follower:
                    follower.status = 'unfollowed'
                    follower.last_seen = datetime.now(timezone.utc)
                    
                    # Track the change
                    version_manager.track_change(
                        target.id, 'follower_lost', follower_username, None, session
                    )
                    
                    # Update target follower count
                    target.follower_count = session.query(Follower).filter(
                        and_(Follower.target_id == target.id, Follower.status == 'active')
                    ).count()
                    
                    logger.info(f"Marked follower {follower_username} as unfollowed for {target_username}")
                    return True
                    
                return False
                
        except Exception as e:
            logger.error(f"Error marking follower unfollowed: {e}")
            return False

    def get_followers(self, target_username: str, status: str = 'active',
                     limit: int = 1000) -> List[Follower]:
        """Get followers for a target"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()

                if not target:
                    return []

                query = session.query(Follower).filter(
                    and_(Follower.target_id == target.id, Follower.status == status)
                )

                return query.order_by(desc(Follower.detected_at)).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting followers for {target_username}: {e}")
            return []

    def get_new_followers(self, target_username: str, hours: int = 24) -> List[Follower]:
        """Get new followers in the last N hours"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()

                if not target:
                    return []

                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                return session.query(Follower).filter(
                    and_(
                        Follower.target_id == target.id,
                        Follower.status == 'active',
                        Follower.detected_at >= cutoff_time
                    )
                ).order_by(desc(Follower.detected_at)).all()

        except Exception as e:
            logger.error(f"Error getting new followers: {e}")
            return []

    # Story Operations
    def add_story(self, target_username: str, story_id: str, media_type: str,
                 **kwargs) -> Optional[Story]:
        """Add a new story with duplicate detection"""
        try:
            with self.db_manager.get_session() as session:
                # Get target
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()

                if not target:
                    logger.error(f"Target {target_username} not found")
                    return None

                # Check for duplicate
                existing = session.query(Story).filter(
                    Story.story_id == story_id
                ).first()

                if existing:
                    logger.debug(f"Story {story_id} already exists")
                    return existing

                # Create new story
                story = create_story(target.id, story_id, media_type, **kwargs)
                session.add(story)
                session.flush()

                # Track the change
                version_manager.track_change(
                    target.id, 'new_story', None, {
                        'story_id': story_id,
                        'media_type': media_type
                    }, session
                )

                logger.info(f"Added story {story_id} for {target_username}")
                return story

        except IntegrityError:
            logger.debug(f"Story {story_id} already exists (integrity constraint)")
            return None
        except Exception as e:
            logger.error(f"Error adding story {story_id}: {e}")
            return None

    def get_active_stories(self, target_username: str) -> List[Story]:
        """Get active (non-expired) stories for a target"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()

                if not target:
                    return []

                now = datetime.now(timezone.utc)
                return session.query(Story).filter(
                    and_(
                        Story.target_id == target.id,
                        or_(Story.expires_at.is_(None), Story.expires_at > now)
                    )
                ).order_by(desc(Story.posted_at)).all()

        except Exception as e:
            logger.error(f"Error getting active stories: {e}")
            return []

    # Change Log Operations
    def get_recent_changes(self, target_username: Optional[str] = None,
                          hours: int = 24, limit: int = 100) -> List[ChangeLog]:
        """Get recent changes, optionally filtered by target"""
        try:
            with self.db_manager.get_session() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = session.query(ChangeLog).filter(
                    ChangeLog.detected_at >= cutoff_time
                )

                if target_username:
                    target = session.query(SurveillanceTarget).filter(
                        SurveillanceTarget.instagram_username == target_username.lower()
                    ).first()
                    if target:
                        query = query.filter(ChangeLog.target_id == target.id)

                return query.order_by(desc(ChangeLog.detected_at)).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []

    # Analytics and Statistics
    def get_target_statistics(self, target_username: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a target"""
        try:
            with self.db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.instagram_username == target_username.lower()
                ).first()

                if not target:
                    return {}

                # Basic counts
                total_posts = session.query(Post).filter(Post.target_id == target.id).count()
                total_followers = session.query(Follower).filter(
                    and_(Follower.target_id == target.id, Follower.status == 'active')
                ).count()
                total_stories = session.query(Story).filter(Story.target_id == target.id).count()

                # Recent activity (last 7 days)
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                recent_posts = session.query(Post).filter(
                    and_(Post.target_id == target.id, Post.posted_at >= week_ago)
                ).count()

                new_followers = session.query(Follower).filter(
                    and_(
                        Follower.target_id == target.id,
                        Follower.status == 'active',
                        Follower.detected_at >= week_ago
                    )
                ).count()

                # Engagement statistics
                avg_likes = session.query(func.avg(Post.like_count)).filter(
                    and_(Post.target_id == target.id, Post.posted_at >= week_ago)
                ).scalar() or 0

                avg_comments = session.query(func.avg(Post.comment_count)).filter(
                    and_(Post.target_id == target.id, Post.posted_at >= week_ago)
                ).scalar() or 0

                return {
                    'target_info': target.to_dict(),
                    'totals': {
                        'posts': total_posts,
                        'followers': total_followers,
                        'stories': total_stories
                    },
                    'recent_activity': {
                        'posts_last_week': recent_posts,
                        'new_followers_last_week': new_followers,
                        'avg_likes_last_week': round(avg_likes, 2),
                        'avg_comments_last_week': round(avg_comments, 2)
                    },
                    'engagement_rate': target.engagement_rate
                }

        except Exception as e:
            logger.error(f"Error getting target statistics: {e}")
            return {}

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        try:
            with self.db_manager.get_session() as session:
                # Basic counts
                total_targets = session.query(SurveillanceTarget).count()
                active_targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).count()

                total_posts = session.query(Post).count()
                total_followers = session.query(Follower).filter(
                    Follower.status == 'active'
                ).count()

                # Recent activity
                day_ago = datetime.now(timezone.utc) - timedelta(days=1)
                recent_posts = session.query(Post).filter(
                    Post.collected_at >= day_ago
                ).count()

                recent_changes = session.query(ChangeLog).filter(
                    ChangeLog.detected_at >= day_ago
                ).count()

                # Database statistics
                db_stats = self.db_manager.get_database_stats()

                return {
                    'targets': {
                        'total': total_targets,
                        'active': active_targets
                    },
                    'content': {
                        'total_posts': total_posts,
                        'total_followers': total_followers,
                        'posts_last_24h': recent_posts,
                        'changes_last_24h': recent_changes
                    },
                    'database': db_stats
                }

        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}

    # Cleanup Operations
    def cleanup_expired_stories(self) -> int:
        """Remove expired stories"""
        try:
            with self.db_manager.get_session() as session:
                now = datetime.now(timezone.utc)
                deleted_count = session.query(Story).filter(
                    and_(Story.expires_at.isnot(None), Story.expires_at < now)
                ).delete()

                logger.info(f"Cleaned up {deleted_count} expired stories")
                return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired stories: {e}")
            return 0

    def cleanup_old_change_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old change log entries"""
        return self.version_manager.cleanup_old_changes(days_to_keep)

    # UI Compatibility Methods
    def add_target(self, instagram_username: str, **kwargs) -> Optional[int]:
        """Add target - UI compatibility method that returns target ID"""
        target = self.add_surveillance_target(instagram_username, **kwargs)
        return target.id if target else None

    def get_active_targets(self) -> List[Dict[str, Any]]:
        """Get all active surveillance targets as dictionaries to avoid session binding issues"""
        try:
            with self.db_manager.get_session() as session:
                targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()

                # Convert to dictionaries to avoid session binding issues
                return [self._target_to_dict(target) for target in targets]
        except Exception as e:
            logger.error(f"Error getting active targets: {e}")
            return []

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        try:
            with self.db_manager.get_session() as session:
                # Count active targets
                active_targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).count()

                # Count total posts
                total_posts = session.query(Post).count()

                # Count new followers (last 24 hours)
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                new_followers = session.query(Follower).filter(
                    Follower.detected_at >= yesterday
                ).count()

                # Count alerts/changes today
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                alerts_today = session.query(ChangeLog).filter(
                    ChangeLog.detected_at >= today
                ).count()

                return {
                    'active_targets': active_targets,
                    'total_posts': total_posts,
                    'new_followers': new_followers,
                    'alerts_today': alerts_today
                }
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                'active_targets': 0,
                'total_posts': 0,
                'new_followers': 0,
                'alerts_today': 0
            }

    def get_all_targets(self) -> List[Dict[str, Any]]:
        """Get all surveillance targets as dictionaries to avoid session binding issues"""
        try:
            with self.db_manager.get_session() as session:
                targets = session.query(SurveillanceTarget).all()
                return [self._target_to_dict(target) for target in targets]
        except Exception as e:
            logger.error(f"Error getting all targets: {e}")
            return []

    def _target_to_dict(self, target: SurveillanceTarget) -> Dict[str, Any]:
        """Convert SurveillanceTarget object to dictionary"""
        return {
            'id': target.id,
            'instagram_username': target.instagram_username,
            'display_name': target.display_name,
            'profile_pic_url': target.profile_pic_url,
            'is_private': target.is_private,
            'follower_count': target.follower_count,
            'following_count': target.following_count,
            'post_count': target.post_count,
            'bio': target.bio,
            'external_url': target.external_url,
            'is_verified': target.is_verified,
            'created_at': target.created_at,
            'last_updated': target.last_updated,
            'status': target.status,
            'category': target.category,
            'priority': target.priority,
            'notes': target.notes,
            'notifications_enabled': getattr(target, 'notifications_enabled', True)
        }

    def get_recent_activities(self, limit: int = 50) -> List[ChangeLog]:
        """Get recent activity/change log entries"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(ChangeLog).order_by(
                    desc(ChangeLog.detected_at)
                ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return []

# Global data manager instance
data_manager = DataManager()
