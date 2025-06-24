"""
Social Media Surveillance System - Pattern Detection Engine
Advanced algorithms for detecting behavioral patterns, anomalies, trends,
and network analysis in social media surveillance data.
"""

import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import math
import re

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from core.database import db_manager
from models.instagram_models import SurveillanceTarget, Post, Follower, Story, ChangeLog

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class PatternResult:
    """Container for pattern detection results"""
    pattern_type: str
    confidence: float
    description: str
    data: Dict[str, Any]
    detected_at: datetime
    severity: str  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'pattern_type': self.pattern_type,
            'confidence': self.confidence,
            'description': self.description,
            'data': self.data,
            'detected_at': self.detected_at.isoformat(),
            'severity': self.severity
        }

@dataclass
class AnomalyResult:
    """Container for anomaly detection results"""
    anomaly_type: str
    score: float
    threshold: float
    description: str
    affected_metrics: List[str]
    time_period: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'anomaly_type': self.anomaly_type,
            'score': self.score,
            'threshold': self.threshold,
            'description': self.description,
            'affected_metrics': self.affected_metrics,
            'time_period': self.time_period
        }

class FollowerPatternAnalyzer:
    """Analyze follower patterns and demographics"""
    
    def __init__(self):
        logger.info("Follower pattern analyzer initialized")
    
    def analyze_follower_growth_patterns(self, target_id: int, days: int = 30) -> List[PatternResult]:
        """
        Analyze follower growth patterns for anomalies and trends
        
        Args:
            target_id: Target surveillance ID
            days: Number of days to analyze
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        try:
            with db_manager.get_session() as session:
                # Get follower data for the specified period
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                followers = session.query(Follower).filter(
                    Follower.target_id == target_id,
                    Follower.detected_at >= cutoff_date
                ).order_by(Follower.detected_at).all()
                
                if len(followers) < 5:  # Need minimum data points
                    return patterns
                
                # Analyze growth rate patterns
                daily_growth = self._calculate_daily_growth(followers)
                growth_patterns = self._detect_growth_anomalies(daily_growth)
                patterns.extend(growth_patterns)
                
                # Analyze follower quality patterns
                quality_patterns = self._analyze_follower_quality_patterns(followers)
                patterns.extend(quality_patterns)
                
                # Analyze temporal patterns
                temporal_patterns = self._analyze_follower_temporal_patterns(followers)
                patterns.extend(temporal_patterns)
                
        except Exception as e:
            logger.error(f"Follower growth pattern analysis failed: {e}")
        
        return patterns
    
    def analyze_bot_patterns(self, target_id: int) -> List[PatternResult]:
        """
        Analyze patterns in bot followers
        
        Args:
            target_id: Target surveillance ID
            
        Returns:
            List of bot-related patterns
        """
        patterns = []
        
        try:
            with db_manager.get_session() as session:
                # Get followers with bot probability data
                followers = session.query(Follower).filter(
                    Follower.target_id == target_id,
                    Follower.bot_probability.isnot(None)
                ).all()
                
                if not followers:
                    return patterns
                
                # Calculate bot statistics
                bot_probabilities = [f.bot_probability for f in followers if f.bot_probability is not None]
                high_bot_probability = [p for p in bot_probabilities if p > 0.7]
                
                if len(high_bot_probability) > len(bot_probabilities) * 0.3:  # More than 30% likely bots
                    patterns.append(PatternResult(
                        pattern_type="high_bot_ratio",
                        confidence=0.8,
                        description=f"High ratio of bot followers detected: {len(high_bot_probability)}/{len(followers)} ({len(high_bot_probability)/len(followers)*100:.1f}%)",
                        data={
                            'total_followers': len(followers),
                            'likely_bots': len(high_bot_probability),
                            'bot_ratio': len(high_bot_probability) / len(followers),
                            'average_bot_probability': statistics.mean(bot_probabilities)
                        },
                        detected_at=datetime.now(timezone.utc),
                        severity="high"
                    ))
                
                # Analyze bot clustering patterns
                bot_clusters = self._detect_bot_clusters(followers)
                patterns.extend(bot_clusters)
                
        except Exception as e:
            logger.error(f"Bot pattern analysis failed: {e}")
        
        return patterns
    
    def analyze_influence_network(self, target_id: int) -> Dict[str, Any]:
        """
        Analyze influence network and connections
        
        Args:
            target_id: Target surveillance ID
            
        Returns:
            Network analysis results
        """
        try:
            with db_manager.get_session() as session:
                # Get followers with influence scores
                followers = session.query(Follower).filter(
                    Follower.target_id == target_id,
                    Follower.influence_score.isnot(None)
                ).all()
                
                if not followers:
                    return {'error': 'No influence data available'}
                
                # Calculate network metrics
                influence_scores = [f.influence_score for f in followers if f.influence_score is not None]
                
                network_analysis = {
                    'total_followers': len(followers),
                    'average_influence': statistics.mean(influence_scores),
                    'median_influence': statistics.median(influence_scores),
                    'high_influence_followers': len([s for s in influence_scores if s > 7.0]),
                    'influence_distribution': self._calculate_influence_distribution(influence_scores),
                    'network_strength': self._calculate_network_strength(influence_scores),
                    'key_influencers': self._identify_key_influencers(followers)
                }
                
                return network_analysis
                
        except Exception as e:
            logger.error(f"Influence network analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_daily_growth(self, followers: List[Follower]) -> Dict[str, int]:
        """Calculate daily follower growth"""
        daily_counts = defaultdict(int)
        
        for follower in followers:
            if follower.detected_at:
                date_key = follower.detected_at.date().isoformat()
                daily_counts[date_key] += 1
        
        return dict(daily_counts)
    
    def _detect_growth_anomalies(self, daily_growth: Dict[str, int]) -> List[PatternResult]:
        """Detect anomalies in growth patterns"""
        patterns = []
        
        if len(daily_growth) < 7:  # Need at least a week of data
            return patterns
        
        growth_values = list(daily_growth.values())
        mean_growth = statistics.mean(growth_values)
        std_growth = statistics.stdev(growth_values) if len(growth_values) > 1 else 0
        
        # Detect spikes (values > mean + 2*std)
        threshold = mean_growth + 2 * std_growth
        
        for date, count in daily_growth.items():
            if count > threshold and count > mean_growth * 3:  # Significant spike
                patterns.append(PatternResult(
                    pattern_type="follower_spike",
                    confidence=0.9,
                    description=f"Unusual follower spike detected on {date}: {count} new followers (avg: {mean_growth:.1f})",
                    data={
                        'date': date,
                        'follower_count': count,
                        'average_growth': mean_growth,
                        'spike_ratio': count / mean_growth if mean_growth > 0 else 0
                    },
                    detected_at=datetime.now(timezone.utc),
                    severity="medium"
                ))
        
        return patterns
    
    def _analyze_follower_quality_patterns(self, followers: List[Follower]) -> List[PatternResult]:
        """Analyze patterns in follower quality"""
        patterns = []
        
        # Analyze verification patterns
        verified_count = sum(1 for f in followers if f.is_verified)
        if verified_count > len(followers) * 0.1:  # More than 10% verified
            patterns.append(PatternResult(
                pattern_type="high_verified_ratio",
                confidence=0.7,
                description=f"High ratio of verified followers: {verified_count}/{len(followers)} ({verified_count/len(followers)*100:.1f}%)",
                data={
                    'verified_count': verified_count,
                    'total_followers': len(followers),
                    'verified_ratio': verified_count / len(followers)
                },
                detected_at=datetime.now(timezone.utc),
                severity="low"
            ))
        
        # Analyze follower count patterns
        follower_counts = [f.follower_count for f in followers if f.follower_count is not None]
        if follower_counts:
            avg_follower_count = statistics.mean(follower_counts)
            high_follower_accounts = [c for c in follower_counts if c > 10000]
            
            if len(high_follower_accounts) > len(follower_counts) * 0.05:  # More than 5% have >10k followers
                patterns.append(PatternResult(
                    pattern_type="high_influence_followers",
                    confidence=0.8,
                    description=f"High number of influential followers detected: {len(high_follower_accounts)} accounts with >10k followers",
                    data={
                        'high_influence_count': len(high_follower_accounts),
                        'total_analyzed': len(follower_counts),
                        'average_follower_count': avg_follower_count
                    },
                    detected_at=datetime.now(timezone.utc),
                    severity="low"
                ))
        
        return patterns
    
    def _analyze_follower_temporal_patterns(self, followers: List[Follower]) -> List[PatternResult]:
        """Analyze temporal patterns in follower acquisition"""
        patterns = []
        
        # Analyze hourly patterns
        hours = []
        for follower in followers:
            if follower.detected_at:
                hours.append(follower.detected_at.hour)
        
        if hours:
            hour_counts = Counter(hours)
            peak_hours = hour_counts.most_common(3)
            
            # Check for unusual concentration in specific hours
            total_followers = len(hours)
            for hour, count in peak_hours:
                if count > total_followers * 0.3:  # More than 30% in one hour
                    patterns.append(PatternResult(
                        pattern_type="temporal_clustering",
                        confidence=0.7,
                        description=f"Unusual temporal clustering: {count} followers ({count/total_followers*100:.1f}%) acquired at hour {hour}",
                        data={
                            'peak_hour': hour,
                            'follower_count': count,
                            'concentration_ratio': count / total_followers,
                            'hour_distribution': dict(hour_counts)
                        },
                        detected_at=datetime.now(timezone.utc),
                        severity="medium"
                    ))
        
        return patterns

    def _detect_bot_clusters(self, followers: List[Follower]) -> List[PatternResult]:
        """Detect clusters of bot accounts"""
        patterns = []

        # Group followers by similar characteristics
        username_patterns = defaultdict(list)

        for follower in followers:
            if follower.bot_probability and follower.bot_probability > 0.7:
                # Analyze username patterns
                username = follower.follower_username.lower()

                # Check for common bot patterns
                if re.match(r'^[a-z]+\d+$', username):  # letters followed by numbers
                    username_patterns['letters_numbers'].append(follower)
                elif re.match(r'^[a-z]+_[a-z]+\d*$', username):  # word_word pattern
                    username_patterns['word_underscore_word'].append(follower)
                elif len(username) < 6:  # very short usernames
                    username_patterns['short_username'].append(follower)

        # Report significant clusters
        for pattern_type, cluster_followers in username_patterns.items():
            if len(cluster_followers) > 5:  # Significant cluster
                patterns.append(PatternResult(
                    pattern_type="bot_cluster",
                    confidence=0.8,
                    description=f"Bot cluster detected: {len(cluster_followers)} accounts with {pattern_type} pattern",
                    data={
                        'cluster_type': pattern_type,
                        'cluster_size': len(cluster_followers),
                        'usernames': [f.follower_username for f in cluster_followers[:10]]  # First 10
                    },
                    detected_at=datetime.now(timezone.utc),
                    severity="medium"
                ))

        return patterns

    def _calculate_influence_distribution(self, influence_scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of influence scores"""
        distribution = {
            'low_influence': len([s for s in influence_scores if s < 3.0]),
            'medium_influence': len([s for s in influence_scores if 3.0 <= s < 7.0]),
            'high_influence': len([s for s in influence_scores if s >= 7.0])
        }
        return distribution

    def _calculate_network_strength(self, influence_scores: List[float]) -> float:
        """Calculate overall network strength score"""
        if not influence_scores:
            return 0.0

        # Weighted average giving more weight to higher influence scores
        weighted_sum = sum(score ** 1.5 for score in influence_scores)
        max_possible = len(influence_scores) * (10 ** 1.5)  # Max score is 10

        return min(1.0, weighted_sum / max_possible)

    def _identify_key_influencers(self, followers: List[Follower]) -> List[Dict[str, Any]]:
        """Identify key influencers among followers"""
        key_influencers = []

        # Sort by influence score
        sorted_followers = sorted(
            [f for f in followers if f.influence_score and f.influence_score > 7.0],
            key=lambda x: x.influence_score,
            reverse=True
        )

        # Take top 10 influencers
        for follower in sorted_followers[:10]:
            key_influencers.append({
                'username': follower.follower_username,
                'display_name': follower.follower_display_name,
                'influence_score': follower.influence_score,
                'follower_count': follower.follower_count,
                'is_verified': follower.is_verified
            })

        return key_influencers

class ContentPatternAnalyzer:
    """Analyze patterns in content posting and engagement"""

    def __init__(self):
        logger.info("Content pattern analyzer initialized")

    def analyze_posting_patterns(self, target_id: int, days: int = 30) -> List[PatternResult]:
        """
        Analyze posting frequency and timing patterns

        Args:
            target_id: Target surveillance ID
            days: Number of days to analyze

        Returns:
            List of detected patterns
        """
        patterns = []

        try:
            with db_manager.get_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                posts = session.query(Post).filter(
                    Post.target_id == target_id,
                    Post.posted_at >= cutoff_date
                ).order_by(Post.posted_at).all()

                if len(posts) < 5:
                    return patterns

                # Analyze posting frequency
                frequency_patterns = self._analyze_posting_frequency(posts)
                patterns.extend(frequency_patterns)

                # Analyze posting times
                timing_patterns = self._analyze_posting_times(posts)
                patterns.extend(timing_patterns)

                # Analyze content type patterns
                content_patterns = self._analyze_content_type_patterns(posts)
                patterns.extend(content_patterns)

        except Exception as e:
            logger.error(f"Posting pattern analysis failed: {e}")

        return patterns

    def analyze_engagement_patterns(self, target_id: int, days: int = 30) -> List[PatternResult]:
        """
        Analyze engagement patterns and anomalies

        Args:
            target_id: Target surveillance ID
            days: Number of days to analyze

        Returns:
            List of detected patterns
        """
        patterns = []

        try:
            with db_manager.get_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                posts = session.query(Post).filter(
                    Post.target_id == target_id,
                    Post.posted_at >= cutoff_date,
                    Post.like_count.isnot(None)
                ).all()

                if len(posts) < 5:
                    return patterns

                # Analyze engagement rates
                engagement_patterns = self._analyze_engagement_rates(posts)
                patterns.extend(engagement_patterns)

                # Analyze engagement timing
                timing_patterns = self._analyze_engagement_timing(posts)
                patterns.extend(timing_patterns)

        except Exception as e:
            logger.error(f"Engagement pattern analysis failed: {e}")

        return patterns

    def _analyze_posting_frequency(self, posts: List[Post]) -> List[PatternResult]:
        """Analyze posting frequency patterns"""
        patterns = []

        # Calculate daily posting frequency
        daily_posts = defaultdict(int)
        for post in posts:
            if post.posted_at:
                date_key = post.posted_at.date().isoformat()
                daily_posts[date_key] += 1

        if len(daily_posts) < 7:
            return patterns

        post_counts = list(daily_posts.values())
        avg_posts_per_day = statistics.mean(post_counts)

        # Detect unusual posting frequency
        if avg_posts_per_day > 5:  # More than 5 posts per day on average
            patterns.append(PatternResult(
                pattern_type="high_posting_frequency",
                confidence=0.8,
                description=f"High posting frequency detected: {avg_posts_per_day:.1f} posts per day on average",
                data={
                    'average_posts_per_day': avg_posts_per_day,
                    'total_posts': len(posts),
                    'analysis_days': len(daily_posts),
                    'max_posts_single_day': max(post_counts)
                },
                detected_at=datetime.now(timezone.utc),
                severity="medium"
            ))

        return patterns

    def _analyze_posting_times(self, posts: List[Post]) -> List[PatternResult]:
        """Analyze posting time patterns"""
        patterns = []

        hours = [post.posted_at.hour for post in posts if post.posted_at]
        if not hours:
            return patterns

        hour_counts = Counter(hours)
        total_posts = len(hours)

        # Check for unusual concentration in specific hours
        for hour, count in hour_counts.most_common(3):
            if count > total_posts * 0.4:  # More than 40% in one hour
                patterns.append(PatternResult(
                    pattern_type="posting_time_clustering",
                    confidence=0.7,
                    description=f"Posting time clustering: {count} posts ({count/total_posts*100:.1f}%) at hour {hour}",
                    data={
                        'peak_hour': hour,
                        'post_count': count,
                        'concentration_ratio': count / total_posts,
                        'hour_distribution': dict(hour_counts)
                    },
                    detected_at=datetime.now(timezone.utc),
                    severity="low"
                ))

        return patterns

    def _analyze_content_type_patterns(self, posts: List[Post]) -> List[PatternResult]:
        """Analyze content type distribution patterns"""
        patterns = []

        type_counts = Counter(post.post_type for post in posts)
        total_posts = len(posts)

        # Check for unusual content type distribution
        for post_type, count in type_counts.items():
            ratio = count / total_posts
            if ratio > 0.8:  # More than 80% of one type
                patterns.append(PatternResult(
                    pattern_type="content_type_dominance",
                    confidence=0.6,
                    description=f"Content type dominance: {count} {post_type} posts ({ratio*100:.1f}% of all posts)",
                    data={
                        'dominant_type': post_type,
                        'count': count,
                        'ratio': ratio,
                        'type_distribution': dict(type_counts)
                    },
                    detected_at=datetime.now(timezone.utc),
                    severity="low"
                ))

        return patterns

    def _analyze_engagement_rates(self, posts: List[Post]) -> List[PatternResult]:
        """Analyze engagement rate patterns"""
        patterns = []

        # Calculate engagement rates
        engagement_rates = []
        for post in posts:
            if post.target and post.target.follower_count > 0:
                total_engagement = (post.like_count or 0) + (post.comment_count or 0)
                rate = total_engagement / post.target.follower_count
                engagement_rates.append(rate)

        if len(engagement_rates) < 5:
            return patterns

        avg_rate = statistics.mean(engagement_rates)

        # Detect unusually high engagement rates
        high_engagement_posts = [rate for rate in engagement_rates if rate > avg_rate * 3]
        if len(high_engagement_posts) > len(engagement_rates) * 0.2:  # More than 20% have high engagement
            patterns.append(PatternResult(
                pattern_type="high_engagement_pattern",
                confidence=0.7,
                description=f"High engagement pattern: {len(high_engagement_posts)} posts with >3x average engagement",
                data={
                    'high_engagement_count': len(high_engagement_posts),
                    'total_posts': len(engagement_rates),
                    'average_engagement_rate': avg_rate,
                    'high_engagement_threshold': avg_rate * 3
                },
                detected_at=datetime.now(timezone.utc),
                severity="low"
            ))

        return patterns

    def _analyze_engagement_timing(self, posts: List[Post]) -> List[PatternResult]:
        """Analyze engagement timing patterns"""
        patterns = []

        # This would require tracking engagement over time
        # For now, return empty list as this requires more complex data
        return patterns

class AnomalyDetector:
    """Detect anomalies in surveillance data"""

    def __init__(self):
        logger.info("Anomaly detector initialized")

    def detect_anomalies(self, target_id: int, days: int = 30) -> List[AnomalyResult]:
        """
        Detect various types of anomalies

        Args:
            target_id: Target surveillance ID
            days: Number of days to analyze

        Returns:
            List of detected anomalies
        """
        anomalies = []

        try:
            # Detect follower count anomalies
            follower_anomalies = self._detect_follower_anomalies(target_id, days)
            anomalies.extend(follower_anomalies)

            # Detect engagement anomalies
            engagement_anomalies = self._detect_engagement_anomalies(target_id, days)
            anomalies.extend(engagement_anomalies)

            # Detect posting frequency anomalies
            posting_anomalies = self._detect_posting_anomalies(target_id, days)
            anomalies.extend(posting_anomalies)

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")

        return anomalies

    def _detect_follower_anomalies(self, target_id: int, days: int) -> List[AnomalyResult]:
        """Detect anomalies in follower growth"""
        anomalies = []

        try:
            with db_manager.get_session() as session:
                # Get follower growth data
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                daily_growth = session.query(
                    func.date(Follower.detected_at).label('date'),
                    func.count(Follower.id).label('count')
                ).filter(
                    Follower.target_id == target_id,
                    Follower.detected_at >= cutoff_date
                ).group_by(func.date(Follower.detected_at)).all()

                if len(daily_growth) < 7:
                    return anomalies

                growth_values = [row.count for row in daily_growth]
                mean_growth = statistics.mean(growth_values)
                std_growth = statistics.stdev(growth_values) if len(growth_values) > 1 else 0

                # Z-score based anomaly detection
                threshold = 2.0  # 2 standard deviations

                for row in daily_growth:
                    if std_growth > 0:
                        z_score = abs(row.count - mean_growth) / std_growth
                        if z_score > threshold:
                            anomalies.append(AnomalyResult(
                                anomaly_type="follower_growth_anomaly",
                                score=z_score,
                                threshold=threshold,
                                description=f"Unusual follower growth on {row.date}: {row.count} new followers (z-score: {z_score:.2f})",
                                affected_metrics=["follower_count"],
                                time_period={
                                    "date": str(row.date),
                                    "analysis_window": f"{days} days"
                                }
                            ))

        except Exception as e:
            logger.error(f"Follower anomaly detection failed: {e}")

        return anomalies

    def _detect_engagement_anomalies(self, target_id: int, days: int) -> List[AnomalyResult]:
        """Detect anomalies in engagement patterns"""
        # Placeholder for engagement anomaly detection
        return []

    def _detect_posting_anomalies(self, target_id: int, days: int) -> List[AnomalyResult]:
        """Detect anomalies in posting patterns"""
        # Placeholder for posting anomaly detection
        return []

class PatternDetector:
    """Main pattern detection engine"""

    def __init__(self):
        self.follower_analyzer = FollowerPatternAnalyzer()
        self.content_analyzer = ContentPatternAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        logger.info("Pattern detector initialized")

    def analyze_target_patterns(self, target_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Comprehensive pattern analysis for a target

        Args:
            target_id: Target surveillance ID
            days: Number of days to analyze

        Returns:
            Dictionary with all pattern analysis results
        """
        results = {
            'target_id': target_id,
            'analysis_period_days': days,
            'analyzed_at': datetime.now(timezone.utc).isoformat(),
            'follower_patterns': [],
            'content_patterns': [],
            'anomalies': [],
            'summary': {}
        }

        try:
            # Analyze follower patterns
            results['follower_patterns'] = [
                pattern.to_dict() for pattern in
                self.follower_analyzer.analyze_follower_growth_patterns(target_id, days)
            ]

            # Analyze bot patterns
            bot_patterns = self.follower_analyzer.analyze_bot_patterns(target_id)
            results['follower_patterns'].extend([pattern.to_dict() for pattern in bot_patterns])

            # Analyze content patterns
            posting_patterns = self.content_analyzer.analyze_posting_patterns(target_id, days)
            engagement_patterns = self.content_analyzer.analyze_engagement_patterns(target_id, days)

            results['content_patterns'] = [
                pattern.to_dict() for pattern in posting_patterns + engagement_patterns
            ]

            # Detect anomalies
            results['anomalies'] = [
                anomaly.to_dict() for anomaly in
                self.anomaly_detector.detect_anomalies(target_id, days)
            ]

            # Generate summary
            results['summary'] = self._generate_analysis_summary(results)

        except Exception as e:
            logger.error(f"Pattern analysis failed for target {target_id}: {e}")
            results['error'] = str(e)

        return results

    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of pattern analysis"""
        summary = {
            'total_patterns_detected': len(results['follower_patterns']) + len(results['content_patterns']),
            'total_anomalies_detected': len(results['anomalies']),
            'severity_breakdown': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
            'pattern_types': set(),
            'risk_level': 'low'
        }

        # Count patterns by severity
        all_patterns = results['follower_patterns'] + results['content_patterns']
        for pattern in all_patterns:
            severity = pattern.get('severity', 'low')
            summary['severity_breakdown'][severity] += 1
            summary['pattern_types'].add(pattern.get('pattern_type', 'unknown'))

        # Convert set to list for JSON serialization
        summary['pattern_types'] = list(summary['pattern_types'])

        # Determine overall risk level
        if summary['severity_breakdown']['critical'] > 0:
            summary['risk_level'] = 'critical'
        elif summary['severity_breakdown']['high'] > 0:
            summary['risk_level'] = 'high'
        elif summary['severity_breakdown']['medium'] > 0:
            summary['risk_level'] = 'medium'

        return summary

# Global pattern detector instance
pattern_detector = PatternDetector()
