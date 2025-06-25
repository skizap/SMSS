# 🔧 SMSS Troubleshooting Guide

This guide helps resolve common issues with the Social Media Surveillance System.

## 🚨 Common Issues

### 1. PyQt6 DLL Load Failed Error

**Error**: `DLL load failed while importing QtCore: The specified procedure could not be found.`

**Solutions**:

#### Option A: Reinstall PyQt6
```bash
pip uninstall PyQt6
pip install PyQt6
```

#### Option B: Install Visual C++ Redistributable (Windows)
1. Download Microsoft Visual C++ Redistributable from Microsoft's website
2. Install the latest x64 version
3. Restart your computer
4. Try running the application again

#### Option C: Use PyQt5 Alternative
```bash
pip uninstall PyQt6
pip install PyQt5
```

#### Option D: Use Conda (if using Anaconda/Miniconda)
```bash
conda install pyqt
```

### 2. Chrome Version Mismatch

**Error**: `This version of ChromeDriver only supports Chrome version X Current browser version is Y`

**Solutions**:

#### Option A: Update Chrome Browser
1. Open Chrome browser
2. Go to Settings > About Chrome
3. Let Chrome update automatically
4. Restart Chrome

#### Option B: Use Auto-updating ChromeDriver
The system uses `undetected-chromedriver` which should auto-update, but you can force it:
```bash
pip uninstall undetected-chromedriver
pip install undetected-chromedriver
```

#### Option C: Manual ChromeDriver Management
```bash
# Clear ChromeDriver cache
rm -rf ~/.cache/selenium/  # Linux/Mac
# Or delete C:\Users\USERNAME\.cache\selenium\ on Windows
```

### 3. Browser Engine Issues

**Error**: Various browser-related errors

**Solutions**:

#### Check Browser Installation
```bash
# Test if Chrome is accessible
python launcher.py --test-browser
```

#### Use Alternative Browser
Edit `core/config.py` to use a different browser:
```python
BROWSER_TYPE = "firefox"  # Instead of "chrome"
```

#### Headless Mode
If GUI issues persist, use headless mode:
```bash
python launcher.py --headless
```

### 4. Permission Issues

**Error**: Permission denied errors

**Solutions**:

#### Windows
- Run Command Prompt as Administrator
- Or adjust folder permissions for the SMSS directory

#### Linux/Mac
```bash
chmod +x launcher.py
sudo python launcher.py  # If needed
```

### 5. Import Errors

**Error**: `ModuleNotFoundError` for various packages

**Solutions**:

#### Install Missing Dependencies
```bash
pip install -r requirements.txt
```

#### Check Python Version
```bash
python --version  # Should be 3.8+
```

#### Virtual Environment (Recommended)
```bash
python -m venv smss_env
source smss_env/bin/activate  # Linux/Mac
# Or: smss_env\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 🛠️ System Requirements Check

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Browser**: Chrome 120+ or Firefox 100+
- **OS**: Windows 10+, macOS 10.14+, or Linux

### Check Your System
```bash
python launcher.py --info
```

## 🔍 Diagnostic Commands

### Test Individual Components
```bash
# Test browser engine
python launcher.py --test-browser

# Test database
python launcher.py --info

# Test coordinator
python launcher.py --coordinator-status

# Test scrapers (requires login)
python launcher.py --scrape-profile instagram
```

### Debug Mode
Enable detailed logging:
```bash
export SMSS_DEBUG=1  # Linux/Mac
set SMSS_DEBUG=1     # Windows
python launcher.py
```

## 🚀 Alternative Usage Methods

### 1. Command Line Interface
If UI doesn't work, use CLI:
```bash
python launcher.py --help
```

### 2. Coordinator Service
Run as background service:
```bash
python launcher.py --start-coordinator
```

### 3. Batch Operations
Process multiple targets:
```bash
python launcher.py --batch-operation profiles
```

### 4. Individual Operations
Direct scraper access:
```bash
python launcher.py --scrape-profile username
python launcher.py --scrape-hashtag travel
python launcher.py --scrape-location 213385402
```

## 📞 Getting Help

### Before Reporting Issues
1. Check this troubleshooting guide
2. Run `python launcher.py --info` and include output
3. Try the suggested solutions
4. Check if the issue persists in headless mode

### Reporting Issues
When reporting issues on GitHub, include:

1. **System Information**:
   ```bash
   python launcher.py --info
   ```

2. **Full Error Message**: Copy the complete error output

3. **Steps to Reproduce**: Exact commands that cause the issue

4. **Environment Details**:
   - Operating System and version
   - Python version
   - Browser version
   - Virtual environment (if used)

### GitHub Repository
- **Issues**: [https://github.com/skizap/SMSS/issues](https://github.com/skizap/SMSS/issues)
- **Discussions**: [https://github.com/skizap/SMSS/discussions](https://github.com/skizap/SMSS/discussions)

## 🔄 Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| PyQt6 DLL Error | `pip uninstall PyQt6 && pip install PyQt6` |
| Chrome Version | Update Chrome browser |
| Permission Error | Run as administrator (Windows) |
| Missing Modules | `pip install -r requirements.txt` |
| UI Not Working | Use `python launcher.py --help` for CLI |
| Browser Issues | `python launcher.py --test-browser` |

## ✅ Verification Steps

After applying fixes:

1. **Test System Info**:
   ```bash
   python launcher.py --info
   ```

2. **Test Browser**:
   ```bash
   python launcher.py --test-browser
   ```

3. **Test UI** (if PyQt6 fixed):
   ```bash
   python launcher.py
   ```

4. **Test CLI**:
   ```bash
   python launcher.py --help
   ```

If all tests pass, your SMSS installation is working correctly! 🎉
