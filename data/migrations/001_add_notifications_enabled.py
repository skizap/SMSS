#!/usr/bin/env python3
"""
Database Migration 001: Add notifications_enabled column to surveillance_targets table
This migration adds the missing notifications_enabled column that was causing database errors.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def upgrade(db_path: str) -> bool:
    """
    Add notifications_enabled column to surveillance_targets table
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        bool: True if migration successful, False otherwise
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("PRAGMA table_info(surveillance_targets)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'notifications_enabled' not in columns:
                logger.info("Adding notifications_enabled column to surveillance_targets table")
                
                # Add the column with default value
                cursor.execute("""
                    ALTER TABLE surveillance_targets 
                    ADD COLUMN notifications_enabled BOOLEAN DEFAULT 1
                """)
                
                # Update existing records to have notifications enabled by default
                cursor.execute("""
                    UPDATE surveillance_targets 
                    SET notifications_enabled = 1 
                    WHERE notifications_enabled IS NULL
                """)
                
                conn.commit()
                logger.info("Successfully added notifications_enabled column")
                return True
            else:
                logger.info("notifications_enabled column already exists, skipping migration")
                return True
                
    except Exception as e:
        logger.error(f"Error running migration 001: {e}")
        return False

def downgrade(db_path: str) -> bool:
    """
    Remove notifications_enabled column from surveillance_targets table
    Note: SQLite doesn't support DROP COLUMN, so this creates a new table without the column
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        bool: True if downgrade successful, False otherwise
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if column exists
            cursor.execute("PRAGMA table_info(surveillance_targets)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'notifications_enabled' in columns:
                logger.info("Removing notifications_enabled column from surveillance_targets table")
                
                # Create new table without the column
                cursor.execute("""
                    CREATE TABLE surveillance_targets_new (
                        id INTEGER PRIMARY KEY,
                        instagram_username VARCHAR(100) UNIQUE NOT NULL,
                        display_name VARCHAR(200),
                        profile_pic_url TEXT,
                        is_private BOOLEAN DEFAULT 0,
                        follower_count INTEGER DEFAULT 0,
                        following_count INTEGER DEFAULT 0,
                        post_count INTEGER DEFAULT 0,
                        bio TEXT,
                        external_url TEXT,
                        is_verified BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP,
                        last_updated TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'active',
                        category VARCHAR(100),
                        priority VARCHAR(20) DEFAULT 'medium',
                        notes TEXT
                    )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                    INSERT INTO surveillance_targets_new 
                    SELECT id, instagram_username, display_name, profile_pic_url, 
                           is_private, follower_count, following_count, post_count,
                           bio, external_url, is_verified, created_at, last_updated,
                           status, category, priority, notes
                    FROM surveillance_targets
                """)
                
                # Drop old table and rename new table
                cursor.execute("DROP TABLE surveillance_targets")
                cursor.execute("ALTER TABLE surveillance_targets_new RENAME TO surveillance_targets")
                
                # Recreate indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_targets_username ON surveillance_targets(instagram_username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_targets_status ON surveillance_targets(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_targets_updated ON surveillance_targets(last_updated)")
                
                conn.commit()
                logger.info("Successfully removed notifications_enabled column")
                return True
            else:
                logger.info("notifications_enabled column doesn't exist, skipping downgrade")
                return True
                
    except Exception as e:
        logger.error(f"Error running downgrade 001: {e}")
        return False

if __name__ == "__main__":
    # Test migration
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    db_path = project_root / "data" / "surveillance.db"
    
    print(f"Testing migration on database: {db_path}")
    
    if upgrade(str(db_path)):
        print("Migration 001 upgrade successful")
    else:
        print("Migration 001 upgrade failed")
