#!/usr/bin/env python3
"""
SMSS Auto-Start Script
Automatically fixes common issues and launches the system without manual intervention.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": "🔵",
        "success": "✅", 
        "warning": "⚠️",
        "error": "❌",
        "working": "🔄"
    }
    print(f"{colors.get(status, '🔵')} {message}")

def run_command(command, description="", silent=False):
    """Run a command and return success status"""
    if description and not silent:
        print_status(f"{description}...", "working")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            if description and not silent:
                print_status(f"{description} completed", "success")
            return True
        else:
            if not silent:
                print_status(f"{description} failed: {result.stderr}", "error")
            return False
    except Exception as e:
        if not silent:
            print_status(f"{description} error: {e}", "error")
        return False

def fix_pyqt6():
    """Automatically fix PyQt6 issues"""
    print_status("Fixing PyQt6 installation", "working")
    
    # Uninstall PyQt6
    run_command(f"{sys.executable} -m pip uninstall PyQt6 -y", "Uninstalling PyQt6", silent=True)
    
    # Install PyQt6
    if run_command(f"{sys.executable} -m pip install PyQt6", "Installing PyQt6"):
        # Test PyQt6
        try:
            from PyQt6.QtCore import QCoreApplication
            print_status("PyQt6 installation successful", "success")
            return True
        except ImportError:
            print_status("PyQt6 still not working, trying PyQt5", "warning")
            if run_command(f"{sys.executable} -m pip install PyQt5", "Installing PyQt5 fallback"):
                return False  # Use CLI mode
    
    return False

def fix_chromedriver():
    """Automatically fix ChromeDriver issues"""
    print_status("Updating ChromeDriver", "working")
    
    # Update undetected-chromedriver
    if run_command(f"{sys.executable} -m pip install --upgrade undetected-chromedriver", "Updating ChromeDriver"):
        return True
    
    return False

def install_missing_dependencies():
    """Install any missing dependencies"""
    print_status("Checking and installing dependencies", "working")
    
    dependencies = [
        "selenium",
        "requests", 
        "beautifulsoup4",
        "pillow",
        "numpy",
        "pandas",
        "matplotlib",
        "python-dotenv"
    ]
    
    for dep in dependencies:
        run_command(f"{sys.executable} -m pip install {dep}", f"Installing {dep}", silent=True)
    
    print_status("Dependencies check completed", "success")

def auto_fix_system():
    """Automatically fix all common issues"""
    print_status("🚀 SMSS Auto-Fix Starting", "info")
    print("=" * 50)
    
    # Fix 1: Install/update dependencies
    install_missing_dependencies()
    
    # Fix 2: Fix ChromeDriver
    fix_chromedriver()
    
    # Fix 3: Fix PyQt6
    pyqt_fixed = fix_pyqt6()
    
    print("=" * 50)
    print_status("Auto-fix completed", "success")
    
    return pyqt_fixed

def launch_smss(use_ui=True):
    """Launch SMSS with appropriate interface"""
    if use_ui:
        print_status("Launching SMSS with UI", "working")
        try:
            # Try to launch with UI
            result = subprocess.run([sys.executable, "launcher.py"], 
                                  capture_output=False, text=True)
            return result.returncode
        except Exception as e:
            print_status(f"UI launch failed: {e}", "error")
            return launch_smss(use_ui=False)
    else:
        print_status("Launching SMSS CLI interface", "working")
        try:
            # Launch CLI interface
            result = subprocess.run([sys.executable, "launcher.py", "--info"], 
                                  capture_output=False, text=True)
            
            print("\n" + "=" * 60)
            print_status("SMSS is ready! Available commands:", "success")
            print("   python launcher.py --help                    # Show all options")
            print("   python launcher.py --info                    # System information")
            print("   python launcher.py --coordinator-status      # Check coordinator")
            print("   python launcher.py --scrape-profile USER     # Scrape profile")
            print("   python launcher.py --scrape-hashtag TAG      # Analyze hashtag")
            print("   python launcher.py --start-coordinator       # Start service")
            print("=" * 60)
            
            return 0
        except Exception as e:
            print_status(f"CLI launch failed: {e}", "error")
            return 1

def main():
    """Main auto-start function"""
    print("🔍 Social Media Surveillance System - Auto-Start")
    print("🤖 Lazy Mode: Automatic fixes and launch")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if launcher.py exists
    if not Path("launcher.py").exists():
        print_status("launcher.py not found in current directory", "error")
        print_status("Please run this script from the SMSS directory", "error")
        return 1
    
    # Auto-fix system
    ui_available = auto_fix_system()
    
    # Launch SMSS
    return launch_smss(use_ui=ui_available)

if __name__ == "__main__":
    try:
        exit_code = main()
        if exit_code == 0:
            print_status("SMSS started successfully! 🎉", "success")
        else:
            print_status("SMSS startup completed with issues", "warning")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_status("\nStartup interrupted by user", "warning")
        sys.exit(0)
    except Exception as e:
        print_status(f"Startup failed: {e}", "error")
        sys.exit(1)
