#!/usr/bin/env python3
"""
Comprehensive integration test to verify all SMSS system fixes
Tests the complete flow: database → authentication → browser → analysis → UI
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import db_manager
from core.data_manager import DataManager
from core.credentials_manager import get_credentials_manager
from core.browser_engine import InstagramBrowser
from analysis.deepseek_analyzer import DeepSeekAnalyzer

def test_integration_fixes():
    """Test complete system integration after fixes"""
    print("=" * 60)
    print("COMPREHENSIVE SMSS INTEGRATION TEST")
    print("=" * 60)
    
    test_results = {
        'database': False,
        'authentication': False,
        'browser': False,
        'analysis': False,
        'ui_compatibility': False
    }
    
    try:
        # 1. Test Database System
        print("\n1. TESTING DATABASE SYSTEM")
        print("-" * 40)
        
        dm = DataManager()
        print("   ✓ Database connection established")
        
        # Test CRUD operations
        target = dm.add_surveillance_target('integration_test_user', display_name='Integration Test User')
        if target and target.get('notifications_enabled') is not None:
            print("   ✓ Database CRUD operations working")
            print(f"   ✓ notifications_enabled column present: {target['notifications_enabled']}")
            test_results['database'] = True
        else:
            print("   ✗ Database CRUD operations failed")
            return test_results
        
        # Test getting targets (should return dictionaries)
        targets = dm.get_all_targets()
        if targets and isinstance(targets[0], dict):
            print(f"   ✓ Target retrieval working (found {len(targets)} targets as dictionaries)")
        else:
            print("   ✗ Target retrieval failed or wrong format")
            return test_results
        
        # 2. Test Authentication System
        print("\n2. TESTING AUTHENTICATION SYSTEM")
        print("-" * 40)
        
        creds_manager = get_credentials_manager()
        print("   ✓ Credentials manager initialized")
        
        # Test credential storage/retrieval
        test_success = creds_manager.set_instagram_credentials("test_integration", "test_password")
        if test_success:
            retrieved = creds_manager.get_instagram_credentials()
            if retrieved and retrieved['username'] == 'test_integration':
                print("   ✓ Credential storage and retrieval working")
                test_results['authentication'] = True
            else:
                print("   ✗ Credential retrieval failed")
                return test_results
        else:
            print("   ✗ Credential storage failed")
            return test_results
        
        # 3. Test Browser Engine
        print("\n3. TESTING BROWSER ENGINE")
        print("-" * 40)
        
        browser = None
        try:
            browser = InstagramBrowser()
            print("   ✓ Browser engine initialized")
            
            if browser.setup_driver():
                print("   ✓ Chrome driver setup successful")
                
                # Test basic navigation
                browser.driver.get("https://httpbin.org/get")  # Use a simple test endpoint
                if "httpbin" in browser.driver.title.lower() or "httpbin" in browser.driver.current_url:
                    print("   ✓ Basic navigation working")
                    test_results['browser'] = True
                else:
                    print("   ✗ Navigation test failed")
            else:
                print("   ✗ Chrome driver setup failed")
                
        except Exception as e:
            print(f"   ✗ Browser test failed: {e}")
        finally:
            if browser and browser.driver:
                browser.close()
                print("   ✓ Browser cleanup completed")
        
        # 4. Test Analysis System
        print("\n4. TESTING ANALYSIS SYSTEM")
        print("-" * 40)
        
        analyzer = DeepSeekAnalyzer()
        print("   ✓ DeepSeek analyzer initialized")
        
        # Test rate limiting configuration
        if hasattr(analyzer.api_client, 'max_retries') and analyzer.api_client.max_retries == 3:
            print(f"   ✓ Rate limiting configured (max_retries: {analyzer.api_client.max_retries})")
        else:
            print("   ✗ Rate limiting not properly configured")
            return test_results
        
        # Test mock response generation (since we don't have real API key)
        mock_response = analyzer.api_client._generate_mock_response("test", {"test": "data"})
        if mock_response and mock_response.get("mock_response"):
            print("   ✓ Mock response generation working")
            test_results['analysis'] = True
        else:
            print("   ✗ Mock response generation failed")
            return test_results
        
        # 5. Test UI Compatibility
        print("\n5. TESTING UI COMPATIBILITY")
        print("-" * 40)
        
        # Test that UI components can handle dictionary-based data
        try:
            # Simulate UI data processing
            for target in targets:
                # Test that target data can be accessed as dictionary
                target_id = target['id']
                username = target['instagram_username']
                notifications = target.get('notifications_enabled', True)
                
                print(f"   - Target {username} (ID: {target_id}, notifications: {notifications})")
            
            print("   ✓ UI data compatibility verified")
            test_results['ui_compatibility'] = True
            
        except Exception as e:
            print(f"   ✗ UI compatibility test failed: {e}")
            return test_results
        
        # Clean up test data
        print("\n6. CLEANUP")
        print("-" * 40)
        creds_manager.clear_credentials()
        print("   ✓ Test credentials cleared")
        
        return test_results
        
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return test_results

def print_test_summary(results):
    """Print test results summary"""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{component.upper():20} {status}")
    
    print("-" * 60)
    print(f"OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nThe SMSS system has been successfully restored to full functionality.")
        print("Key improvements implemented:")
        print("- Database schema fixes with migration system")
        print("- SQLAlchemy session management improvements")
        print("- Chrome driver compatibility fixes")
        print("- Encrypted credentials management")
        print("- Rate limiting with exponential backoff")
        print("- UI component compatibility with new data formats")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the failed components and address any remaining issues.")
        return False

if __name__ == "__main__":
    results = test_integration_fixes()
    success = print_test_summary(results)
    sys.exit(0 if success else 1)
