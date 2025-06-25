#!/usr/bin/env python3
"""
Test script to verify database fixes
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import db_manager
from core.data_manager import DataManager

def test_database_fixes():
    """Test database functionality after fixes"""
    print("=" * 50)
    print("TESTING DATABASE FIXES")
    print("=" * 50)
    
    try:
        # Test database connection
        print("1. Testing database connection...")
        dm = DataManager()
        print("   ✓ Database connection successful")
        
        # Test adding a target
        print("2. Testing add surveillance target...")
        target = dm.add_surveillance_target('test_user_fixed', display_name='Test User Fixed')
        if target:
            print(f"   ✓ Successfully added target: {target['instagram_username']}")
        else:
            print("   ✗ Failed to add target")
            return False
        
        # Test getting targets
        print("3. Testing get all targets...")
        targets = dm.get_all_targets()
        print(f"   ✓ Found {len(targets)} targets")
        
        # Check notifications_enabled column
        print("4. Checking notifications_enabled column...")
        for target in targets:
            username = target.get('instagram_username', 'Unknown')
            notifications = target.get('notifications_enabled', 'N/A')
            print(f"   - {username}: notifications_enabled={notifications}")
        
        # Test dashboard stats
        print("5. Testing dashboard stats...")
        stats = dm.get_dashboard_stats()
        print(f"   ✓ Dashboard stats: {stats}")
        
        print("\n" + "=" * 50)
        print("DATABASE TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_fixes()
    sys.exit(0 if success else 1)
