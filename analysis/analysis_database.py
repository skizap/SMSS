"""
Social Media Surveillance System - Analysis Database Integration
Database layer for storing and retrieving AI analysis results, managing analysis history,
and providing efficient data access for the analysis engines.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base

from core.database import Base
from models.instagram_models import SurveillanceTarget, Post, Follower, Story

# Configure logging
logger = logging.getLogger(__name__)

class AnalysisResult(Base):
    """Model for storing AI analysis results"""
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # post, story, profile, follower
    content_id = Column(Integer, nullable=False)  # ID of the analyzed content
    analysis_type = Column(String(50), nullable=False)  # sentiment, topics, bot_detection, etc.
    
    # Analysis results
    result_data = Column(JSON, nullable=False)  # Main analysis results
    confidence = Column(Float)  # Confidence score (0-1)
    analysis_metadata = Column(JSON)  # Additional metadata
    
    # Timestamps
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    content_timestamp = Column(DateTime, index=True)  # When the content was created
    
    # Processing info
    processing_time = Column(Float)  # Time taken for analysis in seconds
    model_version = Column(String(50))  # AI model version used
    
    # Relationships
    target = relationship("SurveillanceTarget")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_analysis_target_type', 'target_id', 'analysis_type'),
        Index('idx_analysis_content', 'content_type', 'content_id'),
        Index('idx_analysis_timestamp', 'analyzed_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'content_type': self.content_type,
            'content_id': self.content_id,
            'analysis_type': self.analysis_type,
            'result_data': self.result_data,
            'confidence': self.confidence,
            'metadata': self.analysis_metadata,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'content_timestamp': self.content_timestamp.isoformat() if self.content_timestamp else None,
            'processing_time': self.processing_time,
            'model_version': self.model_version
        }

class PatternDetectionResult(Base):
    """Model for storing pattern detection results"""
    __tablename__ = 'pattern_detection_results'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    pattern_type = Column(String(100), nullable=False, index=True)
    
    # Pattern details
    description = Column(Text)
    confidence = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    pattern_data = Column(JSON)  # Detailed pattern information
    
    # Time period
    detection_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    pattern_start_date = Column(DateTime, index=True)
    pattern_end_date = Column(DateTime, index=True)
    
    # Status
    status = Column(String(20), default='active')  # active, resolved, false_positive
    reviewed_by = Column(String(100))  # User who reviewed the pattern
    review_notes = Column(Text)
    
    # Relationships
    target = relationship("SurveillanceTarget")
    
    # Indexes
    __table_args__ = (
        Index('idx_pattern_target_type', 'target_id', 'pattern_type'),
        Index('idx_pattern_severity', 'severity', 'detection_date'),
        Index('idx_pattern_status', 'status', 'detection_date'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'pattern_type': self.pattern_type,
            'description': self.description,
            'confidence': self.confidence,
            'severity': self.severity,
            'pattern_data': self.pattern_data,
            'detection_date': self.detection_date.isoformat() if self.detection_date else None,
            'pattern_start_date': self.pattern_start_date.isoformat() if self.pattern_start_date else None,
            'pattern_end_date': self.pattern_end_date.isoformat() if self.pattern_end_date else None,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'review_notes': self.review_notes
        }

class AnalysisQueue(Base):
    """Model for managing analysis queue"""
    __tablename__ = 'analysis_queue'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('surveillance_targets.id'), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)
    content_id = Column(Integer, nullable=False)
    analysis_types = Column(JSON, nullable=False)  # List of analysis types to perform
    
    # Queue management
    priority = Column(Integer, default=5, index=True)  # 1-10, higher is more priority
    status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text)
    
    # Relationships
    target = relationship("SurveillanceTarget")
    
    # Indexes
    __table_args__ = (
        Index('idx_queue_status_priority', 'status', 'priority', 'created_at'),
        Index('idx_queue_target', 'target_id', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'target_id': self.target_id,
            'content_type': self.content_type,
            'content_id': self.content_id,
            'analysis_types': self.analysis_types,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message
        }

class AnalysisDatabaseManager:
    """Database manager for analysis operations"""
    
    def __init__(self):
        logger.info("Analysis database manager initialized")
    
    def save_analysis_result(
        self,
        target_id: int,
        content_type: str,
        content_id: int,
        analysis_type: str,
        result_data: Dict[str, Any],
        confidence: float = None,
        metadata: Dict[str, Any] = None,
        processing_time: float = None,
        model_version: str = None,
        content_timestamp: datetime = None
    ) -> int:
        """
        Save analysis result to database
        
        Returns:
            ID of the saved analysis result
        """
        try:
            from core.database import db_manager
            with db_manager.get_session() as session:
                analysis_result = AnalysisResult(
                    target_id=target_id,
                    content_type=content_type,
                    content_id=content_id,
                    analysis_type=analysis_type,
                    result_data=result_data,
                    confidence=confidence,
                    analysis_metadata=metadata or {},
                    processing_time=processing_time,
                    model_version=model_version,
                    content_timestamp=content_timestamp
                )
                
                session.add(analysis_result)
                session.commit()
                
                logger.debug(f"Saved analysis result: {analysis_type} for {content_type} {content_id}")
                return analysis_result.id
                
        except Exception as e:
            logger.error(f"Failed to save analysis result: {e}")
            raise
    
    def get_analysis_results(
        self,
        target_id: int = None,
        content_type: str = None,
        analysis_type: str = None,
        since: datetime = None,
        limit: int = 100
    ) -> List[AnalysisResult]:
        """
        Retrieve analysis results with filtering
        
        Args:
            target_id: Filter by target ID
            content_type: Filter by content type
            analysis_type: Filter by analysis type
            since: Filter by analysis date
            limit: Maximum number of results
            
        Returns:
            List of analysis results
        """
        try:
            with db_manager.get_session() as session:
                query = session.query(AnalysisResult)
                
                if target_id:
                    query = query.filter(AnalysisResult.target_id == target_id)
                if content_type:
                    query = query.filter(AnalysisResult.content_type == content_type)
                if analysis_type:
                    query = query.filter(AnalysisResult.analysis_type == analysis_type)
                if since:
                    query = query.filter(AnalysisResult.analyzed_at >= since)
                
                results = query.order_by(AnalysisResult.analyzed_at.desc()).limit(limit).all()
                
                logger.debug(f"Retrieved {len(results)} analysis results")
                return results
                
        except Exception as e:
            logger.error(f"Failed to retrieve analysis results: {e}")
            return []

    def save_pattern_detection_result(
        self,
        target_id: int,
        pattern_type: str,
        description: str,
        confidence: float,
        severity: str,
        pattern_data: Dict[str, Any],
        pattern_start_date: datetime = None,
        pattern_end_date: datetime = None
    ) -> int:
        """
        Save pattern detection result to database

        Returns:
            ID of the saved pattern result
        """
        try:
            with db_manager.get_session() as session:
                pattern_result = PatternDetectionResult(
                    target_id=target_id,
                    pattern_type=pattern_type,
                    description=description,
                    confidence=confidence,
                    severity=severity,
                    pattern_data=pattern_data,
                    pattern_start_date=pattern_start_date,
                    pattern_end_date=pattern_end_date
                )

                session.add(pattern_result)
                session.commit()

                logger.debug(f"Saved pattern detection result: {pattern_type} for target {target_id}")
                return pattern_result.id

        except Exception as e:
            logger.error(f"Failed to save pattern detection result: {e}")
            raise

    def get_pattern_detection_results(
        self,
        target_id: int = None,
        pattern_type: str = None,
        severity: str = None,
        status: str = 'active',
        since: datetime = None,
        limit: int = 100
    ) -> List[PatternDetectionResult]:
        """
        Retrieve pattern detection results with filtering

        Args:
            target_id: Filter by target ID
            pattern_type: Filter by pattern type
            severity: Filter by severity level
            status: Filter by status
            since: Filter by detection date
            limit: Maximum number of results

        Returns:
            List of pattern detection results
        """
        try:
            with db_manager.get_session() as session:
                query = session.query(PatternDetectionResult)

                if target_id:
                    query = query.filter(PatternDetectionResult.target_id == target_id)
                if pattern_type:
                    query = query.filter(PatternDetectionResult.pattern_type == pattern_type)
                if severity:
                    query = query.filter(PatternDetectionResult.severity == severity)
                if status:
                    query = query.filter(PatternDetectionResult.status == status)
                if since:
                    query = query.filter(PatternDetectionResult.detection_date >= since)

                results = query.order_by(PatternDetectionResult.detection_date.desc()).limit(limit).all()

                logger.debug(f"Retrieved {len(results)} pattern detection results")
                return results

        except Exception as e:
            logger.error(f"Failed to retrieve pattern detection results: {e}")
            return []

    def add_to_analysis_queue(
        self,
        target_id: int,
        content_type: str,
        content_id: int,
        analysis_types: List[str],
        priority: int = 5
    ) -> int:
        """
        Add item to analysis queue

        Args:
            target_id: Target ID
            content_type: Type of content (post, story, etc.)
            content_id: Content ID
            analysis_types: List of analysis types to perform
            priority: Priority level (1-10, higher is more priority)

        Returns:
            Queue item ID
        """
        try:
            with db_manager.get_session() as session:
                # Check if item already exists in queue
                existing = session.query(AnalysisQueue).filter(
                    AnalysisQueue.target_id == target_id,
                    AnalysisQueue.content_type == content_type,
                    AnalysisQueue.content_id == content_id,
                    AnalysisQueue.status.in_(['pending', 'processing'])
                ).first()

                if existing:
                    # Update existing item with new analysis types
                    existing_types = set(existing.analysis_types)
                    new_types = set(analysis_types)
                    combined_types = list(existing_types.union(new_types))

                    existing.analysis_types = combined_types
                    existing.priority = max(existing.priority, priority)
                    session.commit()

                    logger.debug(f"Updated existing queue item {existing.id}")
                    return existing.id
                else:
                    # Create new queue item
                    queue_item = AnalysisQueue(
                        target_id=target_id,
                        content_type=content_type,
                        content_id=content_id,
                        analysis_types=analysis_types,
                        priority=priority
                    )

                    session.add(queue_item)
                    session.commit()

                    logger.debug(f"Added new item to analysis queue: {queue_item.id}")
                    return queue_item.id

        except Exception as e:
            logger.error(f"Failed to add item to analysis queue: {e}")
            raise

    def get_next_queue_item(self) -> Optional[AnalysisQueue]:
        """
        Get next item from analysis queue for processing

        Returns:
            Next queue item or None if queue is empty
        """
        try:
            with db_manager.get_session() as session:
                queue_item = session.query(AnalysisQueue).filter(
                    AnalysisQueue.status == 'pending'
                ).order_by(
                    AnalysisQueue.priority.desc(),
                    AnalysisQueue.created_at.asc()
                ).first()

                if queue_item:
                    # Mark as processing
                    queue_item.status = 'processing'
                    queue_item.started_at = datetime.now(timezone.utc)
                    session.commit()

                    logger.debug(f"Retrieved queue item {queue_item.id} for processing")

                return queue_item

        except Exception as e:
            logger.error(f"Failed to get next queue item: {e}")
            return None

    def update_queue_item_status(
        self,
        queue_item_id: int,
        status: str,
        error_message: str = None
    ):
        """
        Update queue item status

        Args:
            queue_item_id: Queue item ID
            status: New status (completed, failed, etc.)
            error_message: Error message if failed
        """
        try:
            with db_manager.get_session() as session:
                queue_item = session.query(AnalysisQueue).filter(
                    AnalysisQueue.id == queue_item_id
                ).first()

                if queue_item:
                    queue_item.status = status
                    queue_item.error_message = error_message

                    if status == 'completed':
                        queue_item.completed_at = datetime.now(timezone.utc)
                    elif status == 'failed':
                        queue_item.retry_count += 1
                        # Reset to pending if retries available
                        if queue_item.retry_count < queue_item.max_retries:
                            queue_item.status = 'pending'
                            queue_item.started_at = None

                    session.commit()
                    logger.debug(f"Updated queue item {queue_item_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update queue item status: {e}")

    def get_analysis_summary(self, target_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get analysis summary for a target

        Args:
            target_id: Target ID
            days: Number of days to analyze

        Returns:
            Analysis summary dictionary
        """
        try:
            with db_manager.get_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Get analysis counts by type
                analysis_counts = session.query(
                    AnalysisResult.analysis_type,
                    session.query(AnalysisResult).filter(
                        AnalysisResult.target_id == target_id,
                        AnalysisResult.analyzed_at >= cutoff_date
                    ).count()
                ).filter(
                    AnalysisResult.target_id == target_id,
                    AnalysisResult.analyzed_at >= cutoff_date
                ).group_by(AnalysisResult.analysis_type).all()

                # Get pattern counts by severity
                pattern_counts = session.query(
                    PatternDetectionResult.severity,
                    session.query(PatternDetectionResult).filter(
                        PatternDetectionResult.target_id == target_id,
                        PatternDetectionResult.detection_date >= cutoff_date,
                        PatternDetectionResult.status == 'active'
                    ).count()
                ).filter(
                    PatternDetectionResult.target_id == target_id,
                    PatternDetectionResult.detection_date >= cutoff_date,
                    PatternDetectionResult.status == 'active'
                ).group_by(PatternDetectionResult.severity).all()

                # Get queue status
                queue_counts = session.query(
                    AnalysisQueue.status,
                    session.query(AnalysisQueue).filter(
                        AnalysisQueue.target_id == target_id
                    ).count()
                ).filter(
                    AnalysisQueue.target_id == target_id
                ).group_by(AnalysisQueue.status).all()

                summary = {
                    'target_id': target_id,
                    'analysis_period_days': days,
                    'analysis_counts': dict(analysis_counts),
                    'pattern_counts': dict(pattern_counts),
                    'queue_counts': dict(queue_counts),
                    'total_analyses': sum(count for _, count in analysis_counts),
                    'total_active_patterns': sum(count for _, count in pattern_counts),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }

                return summary

        except Exception as e:
            logger.error(f"Failed to generate analysis summary: {e}")
            return {'error': str(e)}

    def cleanup_old_results(self, days: int = 90):
        """
        Clean up old analysis results to manage database size

        Args:
            days: Keep results newer than this many days
        """
        try:
            with db_manager.get_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Delete old analysis results
                deleted_analyses = session.query(AnalysisResult).filter(
                    AnalysisResult.analyzed_at < cutoff_date
                ).delete()

                # Delete old completed queue items
                deleted_queue = session.query(AnalysisQueue).filter(
                    AnalysisQueue.completed_at < cutoff_date,
                    AnalysisQueue.status == 'completed'
                ).delete()

                session.commit()

                logger.info(f"Cleaned up {deleted_analyses} old analysis results and {deleted_queue} queue items")

        except Exception as e:
            logger.error(f"Failed to cleanup old results: {e}")

# Global analysis database manager instance
analysis_db = AnalysisDatabaseManager()
