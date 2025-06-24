#!/usr/bin/env python3
"""
Social Media Surveillance System - Main Launcher
Entry point for the surveillance system with full Phase 5 UI integration.
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from typing import List

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/surveillance_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def launch_ui_dashboard():
    """Launch the PyQt6 dashboard interface"""
    try:
        # Import PyQt6 components
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QSettings

        # Import UI components
        from ui.main_dashboard import MainDashboard
        from ui.themes import load_saved_theme, get_theme_manager
        from ui.realtime_updates import get_update_manager

        print("🚀 Launching Social Media Surveillance System - Phase 5 Dashboard")
        print("=" * 70)

        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("Social Media Surveillance System")
        app.setApplicationVersion("1.0.0 - Phase 5")
        app.setOrganizationName("SMSS Team")

        # Load and apply saved theme
        print("🎨 Loading UI theme...")
        load_saved_theme()

        # Initialize real-time update manager
        print("⚡ Initializing real-time updates...")
        update_manager = get_update_manager()

        # Create main dashboard
        print("📊 Creating main dashboard...")
        dashboard = MainDashboard()

        # Connect real-time updates to dashboard
        update_manager.new_post_detected.connect(
            lambda data: dashboard.activity_feed.add_activity("new_post", f"New post from @{data.get('target_username', 'unknown')}")
        )
        update_manager.new_follower_detected.connect(
            lambda data: dashboard.activity_feed.add_activity("new_follower", f"@{data.get('target_username', 'unknown')} gained a follower")
        )
        update_manager.system_status_updated.connect(
            lambda data: dashboard.system_stats.update_stats()
        )

        # Start real-time updates
        print("🔄 Starting real-time update system...")
        update_manager.start()

        # Show dashboard
        print("✨ Displaying dashboard...")
        dashboard.show()

        # Show welcome message
        dashboard.show_notification(
            "SMSS Dashboard Launched",
            "Social Media Surveillance System Phase 5 is now running with full UI integration!",
            "info"
        )

        print("\n🎉 Dashboard launched successfully!")
        print("📋 Available Features:")
        print("   ✅ Main Dashboard with Real-time Monitoring")
        print("   ✅ Surveillance Panel with Target Management")
        print("   ✅ Analytics Panel with Data Visualization")
        print("   ✅ Settings Panel with Configuration")
        print("   ✅ Notification System with Alerts")
        print("   ✅ Real-time Updates and Background Processing")
        print("   ✅ Modern UI with Light/Dark Theme Support")
        print("\n💡 Use the dashboard to manage surveillance targets and monitor activity!")

        # Start event loop
        exit_code = app.exec()

        # Cleanup
        print("\n🔄 Shutting down...")
        update_manager.stop()

        return exit_code

    except ImportError as e:
        print(f"❌ UI components not available: {e}")
        print("   Please ensure PyQt6 is installed: pip install PyQt6")
        return 1
    except Exception as e:
        logger.error(f"Error launching UI dashboard: {e}")
        print(f"❌ Failed to launch dashboard: {e}")
        return 1

def test_browser_engine():
    """Test the browser engine functionality"""
    try:
        from core.browser_engine import InstagramBrowser

        print("🚀 Testing Social Media Surveillance System - Browser Engine")
        print("=" * 60)

        # Initialize browser
        print("📱 Initializing browser engine...")
        browser = InstagramBrowser()

        # Setup driver
        print("🔧 Setting up Chrome driver with stealth configuration...")
        if not browser.setup_driver():
            print("❌ Failed to setup browser driver")
            return False

        print("✅ Browser driver setup successful")

        # Test navigation
        print("🌐 Testing navigation to Instagram...")
        browser.driver.get("https://www.instagram.com")

        # Take screenshot
        print("📸 Taking screenshot...")
        screenshot_path = browser.take_screenshot("test_instagram_page.png")
        if screenshot_path:
            print(f"✅ Screenshot saved: {screenshot_path}")

        # Test scrolling
        print("📜 Testing page scrolling...")
        browser.scroll_page(scrolls=2)
        print("✅ Scrolling test completed")

        print("\n🎉 Browser engine test completed successfully!")

        # Keep browser open for manual inspection
        input("\n⏸️  Press Enter to close browser and exit...")

        return True

    except Exception as e:
        logger.error(f"Error during browser engine test: {e}")
        print(f"❌ Test failed: {e}")
        return False

    finally:
        # Cleanup
        try:
            browser.close()
        except:
            pass

def run_tests():
    """Run comprehensive test suite"""
    print("🧪 Running Comprehensive Test Suite")
    print("=" * 50)

    test_results = {}

    # Test Phase 2 - Database
    try:
        print("\n📊 Testing Phase 2 - Database & Data Models...")
        from test_phase2_database import run_database_tests
        test_results['phase2'] = run_database_tests()
    except Exception as e:
        print(f"❌ Phase 2 tests failed: {e}")
        test_results['phase2'] = False

    # Test Phase 3 - Scrapers
    try:
        print("\n🕷️ Testing Phase 3 - Instagram Scrapers...")
        from test_phase3_scrapers import run_scraper_tests
        test_results['phase3'] = run_scraper_tests()
    except Exception as e:
        print(f"❌ Phase 3 tests failed: {e}")
        test_results['phase3'] = False

    # Test Phase 4 - Analysis
    try:
        print("\n🤖 Testing Phase 4 - AI Analysis Engine...")
        from test_phase4_analysis import run_analysis_tests
        test_results['phase4'] = run_analysis_tests()
    except Exception as e:
        print(f"❌ Phase 4 tests failed: {e}")
        test_results['phase4'] = False

    # Test Phase 5 - UI
    try:
        print("\n🖥️ Testing Phase 5 - PyQt6 Dashboard...")
        from test_phase5_ui import run_ui_tests
        test_results['phase5'] = run_ui_tests()
    except Exception as e:
        print(f"❌ Phase 5 tests failed: {e}")
        test_results['phase5'] = False

    # Test Phase 7 - Integration
    try:
        print("\n🔗 Testing Phase 7 - Complete Integration...")
        from test_phase7_integration import run_all_integration_tests
        test_results['phase7'] = run_all_integration_tests()
    except Exception as e:
        print(f"❌ Phase 7 tests failed: {e}")
        test_results['phase7'] = False

    # Print overall results
    print("\n" + "=" * 70)
    print("📋 COMPREHENSIVE TEST RESULTS:")
    print("=" * 70)

    for phase, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {phase.upper()}: {status}")

    overall_success = all(test_results.values())

    if overall_success:
        print("\n🎉 ALL TESTS PASSED! System is ready for production use.")
    else:
        print("\n⚠️ Some tests failed. Please review and fix issues before deployment.")

    return overall_success

def show_system_info():
    """Show system information and status"""
    print("📋 Social Media Surveillance System - System Information")
    print("=" * 60)

    # System info
    print("🖥️ System Information:")
    print(f"   Python Version: {sys.version}")
    print(f"   Platform: {sys.platform}")
    print(f"   Project Root: {project_root}")

    # Check dependencies
    print("\n📦 Dependency Status:")

    dependencies = [
        ("PyQt6", "PyQt6.QtWidgets"),
        ("Selenium", "selenium"),
        ("SQLAlchemy", "sqlalchemy"),
        ("Requests", "requests"),
        ("Pillow", "PIL"),
        ("NumPy", "numpy"),
        ("Pandas", "pandas"),
        ("Matplotlib", "matplotlib")
    ]

    for name, module in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {name}: Available")
        except ImportError:
            print(f"   ❌ {name}: Not available")

    # Check project structure
    print("\n📁 Project Structure:")

    required_dirs = [
        "core", "models", "scrapers", "analysis", "ui",
        "notifications", "reporting", "security", "data"
    ]

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"   ✅ {dir_name}/: Present")
        else:
            print(f"   ❌ {dir_name}/: Missing")

    # Phase completion status
    print("\n🚀 Phase Completion Status:")
    phases = [
        ("Phase 1", "Browser Engine", "core/browser_engine.py"),
        ("Phase 2", "Database & Models", "models/instagram_models.py"),
        ("Phase 3", "Instagram Scrapers", "scrapers/instagram_profile_scraper.py"),
        ("Phase 4", "AI Analysis", "analysis/deepseek_analyzer.py"),
        ("Phase 5", "PyQt6 Dashboard", "ui/main_dashboard.py"),
        ("Phase 7", "Complete Integration", "scrapers/instagram_hashtag_scraper.py")
    ]

    for phase, description, key_file in phases:
        file_path = project_root / key_file
        if file_path.exists():
            print(f"   ✅ {phase}: {description} - Complete")
        else:
            print(f"   ❌ {phase}: {description} - Missing")

def run_headless_mode(args):
    """Run system in headless mode for automation"""
    try:
        print("🤖 Starting headless automation mode...")
        print("   This mode runs scrapers without UI for automation purposes")

        # This would implement headless automation logic
        # For now, just show what would be available
        print("\n📋 Available headless operations:")
        print("   • Profile scraping: --scrape-profile USERNAME")
        print("   • Post scraping: --scrape-posts USERNAME")
        print("   • Hashtag analysis: --scrape-hashtag HASHTAG")
        print("   • Location analysis: --scrape-location LOCATION_ID")
        print("   • Follower tracking: --track-followers USERNAME")
        print("   • Batch operations: --batch-operation TYPE")

        return 0

    except Exception as e:
        logger.error(f"Error in headless mode: {e}")
        return 1

def run_profile_scraping(username: str, args):
    """Run profile scraping for a specific user"""
    try:
        from scrapers.instagram_profile_scraper import scrape_single_profile

        print(f"👤 Scraping profile: @{username}")
        print("=" * 50)

        # Perform profile scraping
        result = scrape_single_profile(username)

        if result:
            print(f"✅ Profile scraping completed for @{username}")
            _output_results("profile", result, args.output_format)
            return 0
        else:
            print(f"❌ Profile scraping failed for @{username}")
            return 1

    except Exception as e:
        logger.error(f"Error scraping profile {username}: {e}")
        print(f"❌ Error: {e}")
        return 1

def run_post_scraping(username: str, args):
    """Run post scraping for a specific user"""
    try:
        from scrapers.instagram_post_scraper import scrape_user_posts_quick

        print(f"📝 Scraping posts from: @{username}")
        print(f"   Max posts: {args.max_items}")
        print("=" * 50)

        # Perform post scraping
        result = scrape_user_posts_quick(username, args.max_items)

        if result and result.get('status') == 'completed':
            print(f"✅ Post scraping completed for @{username}")
            print(f"   Posts scraped: {len(result.get('posts_scraped', []))}")
            _output_results("posts", result, args.output_format)
            return 0
        else:
            print(f"❌ Post scraping failed for @{username}")
            return 1

    except Exception as e:
        logger.error(f"Error scraping posts for {username}: {e}")
        print(f"❌ Error: {e}")
        return 1

def run_hashtag_analysis(hashtag: str, args):
    """Run hashtag analysis"""
    try:
        from scrapers.instagram_hashtag_scraper import analyze_hashtag_quick

        print(f"🏷️ Analyzing hashtag: #{hashtag}")
        print(f"   Max posts: {args.max_items}")
        print("=" * 50)

        # Perform hashtag analysis
        result = analyze_hashtag_quick(hashtag, args.max_items)

        if result and result.get('status') == 'completed':
            print(f"✅ Hashtag analysis completed for #{hashtag}")
            print(f"   Post count: {result.get('post_count', 0)}")
            print(f"   Trending score: {result.get('trending_score', 0):.2f}")
            _output_results("hashtag", result, args.output_format)
            return 0
        else:
            print(f"❌ Hashtag analysis failed for #{hashtag}")
            return 1

    except Exception as e:
        logger.error(f"Error analyzing hashtag {hashtag}: {e}")
        print(f"❌ Error: {e}")
        return 1

def run_location_analysis(location_id: str, args):
    """Run location analysis"""
    try:
        from scrapers.instagram_location_scraper import analyze_location_quick

        print(f"📍 Analyzing location: {location_id}")
        print(f"   Max posts: {args.max_items}")
        print("=" * 50)

        # Perform location analysis
        result = analyze_location_quick(location_id, args.max_items)

        if result and result.get('status') == 'completed':
            print(f"✅ Location analysis completed for {location_id}")
            print(f"   Location: {result.get('location_name', 'Unknown')}")
            print(f"   Post count: {result.get('post_count', 0)}")
            print(f"   Popularity score: {result.get('popularity_score', 0):.2f}")
            _output_results("location", result, args.output_format)
            return 0
        else:
            print(f"❌ Location analysis failed for {location_id}")
            return 1

    except Exception as e:
        logger.error(f"Error analyzing location {location_id}: {e}")
        print(f"❌ Error: {e}")
        return 1

def run_follower_tracking(username: str, args):
    """Run follower tracking for a specific user"""
    try:
        from scrapers.follower_tracker import track_followers_quick

        print(f"👥 Tracking followers for: @{username}")
        print(f"   Max followers: {args.max_items}")
        print("=" * 50)

        # Perform follower tracking
        result = track_followers_quick(username, args.max_items)

        if result and result.get('status') == 'completed':
            print(f"✅ Follower tracking completed for @{username}")
            print(f"   New followers: {len(result.get('new_followers', []))}")
            print(f"   Unfollowed: {len(result.get('unfollowed_users', []))}")
            _output_results("followers", result, args.output_format)
            return 0
        else:
            print(f"❌ Follower tracking failed for @{username}")
            return 1

    except Exception as e:
        logger.error(f"Error tracking followers for {username}: {e}")
        print(f"❌ Error: {e}")
        return 1

def run_batch_operation(operation_type: str, args):
    """Run batch operations on multiple targets using coordinator"""
    try:
        from core.scraper_coordinator import coordinator, ScraperType, TaskPriority

        print(f"🔄 Running batch {operation_type} operation with intelligent coordination")
        print("=" * 70)

        # Map operation types to scraper types
        scraper_type_map = {
            'profiles': ScraperType.PROFILE,
            'posts': ScraperType.POSTS,
            'hashtags': ScraperType.HASHTAGS,
            'locations': ScraperType.LOCATIONS,
            'followers': ScraperType.FOLLOWERS
        }

        if operation_type not in scraper_type_map:
            print(f"❌ Unknown operation type: {operation_type}")
            return 1

        scraper_type = scraper_type_map[operation_type]

        # Get targets from database or use demo targets
        targets = _get_batch_targets(operation_type)

        if not targets:
            print(f"❌ No targets found for {operation_type} operation")
            return 1

        print(f"📋 Found {len(targets)} targets for processing")
        print(f"🤖 Starting coordinator...")

        # Start coordinator
        coordinator.start()

        # Add tasks to coordinator
        task_ids = []
        for target in targets:
            task_id = coordinator.add_task(
                scraper_type=scraper_type,
                target=target,
                priority=TaskPriority.NORMAL,
                max_items=args.max_items
            )
            task_ids.append(task_id)
            print(f"   ✅ Queued task for {target}: {task_id}")

        print(f"\n⏳ Processing {len(task_ids)} tasks...")
        print("   Use Ctrl+C to stop and view results")

        # Monitor progress
        completed_count = 0
        try:
            while completed_count < len(task_ids):
                time.sleep(5)

                # Check task statuses
                new_completed = 0
                for task_id in task_ids:
                    status = coordinator.get_task_status(task_id)
                    if status and status['status'] in ['completed', 'failed']:
                        new_completed += 1

                if new_completed > completed_count:
                    completed_count = new_completed
                    print(f"   📊 Progress: {completed_count}/{len(task_ids)} tasks completed")

                # Show coordinator stats
                stats = coordinator.get_statistics()
                print(f"   🔄 Active: {stats['active_tasks']}, Pending: {stats['pending_tasks']}")

        except KeyboardInterrupt:
            print("\n⏹️ Stopping batch operation...")

        # Stop coordinator
        coordinator.stop()

        # Generate summary report
        _generate_batch_report(task_ids, operation_type, args.output_format)

        return 0

    except Exception as e:
        logger.error(f"Error in batch operation {operation_type}: {e}")
        print(f"❌ Error: {e}")
        return 1

def _get_batch_targets(operation_type: str) -> List[str]:
    """Get targets for batch operation"""
    try:
        from core.data_manager import data_manager

        if operation_type == 'profiles':
            # Get surveillance targets from database
            targets = data_manager.get_all_surveillance_targets()
            return [target.instagram_username for target in targets[:10]]  # Limit for demo

        elif operation_type == 'hashtags':
            # Demo hashtags
            return ['photography', 'travel', 'food', 'fashion', 'technology']

        elif operation_type == 'locations':
            # Demo location IDs (major cities)
            return ['213385402', '212988663', '213570652']  # NYC, LA, London

        else:
            # For posts and followers, use surveillance targets
            targets = data_manager.get_all_surveillance_targets()
            return [target.instagram_username for target in targets[:5]]  # Limit for demo

    except Exception as e:
        logger.error(f"Error getting batch targets: {e}")
        return []

def _generate_batch_report(task_ids: List[str], operation_type: str, output_format: str):
    """Generate batch operation report"""
    try:
        from core.scraper_coordinator import coordinator

        print(f"\n📊 Generating {operation_type} batch report...")

        # Collect results
        results = []
        for task_id in task_ids:
            status = coordinator.get_task_status(task_id)
            if status:
                results.append(status)

        # Summary statistics
        completed = sum(1 for r in results if r['status'] == 'completed')
        failed = sum(1 for r in results if r['status'] == 'failed')

        print(f"📋 Batch Operation Summary:")
        print(f"   Total tasks: {len(task_ids)}")
        print(f"   Completed: {completed}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {(completed/len(task_ids)*100):.1f}%")

        # Coordinator statistics
        stats = coordinator.get_statistics()
        print(f"\n🤖 Coordinator Statistics:")
        print(f"   Conflicts avoided: {stats['conflicts_avoided']}")
        print(f"   Rate limits respected: {stats['rate_limits_respected']}")
        print(f"   Average execution time: {stats['average_execution_time']:.1f}s")

        # Save detailed report if requested
        if output_format == 'json':
            import json
            report_file = f"batch_{operation_type}_report.json"
            with open(report_file, 'w') as f:
                json.dump({
                    'operation_type': operation_type,
                    'summary': {
                        'total_tasks': len(task_ids),
                        'completed': completed,
                        'failed': failed,
                        'success_rate': completed/len(task_ids)*100
                    },
                    'coordinator_stats': stats,
                    'task_results': results
                }, f, indent=2, default=str)
            print(f"📄 Detailed report saved to: {report_file}")

    except Exception as e:
        logger.error(f"Error generating batch report: {e}")
        print(f"❌ Error generating report: {e}")

def start_coordinator_service():
    """Start the scraper coordinator as a background service"""
    try:
        from core.scraper_coordinator import coordinator

        print("🤖 Starting Scraper Coordinator Service")
        print("=" * 50)

        # Start coordinator
        coordinator.start()

        print("✅ Coordinator service started successfully")
        print("📋 Service Features:")
        print("   • Intelligent task scheduling")
        print("   • Conflict avoidance between scrapers")
        print("   • Rate limit management")
        print("   • Browser resource pooling")
        print("   • Automatic retry logic")

        print(f"\n🔄 Coordinator is running with:")
        print(f"   • Max concurrent tasks: {coordinator.max_concurrent_tasks}")
        print(f"   • Browser pool size: {coordinator.max_browser_instances}")

        print(f"\n💡 Use --coordinator-status to check status")
        print(f"💡 Use --batch-operation to submit batch jobs")
        print(f"💡 Press Ctrl+C to stop the service")

        # Keep service running
        try:
            while True:
                time.sleep(10)
                stats = coordinator.get_statistics()
                if stats['active_tasks'] > 0 or stats['pending_tasks'] > 0:
                    print(f"🔄 Active: {stats['active_tasks']}, Pending: {stats['pending_tasks']}")

        except KeyboardInterrupt:
            print("\n⏹️ Stopping coordinator service...")
            coordinator.stop()
            print("✅ Coordinator service stopped")

        return 0

    except Exception as e:
        logger.error(f"Error starting coordinator service: {e}")
        print(f"❌ Error: {e}")
        return 1

def show_coordinator_status():
    """Show coordinator status and statistics"""
    try:
        from core.scraper_coordinator import coordinator

        print("📊 Scraper Coordinator Status")
        print("=" * 40)

        # Get statistics
        stats = coordinator.get_statistics()

        print(f"🔄 Task Status:")
        print(f"   Active tasks: {stats['active_tasks']}")
        print(f"   Pending tasks: {stats['pending_tasks']}")
        print(f"   Completed tasks: {stats['completed_tasks']}")

        print(f"\n📈 Performance:")
        print(f"   Tasks completed: {stats['tasks_completed']}")
        print(f"   Tasks failed: {stats['tasks_failed']}")
        print(f"   Average execution time: {stats['average_execution_time']:.1f}s")

        print(f"\n🛡️ Protection:")
        print(f"   Conflicts avoided: {stats['conflicts_avoided']}")
        print(f"   Rate limits respected: {stats['rate_limits_respected']}")

        print(f"\n🖥️ Resources:")
        print(f"   Available browsers: {stats['available_browsers']}")
        print(f"   Browser pool size: {coordinator.max_browser_instances}")

        # Calculate success rate
        total_tasks = stats['tasks_completed'] + stats['tasks_failed']
        if total_tasks > 0:
            success_rate = (stats['tasks_completed'] / total_tasks) * 100
            print(f"\n✅ Success rate: {success_rate:.1f}%")

        # Show recent task history
        print(f"\n📋 Recent Tasks:")
        recent_tasks = coordinator.task_history[-5:] if coordinator.task_history else []
        for task in recent_tasks:
            status_emoji = "✅" if task.status.value == "completed" else "❌"
            print(f"   {status_emoji} {task.scraper_type.value}: {task.target} ({task.status.value})")

        if not recent_tasks:
            print("   No recent tasks")

        return 0

    except Exception as e:
        logger.error(f"Error showing coordinator status: {e}")
        print(f"❌ Error: {e}")
        return 1

def _output_results(result_type: str, data: dict, output_format: str):
    """Output results in specified format"""
    try:
        if output_format == "console":
            print(f"\n📊 {result_type.title()} Results:")
            print("-" * 30)
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    print(f"   {key}: {len(value) if isinstance(value, list) else 'object'}")
                else:
                    print(f"   {key}: {value}")

        elif output_format == "json":
            import json
            output_file = f"{result_type}_results.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"📄 Results saved to: {output_file}")

        elif output_format == "csv":
            print(f"📊 CSV output for {result_type} would be implemented here")

    except Exception as e:
        logger.error(f"Error outputting results: {e}")

def main():
    """Main entry point with command line argument support"""
    parser = argparse.ArgumentParser(
        description="Social Media Surveillance System - Phase 5 Complete",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py                              # Launch full UI dashboard
  python launcher.py --test-browser               # Test browser engine only
  python launcher.py --run-tests                  # Run comprehensive test suite
  python launcher.py --info                       # Show system information
  python launcher.py --scrape-profile username    # Scrape specific profile
  python launcher.py --scrape-posts username      # Scrape posts from profile
  python launcher.py --scrape-hashtag travel      # Analyze hashtag
  python launcher.py --scrape-location 123456     # Analyze location
  python launcher.py --track-followers username   # Track follower changes
  python launcher.py --batch-operation profiles   # Run batch profile scraping
  python launcher.py --headless                   # Run in automation mode
        """
    )

    parser.add_argument(
        "--test-browser",
        action="store_true",
        help="Test browser engine functionality only"
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run comprehensive test suite for all phases"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Show system information and status"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no UI)"
    )

    parser.add_argument(
        "--scrape-profile",
        type=str,
        help="Scrape a specific Instagram profile (username)"
    )

    parser.add_argument(
        "--scrape-posts",
        type=str,
        help="Scrape posts from a specific Instagram profile (username)"
    )

    parser.add_argument(
        "--scrape-hashtag",
        type=str,
        help="Analyze a specific hashtag (without # symbol)"
    )

    parser.add_argument(
        "--scrape-location",
        type=str,
        help="Analyze a specific location (location ID)"
    )

    parser.add_argument(
        "--track-followers",
        type=str,
        help="Track followers for a specific profile (username)"
    )

    parser.add_argument(
        "--batch-operation",
        type=str,
        choices=["profiles", "posts", "hashtags", "locations", "followers"],
        help="Run batch operation on multiple targets"
    )

    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="Maximum number of items to process (default: 50)"
    )

    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "csv", "console"],
        default="console",
        help="Output format for results (default: console)"
    )

    parser.add_argument(
        "--start-coordinator",
        action="store_true",
        help="Start the scraper coordinator as a background service"
    )

    parser.add_argument(
        "--coordinator-status",
        action="store_true",
        help="Show coordinator status and statistics"
    )

    args = parser.parse_args()

    # Print header
    print("🔍 Social Media Surveillance System")
    print("🤖 AI-Powered Instagram Monitoring - Phase 5 Complete")
    print("=" * 60)

    try:
        if args.info:
            show_system_info()
            return 0

        elif args.test_browser:
            print("🧪 Running Browser Engine Test...")
            success = test_browser_engine()
            return 0 if success else 1

        elif args.run_tests:
            print("🧪 Running Comprehensive Test Suite...")
            success = run_tests()
            return 0 if success else 1

        elif args.headless:
            print("🔄 Running in headless mode...")
            return run_headless_mode(args)

        elif args.scrape_profile:
            print("👤 Running Profile Scraping...")
            return run_profile_scraping(args.scrape_profile, args)

        elif args.scrape_posts:
            print("📝 Running Post Scraping...")
            return run_post_scraping(args.scrape_posts, args)

        elif args.scrape_hashtag:
            print("🏷️ Running Hashtag Analysis...")
            return run_hashtag_analysis(args.scrape_hashtag, args)

        elif args.scrape_location:
            print("📍 Running Location Analysis...")
            return run_location_analysis(args.scrape_location, args)

        elif args.track_followers:
            print("👥 Running Follower Tracking...")
            return run_follower_tracking(args.track_followers, args)

        elif args.batch_operation:
            print("🔄 Running Batch Operation...")
            return run_batch_operation(args.batch_operation, args)

        elif args.start_coordinator:
            print("🤖 Starting Scraper Coordinator Service...")
            return start_coordinator_service()

        elif args.coordinator_status:
            print("📊 Checking Coordinator Status...")
            return show_coordinator_status()

        else:
            # Default: Launch UI dashboard
            print("🚀 Launching UI Dashboard...")
            return launch_ui_dashboard()

    except KeyboardInterrupt:
        print("\n\n⏹️ Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
