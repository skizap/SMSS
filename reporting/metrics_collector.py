#!/usr/bin/env python3
"""
Social Media Surveillance System - Performance Metrics Collection System
Collects and stores scraping performance metrics, success rates, response times, and data volume.
"""

import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import psutil

from core.config import config
from core.database import db_manager
from models.analytics_models import (
    ScrapingMetrics, AccountHealthMetrics, create_scraping_metrics
)

logger = logging.getLogger(__name__)

@dataclass
class MetricsSession:
    """Represents a metrics collection session for a scraping operation"""
    target_id: int
    scraper_type: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    items_scraped: int = 0
    items_failed: int = 0
    requests_made: int = 0
    requests_failed: int = 0
    response_times: List[float] = field(default_factory=list)
    rate_limit_hits: int = 0
    validation_errors: int = 0
    duplicate_items: int = 0
    error_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate session duration in seconds"""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.items_scraped + self.items_failed
        if total == 0:
            return 0.0
        return (self.items_scraped / total) * 100
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def data_quality_score(self) -> float:
        """Calculate data quality score (0-1)"""
        total_items = self.items_scraped + self.items_failed
        if total_items == 0:
            return 1.0
        
        # Base score from success rate
        success_score = self.success_rate / 100
        
        # Penalty for validation errors
        validation_penalty = min(self.validation_errors / total_items, 0.3)
        
        # Penalty for duplicates
        duplicate_penalty = min(self.duplicate_items / total_items, 0.2)
        
        return max(success_score - validation_penalty - duplicate_penalty, 0.0)

class PerformanceMetricsCollector:
    """Collects and manages performance metrics for scraping operations"""
    
    def __init__(self):
        self.active_sessions: Dict[str, MetricsSession] = {}
        self.session_lock = threading.Lock()
        
        # Real-time metrics tracking
        self.recent_metrics = defaultdict(lambda: deque(maxlen=100))  # Last 100 operations per scraper
        self.system_metrics = {}
        self.last_system_update = None
        
        # Aggregated statistics
        self.daily_stats = defaultdict(dict)
        self.hourly_stats = defaultdict(dict)
        
        # Background thread for periodic tasks
        self.background_thread = None
        self.running = False
        
        self.start_background_tasks()
    
    def start_background_tasks(self):
        """Start background thread for periodic metrics collection"""
        if not self.running:
            self.running = True
            self.background_thread = threading.Thread(target=self._background_worker, daemon=True)
            self.background_thread.start()
            logger.info("Performance metrics collector started")
    
    def stop_background_tasks(self):
        """Stop background thread"""
        self.running = False
        if self.background_thread:
            self.background_thread.join(timeout=5)
        logger.info("Performance metrics collector stopped")
    
    def _background_worker(self):
        """Background worker for periodic tasks"""
        while self.running:
            try:
                # Update system metrics every 30 seconds
                self._update_system_metrics()
                
                # Clean up old sessions every 5 minutes
                self._cleanup_old_sessions()
                
                # Aggregate statistics every hour
                current_hour = datetime.now(timezone.utc).hour
                if current_hour not in self.hourly_stats:
                    self._aggregate_hourly_stats()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics background worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    @contextmanager
    def track_scraping_session(self, target_id: int, scraper_type: str, metadata: Dict[str, Any] = None):
        """Context manager for tracking a scraping session"""
        session_id = f"{target_id}_{scraper_type}_{int(time.time())}"
        
        session = MetricsSession(
            target_id=target_id,
            scraper_type=scraper_type,
            metadata=metadata or {}
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
        
        try:
            yield session
        except Exception as e:
            session.error_messages.append(str(e))
            raise
        finally:
            # Finalize session
            session.end_time = datetime.now(timezone.utc)
            
            # Store metrics in database
            self._store_session_metrics(session)
            
            # Update recent metrics for real-time tracking
            self._update_recent_metrics(session)
            
            # Remove from active sessions
            with self.session_lock:
                self.active_sessions.pop(session_id, None)
    
    def track_request(self, session: MetricsSession, response_time: float, success: bool = True):
        """Track an individual request within a session"""
        session.requests_made += 1
        session.response_times.append(response_time)
        
        if not success:
            session.requests_failed += 1
    
    def track_item_scraped(self, session: MetricsSession, success: bool = True, is_duplicate: bool = False):
        """Track a scraped item"""
        if success:
            session.items_scraped += 1
            if is_duplicate:
                session.duplicate_items += 1
        else:
            session.items_failed += 1
    
    def track_validation_error(self, session: MetricsSession, error_message: str = None):
        """Track a validation error"""
        session.validation_errors += 1
        if error_message:
            session.error_messages.append(f"Validation: {error_message}")
    
    def track_rate_limit_hit(self, session: MetricsSession):
        """Track a rate limit hit"""
        session.rate_limit_hits += 1
    
    def _store_session_metrics(self, session: MetricsSession):
        """Store session metrics in database"""
        try:
            metrics = create_scraping_metrics(
                target_id=session.target_id,
                scraper_type=session.scraper_type,
                start_time=session.start_time,
                end_time=session.end_time,
                duration_seconds=session.duration_seconds,
                items_scraped=session.items_scraped,
                items_failed=session.items_failed,
                success_rate=session.success_rate,
                requests_made=session.requests_made,
                requests_failed=session.requests_failed,
                avg_response_time=session.avg_response_time,
                rate_limit_hits=session.rate_limit_hits,
                data_quality_score=session.data_quality_score,
                validation_errors=session.validation_errors,
                duplicate_items=session.duplicate_items,
                status='completed' if not session.error_messages else 'failed',
                error_message='; '.join(session.error_messages) if session.error_messages else None,
                metadata=session.metadata
            )
            
            with db_manager.get_session() as db_session:
                db_session.add(metrics)
                db_session.commit()
                
            logger.debug(f"Stored metrics for {session.scraper_type} session: {session.items_scraped} items")
            
        except Exception as e:
            logger.error(f"Error storing session metrics: {e}")
    
    def _update_recent_metrics(self, session: MetricsSession):
        """Update recent metrics for real-time tracking"""
        key = f"{session.target_id}_{session.scraper_type}"
        
        metrics_summary = {
            'timestamp': session.end_time,
            'duration': session.duration_seconds,
            'items_scraped': session.items_scraped,
            'success_rate': session.success_rate,
            'avg_response_time': session.avg_response_time,
            'data_quality_score': session.data_quality_score
        }
        
        self.recent_metrics[key].append(metrics_summary)
    
    def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            self.system_metrics = {
                'timestamp': datetime.now(timezone.utc),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'active_sessions': len(self.active_sessions)
            }
            self.last_system_update = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def _cleanup_old_sessions(self):
        """Clean up sessions that have been running too long"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        with self.session_lock:
            old_sessions = [
                session_id for session_id, session in self.active_sessions.items()
                if session.start_time < cutoff_time
            ]
            
            for session_id in old_sessions:
                session = self.active_sessions.pop(session_id)
                session.end_time = datetime.now(timezone.utc)
                session.error_messages.append("Session timed out")
                
                # Store the timed-out session
                self._store_session_metrics(session)
                
                logger.warning(f"Cleaned up old session: {session_id}")
    
    def _aggregate_hourly_stats(self):
        """Aggregate hourly statistics"""
        try:
            current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            hour_start = current_hour - timedelta(hours=1)
            
            with db_manager.get_session() as db_session:
                # Query metrics from the last hour
                metrics = db_session.query(ScrapingMetrics).filter(
                    ScrapingMetrics.start_time >= hour_start,
                    ScrapingMetrics.start_time < current_hour
                ).all()
                
                if metrics:
                    # Aggregate by scraper type
                    stats_by_type = defaultdict(list)
                    for metric in metrics:
                        stats_by_type[metric.scraper_type].append(metric)
                    
                    hourly_summary = {}
                    for scraper_type, type_metrics in stats_by_type.items():
                        hourly_summary[scraper_type] = {
                            'total_sessions': len(type_metrics),
                            'total_items': sum(m.items_scraped for m in type_metrics),
                            'avg_success_rate': statistics.mean(m.success_rate for m in type_metrics if m.success_rate),
                            'avg_response_time': statistics.mean(m.avg_response_time for m in type_metrics if m.avg_response_time),
                            'avg_quality_score': statistics.mean(m.data_quality_score for m in type_metrics if m.data_quality_score),
                            'total_rate_limits': sum(m.rate_limit_hits for m in type_metrics)
                        }
                    
                    self.hourly_stats[current_hour.hour] = hourly_summary
                    logger.info(f"Aggregated hourly stats for hour {current_hour.hour}")
                
        except Exception as e:
            logger.error(f"Error aggregating hourly stats: {e}")
    
    def get_real_time_metrics(self, target_id: int = None, scraper_type: str = None) -> Dict[str, Any]:
        """Get real-time metrics summary"""
        if target_id and scraper_type:
            key = f"{target_id}_{scraper_type}"
            recent = list(self.recent_metrics.get(key, []))
        else:
            # Aggregate all recent metrics
            recent = []
            for metrics_list in self.recent_metrics.values():
                recent.extend(list(metrics_list))
        
        if not recent:
            return {
                'total_sessions': 0,
                'avg_success_rate': 0,
                'avg_response_time': 0,
                'avg_quality_score': 0,
                'items_per_minute': 0
            }
        
        # Calculate aggregated metrics
        total_sessions = len(recent)
        avg_success_rate = statistics.mean(m['success_rate'] for m in recent)
        avg_response_time = statistics.mean(m['avg_response_time'] for m in recent)
        avg_quality_score = statistics.mean(m['data_quality_score'] for m in recent)
        
        # Calculate items per minute (last 10 minutes)
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        recent_items = [
            m for m in recent 
            if m['timestamp'] and m['timestamp'] > ten_minutes_ago
        ]
        total_items = sum(m['items_scraped'] for m in recent_items)
        items_per_minute = total_items / 10 if recent_items else 0
        
        return {
            'total_sessions': total_sessions,
            'avg_success_rate': avg_success_rate,
            'avg_response_time': avg_response_time,
            'avg_quality_score': avg_quality_score,
            'items_per_minute': items_per_minute,
            'active_sessions': len(self.active_sessions),
            'system_metrics': self.system_metrics
        }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with db_manager.get_session() as db_session:
                metrics = db_session.query(ScrapingMetrics).filter(
                    ScrapingMetrics.start_time >= cutoff_time
                ).all()
                
                if not metrics:
                    return {'total_sessions': 0}
                
                # Calculate summary statistics
                total_sessions = len(metrics)
                total_items = sum(m.items_scraped for m in metrics)
                total_requests = sum(m.requests_made for m in metrics)
                avg_success_rate = statistics.mean(m.success_rate for m in metrics if m.success_rate is not None)
                avg_response_time = statistics.mean(m.avg_response_time for m in metrics if m.avg_response_time is not None)
                avg_quality_score = statistics.mean(m.data_quality_score for m in metrics if m.data_quality_score is not None)
                
                # Group by scraper type
                by_scraper = defaultdict(list)
                for metric in metrics:
                    by_scraper[metric.scraper_type].append(metric)
                
                scraper_stats = {}
                for scraper_type, scraper_metrics in by_scraper.items():
                    scraper_stats[scraper_type] = {
                        'sessions': len(scraper_metrics),
                        'items_scraped': sum(m.items_scraped for m in scraper_metrics),
                        'avg_success_rate': statistics.mean(m.success_rate for m in scraper_metrics if m.success_rate is not None),
                        'avg_quality_score': statistics.mean(m.data_quality_score for m in scraper_metrics if m.data_quality_score is not None)
                    }
                
                return {
                    'total_sessions': total_sessions,
                    'total_items_scraped': total_items,
                    'total_requests': total_requests,
                    'avg_success_rate': avg_success_rate,
                    'avg_response_time': avg_response_time,
                    'avg_quality_score': avg_quality_score,
                    'by_scraper_type': scraper_stats,
                    'time_period_hours': hours
                }
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}

# Global metrics collector instance
metrics_collector = PerformanceMetricsCollector()
