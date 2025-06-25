"""
Social Media Surveillance System - Instagram Data Models
SQLAlchemy ORM models for all Instagram entities with relationships and validation.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, JSON,
    ForeignKey, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

from core.database import Base

class SurveillanceTarget(Base):
    """Model for Instagram accounts under surveillance"""
    __tablename__ = 'surveillance_targets'
    
    id = Column(Integer, primary_key=True)
    instagram_username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    profile_pic_url = Column(Text)
    is_private = Column(Boolean, default=False)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    bio = Column(Text)
    external_url = Column(Text)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default='active')  # active, suspended, private, blocked
    
    # Additional metadata
    category = Column(String(100))  # influencer, brand, competitor, etc.
    priority = Column(String(20), default='medium')  # low, medium, high, critical
    notes = Column(Text)
    notifications_enabled = Column(Boolean, default=True)  # Enable/disable notifications for this target
    
    # Relationships
    posts = relationship("Post", back_populates="target", cascade="all, delete-orphan")
    followers = relationship("Follower", back_populates="target", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="target", cascade="all, delete-orphan")
    change_logs = relationship("ChangeLog", back_populates="target", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('follower_count >= 0', name='check_follower_count_positive'),
        CheckConstraint('following_count >= 0', name='check_following_count_positive'),
        CheckConstraint('post_count >= 0', name='check_post_count_positive'),
        CheckConstraint("status IN ('active', 'suspended', 'private', 'blocked')", name='check_status_valid'),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name='check_priority_valid'),
        Index('idx_target_username_status', 'instagram_username', 'status'),
        Index('idx_target_priority_updated', 'priority', 'last_updated'),
    )
    
    @validates('instagram_username')
    def validate_username(self, key, username):
        """Validate Instagram username format"""
        if not username:
            raise ValueError("Username cannot be empty")
        if len(username) > 30:
            raise ValueError("Username too long")
        # Basic Instagram username validation
        import re
        if not re.match(r'^[a-zA-Z0-9._]+$', username):
            raise ValueError("Invalid username format")
        return username.lower()
    
    @hybrid_property
    def engagement_rate(self):
        """Calculate average engagement rate from recent posts"""
        if not self.posts or self.follower_count == 0:
            return 0.0
        
        recent_posts = [p for p in self.posts if p.posted_at and 
                       (datetime.now(timezone.utc) - p.posted_at).days <= 30]
        
        if not recent_posts:
            return 0.0
            
        total_engagement = sum((p.like_count or 0) + (p.comment_count or 0) for p in recent_posts)
        avg_engagement = total_engagement / len(recent_posts)
        
        return (avg_engagement / self.follower_count) * 100 if self.follower_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'instagram_username': self.instagram_username,
            'display_name': self.display_name,
            'profile_pic_url': self.profile_pic_url,
            'is_private': self.is_private,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'post_count': self.post_count,
            'bio': self.bio,
            'external_url': self.external_url,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'status': self.status,
            'category': self.category,
            'priority': self.priority,
            'notes': self.notes,
            'engagement_rate': self.engagement_rate
        }
    
    def __repr__(self):
        return f"<SurveillanceTarget(username='{self.instagram_username}', status='{self.status}')>"

class Post(Base):
    """Model for Instagram posts"""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    instagram_post_id = Column(String(100), unique=True, nullable=False, index=True)
    post_type = Column(String(20), nullable=False)  # photo, video, carousel, reel, story
    caption = Column(Text)
    media_urls = Column(JSON)  # Array of media file paths/URLs
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer)  # For videos/reels
    posted_at = Column(DateTime, index=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Content analysis
    hashtags = Column(JSON)  # Array of hashtags
    mentions = Column(JSON)  # Array of mentioned users
    location_name = Column(String(200))
    location_id = Column(String(100))
    
    # AI analysis results
    sentiment_score = Column(Float)  # -1 to 1
    topics = Column(JSON)  # Array of detected topics
    language = Column(String(10))
    
    # Relationships
    target = relationship("SurveillanceTarget", back_populates="posts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('like_count >= 0', name='check_like_count_positive'),
        CheckConstraint('comment_count >= 0', name='check_comment_count_positive'),
        CheckConstraint('share_count >= 0', name='check_share_count_positive'),
        CheckConstraint("post_type IN ('photo', 'video', 'carousel', 'reel', 'story')", name='check_post_type_valid'),
        CheckConstraint('sentiment_score >= -1 AND sentiment_score <= 1', name='check_sentiment_range'),
        Index('idx_post_target_posted', 'target_id', 'posted_at'),
        Index('idx_post_type_posted', 'post_type', 'posted_at'),
        UniqueConstraint('instagram_post_id', name='uq_instagram_post_id'),
    )
    
    @validates('post_type')
    def validate_post_type(self, key, post_type):
        """Validate post type"""
        valid_types = ['photo', 'video', 'carousel', 'reel', 'story']
        if post_type not in valid_types:
            raise ValueError(f"Invalid post type. Must be one of: {valid_types}")
        return post_type
    
    @hybrid_property
    def engagement_rate(self):
        """Calculate engagement rate for this post"""
        if not self.target or self.target.follower_count == 0:
            return 0.0
        
        total_engagement = (self.like_count or 0) + (self.comment_count or 0)
        return (total_engagement / self.target.follower_count) * 100
    
    @hybrid_property
    def is_recent(self):
        """Check if post is from last 24 hours"""
        if not self.posted_at:
            return False
        return (datetime.now(timezone.utc) - self.posted_at).days == 0
    
    def get_hashtags_list(self) -> List[str]:
        """Get hashtags as a list"""
        if isinstance(self.hashtags, str):
            return json.loads(self.hashtags)
        return self.hashtags or []
    
    def get_mentions_list(self) -> List[str]:
        """Get mentions as a list"""
        if isinstance(self.mentions, str):
            return json.loads(self.mentions)
        return self.mentions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'instagram_post_id': self.instagram_post_id,
            'post_type': self.post_type,
            'caption': self.caption,
            'media_urls': self.media_urls,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'view_count': self.view_count,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'hashtags': self.get_hashtags_list(),
            'mentions': self.get_mentions_list(),
            'location_name': self.location_name,
            'location_id': self.location_id,
            'sentiment_score': self.sentiment_score,
            'topics': self.topics,
            'language': self.language,
            'engagement_rate': self.engagement_rate,
            'is_recent': self.is_recent
        }
    
    def __repr__(self):
        return f"<Post(id='{self.instagram_post_id}', type='{self.post_type}', target_id={self.target_id})>"

class Follower(Base):
    """Model for tracking followers of surveillance targets"""
    __tablename__ = 'followers'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    follower_username = Column(String(100), nullable=False, index=True)
    follower_display_name = Column(String(200))
    follower_profile_pic = Column(Text)
    is_verified = Column(Boolean, default=False)
    follower_count = Column(Integer)  # Follower's own follower count
    following_count = Column(Integer)  # Follower's following count

    # Tracking information
    followed_at = Column(DateTime)  # When they followed the target
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # When we detected them
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default='active')  # active, unfollowed, blocked

    # Analysis data
    influence_score = Column(Float)  # 0-10 influence rating
    bot_probability = Column(Float)  # 0-1 probability of being a bot
    engagement_rate = Column(Float)  # Their engagement rate

    # Relationships
    target = relationship("SurveillanceTarget", back_populates="followers")

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'unfollowed', 'blocked')", name='check_follower_status_valid'),
        CheckConstraint('influence_score >= 0 AND influence_score <= 10', name='check_influence_score_range'),
        CheckConstraint('bot_probability >= 0 AND bot_probability <= 1', name='check_bot_probability_range'),
        Index('idx_follower_target_status', 'target_id', 'status'),
        Index('idx_follower_username_detected', 'follower_username', 'detected_at'),
        UniqueConstraint('target_id', 'follower_username', name='uq_target_follower'),
    )

    @validates('follower_username')
    def validate_follower_username(self, key, username):
        """Validate follower username format"""
        if not username:
            raise ValueError("Follower username cannot be empty")
        return username.lower()

    @hybrid_property
    def is_new_follower(self):
        """Check if this is a new follower (detected in last 24 hours)"""
        if not self.detected_at:
            return False
        return (datetime.now(timezone.utc) - self.detected_at).days == 0

    @hybrid_property
    def likely_bot(self):
        """Check if follower is likely a bot"""
        return (self.bot_probability or 0) > 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'follower_username': self.follower_username,
            'follower_display_name': self.follower_display_name,
            'follower_profile_pic': self.follower_profile_pic,
            'is_verified': self.is_verified,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'followed_at': self.followed_at.isoformat() if self.followed_at else None,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'status': self.status,
            'influence_score': self.influence_score,
            'bot_probability': self.bot_probability,
            'engagement_rate': self.engagement_rate,
            'is_new_follower': self.is_new_follower,
            'likely_bot': self.likely_bot
        }

    def __repr__(self):
        return f"<Follower(username='{self.follower_username}', target_id={self.target_id}, status='{self.status}')>"

class Story(Base):
    """Model for Instagram stories"""
    __tablename__ = 'stories'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    story_id = Column(String(100), unique=True, nullable=False)
    media_type = Column(String(20), nullable=False)  # photo, video
    media_url = Column(Text)
    story_text = Column(Text)  # Text overlay on story
    view_count = Column(Integer, default=0)

    # Timestamps
    posted_at = Column(DateTime, index=True)
    expires_at = Column(DateTime, index=True)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Story-specific data
    is_highlight = Column(Boolean, default=False)
    highlight_title = Column(String(100))
    stickers = Column(JSON)  # Array of sticker data (polls, questions, etc.)
    music_info = Column(JSON)  # Music information if present

    # Analysis data
    sentiment_score = Column(Float)
    topics = Column(JSON)

    # Relationships
    target = relationship("SurveillanceTarget", back_populates="stories")

    # Constraints
    __table_args__ = (
        CheckConstraint("media_type IN ('photo', 'video')", name='check_story_media_type_valid'),
        CheckConstraint('view_count >= 0', name='check_story_view_count_positive'),
        CheckConstraint('sentiment_score >= -1 AND sentiment_score <= 1', name='check_story_sentiment_range'),
        Index('idx_story_target_posted', 'target_id', 'posted_at'),
        Index('idx_story_expires', 'expires_at'),
        UniqueConstraint('story_id', name='uq_story_id'),
    )

    @validates('media_type')
    def validate_media_type(self, key, media_type):
        """Validate story media type"""
        valid_types = ['photo', 'video']
        if media_type not in valid_types:
            raise ValueError(f"Invalid media type. Must be one of: {valid_types}")
        return media_type

    @hybrid_property
    def is_expired(self):
        """Check if story has expired"""
        if not self.expires_at:
            return True
        return datetime.now(timezone.utc) > self.expires_at

    @hybrid_property
    def is_active(self):
        """Check if story is still active"""
        return not self.is_expired

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'story_id': self.story_id,
            'media_type': self.media_type,
            'media_url': self.media_url,
            'story_text': self.story_text,
            'view_count': self.view_count,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'is_highlight': self.is_highlight,
            'highlight_title': self.highlight_title,
            'stickers': self.stickers,
            'music_info': self.music_info,
            'sentiment_score': self.sentiment_score,
            'topics': self.topics,
            'is_expired': self.is_expired,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<Story(id='{self.story_id}', target_id={self.target_id}, type='{self.media_type}')>"

class ChangeLog(Base):
    """Model for tracking changes in surveillance data"""
    __tablename__ = 'change_log'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    change_type = Column(String(50), nullable=False, index=True)
    old_value = Column(Text)  # JSON string of old value
    new_value = Column(Text)  # JSON string of new value
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Additional context
    change_source = Column(String(50))  # scraper, manual, api, etc.
    severity = Column(String(20), default='medium')  # low, medium, high, critical
    description = Column(Text)  # Human-readable description

    # Relationships
    target = relationship("SurveillanceTarget", back_populates="change_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_change_severity_valid'),
        Index('idx_changelog_target_type', 'target_id', 'change_type'),
        Index('idx_changelog_detected_severity', 'detected_at', 'severity'),
    )

    # Common change types
    CHANGE_TYPES = {
        'target_added': 'Surveillance target added',
        'new_post': 'New post published',
        'new_follower': 'New follower detected',
        'follower_lost': 'Follower unfollowed',
        'follower_returned': 'Follower returned',
        'new_story': 'New story published',
        'bio_changed': 'Profile bio updated',
        'name_changed': 'Display name changed',
        'profile_pic_changed': 'Profile picture updated',
        'follower_count_changed': 'Follower count changed',
        'following_count_changed': 'Following count changed',
        'post_count_changed': 'Post count changed',
        'privacy_changed': 'Account privacy setting changed',
        'verification_changed': 'Verification status changed',
        'account_suspended': 'Account suspended',
        'account_reactivated': 'Account reactivated',
        'engagement_spike': 'Unusual engagement activity',
        'mention_detected': 'Account mentioned in post',
        'hashtag_trending': 'Hashtag gaining popularity'
    }

    @validates('change_type')
    def validate_change_type(self, key, change_type):
        """Validate change type"""
        if change_type not in self.CHANGE_TYPES:
            # Allow custom change types but log a warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown change type: {change_type}")
        return change_type

    @validates('severity')
    def validate_severity(self, key, severity):
        """Validate severity level"""
        valid_severities = ['low', 'medium', 'high', 'critical']
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity. Must be one of: {valid_severities}")
        return severity

    @hybrid_property
    def is_recent(self):
        """Check if change was detected in last 24 hours"""
        if not self.detected_at:
            return False
        return (datetime.now(timezone.utc) - self.detected_at).days == 0

    @hybrid_property
    def is_critical(self):
        """Check if change is critical severity"""
        return self.severity == 'critical'

    def get_old_value_parsed(self):
        """Parse old value from JSON string"""
        if not self.old_value:
            return None
        try:
            return json.loads(self.old_value)
        except (json.JSONDecodeError, TypeError):
            return self.old_value

    def get_new_value_parsed(self):
        """Parse new value from JSON string"""
        if not self.new_value:
            return None
        try:
            return json.loads(self.new_value)
        except (json.JSONDecodeError, TypeError):
            return self.new_value

    def get_change_description(self) -> str:
        """Get human-readable change description"""
        if self.description:
            return self.description

        # Generate description based on change type
        base_description = self.CHANGE_TYPES.get(self.change_type, f"Change of type: {self.change_type}")

        old_val = self.get_old_value_parsed()
        new_val = self.get_new_value_parsed()

        if old_val is not None and new_val is not None:
            return f"{base_description} (from {old_val} to {new_val})"
        elif new_val is not None:
            return f"{base_description}: {new_val}"
        else:
            return base_description

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'change_type': self.change_type,
            'old_value': self.get_old_value_parsed(),
            'new_value': self.get_new_value_parsed(),
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'change_source': self.change_source,
            'severity': self.severity,
            'description': self.get_change_description(),
            'is_recent': self.is_recent,
            'is_critical': self.is_critical
        }

    def __repr__(self):
        return f"<ChangeLog(type='{self.change_type}', target_id={self.target_id}, severity='{self.severity}')>"

# Utility functions for model operations
def create_surveillance_target(username: str, **kwargs) -> SurveillanceTarget:
    """Create a new surveillance target with validation"""
    target = SurveillanceTarget(instagram_username=username, **kwargs)
    return target

def create_post(target_id: int, instagram_post_id: str, post_type: str, **kwargs) -> Post:
    """Create a new post with validation"""
    post = Post(
        target_id=target_id,
        instagram_post_id=instagram_post_id,
        post_type=post_type,
        **kwargs
    )
    return post

def create_follower(target_id: int, follower_username: str, **kwargs) -> Follower:
    """Create a new follower record with validation"""
    follower = Follower(
        target_id=target_id,
        follower_username=follower_username,
        **kwargs
    )
    return follower

def create_story(target_id: int, story_id: str, media_type: str, **kwargs) -> Story:
    """Create a new story with validation"""
    story = Story(
        target_id=target_id,
        story_id=story_id,
        media_type=media_type,
        **kwargs
    )
    return story

def create_change_log(target_id: int, change_type: str, **kwargs) -> ChangeLog:
    """Create a new change log entry with validation"""
    change_log = ChangeLog(
        target_id=target_id,
        change_type=change_type,
        **kwargs
    )
    return change_log
