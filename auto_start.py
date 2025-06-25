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
    """Print colored status messages with fallback for encoding issues"""
    colors = {
        "info": "🔵",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "working": "🔄"
    }

    # Fallback colors for systems that don't support Unicode
    fallback_colors = {
        "info": "[INFO]",
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERROR]",
        "working": "[...]"
    }

    try:
        print(f"{colors.get(status, '🔵')} {message}")
    except UnicodeEncodeError:
        # Fallback to ASCII-safe symbols
        print(f"{fallback_colors.get(status, '[INFO]')} {message}")

def run_command(command, description="", silent=False):
    """Run a command and return success status"""
    if description and not silent:
        print_status(f"{description}...", "working")

    try:
        # Handle command as list or string
        if isinstance(command, list):
            result = subprocess.run(command, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True, shell=True)

        if result.returncode == 0:
            if description and not silent:
                print_status(f"{description} completed", "success")
            return True
        else:
            if not silent:
                print_status(f"{description} failed: {result.stderr.strip()}", "error")
            return False
    except Exception as e:
        if not silent:
            print_status(f"{description} error: {e}", "error")
        return False

def check_and_suggest_vcredist():
    """Check for Visual C++ Redistributable and suggest installation if needed"""
    print_status("Checking Visual C++ Redistributable", "working")

    # Try to detect if VC++ Redistributable is installed
    try:
        import winreg
        # Check for VC++ 2015-2022 Redistributable
        key_paths = [
            r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
            r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
        ]

        for key_path in key_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path):
                    print_status("Visual C++ Redistributable found", "success")
                    return True
            except FileNotFoundError:
                continue

        print_status("Visual C++ Redistributable not found", "warning")
        print("💡 PyQt6 DLL issues often require Visual C++ Redistributable")
        print("💡 Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        return False

    except ImportError:
        print_status("Cannot check VC++ Redistributable (winreg not available)", "warning")
        return False

def fix_pyqt6():
    """Automatically fix PyQt6 issues including DLL problems"""
    print_status("Fixing PyQt6 installation", "working")

    # First check for VC++ Redistributable
    check_and_suggest_vcredist()

    # Uninstall PyQt6 and related packages
    packages_to_remove = ["PyQt6", "PyQt6-Qt6", "PyQt6-sip"]
    for package in packages_to_remove:
        run_command([sys.executable, "-m", "pip", "uninstall", package, "-y"],
                   f"Uninstalling {package}", silent=True)

    # Try multiple PyQt6 installation strategies
    installation_strategies = [
        # Strategy 1: Standard PyQt6
        ([sys.executable, "-m", "pip", "install", "PyQt6"], "Installing PyQt6 (standard)"),

        # Strategy 2: PyQt6 with specific version that works better on Windows
        ([sys.executable, "-m", "pip", "install", "PyQt6==6.4.2"], "Installing PyQt6 v6.4.2"),

        # Strategy 3: Install with no-cache to avoid corrupted downloads
        ([sys.executable, "-m", "pip", "install", "--no-cache-dir", "PyQt6"], "Installing PyQt6 (no-cache)"),

        # Strategy 4: Try PyQt5 as fallback
        ([sys.executable, "-m", "pip", "install", "PyQt5"], "Installing PyQt5 fallback")
    ]

    for command, description in installation_strategies:
        if run_command(command, description):
            # Test the installation
            try:
                if "PyQt6" in description:
                    from PyQt6.QtCore import QCoreApplication
                    print_status("PyQt6 installation successful", "success")
                    return True
                else:  # PyQt5
                    from PyQt5.QtCore import QCoreApplication
                    print_status("PyQt5 fallback installation successful", "success")
                    return False  # Return False to indicate CLI mode should be used
            except ImportError as e:
                print_status(f"Import test failed: {e}", "warning")
                continue
            except Exception as e:
                if "DLL load failed" in str(e):
                    print_status("DLL load error detected - may need Visual C++ Redistributable", "warning")
                else:
                    print_status(f"Other error: {e}", "warning")
                continue

    print_status("All PyQt installation strategies failed", "error")
    print("💡 If you see DLL errors, install Visual C++ Redistributable:")
    print("💡 https://aka.ms/vs/17/release/vc_redist.x64.exe")
    return False

def fix_chromedriver():
    """Automatically fix ChromeDriver issues"""
    print_status("Updating ChromeDriver", "working")

    # Update undetected-chromedriver
    if run_command([sys.executable, "-m", "pip", "install", "--upgrade", "undetected-chromedriver"],
                   "Updating ChromeDriver"):
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
        run_command([sys.executable, "-m", "pip", "install", dep],
                   f"Installing {dep}", silent=True)

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
                                  capture_output=False, text=True, cwd=Path(__file__).parent)
            return result.returncode
        except Exception as e:
            print_status(f"UI launch failed: {e}", "error")
            return launch_smss(use_ui=False)
    else:
        print_status("Launching SMSS CLI interface", "working")
        try:
            # Launch CLI interface - show info and then provide menu
            result = subprocess.run([sys.executable, "launcher.py", "--info"],
                                  capture_output=False, text=True, cwd=Path(__file__).parent)

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
