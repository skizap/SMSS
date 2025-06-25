"""
Social Media Surveillance System - Database Engine
Comprehensive SQLite database management with efficient indexing and relationships.
"""

import os
import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from contextlib import contextmanager
from datetime import datetime, timedelta
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, 
    Float, JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    event, pool
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, scoped_session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.sql import func, text

from .config import config

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

class DatabaseManager:
    """Main database management class with connection pooling and optimization"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.db_path
        self.engine = None
        self.session_factory = None
        self.scoped_session = None
        
        # Connection pool settings
        self.pool_size = config.database.max_connections
        self.pool_timeout = config.database.connection_timeout
        
        # Thread-local storage for sessions
        self._local = threading.local()
        
        # Database statistics
        self.stats = {
            'connections_created': 0,
            'queries_executed': 0,
            'errors_occurred': 0,
            'last_backup': None
        }
        
        self._setup_database()
        
    def _setup_database(self):
        """Initialize database engine and session factory"""
        try:
            # Ensure database directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Create SQLite engine with optimizations
            self.engine = create_engine(
                f'sqlite:///{self.db_path}',
                poolclass=StaticPool,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                connect_args={
                    'check_same_thread': False,
                    'timeout': self.pool_timeout,
                    'isolation_level': None  # Autocommit mode
                },
                echo=False  # Set to True for SQL debugging
            )
            
            # Configure SQLite for performance
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # Performance optimizations
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous=NORMAL")  # Balanced safety/speed
                cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
                cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
                cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
                cursor.close()
                
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            self.scoped_session = scoped_session(self.session_factory)
            
            # Create all tables
            self._create_tables()
            
            # Create indexes for performance
            self._create_indexes()

            # Run database migrations
            self._run_migrations()

            logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            raise
            
    def _create_tables(self):
        """Create all database tables"""
        try:
            # Import models to register them with Base
            from models import instagram_models
            from models import analytics_models
            # Note: analysis_database import disabled due to circular import
            # from analysis import analysis_database

            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
            
    def _create_indexes(self):
        """Create database indexes for performance optimization"""
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                # Surveillance targets indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_targets_username ON surveillance_targets(instagram_username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_targets_status ON surveillance_targets(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_targets_updated ON surveillance_targets(last_updated)"))

                # Posts indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_target ON posts(target_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_instagram_id ON posts(instagram_post_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(post_type)"))

                # Followers indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_followers_target ON followers(target_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_followers_username ON followers(follower_username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_followers_status ON followers(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_followers_detected ON followers(detected_at)"))

                # Stories indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stories_target ON stories(target_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stories_posted ON stories(posted_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stories_expires ON stories(expires_at)"))

                # Change log indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_changelog_target ON change_log(target_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_changelog_type ON change_log(change_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_changelog_detected ON change_log(detected_at)"))

                conn.commit()

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def _run_migrations(self):
        """Run pending database migrations"""
        try:
            from .migration_manager import get_migration_manager

            migration_manager = get_migration_manager(self.db_path)
            success = migration_manager.run_pending_migrations()

            if success:
                logger.info("Database migrations completed successfully")
            else:
                logger.warning("Some database migrations failed")

        except Exception as e:
            logger.error(f"Error running migrations: {e}")

    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.scoped_session()
        try:
            yield session
            session.commit()
            self.stats['queries_executed'] += 1
        except Exception as e:
            session.rollback()
            self.stats['errors_occurred'] += 1
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
            
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute raw SQL query and return results"""
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
            
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create database backup"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.db_path}.backup_{timestamp}"
                
            # Use SQLite backup API for consistent backup
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
                    
            self.stats['last_backup'] = datetime.now()
            logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return False
            
    def optimize_database(self):
        """Optimize database performance"""
        try:
            with self.engine.connect() as conn:
                # Analyze tables for query optimization
                conn.execute("ANALYZE")
                
                # Vacuum database to reclaim space
                conn.execute("VACUUM")
                
                # Update table statistics
                conn.execute("PRAGMA optimize")
                
                conn.commit()
                
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information"""
        try:
            from sqlalchemy import text

            stats = self.stats.copy()

            with self.engine.connect() as conn:
                # Get database size
                result = conn.execute(text("PRAGMA page_count"))
                page_count = result.fetchone()[0]

                result = conn.execute(text("PRAGMA page_size"))
                page_size = result.fetchone()[0]

                stats['database_size_mb'] = (page_count * page_size) / (1024 * 1024)

                # Get table counts
                tables = ['surveillance_targets', 'posts', 'followers', 'stories', 'change_log']
                for table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[f'{table}_count'] = result.fetchone()[0]

            return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return self.stats.copy()
            
    def close(self):
        """Close database connections"""
        try:
            if self.scoped_session:
                self.scoped_session.remove()
            if self.engine:
                self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

class DataVersionManager:
    """Manages data versioning and change tracking"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def track_change(self, target_id: int, change_type: str, old_value: Any = None,
                    new_value: Any = None, session: Optional[Session] = None):
        """Track a change in the change log"""
        try:
            from models.instagram_models import ChangeLog

            change_log = ChangeLog(
                target_id=target_id,
                change_type=change_type,
                old_value=json.dumps(old_value) if old_value is not None else None,
                new_value=json.dumps(new_value) if new_value is not None else None,
                detected_at=datetime.utcnow()
            )

            if session:
                session.add(change_log)
            else:
                with self.db_manager.get_session() as session:
                    session.add(change_log)

        except Exception as e:
            logger.error(f"Error tracking change: {e}")

    def get_changes(self, target_id: Optional[int] = None, change_type: Optional[str] = None,
                   since: Optional[datetime] = None, limit: int = 100) -> List[Dict]:
        """Get change history with optional filters"""
        try:
            from models.instagram_models import ChangeLog

            with self.db_manager.get_session() as session:
                query = session.query(ChangeLog)

                if target_id:
                    query = query.filter(ChangeLog.target_id == target_id)
                if change_type:
                    query = query.filter(ChangeLog.change_type == change_type)
                if since:
                    query = query.filter(ChangeLog.detected_at >= since)

                changes = query.order_by(ChangeLog.detected_at.desc()).limit(limit).all()

                return [{
                    'id': change.id,
                    'target_id': change.target_id,
                    'change_type': change.change_type,
                    'old_value': json.loads(change.old_value) if change.old_value else None,
                    'new_value': json.loads(change.new_value) if change.new_value else None,
                    'detected_at': change.detected_at
                } for change in changes]

        except Exception as e:
            logger.error(f"Error getting changes: {e}")
            return []

    def cleanup_old_changes(self, days_to_keep: int = 90):
        """Clean up old change log entries"""
        try:
            from models.instagram_models import ChangeLog

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            with self.db_manager.get_session() as session:
                deleted_count = session.query(ChangeLog).filter(
                    ChangeLog.detected_at < cutoff_date
                ).delete()

                logger.info(f"Cleaned up {deleted_count} old change log entries")
                return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old changes: {e}")
            return 0

class DatabaseHealthMonitor:
    """Monitors database health and performance"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive database health check"""
        health_report = {
            'status': 'healthy',
            'issues': [],
            'recommendations': [],
            'stats': {}
        }

        try:
            # Check database connectivity
            from sqlalchemy import text

            with self.db_manager.get_session() as session:
                session.execute(text("SELECT 1"))

            # Get database statistics
            health_report['stats'] = self.db_manager.get_database_stats()

            # Check for performance issues
            self._check_performance_issues(health_report)

            # Check for data integrity issues
            self._check_data_integrity(health_report)

            # Check disk space
            self._check_disk_space(health_report)

            # Determine overall status
            if health_report['issues']:
                health_report['status'] = 'warning' if len(health_report['issues']) < 3 else 'critical'

        except Exception as e:
            health_report['status'] = 'critical'
            health_report['issues'].append(f"Database connectivity error: {e}")

        return health_report

    def _check_performance_issues(self, health_report: Dict):
        """Check for database performance issues"""
        try:
            stats = health_report['stats']

            # Check error rate
            if stats.get('errors_occurred', 0) > 0:
                error_rate = stats['errors_occurred'] / max(stats.get('queries_executed', 1), 1)
                if error_rate > 0.05:  # 5% error rate
                    health_report['issues'].append(f"High error rate: {error_rate:.2%}")

            # Check database size
            db_size_mb = stats.get('database_size_mb', 0)
            if db_size_mb > 1000:  # 1GB
                health_report['issues'].append(f"Large database size: {db_size_mb:.1f}MB")
                health_report['recommendations'].append("Consider archiving old data")

        except Exception as e:
            logger.error(f"Error checking performance issues: {e}")

    def _check_data_integrity(self, health_report: Dict):
        """Check for data integrity issues"""
        try:
            from sqlalchemy import text

            with self.db_manager.get_session() as session:
                # Check for orphaned records
                orphaned_posts = session.execute(text("""
                    SELECT COUNT(*) FROM posts p
                    LEFT JOIN surveillance_targets t ON p.target_id = t.id
                    WHERE t.id IS NULL
                """)).fetchone()[0]

                if orphaned_posts > 0:
                    health_report['issues'].append(f"Found {orphaned_posts} orphaned posts")

                orphaned_followers = session.execute(text("""
                    SELECT COUNT(*) FROM followers f
                    LEFT JOIN surveillance_targets t ON f.target_id = t.id
                    WHERE t.id IS NULL
                """)).fetchone()[0]

                if orphaned_followers > 0:
                    health_report['issues'].append(f"Found {orphaned_followers} orphaned followers")

        except Exception as e:
            logger.error(f"Error checking data integrity: {e}")

    def _check_disk_space(self, health_report: Dict):
        """Check available disk space"""
        try:
            import shutil

            db_path = Path(self.db_manager.db_path)
            total, used, free = shutil.disk_usage(db_path.parent)

            free_gb = free / (1024**3)
            if free_gb < 1:  # Less than 1GB free
                health_report['issues'].append(f"Low disk space: {free_gb:.1f}GB free")
                health_report['recommendations'].append("Free up disk space")

        except Exception as e:
            logger.error(f"Error checking disk space: {e}")

# Global database instance
db_manager = DatabaseManager()
version_manager = DataVersionManager(db_manager)
health_monitor = DatabaseHealthMonitor(db_manager)
