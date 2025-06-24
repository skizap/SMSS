#!/usr/bin/env python3
"""
Social Media Surveillance System - Account Health Monitoring Engine
Monitors follower growth, engagement rates, and content performance tracking.
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics

from core.config import config
from core.database import db_manager
from core.data_manager import data_manager
from models.instagram_models import SurveillanceTarget, Post, Follower
from models.analytics_models import AccountHealthMetrics, create_account_health_metrics
from notifications.enhanced_notification_manager import enhanced_notification_manager

logger = logging.getLogger(__name__)

@dataclass
class HealthAlert:
    """Represents a health monitoring alert"""
    target_id: int
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    metrics: Dict[str, Any]
    timestamp: datetime

class AccountHealthMonitor:
    """Monitors account health metrics and generates alerts"""
    
    def __init__(self):
        self.monitoring_thread = None
        self.running = False
        self.last_health_check = {}  # target_id -> timestamp
        self.health_history = defaultdict(list)  # target_id -> list of health scores
        
        # Alert thresholds
        self.thresholds = {
            'follower_growth_decline': -5.0,  # % decline that triggers alert
            'engagement_drop': -30.0,  # % drop in engagement
            'posting_frequency_drop': -50.0,  # % drop in posting frequency
            'bot_follower_increase': 20.0,  # % increase in bot followers
            'health_score_critical': 30.0,  # Health score below this is critical
            'health_score_warning': 50.0   # Health score below this is warning
        }
        
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start the health monitoring thread"""
        if not self.running:
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
            self.monitoring_thread.start()
            logger.info("Account health monitoring started")
    
    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        logger.info("Account health monitoring stopped")
    
    def _monitoring_worker(self):
        """Background worker for health monitoring"""
        while self.running:
            try:
                # Get all active surveillance targets
                targets = self._get_active_targets()
                
                for target in targets:
                    try:
                        # Check if it's time to update health metrics for this target
                        if self._should_update_health_metrics(target.id):
                            self._update_target_health_metrics(target)
                            
                        # Check for health alerts
                        self._check_health_alerts(target)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring target {target.instagram_username}: {e}")
                
                # Sleep for 5 minutes between checks
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in health monitoring worker: {e}")
                time.sleep(600)  # Wait longer on error
    
    def _get_active_targets(self) -> List[SurveillanceTarget]:
        """Get all active surveillance targets"""
        try:
            with db_manager.get_session() as session:
                return session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()
        except Exception as e:
            logger.error(f"Error getting active targets: {e}")
            return []
    
    def _should_update_health_metrics(self, target_id: int) -> bool:
        """Check if health metrics should be updated for a target"""
        last_check = self.last_health_check.get(target_id)
        if not last_check:
            return True
        
        # Update every 6 hours
        return (datetime.now(timezone.utc) - last_check).seconds >= 21600
    
    def _update_target_health_metrics(self, target: SurveillanceTarget):
        """Update health metrics for a specific target"""
        try:
            logger.debug(f"Updating health metrics for {target.instagram_username}")
            
            # Calculate current metrics
            metrics = self._calculate_health_metrics(target)
            
            # Store in database
            health_record = create_account_health_metrics(
                target_id=target.id,
                **metrics
            )
            
            with db_manager.get_session() as session:
                session.add(health_record)
                session.commit()
            
            # Update last check time
            self.last_health_check[target.id] = datetime.now(timezone.utc)
            
            # Store health score in history
            self.health_history[target.id].append({
                'timestamp': datetime.now(timezone.utc),
                'health_score': health_record.health_score
            })
            
            # Keep only last 30 days of history
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            self.health_history[target.id] = [
                h for h in self.health_history[target.id] 
                if h['timestamp'] > cutoff
            ]
            
            logger.debug(f"Health metrics updated for {target.instagram_username}: score {health_record.health_score:.1f}")
            
        except Exception as e:
            logger.error(f"Error updating health metrics for {target.instagram_username}: {e}")
    
    def _calculate_health_metrics(self, target: SurveillanceTarget) -> Dict[str, Any]:
        """Calculate comprehensive health metrics for a target"""
        now = datetime.now(timezone.utc)
        
        # Get recent data
        recent_posts = self._get_recent_posts(target.id, days=30)
        recent_followers = self._get_recent_followers(target.id, days=7)
        
        # Calculate follower metrics
        follower_metrics = self._calculate_follower_metrics(target, recent_followers)
        
        # Calculate content metrics
        content_metrics = self._calculate_content_metrics(target, recent_posts)
        
        # Calculate engagement metrics
        engagement_metrics = self._calculate_engagement_metrics(target, recent_posts)
        
        # Calculate activity patterns
        activity_metrics = self._calculate_activity_patterns(target, recent_posts)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(target, recent_followers, recent_posts)
        
        # Combine all metrics
        all_metrics = {
            **follower_metrics,
            **content_metrics,
            **engagement_metrics,
            **activity_metrics,
            **quality_metrics
        }
        
        return all_metrics
    
    def _get_recent_posts(self, target_id: int, days: int = 30) -> List[Post]:
        """Get recent posts for a target"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            with db_manager.get_session() as session:
                return session.query(Post).filter(
                    Post.target_id == target_id,
                    Post.posted_at >= cutoff
                ).order_by(Post.posted_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting recent posts: {e}")
            return []
    
    def _get_recent_followers(self, target_id: int, days: int = 7) -> List[Follower]:
        """Get recent followers for a target"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            with db_manager.get_session() as session:
                return session.query(Follower).filter(
                    Follower.target_id == target_id,
                    Follower.detected_at >= cutoff
                ).all()
        except Exception as e:
            logger.error(f"Error getting recent followers: {e}")
            return []
    
    def _calculate_follower_metrics(self, target: SurveillanceTarget, recent_followers: List[Follower]) -> Dict[str, Any]:
        """Calculate follower-related metrics"""
        # Get previous health record for comparison
        previous_metrics = self._get_previous_health_metrics(target.id)
        
        # Calculate growth rates
        follower_growth_rate = 0.0
        follower_churn_rate = 0.0
        net_follower_change = len(recent_followers)
        
        if previous_metrics:
            days_diff = (datetime.now(timezone.utc) - previous_metrics.recorded_at).days
            if days_diff > 0:
                prev_count = previous_metrics.follower_count
                current_count = target.follower_count
                
                if prev_count > 0:
                    follower_growth_rate = ((current_count - prev_count) / prev_count) * 100 / days_diff
        
        return {
            'follower_count': target.follower_count,
            'following_count': target.following_count,
            'follower_growth_rate': follower_growth_rate,
            'follower_churn_rate': follower_churn_rate,
            'net_follower_change': net_follower_change
        }
    
    def _calculate_content_metrics(self, target: SurveillanceTarget, recent_posts: List[Post]) -> Dict[str, Any]:
        """Calculate content-related metrics"""
        now = datetime.now(timezone.utc)
        
        # Count posts by time period
        posts_24h = len([p for p in recent_posts if (now - p.posted_at).days == 0])
        posts_7d = len([p for p in recent_posts if (now - p.posted_at).days <= 7])
        posts_30d = len(recent_posts)
        
        # Calculate average posting frequency
        avg_posts_per_day = posts_30d / 30 if posts_30d > 0 else 0
        
        return {
            'post_count': target.post_count,
            'posts_last_24h': posts_24h,
            'posts_last_7d': posts_7d,
            'posts_last_30d': posts_30d,
            'avg_posts_per_day': avg_posts_per_day
        }
    
    def _calculate_engagement_metrics(self, target: SurveillanceTarget, recent_posts: List[Post]) -> Dict[str, Any]:
        """Calculate engagement-related metrics"""
        if not recent_posts:
            return {
                'avg_likes_per_post': 0.0,
                'avg_comments_per_post': 0.0,
                'avg_engagement_rate': 0.0,
                'engagement_trend': 'stable'
            }
        
        # Calculate averages
        avg_likes = statistics.mean(p.like_count or 0 for p in recent_posts)
        avg_comments = statistics.mean(p.comment_count or 0 for p in recent_posts)
        
        # Calculate engagement rate
        if target.follower_count > 0:
            avg_engagement_rate = ((avg_likes + avg_comments) / target.follower_count) * 100
        else:
            avg_engagement_rate = 0.0
        
        # Determine engagement trend
        engagement_trend = self._calculate_engagement_trend(recent_posts)
        
        return {
            'avg_likes_per_post': avg_likes,
            'avg_comments_per_post': avg_comments,
            'avg_engagement_rate': avg_engagement_rate,
            'engagement_trend': engagement_trend
        }
    
    def _calculate_activity_patterns(self, target: SurveillanceTarget, recent_posts: List[Post]) -> Dict[str, Any]:
        """Calculate activity pattern metrics"""
        if not recent_posts:
            return {
                'most_active_hour': 12,
                'most_active_day': 1,
                'posting_frequency_score': 5.0
            }
        
        # Analyze posting times
        hours = [p.posted_at.hour for p in recent_posts if p.posted_at]
        days = [p.posted_at.weekday() for p in recent_posts if p.posted_at]
        
        most_active_hour = statistics.mode(hours) if hours else 12
        most_active_day = statistics.mode(days) if days else 1
        
        # Calculate posting frequency consistency (0-10 score)
        posting_frequency_score = self._calculate_posting_consistency(recent_posts)
        
        return {
            'most_active_hour': most_active_hour,
            'most_active_day': most_active_day,
            'posting_frequency_score': posting_frequency_score
        }
    
    def _calculate_quality_metrics(self, target: SurveillanceTarget, recent_followers: List[Follower], 
                                 recent_posts: List[Post]) -> Dict[str, Any]:
        """Calculate quality-related metrics"""
        # Calculate bot follower percentage
        bot_followers = [f for f in recent_followers if f.bot_probability and f.bot_probability > 0.7]
        bot_percentage = (len(bot_followers) / len(recent_followers) * 100) if recent_followers else 0.0
        
        # Calculate authentic engagement score (0-10)
        authentic_engagement_score = self._calculate_authentic_engagement_score(target, recent_posts)
        
        # Calculate content consistency score (0-10)
        content_consistency_score = self._calculate_content_consistency_score(recent_posts)
        
        return {
            'bot_follower_percentage': bot_percentage,
            'authentic_engagement_score': authentic_engagement_score,
            'content_consistency_score': content_consistency_score
        }
    
    def _get_previous_health_metrics(self, target_id: int) -> Optional[AccountHealthMetrics]:
        """Get the most recent health metrics for a target"""
        try:
            with db_manager.get_session() as session:
                return session.query(AccountHealthMetrics).filter(
                    AccountHealthMetrics.target_id == target_id
                ).order_by(AccountHealthMetrics.recorded_at.desc()).first()
        except Exception as e:
            logger.error(f"Error getting previous health metrics: {e}")
            return None
    
    def _calculate_engagement_trend(self, posts: List[Post]) -> str:
        """Calculate engagement trend from recent posts"""
        if len(posts) < 5:
            return 'stable'
        
        # Sort posts by date
        sorted_posts = sorted(posts, key=lambda p: p.posted_at or datetime.min.replace(tzinfo=timezone.utc))
        
        # Calculate engagement for each post
        engagements = []
        for post in sorted_posts:
            if post.target and post.target.follower_count > 0:
                engagement = ((post.like_count or 0) + (post.comment_count or 0)) / post.target.follower_count * 100
                engagements.append(engagement)
        
        if len(engagements) < 5:
            return 'stable'
        
        # Compare first half with second half
        mid = len(engagements) // 2
        first_half_avg = statistics.mean(engagements[:mid])
        second_half_avg = statistics.mean(engagements[mid:])
        
        change_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if change_percent > 10:
            return 'increasing'
        elif change_percent < -10:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_posting_consistency(self, posts: List[Post]) -> float:
        """Calculate posting consistency score (0-10)"""
        if len(posts) < 7:
            return 5.0  # Default score for insufficient data
        
        # Calculate time intervals between posts
        sorted_posts = sorted(posts, key=lambda p: p.posted_at or datetime.min.replace(tzinfo=timezone.utc))
        intervals = []
        
        for i in range(1, len(sorted_posts)):
            if sorted_posts[i].posted_at and sorted_posts[i-1].posted_at:
                interval = (sorted_posts[i].posted_at - sorted_posts[i-1].posted_at).total_seconds() / 3600  # hours
                intervals.append(interval)
        
        if not intervals:
            return 5.0
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_interval = statistics.mean(intervals)
        if mean_interval == 0:
            return 5.0
        
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        cv = std_interval / mean_interval
        
        # Convert to 0-10 score (lower CV = higher score)
        consistency_score = max(0, 10 - (cv * 2))
        return min(consistency_score, 10.0)
    
    def _calculate_authentic_engagement_score(self, target: SurveillanceTarget, posts: List[Post]) -> float:
        """Calculate authentic engagement score (0-10)"""
        if not posts or target.follower_count == 0:
            return 5.0
        
        # Base score from engagement rate
        total_engagement = sum((p.like_count or 0) + (p.comment_count or 0) for p in posts)
        avg_engagement_rate = (total_engagement / len(posts)) / target.follower_count * 100
        
        # Normalize to 0-10 scale (2% engagement rate = score of 10)
        base_score = min(avg_engagement_rate / 2 * 10, 10)
        
        # Adjust for posting frequency (too frequent or too rare reduces authenticity)
        posts_per_day = len(posts) / 30
        frequency_penalty = 0
        if posts_per_day > 3:  # More than 3 posts per day
            frequency_penalty = (posts_per_day - 3) * 0.5
        elif posts_per_day < 0.2:  # Less than 1 post per 5 days
            frequency_penalty = (0.2 - posts_per_day) * 10
        
        authentic_score = max(0, base_score - frequency_penalty)
        return min(authentic_score, 10.0)
    
    def _calculate_content_consistency_score(self, posts: List[Post]) -> float:
        """Calculate content consistency score (0-10)"""
        if len(posts) < 5:
            return 5.0
        
        # Analyze post types
        post_types = [p.post_type for p in posts if p.post_type]
        type_distribution = {}
        for post_type in post_types:
            type_distribution[post_type] = type_distribution.get(post_type, 0) + 1
        
        # Calculate diversity (balanced is better)
        if len(type_distribution) == 0:
            return 5.0
        
        total_posts = len(post_types)
        entropy = 0
        for count in type_distribution.values():
            p = count / total_posts
            if p > 0:
                entropy -= p * (p ** 0.5)  # Modified entropy calculation
        
        # Normalize to 0-10 scale
        max_entropy = 1.0  # Theoretical maximum for our calculation
        consistency_score = (entropy / max_entropy) * 10 if max_entropy > 0 else 5.0
        
        return min(max(consistency_score, 0), 10.0)
    
    def _check_health_alerts(self, target: SurveillanceTarget):
        """Check for health-related alerts"""
        try:
            current_metrics = self._get_previous_health_metrics(target.id)
            if not current_metrics:
                return
            
            alerts = []
            
            # Check health score thresholds
            if current_metrics.health_score < self.thresholds['health_score_critical']:
                alerts.append(HealthAlert(
                    target_id=target.id,
                    alert_type='health_score_critical',
                    severity='critical',
                    message=f"Critical health score: {current_metrics.health_score:.1f}",
                    metrics={'health_score': current_metrics.health_score},
                    timestamp=datetime.now(timezone.utc)
                ))
            elif current_metrics.health_score < self.thresholds['health_score_warning']:
                alerts.append(HealthAlert(
                    target_id=target.id,
                    alert_type='health_score_warning',
                    severity='medium',
                    message=f"Low health score: {current_metrics.health_score:.1f}",
                    metrics={'health_score': current_metrics.health_score},
                    timestamp=datetime.now(timezone.utc)
                ))
            
            # Check follower growth decline
            if (current_metrics.follower_growth_rate and 
                current_metrics.follower_growth_rate < self.thresholds['follower_growth_decline']):
                alerts.append(HealthAlert(
                    target_id=target.id,
                    alert_type='follower_decline',
                    severity='medium',
                    message=f"Follower growth declining: {current_metrics.follower_growth_rate:.1f}%",
                    metrics={'growth_rate': current_metrics.follower_growth_rate},
                    timestamp=datetime.now(timezone.utc)
                ))
            
            # Check engagement drop
            if current_metrics.engagement_trend == 'decreasing':
                alerts.append(HealthAlert(
                    target_id=target.id,
                    alert_type='engagement_decline',
                    severity='medium',
                    message=f"Engagement rate declining: {current_metrics.avg_engagement_rate:.2f}%",
                    metrics={'engagement_rate': current_metrics.avg_engagement_rate},
                    timestamp=datetime.now(timezone.utc)
                ))
            
            # Send alerts through notification system
            for alert in alerts:
                self._send_health_alert(target, alert)
                
        except Exception as e:
            logger.error(f"Error checking health alerts for {target.instagram_username}: {e}")
    
    def _send_health_alert(self, target: SurveillanceTarget, alert: HealthAlert):
        """Send health alert through notification system"""
        try:
            enhanced_notification_manager.alert_data_quality_issue(
                target_username=target.instagram_username,
                quality_score=alert.metrics.get('health_score', 0) / 100,  # Convert to 0-1 scale
                issues=[alert.message]
            )
            
            logger.info(f"Health alert sent for {target.instagram_username}: {alert.message}")
            
        except Exception as e:
            logger.error(f"Error sending health alert: {e}")
    
    def get_health_summary(self, target_id: int, days: int = 30) -> Dict[str, Any]:
        """Get health summary for a target"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            with db_manager.get_session() as session:
                metrics = session.query(AccountHealthMetrics).filter(
                    AccountHealthMetrics.target_id == target_id,
                    AccountHealthMetrics.recorded_at >= cutoff
                ).order_by(AccountHealthMetrics.recorded_at.desc()).all()
                
                if not metrics:
                    return {'error': 'No health data available'}
                
                latest = metrics[0]
                
                # Calculate trends
                health_trend = 'stable'
                if len(metrics) > 1:
                    recent_avg = statistics.mean(m.health_score for m in metrics[:5])
                    older_avg = statistics.mean(m.health_score for m in metrics[-5:])
                    
                    change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
                    
                    if change > 10:
                        health_trend = 'improving'
                    elif change < -10:
                        health_trend = 'declining'
                
                return {
                    'current_health_score': latest.health_score,
                    'health_trend': health_trend,
                    'follower_count': latest.follower_count,
                    'follower_growth_rate': latest.follower_growth_rate,
                    'avg_engagement_rate': latest.avg_engagement_rate,
                    'engagement_trend': latest.engagement_trend,
                    'bot_follower_percentage': latest.bot_follower_percentage,
                    'authentic_engagement_score': latest.authentic_engagement_score,
                    'content_consistency_score': latest.content_consistency_score,
                    'last_updated': latest.recorded_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {'error': str(e)}

# Global health monitor instance
account_health_monitor = AccountHealthMonitor()
