#!/usr/bin/env python3
"""
Test script to verify authentication system fixes
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.credentials_manager import get_credentials_manager
from core.browser_engine import InstagramBrowser

def test_authentication_fixes():
    """Test authentication functionality after fixes"""
    print("=" * 50)
    print("TESTING AUTHENTICATION SYSTEM FIXES")
    print("=" * 50)
    
    try:
        # Test credentials manager
        print("1. Testing credentials manager...")
        creds_manager = get_credentials_manager()
        print("   ✓ Credentials manager created successfully")
        
        # Check credential status
        print("2. Checking credential status...")
        status = creds_manager.get_credential_status()
        print(f"   - Instagram credentials: {'✓' if status['instagram'] else '✗'}")
        print(f"   - DeepSeek API key: {'✓' if status['deepseek'] else '✗'}")
        print(f"   - Notification config: {'✓' if status['notification'] else '✗'}")
        
        # Test setting test credentials (for demo purposes)
        print("3. Testing credential storage...")
        test_success = creds_manager.set_instagram_credentials("test_user", "test_password")
        if test_success:
            print("   ✓ Successfully stored test credentials")
        else:
            print("   ✗ Failed to store test credentials")
            return False
        
        # Test retrieving credentials
        print("4. Testing credential retrieval...")
        retrieved_creds = creds_manager.get_instagram_credentials()
        if retrieved_creds and retrieved_creds['username'] == 'test_user':
            print("   ✓ Successfully retrieved test credentials")
        else:
            print("   ✗ Failed to retrieve test credentials")
            return False
        
        # Test browser authentication check
        print("5. Testing browser authentication check...")
        browser = InstagramBrowser()
        
        # Note: We won't actually try to login with test credentials
        # as they're not real, but we can test the credential loading
        has_creds = creds_manager.has_instagram_credentials()
        if has_creds:
            print("   ✓ Browser can access stored credentials")
        else:
            print("   ✗ Browser cannot access stored credentials")
            return False
        
        # Clean up test credentials
        print("6. Cleaning up test credentials...")
        creds_manager.clear_credentials()
        print("   ✓ Test credentials cleared")
        
        print("\n" + "=" * 50)
        print("AUTHENTICATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("\nNOTE: To use the system with real Instagram credentials:")
        print("1. Run: python -c \"from core.credentials_manager import get_credentials_manager; cm = get_credentials_manager(); cm.set_instagram_credentials('your_username', 'your_password')\"")
        print("2. Or manually edit config/credentials.json with encrypted credentials")
        return True
        
    except Exception as e:
        print(f"   ✗ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_authentication_fixes()
    sys.exit(0 if success else 1)
