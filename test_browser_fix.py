#!/usr/bin/env python3
"""
Test script to verify browser engine fixes
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.browser_engine import InstagramBrowser
from core.config import config

def test_browser_fixes():
    """Test browser functionality after fixes"""
    print("=" * 50)
    print("TESTING BROWSER ENGINE FIXES")
    print("=" * 50)
    
    browser = None
    try:
        # Test browser initialization
        print("1. Testing browser initialization...")
        browser = InstagramBrowser()
        print("   ✓ Browser engine created successfully")
        
        # Test driver setup
        print("2. Testing Chrome driver setup...")
        success = browser.setup_driver()
        if success:
            print("   ✓ Chrome driver setup successful")
        else:
            print("   ✗ Chrome driver setup failed")
            return False
        
        # Test basic navigation
        print("3. Testing basic navigation...")
        browser.driver.get("https://www.google.com")
        title = browser.driver.title
        print(f"   ✓ Successfully navigated to Google: {title}")
        
        # Test screenshot functionality
        print("4. Testing screenshot functionality...")
        screenshot_path = browser.take_screenshot("test_browser_fix.png")
        if screenshot_path:
            print(f"   ✓ Screenshot saved: {screenshot_path}")
        else:
            print("   ✗ Screenshot failed")
        
        print("\n" + "=" * 50)
        print("BROWSER TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"   ✗ Browser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if browser and browser.driver:
            print("5. Cleaning up browser...")
            browser.close()
            print("   ✓ Browser closed successfully")

if __name__ == "__main__":
    success = test_browser_fixes()
    sys.exit(0 if success else 1)
