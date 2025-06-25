"""
Social Media Surveillance System - Database Migration Manager
Handles database schema migrations and version tracking.
"""

import sqlite3
import logging
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_path: str, migrations_dir: str = "data/migrations"):
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure migration tracking table exists
        self._create_migration_table()
    
    def _create_migration_table(self):
        """Create table to track applied migrations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_name VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error creating migration table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration names"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT migration_name FROM schema_migrations 
                    WHERE success = 1 
                    ORDER BY migration_name
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Path]:
        """Get list of pending migration files"""
        try:
            applied = set(self.get_applied_migrations())
            all_migrations = []
            
            # Find all migration files
            for migration_file in self.migrations_dir.glob("*.py"):
                if migration_file.name.startswith("__"):
                    continue  # Skip __init__.py and __pycache__
                    
                migration_name = migration_file.stem
                if migration_name not in applied:
                    all_migrations.append(migration_file)
            
            # Sort by filename (which should include version numbers)
            return sorted(all_migrations)
            
        except Exception as e:
            logger.error(f"Error getting pending migrations: {e}")
            return []
    
    def run_migration(self, migration_file: Path) -> bool:
        """Run a single migration file"""
        try:
            migration_name = migration_file.stem
            logger.info(f"Running migration: {migration_name}")
            
            # Load migration module
            spec = importlib.util.spec_from_file_location(migration_name, migration_file)
            if not spec or not spec.loader:
                logger.error(f"Could not load migration module: {migration_file}")
                return False
                
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Check if upgrade function exists
            if not hasattr(migration_module, 'upgrade'):
                logger.error(f"Migration {migration_name} missing upgrade function")
                return False
            
            # Run the migration
            success = migration_module.upgrade(self.db_path)
            
            if success:
                # Record successful migration
                self._record_migration(migration_name, True)
                logger.info(f"Migration {migration_name} completed successfully")
            else:
                # Record failed migration
                self._record_migration(migration_name, False)
                logger.error(f"Migration {migration_name} failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error running migration {migration_file}: {e}")
            self._record_migration(migration_file.stem, False)
            return False
    
    def run_pending_migrations(self) -> bool:
        """Run all pending migrations"""
        try:
            pending = self.get_pending_migrations()
            
            if not pending:
                logger.info("No pending migrations")
                return True
            
            logger.info(f"Found {len(pending)} pending migrations")
            
            success_count = 0
            for migration_file in pending:
                if self.run_migration(migration_file):
                    success_count += 1
                else:
                    logger.error(f"Migration failed, stopping: {migration_file.name}")
                    break
            
            if success_count == len(pending):
                logger.info(f"All {success_count} migrations completed successfully")
                return True
            else:
                logger.error(f"Only {success_count}/{len(pending)} migrations completed")
                return False
                
        except Exception as e:
            logger.error(f"Error running pending migrations: {e}")
            return False
    
    def _record_migration(self, migration_name: str, success: bool):
        """Record migration attempt in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO schema_migrations 
                    (migration_name, applied_at, success) 
                    VALUES (?, ?, ?)
                """, (migration_name, datetime.now(timezone.utc), success))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording migration: {e}")
    
    def rollback_migration(self, migration_name: str) -> bool:
        """Rollback a specific migration"""
        try:
            migration_file = self.migrations_dir / f"{migration_name}.py"
            
            if not migration_file.exists():
                logger.error(f"Migration file not found: {migration_file}")
                return False
            
            # Load migration module
            spec = importlib.util.spec_from_file_location(migration_name, migration_file)
            if not spec or not spec.loader:
                logger.error(f"Could not load migration module: {migration_file}")
                return False
                
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Check if downgrade function exists
            if not hasattr(migration_module, 'downgrade'):
                logger.error(f"Migration {migration_name} missing downgrade function")
                return False
            
            # Run the rollback
            success = migration_module.downgrade(self.db_path)
            
            if success:
                # Remove migration record
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM schema_migrations 
                        WHERE migration_name = ?
                    """, (migration_name,))
                    conn.commit()
                
                logger.info(f"Migration {migration_name} rolled back successfully")
            else:
                logger.error(f"Migration {migration_name} rollback failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rolling back migration {migration_name}: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            applied = self.get_applied_migrations()
            pending = self.get_pending_migrations()
            
            return {
                'applied_count': len(applied),
                'pending_count': len(pending),
                'applied_migrations': applied,
                'pending_migrations': [f.name for f in pending],
                'last_migration': applied[-1] if applied else None
            }
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return {
                'applied_count': 0,
                'pending_count': 0,
                'applied_migrations': [],
                'pending_migrations': [],
                'last_migration': None,
                'error': str(e)
            }

# Global migration manager instance
migration_manager = None

def get_migration_manager(db_path: Optional[str] = None) -> MigrationManager:
    """Get global migration manager instance"""
    global migration_manager
    
    if migration_manager is None:
        if db_path is None:
            from core.config import config
            db_path = config.database.db_path
        migration_manager = MigrationManager(db_path)
    
    return migration_manager
