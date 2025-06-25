"""
Social Media Surveillance System - Analytics Data Models
SQLAlchemy ORM models for analytics, metrics, and reporting data.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, JSON,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, BigInteger
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

from core.database import Base

class ScrapingMetrics(Base):
    """Model for tracking scraping performance metrics"""
    __tablename__ = 'scraping_metrics'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    scraper_type = Column(String(50), nullable=False, index=True)  # posts, followers, stories, profile
    
    # Performance metrics
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, index=True)
    duration_seconds = Column(Float)
    items_scraped = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    success_rate = Column(Float)  # 0-100 percentage
    
    # Request metrics
    requests_made = Column(Integer, default=0)
    requests_failed = Column(Integer, default=0)
    avg_response_time = Column(Float)  # Average response time in seconds
    rate_limit_hits = Column(Integer, default=0)
    
    # Data quality metrics
    data_quality_score = Column(Float)  # 0-1 score
    validation_errors = Column(Integer, default=0)
    duplicate_items = Column(Integer, default=0)
    
    # Status and metadata
    status = Column(String(20), default='completed')  # running, completed, failed, cancelled
    error_message = Column(Text)
    scraper_metadata = Column(JSON)  # Additional scraper-specific data
    
    # Relationships
    target = relationship("SurveillanceTarget")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('items_scraped >= 0', name='check_items_scraped_positive'),
        CheckConstraint('items_failed >= 0', name='check_items_failed_positive'),
        CheckConstraint('success_rate >= 0 AND success_rate <= 100', name='check_success_rate_range'),
        CheckConstraint('data_quality_score >= 0 AND data_quality_score <= 1', name='check_quality_score_range'),
        CheckConstraint("status IN ('running', 'completed', 'failed', 'cancelled')", name='check_status_valid'),
        Index('idx_metrics_target_scraper_time', 'target_id', 'scraper_type', 'start_time'),
        Index('idx_metrics_status_time', 'status', 'start_time'),
    )
    
    @hybrid_property
    def items_per_second(self):
        """Calculate items scraped per second"""
        if not self.duration_seconds or self.duration_seconds <= 0:
            return 0.0
        return self.items_scraped / self.duration_seconds
    
    @hybrid_property
    def total_items(self):
        """Total items processed (success + failed)"""
        return (self.items_scraped or 0) + (self.items_failed or 0)
    
    def calculate_success_rate(self):
        """Calculate and update success rate"""
        total = self.total_items
        if total > 0:
            self.success_rate = (self.items_scraped / total) * 100
        else:
            self.success_rate = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'scraper_type': self.scraper_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'items_scraped': self.items_scraped,
            'items_failed': self.items_failed,
            'success_rate': self.success_rate,
            'requests_made': self.requests_made,
            'requests_failed': self.requests_failed,
            'avg_response_time': self.avg_response_time,
            'rate_limit_hits': self.rate_limit_hits,
            'data_quality_score': self.data_quality_score,
            'validation_errors': self.validation_errors,
            'duplicate_items': self.duplicate_items,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'items_per_second': self.items_per_second,
            'total_items': self.total_items
        }

class AccountHealthMetrics(Base):
    """Model for tracking account health and growth metrics"""
    __tablename__ = 'account_health_metrics'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Follower metrics
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    follower_growth_rate = Column(Float)  # Daily growth rate percentage
    follower_churn_rate = Column(Float)  # Daily churn rate percentage
    net_follower_change = Column(Integer, default=0)  # Daily net change
    
    # Content metrics
    post_count = Column(Integer, default=0)
    posts_last_24h = Column(Integer, default=0)
    posts_last_7d = Column(Integer, default=0)
    posts_last_30d = Column(Integer, default=0)
    avg_posts_per_day = Column(Float)
    
    # Engagement metrics
    avg_likes_per_post = Column(Float)
    avg_comments_per_post = Column(Float)
    avg_engagement_rate = Column(Float)  # Percentage
    engagement_trend = Column(String(20))  # increasing, decreasing, stable
    
    # Story metrics
    stories_last_24h = Column(Integer, default=0)
    avg_story_views = Column(Float)
    story_completion_rate = Column(Float)
    
    # Quality metrics
    bot_follower_percentage = Column(Float)  # Estimated percentage of bot followers
    authentic_engagement_score = Column(Float)  # 0-10 score
    content_consistency_score = Column(Float)  # 0-10 score
    
    # Activity patterns
    most_active_hour = Column(Integer)  # 0-23 hour of day
    most_active_day = Column(Integer)  # 0-6 day of week (Monday=0)
    posting_frequency_score = Column(Float)  # 0-10 consistency score
    
    # Relationships
    target = relationship("SurveillanceTarget")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('follower_count >= 0', name='check_follower_count_positive'),
        CheckConstraint('following_count >= 0', name='check_following_count_positive'),
        CheckConstraint('avg_engagement_rate >= 0', name='check_engagement_rate_positive'),
        CheckConstraint('bot_follower_percentage >= 0 AND bot_follower_percentage <= 100', name='check_bot_percentage_range'),
        CheckConstraint('authentic_engagement_score >= 0 AND authentic_engagement_score <= 10', name='check_engagement_score_range'),
        CheckConstraint('most_active_hour >= 0 AND most_active_hour <= 23', name='check_active_hour_range'),
        CheckConstraint('most_active_day >= 0 AND most_active_day <= 6', name='check_active_day_range'),
        CheckConstraint("engagement_trend IN ('increasing', 'decreasing', 'stable')", name='check_engagement_trend_valid'),
        Index('idx_health_target_recorded', 'target_id', 'recorded_at'),
        Index('idx_health_recorded', 'recorded_at'),
    )
    
    @hybrid_property
    def follower_to_following_ratio(self):
        """Calculate follower to following ratio"""
        if self.following_count == 0:
            return float('inf') if self.follower_count > 0 else 0
        return self.follower_count / self.following_count
    
    @hybrid_property
    def health_score(self):
        """Calculate overall account health score (0-100)"""
        scores = []
        
        # Engagement score (0-30 points)
        if self.avg_engagement_rate is not None:
            engagement_score = min(self.avg_engagement_rate * 3, 30)
            scores.append(engagement_score)
        
        # Authenticity score (0-25 points)
        if self.authentic_engagement_score is not None:
            auth_score = (self.authentic_engagement_score / 10) * 25
            scores.append(auth_score)
        
        # Content consistency (0-20 points)
        if self.content_consistency_score is not None:
            consistency_score = (self.content_consistency_score / 10) * 20
            scores.append(consistency_score)
        
        # Growth trend (0-25 points)
        if self.follower_growth_rate is not None:
            growth_score = min(max(self.follower_growth_rate * 5, 0), 25)
            scores.append(growth_score)
        
        return sum(scores) if scores else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'follower_count': self.follower_count,
            'following_count': self.following_count,
            'follower_growth_rate': self.follower_growth_rate,
            'follower_churn_rate': self.follower_churn_rate,
            'net_follower_change': self.net_follower_change,
            'post_count': self.post_count,
            'posts_last_24h': self.posts_last_24h,
            'posts_last_7d': self.posts_last_7d,
            'posts_last_30d': self.posts_last_30d,
            'avg_posts_per_day': self.avg_posts_per_day,
            'avg_likes_per_post': self.avg_likes_per_post,
            'avg_comments_per_post': self.avg_comments_per_post,
            'avg_engagement_rate': self.avg_engagement_rate,
            'engagement_trend': self.engagement_trend,
            'stories_last_24h': self.stories_last_24h,
            'avg_story_views': self.avg_story_views,
            'story_completion_rate': self.story_completion_rate,
            'bot_follower_percentage': self.bot_follower_percentage,
            'authentic_engagement_score': self.authentic_engagement_score,
            'content_consistency_score': self.content_consistency_score,
            'most_active_hour': self.most_active_hour,
            'most_active_day': self.most_active_day,
            'posting_frequency_score': self.posting_frequency_score,
            'follower_to_following_ratio': self.follower_to_following_ratio,
            'health_score': self.health_score
        }

class TrendAnalysis(Base):
    """Model for storing trend analysis data"""
    __tablename__ = 'trend_analysis'

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # hashtag, mention, engagement, growth
    analysis_period = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Trend data
    trend_data = Column(JSON)  # Time series data points
    trend_direction = Column(String(20))  # increasing, decreasing, stable, volatile
    trend_strength = Column(Float)  # 0-1 strength of trend
    change_percentage = Column(Float)  # Percentage change over period

    # Statistical measures
    mean_value = Column(Float)
    median_value = Column(Float)
    std_deviation = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)

    # Anomaly detection
    anomalies_detected = Column(Integer, default=0)
    anomaly_score = Column(Float)  # 0-1 anomaly strength
    anomaly_details = Column(JSON)  # Details about detected anomalies

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    confidence_score = Column(Float)  # 0-1 confidence in analysis

    # Relationships
    target = relationship("SurveillanceTarget")

    # Constraints
    __table_args__ = (
        CheckConstraint('trend_strength >= 0 AND trend_strength <= 1', name='check_trend_strength_range'),
        CheckConstraint('anomaly_score >= 0 AND anomaly_score <= 1', name='check_anomaly_score_range'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_score_range'),
        CheckConstraint("trend_direction IN ('increasing', 'decreasing', 'stable', 'volatile')", name='check_trend_direction_valid'),
        CheckConstraint("analysis_period IN ('daily', 'weekly', 'monthly')", name='check_analysis_period_valid'),
        Index('idx_trend_target_type_period', 'target_id', 'analysis_type', 'period_start'),
        Index('idx_trend_period_range', 'period_start', 'period_end'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'analysis_type': self.analysis_type,
            'analysis_period': self.analysis_period,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'trend_data': self.trend_data,
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'change_percentage': self.change_percentage,
            'mean_value': self.mean_value,
            'median_value': self.median_value,
            'std_deviation': self.std_deviation,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'anomalies_detected': self.anomalies_detected,
            'anomaly_score': self.anomaly_score,
            'anomaly_details': self.anomaly_details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confidence_score': self.confidence_score
        }

class ReportTemplate(Base):
    """Model for storing report templates"""
    __tablename__ = 'report_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    template_type = Column(String(50), nullable=False)  # dashboard, pdf, csv, json

    # Template configuration
    config = Column(JSON)  # Template-specific configuration
    sections = Column(JSON)  # Array of report sections
    filters = Column(JSON)  # Default filters to apply

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String(100))
    is_active = Column(Boolean, default=True)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)

    # Constraints
    __table_args__ = (
        CheckConstraint("template_type IN ('dashboard', 'pdf', 'csv', 'json')", name='check_template_type_valid'),
        CheckConstraint('usage_count >= 0', name='check_usage_count_positive'),
        Index('idx_template_type_active', 'template_type', 'is_active'),
    )

    def increment_usage(self):
        """Increment usage counter and update last used timestamp"""
        self.usage_count = (self.usage_count or 0) + 1
        self.last_used = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_type': self.template_type,
            'config': self.config,
            'sections': self.sections,
            'filters': self.filters,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }

class GeneratedReport(Base):
    """Model for tracking generated reports"""
    __tablename__ = 'generated_reports'

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('report_templates.id'), index=True)
    report_name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)

    # Report metadata
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    generated_by = Column(String(100))
    file_path = Column(Text)  # Path to generated report file
    file_size = Column(BigInteger)  # File size in bytes

    # Report parameters
    target_ids = Column(JSON)  # Array of target IDs included
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    filters_applied = Column(JSON)  # Filters used in generation

    # Status and metrics
    status = Column(String(20), default='completed')  # generating, completed, failed
    generation_time_seconds = Column(Float)
    error_message = Column(Text)

    # Access tracking
    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)

    # Relationships
    template = relationship("ReportTemplate")

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('generating', 'completed', 'failed')", name='check_report_status_valid'),
        CheckConstraint('file_size >= 0', name='check_file_size_positive'),
        CheckConstraint('download_count >= 0', name='check_download_count_positive'),
        Index('idx_report_generated_status', 'generated_at', 'status'),
        Index('idx_report_type_generated', 'report_type', 'generated_at'),
    )

    def increment_download(self):
        """Increment download counter and update last accessed timestamp"""
        self.download_count = (self.download_count or 0) + 1
        self.last_accessed = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'report_name': self.report_name,
            'report_type': self.report_type,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'generated_by': self.generated_by,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'target_ids': self.target_ids,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'filters_applied': self.filters_applied,
            'status': self.status,
            'generation_time_seconds': self.generation_time_seconds,
            'error_message': self.error_message,
            'download_count': self.download_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }

# Factory functions for creating analytics models
def create_scraping_metrics(target_id: int, scraper_type: str, **kwargs) -> ScrapingMetrics:
    """Create a new scraping metrics record"""
    return ScrapingMetrics(
        target_id=target_id,
        scraper_type=scraper_type,
        start_time=kwargs.get('start_time', datetime.now(timezone.utc)),
        **{k: v for k, v in kwargs.items() if k != 'start_time'}
    )

def create_account_health_metrics(target_id: int, **kwargs) -> AccountHealthMetrics:
    """Create a new account health metrics record"""
    return AccountHealthMetrics(
        target_id=target_id,
        **kwargs
    )

def create_trend_analysis(target_id: int, analysis_type: str, analysis_period: str,
                         period_start: datetime, period_end: datetime, **kwargs) -> TrendAnalysis:
    """Create a new trend analysis record"""
    return TrendAnalysis(
        target_id=target_id,
        analysis_type=analysis_type,
        analysis_period=analysis_period,
        period_start=period_start,
        period_end=period_end,
        **kwargs
    )

def create_report_template(name: str, template_type: str, **kwargs) -> ReportTemplate:
    """Create a new report template"""
    return ReportTemplate(
        name=name,
        template_type=template_type,
        **kwargs
    )

def create_generated_report(template_id: int, report_name: str, report_type: str, **kwargs) -> GeneratedReport:
    """Create a new generated report record"""
    return GeneratedReport(
        template_id=template_id,
        report_name=report_name,
        report_type=report_type,
        **kwargs
    )
