#!/usr/bin/env python3
"""
Social Media Surveillance System - Analytics Service
Comprehensive analytics service that coordinates all analysis components.
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import schedule

from core.config import config
from core.database import db_manager
from models.instagram_models import SurveillanceTarget
from .statistical_analysis_engine import statistical_engine, data_aggregation_engine
from .metrics_collector import metrics_collector
from .account_health_monitor import account_health_monitor
from notifications.enhanced_notification_manager import enhanced_notification_manager

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Comprehensive analytics service for Instagram surveillance system"""
    
    def __init__(self):
        self.statistical_engine = statistical_engine
        self.aggregation_engine = data_aggregation_engine
        self.metrics_collector = metrics_collector
        self.health_monitor = account_health_monitor
        
        # Scheduler for automated analytics tasks
        self.scheduler_thread = None
        self.running = False
        
        # Cache for frequently accessed analytics
        self.analytics_cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        self.start_scheduler()
    
    def start_scheduler(self):
        """Start the analytics scheduler"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
            self.scheduler_thread.start()
            
            # Schedule automated analytics tasks
            self._setup_scheduled_tasks()
            
            logger.info("Analytics service scheduler started")
    
    def stop_scheduler(self):
        """Stop the analytics scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("Analytics service scheduler stopped")
    
    def _setup_scheduled_tasks(self):
        """Setup scheduled analytics tasks"""
        # Daily trend analysis for all active targets
        schedule.every().day.at("02:00").do(self._run_daily_trend_analysis)
        
        # Weekly comparative analysis
        schedule.every().monday.at("03:00").do(self._run_weekly_comparative_analysis)
        
        # Monthly comprehensive report generation (first day of each month)
        schedule.every().day.at("04:00").do(self._check_monthly_analysis)
        
        # Hourly cache cleanup
        schedule.every().hour.do(self._cleanup_cache)
    
    def _scheduler_worker(self):
        """Background scheduler worker"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in analytics scheduler: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_target_analytics_dashboard(self, target_id: int, time_range: str = "30d") -> Dict[str, Any]:
        """Get comprehensive analytics dashboard for a target"""
        cache_key = f"dashboard_{target_id}_{time_range}"
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Determine date range
            end_date = datetime.now(timezone.utc)
            if time_range == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_range == "30d":
                start_date = end_date - timedelta(days=30)
            elif time_range == "90d":
                start_date = end_date - timedelta(days=90)
            else:  # 1y
                start_date = end_date - timedelta(days=365)
            
            # Get target information
            with db_manager.get_session() as session:
                target = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.id == target_id
                ).first()
                
                if not target:
                    return {'error': 'Target not found'}
            
            # Collect analytics data
            dashboard_data = {
                'target_info': {
                    'id': target.id,
                    'username': target.instagram_username,
                    'display_name': target.display_name,
                    'follower_count': target.follower_count,
                    'following_count': target.following_count,
                    'post_count': target.post_count,
                    'is_verified': target.is_verified,
                    'category': target.category,
                    'priority': target.priority
                },
                'time_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'period': time_range
                }
            }
            
            # Get aggregated metrics
            aggregated_metrics = self.aggregation_engine.aggregate_target_metrics(
                target_id, start_date, end_date, "daily"
            )
            dashboard_data['aggregated_metrics'] = aggregated_metrics
            
            # Get trend analyses for key metrics
            key_metrics = ['follower_count', 'engagement_rate', 'health_score', 'post_frequency']
            trend_analyses = {}
            
            for metric in key_metrics:
                trend_result = self.aggregation_engine.generate_trend_analysis(
                    target_id, metric, "daily"
                )
                if 'error' not in trend_result:
                    trend_analyses[metric] = trend_result
            
            dashboard_data['trend_analyses'] = trend_analyses
            
            # Get real-time performance metrics
            performance_metrics = self.metrics_collector.get_real_time_metrics(target_id)
            dashboard_data['performance_metrics'] = performance_metrics
            
            # Get health summary
            health_summary = self.health_monitor.get_health_summary(target_id, 30)
            dashboard_data['health_summary'] = health_summary
            
            # Calculate key insights
            insights = self._generate_key_insights(dashboard_data)
            dashboard_data['key_insights'] = insights
            
            # Cache the result
            self._store_in_cache(cache_key, dashboard_data)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generating target analytics dashboard: {e}")
            return {'error': str(e)}
    
    def get_multi_target_comparison(self, target_ids: List[int], time_range: str = "30d") -> Dict[str, Any]:
        """Get comparative analytics across multiple targets"""
        try:
            # Determine date range
            end_date = datetime.now(timezone.utc)
            if time_range == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_range == "30d":
                start_date = end_date - timedelta(days=30)
            elif time_range == "90d":
                start_date = end_date - timedelta(days=90)
            else:  # 1y
                start_date = end_date - timedelta(days=365)
            
            # Get comparative data
            comparison_data = self.aggregation_engine.aggregate_multi_target_comparison(
                target_ids, start_date, end_date
            )
            
            # Calculate correlation matrix for key metrics
            key_metrics = ['follower_count', 'engagement_rate', 'health_score']
            correlation_matrix = self.aggregation_engine.calculate_correlation_matrix(
                target_ids, key_metrics, start_date, end_date
            )
            
            # Generate comparative insights
            comparative_insights = self._generate_comparative_insights(comparison_data, correlation_matrix)
            
            return {
                'comparison_data': comparison_data,
                'correlation_analysis': correlation_matrix,
                'comparative_insights': comparative_insights,
                'time_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'period': time_range
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating multi-target comparison: {e}")
            return {'error': str(e)}
    
    def get_system_performance_analytics(self) -> Dict[str, Any]:
        """Get system-wide performance analytics"""
        try:
            # Get performance summary for different time periods
            performance_24h = self.metrics_collector.get_performance_summary(24)
            performance_7d = self.metrics_collector.get_performance_summary(168)  # 7 days
            performance_30d = self.metrics_collector.get_performance_summary(720)  # 30 days
            
            # Get real-time metrics
            real_time_metrics = self.metrics_collector.get_real_time_metrics()
            
            # Calculate system health score
            system_health_score = self._calculate_system_health_score(performance_24h, real_time_metrics)
            
            return {
                'system_health_score': system_health_score,
                'performance_24h': performance_24h,
                'performance_7d': performance_7d,
                'performance_30d': performance_30d,
                'real_time_metrics': real_time_metrics,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating system performance analytics: {e}")
            return {'error': str(e)}
    
    def generate_anomaly_report(self, target_id: int = None, days: int = 7) -> Dict[str, Any]:
        """Generate anomaly detection report"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            anomaly_report = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'anomalies_by_target': {},
                'summary': {
                    'total_anomalies': 0,
                    'critical_anomalies': 0,
                    'anomaly_types': {}
                }
            }
            
            # Get targets to analyze
            if target_id:
                target_ids = [target_id]
            else:
                with db_manager.get_session() as session:
                    targets = session.query(SurveillanceTarget).filter(
                        SurveillanceTarget.status == 'active'
                    ).all()
                    target_ids = [t.id for t in targets]
            
            # Analyze each target
            for tid in target_ids:
                target_anomalies = []
                
                # Check different metrics for anomalies
                metrics_to_check = ['follower_count', 'engagement_rate', 'post_frequency']
                
                for metric in metrics_to_check:
                    timestamps, values = self.aggregation_engine._get_metric_time_series(
                        tid, metric, start_date, end_date
                    )
                    
                    if len(values) >= 3:
                        anomaly_result = self.statistical_engine.detect_anomalies(values, method="zscore")
                        
                        for anomaly in anomaly_result.anomalies:
                            target_anomalies.append({
                                'metric': metric,
                                'timestamp': timestamps[anomaly['index']].isoformat() if anomaly['index'] < len(timestamps) else None,
                                'value': anomaly['value'],
                                'type': anomaly['type'],
                                'severity': 'critical' if anomaly.get('z_score', 0) > 3 else 'medium'
                            })
                
                if target_anomalies:
                    anomaly_report['anomalies_by_target'][tid] = target_anomalies
                    
                    # Update summary
                    anomaly_report['summary']['total_anomalies'] += len(target_anomalies)
                    
                    for anomaly in target_anomalies:
                        if anomaly['severity'] == 'critical':
                            anomaly_report['summary']['critical_anomalies'] += 1
                        
                        anomaly_type = anomaly['type']
                        anomaly_report['summary']['anomaly_types'][anomaly_type] = \
                            anomaly_report['summary']['anomaly_types'].get(anomaly_type, 0) + 1
            
            return anomaly_report
            
        except Exception as e:
            logger.error(f"Error generating anomaly report: {e}")
            return {'error': str(e)}
    
    def _generate_key_insights(self, dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate key insights from dashboard data"""
        insights = []
        
        try:
            # Analyze trend data for insights
            trend_analyses = dashboard_data.get('trend_analyses', {})
            
            for metric, trend_data in trend_analyses.items():
                trend_analysis = trend_data.get('trend_analysis', {})
                direction = trend_analysis.get('direction', 'stable')
                strength = trend_analysis.get('strength', 0)
                change_percentage = trend_analysis.get('change_percentage', 0)
                
                if strength > 0.7 and abs(change_percentage) > 10:
                    insight_type = 'positive' if change_percentage > 0 else 'negative'
                    insights.append({
                        'type': insight_type,
                        'metric': metric,
                        'message': f"{metric.replace('_', ' ').title()} is {direction} with {abs(change_percentage):.1f}% change",
                        'strength': strength,
                        'change_percentage': change_percentage
                    })
            
            # Analyze health data
            health_summary = dashboard_data.get('health_summary', {})
            health_score = health_summary.get('current_health_score', 0)
            
            if health_score < 30:
                insights.append({
                    'type': 'critical',
                    'metric': 'health_score',
                    'message': f"Account health score is critically low at {health_score:.1f}",
                    'strength': 1.0,
                    'health_score': health_score
                })
            elif health_score < 50:
                insights.append({
                    'type': 'warning',
                    'metric': 'health_score',
                    'message': f"Account health score needs attention at {health_score:.1f}",
                    'strength': 0.7,
                    'health_score': health_score
                })
            
            # Analyze performance metrics
            performance_metrics = dashboard_data.get('performance_metrics', {})
            success_rate = performance_metrics.get('avg_success_rate', 0)
            
            if success_rate < 80:
                insights.append({
                    'type': 'warning',
                    'metric': 'scraping_performance',
                    'message': f"Scraping success rate is low at {success_rate:.1f}%",
                    'strength': 0.8,
                    'success_rate': success_rate
                })
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
        
        return insights
    
    def _generate_comparative_insights(self, comparison_data: Dict[str, Any], 
                                     correlation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from comparative analysis"""
        insights = []
        
        try:
            # Analyze comparative statistics
            comparative_stats = comparison_data.get('comparative_statistics', {})
            
            for metric, stats in comparative_stats.items():
                rankings = stats.get('rankings', [])
                if len(rankings) >= 2:
                    top_performer = rankings[0]
                    bottom_performer = rankings[-1]
                    
                    if top_performer['value'] > 0 and bottom_performer['value'] >= 0:
                        performance_gap = ((top_performer['value'] - bottom_performer['value']) / 
                                         top_performer['value'] * 100)
                        
                        if performance_gap > 50:
                            insights.append({
                                'type': 'comparative',
                                'metric': metric,
                                'message': f"Large performance gap in {metric.replace('_', ' ')}: {performance_gap:.1f}%",
                                'top_performer': top_performer,
                                'bottom_performer': bottom_performer,
                                'gap_percentage': performance_gap
                            })
            
            # Analyze correlations
            correlation_matrix = correlation_data.get('correlation_matrix', {})
            
            for metric1, correlations in correlation_matrix.items():
                for metric2, correlation in correlations.items():
                    if metric1 != metric2 and abs(correlation) > 0.7:
                        correlation_type = 'strong positive' if correlation > 0 else 'strong negative'
                        insights.append({
                            'type': 'correlation',
                            'metrics': [metric1, metric2],
                            'message': f"{correlation_type.title()} correlation between {metric1} and {metric2}",
                            'correlation_value': correlation,
                            'correlation_type': correlation_type
                        })
            
        except Exception as e:
            logger.error(f"Error generating comparative insights: {e}")
        
        return insights
    
    def _calculate_system_health_score(self, performance_data: Dict[str, Any], 
                                     real_time_data: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            scores = []
            
            # Success rate score (0-30 points)
            success_rate = performance_data.get('avg_success_rate', 0)
            success_score = (success_rate / 100) * 30
            scores.append(success_score)
            
            # Response time score (0-25 points)
            avg_response_time = performance_data.get('avg_response_time', 10)
            response_score = max(0, 25 - (avg_response_time * 2.5))  # Penalty for slow responses
            scores.append(response_score)
            
            # Data quality score (0-25 points)
            quality_score = performance_data.get('avg_quality_score', 0.5)
            quality_points = quality_score * 25
            scores.append(quality_points)
            
            # System resource score (0-20 points)
            system_metrics = real_time_data.get('system_metrics', {})
            memory_usage = system_metrics.get('memory_percent', 50)
            cpu_usage = system_metrics.get('cpu_percent', 50)
            
            resource_score = max(0, 20 - ((memory_usage + cpu_usage) / 10))
            scores.append(resource_score)
            
            return sum(scores)
            
        except Exception as e:
            logger.error(f"Error calculating system health score: {e}")
            return 50.0  # Default middle score
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired"""
        if key in self.analytics_cache:
            cached_data, timestamp = self.analytics_cache[key]
            if (datetime.now(timezone.utc) - timestamp).seconds < self.cache_ttl:
                return cached_data
            else:
                del self.analytics_cache[key]
        return None
    
    def _store_in_cache(self, key: str, data: Dict[str, Any]):
        """Store data in cache with timestamp"""
        self.analytics_cache[key] = (data, datetime.now(timezone.utc))
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for key, (data, timestamp) in self.analytics_cache.items():
            if (current_time - timestamp).seconds >= self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.analytics_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _run_daily_trend_analysis(self):
        """Run daily trend analysis for all active targets"""
        try:
            with db_manager.get_session() as session:
                targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()
                
                for target in targets:
                    # Generate trend analysis for key metrics
                    key_metrics = ['follower_count', 'engagement_rate', 'health_score']
                    
                    for metric in key_metrics:
                        self.aggregation_engine.generate_trend_analysis(
                            target.id, metric, "daily"
                        )
                
                logger.info(f"Completed daily trend analysis for {len(targets)} targets")
                
        except Exception as e:
            logger.error(f"Error in daily trend analysis: {e}")
    
    def _run_weekly_comparative_analysis(self):
        """Run weekly comparative analysis"""
        try:
            with db_manager.get_session() as session:
                targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()
                
                target_ids = [t.id for t in targets]
                
                if len(target_ids) > 1:
                    comparison_result = self.get_multi_target_comparison(target_ids, "7d")
                    
                    # Store results or send notifications as needed
                    logger.info(f"Completed weekly comparative analysis for {len(target_ids)} targets")
                
        except Exception as e:
            logger.error(f"Error in weekly comparative analysis: {e}")
    
    def _check_monthly_analysis(self):
        """Check if monthly analysis should run (first day of month)"""
        try:
            current_date = datetime.now(timezone.utc)
            if current_date.day == 1:  # First day of the month
                self._run_monthly_comprehensive_analysis()
        except Exception as e:
            logger.error(f"Error checking monthly analysis: {e}")

    def _run_monthly_comprehensive_analysis(self):
        """Run monthly comprehensive analysis"""
        try:
            # Generate comprehensive reports for all targets
            # This could trigger report generation, send summary emails, etc.
            logger.info("Running monthly comprehensive analysis")

        except Exception as e:
            logger.error(f"Error in monthly comprehensive analysis: {e}")

# Global analytics service instance
analytics_service = AnalyticsService()
