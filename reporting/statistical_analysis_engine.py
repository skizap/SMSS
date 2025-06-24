#!/usr/bin/env python3
"""
Social Media Surveillance System - Statistical Analysis Engine
Advanced data aggregation and statistical analysis with trend detection and forecasting.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import statistics
from scipy import stats
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

from core.config import config
from core.database import db_manager
from models.instagram_models import SurveillanceTarget, Post, Follower
from models.analytics_models import (
    ScrapingMetrics, AccountHealthMetrics, TrendAnalysis, 
    create_trend_analysis
)

logger = logging.getLogger(__name__)

class TrendDirection(Enum):
    """Trend direction enumeration"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"

class AnomalyType(Enum):
    """Anomaly type enumeration"""
    SPIKE = "spike"
    DROP = "drop"
    OUTLIER = "outlier"
    PATTERN_BREAK = "pattern_break"

@dataclass
class StatisticalSummary:
    """Statistical summary of a dataset"""
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    q1: float
    q3: float
    skewness: float
    kurtosis: float
    
    @property
    def iqr(self) -> float:
        """Interquartile range"""
        return self.q3 - self.q1
    
    @property
    def coefficient_of_variation(self) -> float:
        """Coefficient of variation"""
        return self.std_dev / self.mean if self.mean != 0 else 0

@dataclass
class TrendAnalysisResult:
    """Result of trend analysis"""
    direction: TrendDirection
    strength: float  # 0-1
    slope: float
    r_squared: float
    p_value: float
    confidence_interval: Tuple[float, float]
    forecast_values: List[float]
    change_percentage: float

@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection"""
    anomalies: List[Dict[str, Any]]
    anomaly_score: float
    threshold: float
    method_used: str

class StatisticalAnalysisEngine:
    """Advanced statistical analysis engine for Instagram data"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_threshold = 2.5  # Z-score threshold for anomaly detection
        self.trend_window = 30  # Days for trend analysis
        self.forecast_periods = 7  # Days to forecast
        
    def calculate_statistical_summary(self, data: List[float]) -> StatisticalSummary:
        """Calculate comprehensive statistical summary"""
        if not data or len(data) == 0:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        data_array = np.array(data)
        
        return StatisticalSummary(
            count=len(data),
            mean=float(np.mean(data_array)),
            median=float(np.median(data_array)),
            std_dev=float(np.std(data_array)),
            min_value=float(np.min(data_array)),
            max_value=float(np.max(data_array)),
            q1=float(np.percentile(data_array, 25)),
            q3=float(np.percentile(data_array, 75)),
            skewness=float(stats.skew(data_array)),
            kurtosis=float(stats.kurtosis(data_array))
        )
    
    def analyze_time_series_trend(self, timestamps: List[datetime], values: List[float]) -> TrendAnalysisResult:
        """Analyze trend in time series data"""
        if len(timestamps) != len(values) or len(values) < 3:
            return TrendAnalysisResult(
                direction=TrendDirection.STABLE,
                strength=0.0,
                slope=0.0,
                r_squared=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                forecast_values=[],
                change_percentage=0.0
            )
        
        # Convert timestamps to numeric values (days since first timestamp)
        first_timestamp = min(timestamps)
        x = np.array([(ts - first_timestamp).total_seconds() / 86400 for ts in timestamps])
        y = np.array(values)
        
        # Perform linear regression
        model = LinearRegression()
        X = x.reshape(-1, 1)
        model.fit(X, y)
        
        # Calculate statistics
        y_pred = model.predict(X)
        r_squared = r2_score(y, y_pred)
        
        # Calculate p-value for slope significance
        slope = model.coef_[0]
        n = len(y)
        if n > 2:
            mse = mean_squared_error(y, y_pred)
            se_slope = np.sqrt(mse / np.sum((x - np.mean(x))**2))
            t_stat = slope / se_slope if se_slope > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        else:
            p_value = 1.0
        
        # Determine trend direction and strength
        direction = self._determine_trend_direction(slope, p_value, r_squared)
        strength = min(abs(r_squared), 1.0)
        
        # Calculate confidence interval for slope
        if n > 2 and se_slope > 0:
            t_critical = stats.t.ppf(0.975, n - 2)
            margin_error = t_critical * se_slope
            confidence_interval = (slope - margin_error, slope + margin_error)
        else:
            confidence_interval = (slope, slope)
        
        # Generate forecast
        forecast_values = self._generate_forecast(model, x, self.forecast_periods)
        
        # Calculate change percentage
        if len(values) >= 2:
            change_percentage = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
        else:
            change_percentage = 0.0
        
        return TrendAnalysisResult(
            direction=direction,
            strength=strength,
            slope=slope,
            r_squared=r_squared,
            p_value=p_value,
            confidence_interval=confidence_interval,
            forecast_values=forecast_values,
            change_percentage=change_percentage
        )
    
    def detect_anomalies(self, data: List[float], method: str = "zscore") -> AnomalyDetectionResult:
        """Detect anomalies in data using various methods"""
        if not data or len(data) < 3:
            return AnomalyDetectionResult([], 0.0, 0.0, method)
        
        data_array = np.array(data)
        anomalies = []
        
        if method == "zscore":
            anomalies, threshold = self._detect_zscore_anomalies(data_array)
        elif method == "iqr":
            anomalies, threshold = self._detect_iqr_anomalies(data_array)
        elif method == "isolation_forest":
            anomalies, threshold = self._detect_isolation_forest_anomalies(data_array)
        elif method == "dbscan":
            anomalies, threshold = self._detect_dbscan_anomalies(data_array)
        else:
            # Default to z-score
            anomalies, threshold = self._detect_zscore_anomalies(data_array)
        
        # Calculate overall anomaly score
        anomaly_score = len(anomalies) / len(data) if data else 0.0
        
        return AnomalyDetectionResult(
            anomalies=anomalies,
            anomaly_score=anomaly_score,
            threshold=threshold,
            method_used=method
        )
    
    def analyze_correlation(self, x_data: List[float], y_data: List[float]) -> Dict[str, float]:
        """Analyze correlation between two datasets"""
        if len(x_data) != len(y_data) or len(x_data) < 3:
            return {
                'pearson_correlation': 0.0,
                'spearman_correlation': 0.0,
                'kendall_correlation': 0.0,
                'p_value_pearson': 1.0,
                'p_value_spearman': 1.0
            }
        
        x_array = np.array(x_data)
        y_array = np.array(y_data)
        
        # Pearson correlation
        pearson_corr, pearson_p = stats.pearsonr(x_array, y_array)
        
        # Spearman correlation
        spearman_corr, spearman_p = stats.spearmanr(x_array, y_array)
        
        # Kendall correlation
        kendall_corr, _ = stats.kendalltau(x_array, y_array)
        
        return {
            'pearson_correlation': float(pearson_corr),
            'spearman_correlation': float(spearman_corr),
            'kendall_correlation': float(kendall_corr),
            'p_value_pearson': float(pearson_p),
            'p_value_spearman': float(spearman_p)
        }
    
    def detect_seasonal_patterns(self, timestamps: List[datetime], values: List[float]) -> Dict[str, Any]:
        """Detect seasonal patterns in time series data"""
        if len(timestamps) != len(values) or len(values) < 14:  # Need at least 2 weeks
            return {'has_pattern': False, 'pattern_type': None, 'strength': 0.0}
        
        # Create DataFrame for easier manipulation
        df = pd.DataFrame({
            'timestamp': timestamps,
            'value': values
        })
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        
        patterns = {}
        
        # Hourly patterns
        hourly_means = df.groupby('hour')['value'].mean()
        hourly_std = df.groupby('hour')['value'].std()
        hourly_cv = hourly_std / hourly_means
        patterns['hourly'] = {
            'strength': float(1 - hourly_cv.mean()) if not hourly_cv.isna().all() else 0.0,
            'peak_hours': hourly_means.nlargest(3).index.tolist(),
            'low_hours': hourly_means.nsmallest(3).index.tolist()
        }
        
        # Daily patterns
        daily_means = df.groupby('day_of_week')['value'].mean()
        daily_std = df.groupby('day_of_week')['value'].std()
        daily_cv = daily_std / daily_means
        patterns['daily'] = {
            'strength': float(1 - daily_cv.mean()) if not daily_cv.isna().all() else 0.0,
            'peak_days': daily_means.nlargest(2).index.tolist(),
            'low_days': daily_means.nsmallest(2).index.tolist()
        }
        
        # Determine strongest pattern
        strongest_pattern = max(patterns.keys(), key=lambda k: patterns[k]['strength'])
        max_strength = patterns[strongest_pattern]['strength']
        
        return {
            'has_pattern': max_strength > 0.3,
            'pattern_type': strongest_pattern if max_strength > 0.3 else None,
            'strength': max_strength,
            'patterns': patterns
        }
    
    def calculate_growth_metrics(self, values: List[float], periods: List[datetime]) -> Dict[str, float]:
        """Calculate various growth metrics"""
        if len(values) < 2 or len(values) != len(periods):
            return {
                'total_growth_rate': 0.0,
                'average_growth_rate': 0.0,
                'compound_annual_growth_rate': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0
            }
        
        # Calculate period-over-period growth rates
        growth_rates = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                growth_rate = (values[i] - values[i-1]) / values[i-1]
                growth_rates.append(growth_rate)
        
        if not growth_rates:
            return {
                'total_growth_rate': 0.0,
                'average_growth_rate': 0.0,
                'compound_annual_growth_rate': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0
            }
        
        # Total growth rate
        total_growth = (values[-1] - values[0]) / values[0] if values[0] != 0 else 0.0
        
        # Average growth rate
        avg_growth = statistics.mean(growth_rates)
        
        # Compound Annual Growth Rate (CAGR)
        time_span = (periods[-1] - periods[0]).days / 365.25
        if time_span > 0 and values[0] > 0:
            cagr = (values[-1] / values[0]) ** (1 / time_span) - 1
        else:
            cagr = 0.0
        
        # Volatility (standard deviation of growth rates)
        volatility = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0.0
        
        # Maximum drawdown
        peak = values[0]
        max_drawdown = 0.0
        for value in values[1:]:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_growth_rate': total_growth,
            'average_growth_rate': avg_growth,
            'compound_annual_growth_rate': cagr,
            'volatility': volatility,
            'max_drawdown': max_drawdown
        }
    
    def _determine_trend_direction(self, slope: float, p_value: float, r_squared: float) -> TrendDirection:
        """Determine trend direction based on slope and statistical significance"""
        # Check if trend is statistically significant
        if p_value > 0.05 or r_squared < 0.1:
            return TrendDirection.STABLE
        
        # Check for high volatility
        if r_squared < 0.3:
            return TrendDirection.VOLATILE
        
        # Determine direction based on slope
        if slope > 0:
            return TrendDirection.INCREASING
        elif slope < 0:
            return TrendDirection.DECREASING
        else:
            return TrendDirection.STABLE
    
    def _generate_forecast(self, model: LinearRegression, x_data: np.ndarray, periods: int) -> List[float]:
        """Generate forecast values using the fitted model"""
        if len(x_data) == 0:
            return []
        
        last_x = x_data[-1]
        forecast_x = np.array([last_x + i + 1 for i in range(periods)])
        forecast_values = model.predict(forecast_x.reshape(-1, 1))
        
        return [max(0, float(val)) for val in forecast_values]  # Ensure non-negative values
    
    def _detect_zscore_anomalies(self, data: np.ndarray) -> Tuple[List[Dict[str, Any]], float]:
        """Detect anomalies using Z-score method"""
        mean_val = np.mean(data)
        std_val = np.std(data)
        
        if std_val == 0:
            return [], 0.0
        
        z_scores = np.abs((data - mean_val) / std_val)
        anomaly_indices = np.where(z_scores > self.anomaly_threshold)[0]
        
        anomalies = []
        for idx in anomaly_indices:
            anomaly_type = AnomalyType.SPIKE if data[idx] > mean_val else AnomalyType.DROP
            anomalies.append({
                'index': int(idx),
                'value': float(data[idx]),
                'z_score': float(z_scores[idx]),
                'type': anomaly_type.value
            })
        
        return anomalies, self.anomaly_threshold
    
    def _detect_iqr_anomalies(self, data: np.ndarray) -> Tuple[List[Dict[str, Any]], float]:
        """Detect anomalies using Interquartile Range method"""
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomaly_indices = np.where((data < lower_bound) | (data > upper_bound))[0]
        
        anomalies = []
        for idx in anomaly_indices:
            if data[idx] < lower_bound:
                anomaly_type = AnomalyType.DROP
            else:
                anomaly_type = AnomalyType.SPIKE
            
            anomalies.append({
                'index': int(idx),
                'value': float(data[idx]),
                'deviation': float(min(abs(data[idx] - lower_bound), abs(data[idx] - upper_bound))),
                'type': anomaly_type.value
            })
        
        return anomalies, 1.5
    
    def _detect_isolation_forest_anomalies(self, data: np.ndarray) -> Tuple[List[Dict[str, Any]], float]:
        """Detect anomalies using Isolation Forest (simplified version)"""
        # For simplicity, using a statistical approach similar to z-score
        # In a full implementation, you would use sklearn.ensemble.IsolationForest
        return self._detect_zscore_anomalies(data)
    
    def _detect_dbscan_anomalies(self, data: np.ndarray) -> Tuple[List[Dict[str, Any]], float]:
        """Detect anomalies using DBSCAN clustering"""
        if len(data) < 3:
            return [], 0.0
        
        # Reshape data for DBSCAN
        X = data.reshape(-1, 1)
        
        # Apply DBSCAN
        dbscan = DBSCAN(eps=np.std(data), min_samples=max(2, len(data) // 10))
        labels = dbscan.fit_predict(X)
        
        # Points labeled as -1 are anomalies
        anomaly_indices = np.where(labels == -1)[0]
        
        anomalies = []
        for idx in anomaly_indices:
            anomalies.append({
                'index': int(idx),
                'value': float(data[idx]),
                'cluster_label': int(labels[idx]),
                'type': AnomalyType.OUTLIER.value
            })
        
        return anomalies, 0.0

class DataAggregationEngine:
    """Data aggregation engine for Instagram surveillance data"""

    def __init__(self):
        self.statistical_engine = StatisticalAnalysisEngine()

    def aggregate_target_metrics(self, target_id: int, start_date: datetime,
                                end_date: datetime, granularity: str = "daily") -> Dict[str, Any]:
        """Aggregate metrics for a specific target over a time period"""
        try:
            with db_manager.get_session() as session:
                # Get target information
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.id == target_id
                ).first()

                if not target:
                    return {'error': 'Target not found'}

                # Aggregate different types of data
                post_metrics = self._aggregate_post_metrics(session, target_id, start_date, end_date, granularity)
                follower_metrics = self._aggregate_follower_metrics(session, target_id, start_date, end_date, granularity)
                health_metrics = self._aggregate_health_metrics(session, target_id, start_date, end_date, granularity)
                scraping_metrics = self._aggregate_scraping_metrics(session, target_id, start_date, end_date, granularity)

                return {
                    'target_id': target_id,
                    'target_username': target.instagram_username,
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'granularity': granularity
                    },
                    'post_metrics': post_metrics,
                    'follower_metrics': follower_metrics,
                    'health_metrics': health_metrics,
                    'scraping_metrics': scraping_metrics
                }

        except Exception as e:
            logger.error(f"Error aggregating target metrics: {e}")
            return {'error': str(e)}

    def aggregate_multi_target_comparison(self, target_ids: List[int],
                                        start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Aggregate and compare metrics across multiple targets"""
        try:
            comparison_data = {}

            for target_id in target_ids:
                target_data = self.aggregate_target_metrics(target_id, start_date, end_date)
                if 'error' not in target_data:
                    comparison_data[target_id] = target_data

            # Calculate comparative statistics
            comparative_stats = self._calculate_comparative_statistics(comparison_data)

            return {
                'comparison_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'targets_data': comparison_data,
                'comparative_statistics': comparative_stats
            }

        except Exception as e:
            logger.error(f"Error in multi-target comparison: {e}")
            return {'error': str(e)}

    def generate_trend_analysis(self, target_id: int, metric_type: str,
                              analysis_period: str = "monthly") -> Dict[str, Any]:
        """Generate comprehensive trend analysis for a specific metric"""
        try:
            # Determine time range based on analysis period
            end_date = datetime.now(timezone.utc)
            if analysis_period == "daily":
                start_date = end_date - timedelta(days=30)
            elif analysis_period == "weekly":
                start_date = end_date - timedelta(weeks=12)
            else:  # monthly
                start_date = end_date - timedelta(days=365)

            # Get time series data
            timestamps, values = self._get_metric_time_series(target_id, metric_type, start_date, end_date)

            if not timestamps or not values:
                return {'error': 'No data available for analysis'}

            # Perform statistical analysis
            trend_result = self.statistical_engine.analyze_time_series_trend(timestamps, values)
            anomaly_result = self.statistical_engine.detect_anomalies(values)
            seasonal_patterns = self.statistical_engine.detect_seasonal_patterns(timestamps, values)
            growth_metrics = self.statistical_engine.calculate_growth_metrics(values, timestamps)
            statistical_summary = self.statistical_engine.calculate_statistical_summary(values)

            # Store trend analysis in database
            trend_record = create_trend_analysis(
                target_id=target_id,
                analysis_type=metric_type,
                analysis_period=analysis_period,
                period_start=start_date,
                period_end=end_date,
                trend_data={'timestamps': [t.isoformat() for t in timestamps], 'values': values},
                trend_direction=trend_result.direction.value,
                trend_strength=trend_result.strength,
                change_percentage=trend_result.change_percentage,
                mean_value=statistical_summary.mean,
                median_value=statistical_summary.median,
                std_deviation=statistical_summary.std_dev,
                min_value=statistical_summary.min_value,
                max_value=statistical_summary.max_value,
                anomalies_detected=len(anomaly_result.anomalies),
                anomaly_score=anomaly_result.anomaly_score,
                anomaly_details={'anomalies': anomaly_result.anomalies, 'method': anomaly_result.method_used},
                confidence_score=1.0 - trend_result.p_value
            )

            with db_manager.get_session() as session:
                session.add(trend_record)
                session.commit()

            return {
                'target_id': target_id,
                'metric_type': metric_type,
                'analysis_period': analysis_period,
                'trend_analysis': {
                    'direction': trend_result.direction.value,
                    'strength': trend_result.strength,
                    'slope': trend_result.slope,
                    'r_squared': trend_result.r_squared,
                    'p_value': trend_result.p_value,
                    'change_percentage': trend_result.change_percentage,
                    'forecast_values': trend_result.forecast_values
                },
                'anomaly_detection': {
                    'anomalies_count': len(anomaly_result.anomalies),
                    'anomaly_score': anomaly_result.anomaly_score,
                    'anomalies': anomaly_result.anomalies
                },
                'seasonal_patterns': seasonal_patterns,
                'growth_metrics': growth_metrics,
                'statistical_summary': {
                    'count': statistical_summary.count,
                    'mean': statistical_summary.mean,
                    'median': statistical_summary.median,
                    'std_dev': statistical_summary.std_dev,
                    'min_value': statistical_summary.min_value,
                    'max_value': statistical_summary.max_value,
                    'skewness': statistical_summary.skewness,
                    'kurtosis': statistical_summary.kurtosis
                },
                'data_points': len(values),
                'time_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error generating trend analysis: {e}")
            return {'error': str(e)}

    def _aggregate_post_metrics(self, session, target_id: int, start_date: datetime,
                               end_date: datetime, granularity: str) -> Dict[str, Any]:
        """Aggregate post-related metrics"""
        posts = session.query(Post).filter(
            Post.target_id == target_id,
            Post.posted_at >= start_date,
            Post.posted_at <= end_date
        ).all()

        if not posts:
            return {'total_posts': 0}

        # Basic aggregations
        total_posts = len(posts)
        total_likes = sum(p.like_count or 0 for p in posts)
        total_comments = sum(p.comment_count or 0 for p in posts)
        total_shares = sum(p.share_count or 0 for p in posts)

        # Calculate averages
        avg_likes = total_likes / total_posts if total_posts > 0 else 0
        avg_comments = total_comments / total_posts if total_posts > 0 else 0
        avg_engagement = (total_likes + total_comments) / total_posts if total_posts > 0 else 0

        # Post type distribution
        post_types = {}
        for post in posts:
            post_type = post.post_type or 'unknown'
            post_types[post_type] = post_types.get(post_type, 0) + 1

        # Time-based aggregation
        time_series = self._create_time_series(posts, granularity, 'posted_at')

        return {
            'total_posts': total_posts,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'avg_likes_per_post': avg_likes,
            'avg_comments_per_post': avg_comments,
            'avg_engagement_per_post': avg_engagement,
            'post_type_distribution': post_types,
            'time_series': time_series
        }

    def _aggregate_follower_metrics(self, session, target_id: int, start_date: datetime,
                                   end_date: datetime, granularity: str) -> Dict[str, Any]:
        """Aggregate follower-related metrics"""
        followers = session.query(Follower).filter(
            Follower.target_id == target_id,
            Follower.detected_at >= start_date,
            Follower.detected_at <= end_date
        ).all()

        if not followers:
            return {'new_followers': 0}

        # Basic counts
        new_followers = len(followers)
        verified_followers = len([f for f in followers if f.is_verified])
        likely_bots = len([f for f in followers if f.bot_probability and f.bot_probability > 0.7])

        # Influence distribution
        influence_scores = [f.influence_score for f in followers if f.influence_score is not None]
        avg_influence = statistics.mean(influence_scores) if influence_scores else 0

        # Time-based aggregation
        time_series = self._create_time_series(followers, granularity, 'detected_at')

        return {
            'new_followers': new_followers,
            'verified_followers': verified_followers,
            'likely_bot_followers': likely_bots,
            'bot_percentage': (likely_bots / new_followers * 100) if new_followers > 0 else 0,
            'avg_influence_score': avg_influence,
            'time_series': time_series
        }

    def _aggregate_health_metrics(self, session, target_id: int, start_date: datetime,
                                 end_date: datetime, granularity: str) -> Dict[str, Any]:
        """Aggregate health-related metrics"""
        health_records = session.query(AccountHealthMetrics).filter(
            AccountHealthMetrics.target_id == target_id,
            AccountHealthMetrics.recorded_at >= start_date,
            AccountHealthMetrics.recorded_at <= end_date
        ).order_by(AccountHealthMetrics.recorded_at).all()

        if not health_records:
            return {'records_count': 0}

        # Extract time series data
        health_scores = [h.health_score for h in health_records if h.health_score is not None]
        engagement_rates = [h.avg_engagement_rate for h in health_records if h.avg_engagement_rate is not None]

        # Calculate trends
        if len(health_scores) >= 2:
            health_trend = "improving" if health_scores[-1] > health_scores[0] else "declining"
        else:
            health_trend = "stable"

        return {
            'records_count': len(health_records),
            'avg_health_score': statistics.mean(health_scores) if health_scores else 0,
            'latest_health_score': health_scores[-1] if health_scores else 0,
            'health_trend': health_trend,
            'avg_engagement_rate': statistics.mean(engagement_rates) if engagement_rates else 0,
            'health_score_range': {
                'min': min(health_scores) if health_scores else 0,
                'max': max(health_scores) if health_scores else 0
            }
        }

    def _aggregate_scraping_metrics(self, session, target_id: int, start_date: datetime,
                                   end_date: datetime, granularity: str) -> Dict[str, Any]:
        """Aggregate scraping performance metrics"""
        scraping_records = session.query(ScrapingMetrics).filter(
            ScrapingMetrics.target_id == target_id,
            ScrapingMetrics.start_time >= start_date,
            ScrapingMetrics.start_time <= end_date
        ).all()

        if not scraping_records:
            return {'total_sessions': 0}

        # Basic aggregations
        total_sessions = len(scraping_records)
        total_items = sum(s.items_scraped or 0 for s in scraping_records)
        total_requests = sum(s.requests_made or 0 for s in scraping_records)

        # Calculate averages
        success_rates = [s.success_rate for s in scraping_records if s.success_rate is not None]
        response_times = [s.avg_response_time for s in scraping_records if s.avg_response_time is not None]
        quality_scores = [s.data_quality_score for s in scraping_records if s.data_quality_score is not None]

        return {
            'total_sessions': total_sessions,
            'total_items_scraped': total_items,
            'total_requests': total_requests,
            'avg_success_rate': statistics.mean(success_rates) if success_rates else 0,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'avg_quality_score': statistics.mean(quality_scores) if quality_scores else 0,
            'items_per_session': total_items / total_sessions if total_sessions > 0 else 0
        }

    def _create_time_series(self, records: List, granularity: str, timestamp_field: str) -> Dict[str, Any]:
        """Create time series data from records"""
        if not records:
            return {'timestamps': [], 'values': []}

        # Group records by time period
        time_groups = {}

        for record in records:
            timestamp = getattr(record, timestamp_field)
            if not timestamp:
                continue

            # Determine time key based on granularity
            if granularity == "hourly":
                time_key = timestamp.replace(minute=0, second=0, microsecond=0)
            elif granularity == "daily":
                time_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif granularity == "weekly":
                days_since_monday = timestamp.weekday()
                time_key = (timestamp - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # monthly
                time_key = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(record)

        # Sort by timestamp and create series
        sorted_times = sorted(time_groups.keys())
        timestamps = []
        values = []

        for time_key in sorted_times:
            timestamps.append(time_key)
            values.append(len(time_groups[time_key]))  # Count of records in this time period

        return {
            'timestamps': [t.isoformat() for t in timestamps],
            'values': values,
            'granularity': granularity
        }

    def _get_metric_time_series(self, target_id: int, metric_type: str,
                               start_date: datetime, end_date: datetime) -> Tuple[List[datetime], List[float]]:
        """Get time series data for a specific metric type"""
        timestamps = []
        values = []

        try:
            with db_manager.get_session() as session:
                if metric_type == "follower_count":
                    # Get health metrics for follower count
                    records = session.query(AccountHealthMetrics).filter(
                        AccountHealthMetrics.target_id == target_id,
                        AccountHealthMetrics.recorded_at >= start_date,
                        AccountHealthMetrics.recorded_at <= end_date
                    ).order_by(AccountHealthMetrics.recorded_at).all()

                    timestamps = [r.recorded_at for r in records]
                    values = [float(r.follower_count or 0) for r in records]

                elif metric_type == "engagement_rate":
                    # Get health metrics for engagement rate
                    records = session.query(AccountHealthMetrics).filter(
                        AccountHealthMetrics.target_id == target_id,
                        AccountHealthMetrics.recorded_at >= start_date,
                        AccountHealthMetrics.recorded_at <= end_date
                    ).order_by(AccountHealthMetrics.recorded_at).all()

                    timestamps = [r.recorded_at for r in records]
                    values = [float(r.avg_engagement_rate or 0) for r in records]

                elif metric_type == "post_frequency":
                    # Calculate daily post frequency
                    posts = session.query(Post).filter(
                        Post.target_id == target_id,
                        Post.posted_at >= start_date,
                        Post.posted_at <= end_date
                    ).order_by(Post.posted_at).all()

                    # Group posts by day
                    daily_counts = {}
                    for post in posts:
                        if post.posted_at:
                            day_key = post.posted_at.replace(hour=0, minute=0, second=0, microsecond=0)
                            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

                    timestamps = sorted(daily_counts.keys())
                    values = [float(daily_counts[ts]) for ts in timestamps]

                elif metric_type == "health_score":
                    # Get health scores
                    records = session.query(AccountHealthMetrics).filter(
                        AccountHealthMetrics.target_id == target_id,
                        AccountHealthMetrics.recorded_at >= start_date,
                        AccountHealthMetrics.recorded_at <= end_date
                    ).order_by(AccountHealthMetrics.recorded_at).all()

                    timestamps = [r.recorded_at for r in records]
                    values = [float(r.health_score or 0) for r in records]

                elif metric_type == "scraping_success_rate":
                    # Get scraping success rates
                    records = session.query(ScrapingMetrics).filter(
                        ScrapingMetrics.target_id == target_id,
                        ScrapingMetrics.start_time >= start_date,
                        ScrapingMetrics.start_time <= end_date
                    ).order_by(ScrapingMetrics.start_time).all()

                    timestamps = [r.start_time for r in records]
                    values = [float(r.success_rate or 0) for r in records]

        except Exception as e:
            logger.error(f"Error getting metric time series: {e}")

        return timestamps, values

    def _calculate_comparative_statistics(self, comparison_data: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparative statistics across multiple targets"""
        if not comparison_data:
            return {}

        # Extract metrics for comparison
        metrics_by_target = {}

        for target_id, data in comparison_data.items():
            metrics_by_target[target_id] = {
                'total_posts': data.get('post_metrics', {}).get('total_posts', 0),
                'avg_engagement': data.get('post_metrics', {}).get('avg_engagement_per_post', 0),
                'new_followers': data.get('follower_metrics', {}).get('new_followers', 0),
                'health_score': data.get('health_metrics', {}).get('latest_health_score', 0),
                'success_rate': data.get('scraping_metrics', {}).get('avg_success_rate', 0)
            }

        # Calculate rankings and statistics
        comparative_stats = {}

        for metric_name in ['total_posts', 'avg_engagement', 'new_followers', 'health_score', 'success_rate']:
            values = [metrics[metric_name] for metrics in metrics_by_target.values()]

            if values:
                # Create rankings
                target_values = [(target_id, metrics[metric_name]) for target_id, metrics in metrics_by_target.items()]
                target_values.sort(key=lambda x: x[1], reverse=True)

                comparative_stats[metric_name] = {
                    'rankings': [{'target_id': tid, 'value': val, 'rank': i+1} for i, (tid, val) in enumerate(target_values)],
                    'statistics': {
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                        'min': min(values),
                        'max': max(values)
                    }
                }

        return comparative_stats

    def calculate_correlation_matrix(self, target_ids: List[int], metrics: List[str],
                                   start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate correlation matrix between different metrics"""
        try:
            correlation_data = {}

            # Collect data for each metric and target
            for target_id in target_ids:
                target_data = {}
                for metric in metrics:
                    timestamps, values = self._get_metric_time_series(target_id, metric, start_date, end_date)
                    target_data[metric] = values
                correlation_data[target_id] = target_data

            # Calculate correlations
            correlation_matrix = {}

            for i, metric1 in enumerate(metrics):
                correlation_matrix[metric1] = {}
                for j, metric2 in enumerate(metrics):
                    if i <= j:  # Only calculate upper triangle
                        correlations = []

                        for target_id in target_ids:
                            data1 = correlation_data[target_id].get(metric1, [])
                            data2 = correlation_data[target_id].get(metric2, [])

                            if len(data1) == len(data2) and len(data1) > 2:
                                corr_result = self.statistical_engine.analyze_correlation(data1, data2)
                                correlations.append(corr_result['pearson_correlation'])

                        if correlations:
                            avg_correlation = statistics.mean(correlations)
                            correlation_matrix[metric1][metric2] = avg_correlation
                            if i != j:  # Mirror for lower triangle
                                if metric2 not in correlation_matrix:
                                    correlation_matrix[metric2] = {}
                                correlation_matrix[metric2][metric1] = avg_correlation
                        else:
                            correlation_matrix[metric1][metric2] = 0.0

            return {
                'correlation_matrix': correlation_matrix,
                'metrics': metrics,
                'target_ids': target_ids,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {'error': str(e)}

# Global instances
statistical_engine = StatisticalAnalysisEngine()
data_aggregation_engine = DataAggregationEngine()
