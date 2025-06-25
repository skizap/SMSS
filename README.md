# 🔍 Social Media Surveillance System (SMSS)

[![GitHub Repository](https://img.shields.io/badge/GitHub-SMSS-blue?logo=github)](https://github.com/skizap/SMSS)
[![Python](https://img.shields.io/badge/Python-3.8+-green?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-Educational-orange)](https://github.com/skizap/SMSS)
[![Phase](https://img.shields.io/badge/Phase-7%20Complete-success)](https://github.com/skizap/SMSS)
[![Stars](https://img.shields.io/github/stars/skizap/SMSS?style=social)](https://github.com/skizap/SMSS/stargazers)
[![Forks](https://img.shields.io/github/forks/skizap/SMSS?style=social)](https://github.com/skizap/SMSS/network/members)
[![Issues](https://img.shields.io/github/issues/skizap/SMSS)](https://github.com/skizap/SMSS/issues)
[![Last Commit](https://img.shields.io/github/last-commit/skizap/SMSS)](https://github.com/skizap/SMSS/commits/main)

An advanced AI-powered Instagram monitoring system using browser automation for comprehensive social media surveillance with intelligent coordination and production-ready error handling.

## 📑 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Key Features](#-key-features)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📝 Usage Examples](#-usage-examples)
- [📊 Development Phases](#-development-phases)
- [🎯 Phase 7 Integration Features](#-phase-7-integration-features)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [⚠️ Disclaimer](#️-disclaimer)

## 🎯 Overview

**Repository**: [https://github.com/skizap/SMSS](https://github.com/skizap/SMSS)

This system transforms traditional social media monitoring by using browser automation instead of API dependencies, enabling real-time surveillance through authentic browser sessions with advanced anti-detection measures, intelligent scraper coordination, and comprehensive error handling.

> **⚠️ Educational Purpose**: This project is designed for educational and research purposes. Users are responsible for complying with Instagram's Terms of Service and applicable laws.

## ✨ Key Features

- **🤖 Browser Automation**: Undetectable Chromium automation with stealth mode
- **📊 Real-time Monitoring**: Continuous Instagram account surveillance
- **🧠 AI Analysis**: DeepSeek AI integration for content analysis
- **🖥️ Modern Dashboard**: PyQt6 real-time interface
- **🔔 Smart Notifications**: Intelligent alert system
- **🛡️ Stealth Operation**: Advanced anti-detection measures
- **🏷️ Hashtag Analysis**: Comprehensive hashtag trending and analysis
- **📍 Location Scraping**: Geographic analysis and location-based monitoring
- **🤝 Intelligent Coordination**: Smart scheduling to avoid conflicts and rate limits
- **🔄 Production Error Handling**: Robust retry logic and graceful degradation
- **⚡ Batch Operations**: Efficient processing of multiple targets

## 🏗️ Architecture

### Repository Structure

### Core Components:
1. **Browser Engine** - Chromium automation with stealth capabilities
2. **Data Collection Engine** - Instagram scraping and monitoring
3. **Analysis Engine** - DeepSeek AI-powered content analysis
4. **Storage Engine** - SQLite database with efficient indexing
5. **Dashboard Engine** - PyQt6 real-time interface
6. **Notification Engine** - Real-time alerts and reporting
7. **Coordination Engine** - Intelligent task scheduling and resource management
8. **Error Handling Engine** - Production-ready resilience and recovery

## 📦 Installation

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser
- 4GB+ RAM recommended

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd social_media_surveillance

# Install dependencies
pip install -r requirements.txt

# Run initial test
python launcher.py
```

## 🚀 Quick Start

### Installation

#### System Requirements
- Python 3.8 or higher
- Chrome/Chromium browser
- 4GB+ RAM recommended
- Windows, macOS, or Linux

#### Installation Steps
```bash
# Clone the repository
git clone https://github.com/skizap/SMSS.git
cd SMSS

# Install dependencies
pip install -r requirements.txt

# Configure the system
python launcher.py --info

# Test the installation
python launcher.py --test-browser
```

#### Dependencies
The system requires the following Python packages:
- `selenium` - Browser automation
- `PyQt6` - GUI framework
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `sqlite3` - Database (built-in)
- `python-dotenv` - Environment configuration

### Launch Full Dashboard
```bash
# Launch complete UI dashboard
python launcher.py
```

### Command Line Operations
```bash
# Test browser engine
python launcher.py --test-browser

# Show system information
python launcher.py --info

# Run comprehensive tests
python launcher.py --run-tests

# Scrape specific profile
python launcher.py --scrape-profile username

# Analyze hashtag
python launcher.py --scrape-hashtag travel

# Analyze location
python launcher.py --scrape-location 213385402

# Track followers
python launcher.py --track-followers username

# Run batch operations
python launcher.py --batch-operation profiles

# Start coordinator service
python launcher.py --start-coordinator

# Check coordinator status
python launcher.py --coordinator-status
```

## 📁 Project Structure

```
social_media_surveillance/
├── core/                   # Core system components
│   ├── browser_engine.py   # Browser automation
│   ├── config.py          # Configuration management
│   ├── data_manager.py     # Database operations
│   ├── error_handler.py    # Production error handling
│   ├── scraper_resilience.py # Resilience patterns
│   └── scraper_coordinator.py # Intelligent coordination
├── models/                 # Data models
│   ├── instagram_models.py # Instagram data structures
│   └── analytics_models.py # Analytics models
├── scrapers/              # Instagram scrapers
│   ├── instagram_profile_scraper.py # Profile scraping
│   ├── instagram_post_scraper.py    # Post scraping
│   ├── instagram_story_scraper.py   # Story scraping
│   ├── instagram_hashtag_scraper.py # Hashtag analysis
│   ├── instagram_location_scraper.py # Location analysis
│   └── follower_tracker.py         # Follower tracking
├── analysis/              # AI analysis engine
├── ui/                    # PyQt6 dashboard
├── notifications/         # Alert system
├── reporting/             # Report generation
├── security/              # Stealth & security
├── data/                  # Database & media storage
├── config/                # Configuration files
├── docs/                  # Documentation
└── launcher.py            # Main entry point
```

## 🔧 Configuration

### Basic Configuration
Edit `config/settings.json`:
```json
{
  "browser": {
    "headless": false,
    "stealth_mode": true,
    "window_size": [1920, 1080]
  },
  "instagram": {
    "max_followers_per_session": 1000,
    "scroll_pause_time": 2.0
  }
}
```

### Credentials
Use the built-in encryption for storing Instagram credentials:
```python
from core.config import config
config.save_credentials("username", "password")
```

## 🛡️ Security Features

- **Anti-Detection**: Advanced browser fingerprint randomization
- **Session Management**: Automatic session rotation and persistence
- **Behavioral Mimicry**: Human-like interaction patterns
- **Encrypted Storage**: Secure credential and session storage

## 📊 Development Phases

- [x] **Phase 1**: Foundation & Browser Engine ✅
- [x] **Phase 2**: Database & Data Models ✅
- [x] **Phase 3**: Instagram Scraper Engine ✅
- [x] **Phase 4**: DeepSeek AI Analysis Engine ✅
- [x] **Phase 5**: PyQt6 Dashboard Interface ✅
- [x] **Phase 7**: Complete Integration & Production Features ✅

## 🔍 Current Status: Phase 7 Complete - Production Ready

### ✅ Phase 7 Completed Features:

#### 🆕 New Scraper Components:
- **Hashtag Scraper**: Comprehensive hashtag analysis with trending detection
- **Location Scraper**: Geographic analysis and location-based post collection
- **Enhanced Post Scraper**: Improved with hashtag and location extraction

#### 🤖 Intelligent Coordination System:
- **Task Scheduling**: Smart scheduling to avoid conflicts between scrapers
- **Resource Management**: Browser pool management for concurrent operations
- **Rate Limiting**: Intelligent rate limiting to respect Instagram limits
- **Conflict Avoidance**: Prevents conflicting operations that could trigger detection

#### 🛡️ Production Error Handling:
- **Retry Logic**: Exponential backoff retry mechanisms
- **Circuit Breaker**: Prevents cascading failures
- **Graceful Degradation**: Fallback strategies when primary methods fail
- **Comprehensive Logging**: Detailed error tracking and statistics

#### ⚡ Enhanced Launcher Integration:
- **Command Line Interface**: Complete CLI for all scraper operations
- **Batch Operations**: Efficient processing of multiple targets
- **Coordinator Service**: Background service for continuous operation
- **Output Formats**: JSON, CSV, and console output options

#### 🔧 Production Features:
- **Browser Recovery**: Automatic browser session recovery
- **Data Validation**: Robust data validation and sanitization
- **Performance Monitoring**: Comprehensive statistics and monitoring
- **Context Management**: Proper resource cleanup and management

## 📝 Usage Examples

### Profile Scraping
```python
from scrapers.instagram_profile_scraper import scrape_single_profile

# Scrape a profile
profile_data = scrape_single_profile("username")
print(f"Followers: {profile_data['follower_count']}")
```

### Hashtag Analysis
```python
from scrapers.instagram_hashtag_scraper import analyze_hashtag_quick

# Analyze hashtag trends
hashtag_data = analyze_hashtag_quick("travel", max_posts=50)
print(f"Trending score: {hashtag_data['trending_score']}")
```

### Location Analysis
```python
from scrapers.instagram_location_scraper import analyze_location_quick

# Analyze location activity
location_data = analyze_location_quick("213385402", max_posts=30)
print(f"Location: {location_data['location_name']}")
```

### Batch Operations with Coordinator
```python
from core.scraper_coordinator import coordinator, ScraperType, TaskPriority

# Start coordinator
coordinator.start()

# Add tasks
task_id = coordinator.add_task(
    scraper_type=ScraperType.PROFILE,
    target="username",
    priority=TaskPriority.HIGH,
    max_items=100
)

# Monitor progress
status = coordinator.get_task_status(task_id)
print(f"Task status: {status['status']}")
```

### Error Handling
```python
from core.error_handler import error_handler
from core.scraper_resilience import ScraperResilience

@error_handler.with_retry(max_retries=3)
@ScraperResilience.with_rate_limit_handling()
def robust_scraping_function():
    # Your scraping logic with automatic retry and rate limiting
    pass
```

## 🤝 Contributing

This project follows a structured 10-phase development plan. Each phase must be completed before proceeding to the next.

## 📄 License

This project is for educational and research purposes only. Please ensure compliance with Instagram's Terms of Service and applicable laws.

## ⚠️ Disclaimer

This tool is designed for legitimate surveillance and monitoring purposes. Users are responsible for ensuring compliance with all applicable laws and platform terms of service.

## 🎯 Phase 7 Integration Features

### Intelligent Scraper Coordination
The system now includes a sophisticated coordinator that:
- **Prevents Conflicts**: Automatically schedules tasks to avoid conflicting operations
- **Manages Resources**: Efficiently pools browser instances for concurrent operations
- **Respects Rate Limits**: Intelligent delays to prevent Instagram rate limiting
- **Handles Failures**: Automatic retry with exponential backoff

### Production Error Handling
Comprehensive error handling system featuring:
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Graceful Degradation**: Fallback strategies for robust operation
- **Comprehensive Logging**: Detailed error tracking and statistics
- **Browser Recovery**: Automatic session recovery on failures

### Enhanced Scraper Capabilities
- **Hashtag Scraper**: Analyze hashtag trends, related hashtags, and post metrics
- **Location Scraper**: Geographic analysis with nearby location discovery
- **Improved Scrapers**: All existing scrapers enhanced with error handling

### Command Line Interface
Complete CLI for automation and batch operations:
```bash
# Individual operations
python launcher.py --scrape-profile username
python launcher.py --scrape-hashtag travel
python launcher.py --scrape-location 213385402

# Batch operations
python launcher.py --batch-operation profiles
python launcher.py --batch-operation hashtags

# Coordinator management
python launcher.py --start-coordinator
python launcher.py --coordinator-status
```

## 📚 Documentation

- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Solutions for common issues and setup problems
- **[Production Error Handling Guide](docs/production_error_handling.md)** - Comprehensive error handling documentation
- **[API Documentation](docs/)** - Detailed API documentation for all components
- **[Configuration Guide](config/)** - System configuration and setup instructions

## 🤝 Contributing

We welcome contributions to the SMSS project! Here's how to get started:

### Getting Started
1. **Star** the repository: [https://github.com/skizap/SMSS](https://github.com/skizap/SMSS) ⭐
2. **Fork** the repository to your GitHub account
3. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/SMSS.git
   cd SMSS
   ```

### Development Workflow
1. Create a feature branch: `git checkout -b feature/new-feature`
2. Make your changes and test thoroughly
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to your branch: `git push origin feature/new-feature`
5. Submit a pull request to the main repository

### Contribution Guidelines
- Follow the existing code style and patterns
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Include clear commit messages and PR descriptions

### Areas for Contribution
- 🐛 Bug fixes and improvements
- 📚 Documentation enhancements
- 🧪 Additional test coverage
- ⚡ Performance optimizations
- 🆕 New scraper features
- 🛡️ Security improvements

## 📄 License

This project is licensed for educational and research purposes. See the repository for full license details.

## 🆘 Support & Issues

### Getting Help
- 📖 **Documentation**: Check the [docs/](docs/) directory for detailed guides
- 🐛 **Bug Reports**: [Create an issue](https://github.com/skizap/SMSS/issues/new) on GitHub
- 💡 **Feature Requests**: [Submit a feature request](https://github.com/skizap/SMSS/issues/new)
- 💬 **Discussions**: Use [GitHub Discussions](https://github.com/skizap/SMSS/discussions) for questions

### Common Issues
- **Browser not found**: Ensure Chrome/Chromium is installed
- **Permission errors**: Run with appropriate permissions
- **Rate limiting**: Use the coordinator system to manage requests
- **Authentication issues**: Check Instagram login credentials

### Reporting Issues
When reporting issues, please include:
- Operating system and Python version
- Full error message and stack trace
- Steps to reproduce the issue
- Expected vs actual behavior

## ⚠️ Disclaimer

This software is provided for educational and research purposes only. Users are solely responsible for:
- Complying with Instagram's Terms of Service
- Respecting privacy and data protection laws
- Using the software ethically and legally
- Any consequences arising from the use of this software

The developers assume no responsibility for misuse of this software.

## 🔗 Repository

**GitHub**: [https://github.com/skizap/SMSS](https://github.com/skizap/SMSS)

---

**Status**: Phase 7 Complete - Production-Ready Instagram Surveillance System ✅
**Repository**: [https://github.com/skizap/SMSS](https://github.com/skizap/SMSS)
**Features**: Complete integration with intelligent coordination and production error handling
