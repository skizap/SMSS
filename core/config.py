"""
Social Media Surveillance System - Configuration Management
Handles all system configuration, settings, and environment variables.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class BrowserConfig:
    """Browser automation configuration"""
    headless: bool = False
    stealth_mode: bool = True
    user_data_dir: Optional[str] = None
    window_size: tuple = (1920, 1080)
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    timeout: int = 30
    page_load_timeout: int = 30
    implicit_wait: int = 10
    
@dataclass
class InstagramConfig:
    """Instagram-specific configuration"""
    login_url: str = "https://www.instagram.com/accounts/login/"
    base_url: str = "https://www.instagram.com/"
    max_followers_per_session: int = 1000
    scroll_pause_time: float = 2.0
    action_delay_range: tuple = (1, 3)
    max_retries: int = 3
    
@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "data/surveillance.db"
    backup_interval: int = 3600  # seconds
    max_connections: int = 10
    connection_timeout: int = 30
    
@dataclass
class DeepSeekConfig:
    """DeepSeek AI configuration"""
    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com/v1"
    model_chat: str = "deepseek-chat"
    model_coder: str = "deepseek-coder"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    
@dataclass
class EmailConfig:
    """Email notification configuration"""
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""  # Should be encrypted
    from_email: str = ""
    to_emails: List[str] = None
    subject_prefix: str = "[Instagram Scraper]"

    def __post_init__(self):
        if self.to_emails is None:
            self.to_emails = []

@dataclass
class WebhookConfig:
    """Webhook notification configuration"""
    enabled: bool = False
    urls: List[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    auth_type: str = "none"  # none, bearer, basic, custom
    auth_token: str = ""
    custom_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.urls is None:
            self.urls = []
        if self.custom_headers is None:
            self.custom_headers = {}

@dataclass
class AlertThresholds:
    """Alert threshold configuration"""
    # Rate limit thresholds
    rate_limit_warning_percent: float = 80.0  # Warn at 80% of rate limit
    rate_limit_critical_percent: float = 95.0  # Critical at 95% of rate limit

    # Data quality thresholds
    failed_requests_threshold: int = 5  # Alert after 5 consecutive failures
    data_quality_threshold: float = 0.8  # Alert if data quality drops below 80%

    # System health thresholds
    memory_usage_threshold: float = 85.0  # Alert at 85% memory usage
    disk_usage_threshold: float = 90.0  # Alert at 90% disk usage
    response_time_threshold: float = 10.0  # Alert if response time > 10 seconds

    # Account monitoring thresholds
    follower_change_threshold: int = 100  # Alert on follower changes > 100
    engagement_drop_threshold: float = 0.3  # Alert if engagement drops by 30%
    suspicious_activity_threshold: int = 3  # Alert after 3 suspicious activities

@dataclass
class EscalationPolicy:
    """Escalation policy configuration"""
    enabled: bool = False
    escalation_delay_minutes: int = 30  # Escalate after 30 minutes
    max_escalation_level: int = 3
    escalation_channels: List[str] = None  # email, webhook, sms

    def __post_init__(self):
        if self.escalation_channels is None:
            self.escalation_channels = ["email"]

@dataclass
class NotificationConfig:
    """Enhanced notification system configuration"""
    enabled: bool = True
    desktop_enabled: bool = True
    sound_enabled: bool = True
    min_priority: str = "medium"  # low, medium, high, critical

    # Enhanced notification channels
    email: EmailConfig = None
    webhook: WebhookConfig = None

    # Alert management
    alert_thresholds: AlertThresholds = None
    escalation_policy: EscalationPolicy = None

    # Do Not Disturb settings
    dnd_enabled: bool = False
    dnd_start_hour: int = 22
    dnd_end_hour: int = 8
    dnd_override_critical: bool = True  # Allow critical notifications during DND

    def __post_init__(self):
        if self.email is None:
            self.email = EmailConfig()
        if self.webhook is None:
            self.webhook = WebhookConfig()
        if self.alert_thresholds is None:
            self.alert_thresholds = AlertThresholds()
        if self.escalation_policy is None:
            self.escalation_policy = EscalationPolicy()
    
@dataclass
class SecurityConfig:
    """Security and stealth configuration"""
    session_rotation_interval: int = 3600  # seconds
    max_session_duration: int = 7200  # seconds
    anti_detection_enabled: bool = True
    behavior_randomization: bool = True
    proxy_rotation: bool = False

@dataclass
class AnalysisConfig:
    """AI Analysis system configuration"""
    # General analysis settings
    enabled: bool = True
    cache_ttl: int = 3600  # Cache time-to-live in seconds
    batch_size: int = 10  # Number of items to process in batch

    # Sentiment analysis settings
    sentiment_enabled: bool = True
    sentiment_confidence_threshold: float = 0.7

    # Topic analysis settings
    topic_analysis_enabled: bool = True
    max_topics_per_content: int = 5
    topic_confidence_threshold: float = 0.6

    # Bot detection settings
    bot_detection_enabled: bool = True
    bot_probability_threshold: float = 0.7
    bot_detection_factors: List[str] = None

    # Influence scoring settings
    influence_scoring_enabled: bool = True
    influence_score_weights: Dict[str, float] = None

    # Pattern detection settings
    pattern_detection_enabled: bool = True
    anomaly_detection_threshold: float = 2.0  # Z-score threshold
    pattern_analysis_window_days: int = 30

    # Content processing settings
    content_processing_enabled: bool = True
    media_analysis_enabled: bool = True
    text_analysis_enabled: bool = True

    def __post_init__(self):
        """Initialize default values for complex fields"""
        if self.bot_detection_factors is None:
            self.bot_detection_factors = [
                'username_pattern',
                'profile_completeness',
                'posting_frequency',
                'engagement_pattern',
                'follower_ratio'
            ]

        if self.influence_score_weights is None:
            self.influence_score_weights = {
                'follower_count': 0.3,
                'engagement_rate': 0.25,
                'content_quality': 0.2,
                'network_connections': 0.15,
                'verification_status': 0.1
            }
    
class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration file paths
        self.settings_file = self.config_dir / "settings.json"
        self.targets_file = self.config_dir / "targets.json"
        self.credentials_file = self.config_dir / "credentials.json"
        
        # Encryption key for sensitive data
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Load configurations
        self.browser = BrowserConfig()
        self.instagram = InstagramConfig()
        self.database = DatabaseConfig()
        self.deepseek = DeepSeekConfig()
        self.notification = NotificationConfig()
        self.security = SecurityConfig()
        self.analysis = AnalysisConfig()
        
        self._load_configurations()
        self._setup_logging()
        
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = self.config_dir / ".key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Restrict permissions
            return key
            
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'surveillance_system.log'),
                logging.StreamHandler()
            ]
        )
        
        # Set specific log levels for noisy libraries
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
    def _load_configurations(self):
        """Load all configuration files"""
        try:
            # Load general settings
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self._update_configs_from_dict(settings)
                    
            # Load DeepSeek API key from environment or config
            self.deepseek.api_key = os.getenv('DEEPSEEK_API_KEY') or self.deepseek.api_key
            
        except Exception as e:
            logging.error(f"Error loading configurations: {e}")
            
    def _update_configs_from_dict(self, settings: Dict[str, Any]):
        """Update configuration objects from dictionary"""
        for section, values in settings.items():
            if hasattr(self, section):
                config_obj = getattr(self, section)
                for key, value in values.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
                        
    def save_settings(self):
        """Save current settings to file"""
        try:
            settings = {
                'browser': asdict(self.browser),
                'instagram': asdict(self.instagram),
                'database': asdict(self.database),
                'deepseek': {k: v for k, v in asdict(self.deepseek).items() if k != 'api_key'},
                'notification': asdict(self.notification),
                'security': asdict(self.security),
                'analysis': asdict(self.analysis)
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            
    def load_targets(self) -> List[Dict[str, Any]]:
        """Load surveillance targets"""
        try:
            if self.targets_file.exists():
                with open(self.targets_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logging.error(f"Error loading targets: {e}")
            return []
            
    def save_targets(self, targets: List[Dict[str, Any]]):
        """Save surveillance targets"""
        try:
            with open(self.targets_file, 'w') as f:
                json.dump(targets, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving targets: {e}")
            
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
        
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
        
    def save_credentials(self, username: str, password: str):
        """Save encrypted Instagram credentials"""
        try:
            credentials = {
                'username': self.encrypt_data(username),
                'password': self.encrypt_data(password)
            }
            
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f)
                
        except Exception as e:
            logging.error(f"Error saving credentials: {e}")
            
    def load_credentials(self) -> Optional[tuple]:
        """Load and decrypt Instagram credentials"""
        try:
            if self.credentials_file.exists():
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    
                username = self.decrypt_data(credentials['username'])
                password = self.decrypt_data(credentials['password'])
                return username, password
                
        except Exception as e:
            logging.error(f"Error loading credentials: {e}")
            
        return None
        
    def get_data_dir(self) -> Path:
        """Get data directory path"""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        return data_dir
        
    def get_media_dir(self) -> Path:
        """Get media storage directory"""
        media_dir = self.get_data_dir() / "media"
        media_dir.mkdir(exist_ok=True)
        return media_dir
        
    def get_reports_dir(self) -> Path:
        """Get reports directory"""
        reports_dir = self.get_data_dir() / "reports"
        reports_dir.mkdir(exist_ok=True)
        return reports_dir

    def get_analysis_cache_dir(self) -> Path:
        """Get analysis cache directory"""
        cache_dir = self.get_data_dir() / "analysis_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def update_analysis_config(self, **kwargs):
        """Update analysis configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self.analysis, key):
                setattr(self.analysis, key, value)
                logging.info(f"Updated analysis config: {key} = {value}")
            else:
                logging.warning(f"Unknown analysis config parameter: {key}")

    def get_analysis_thresholds(self) -> Dict[str, float]:
        """Get analysis thresholds for easy access"""
        return {
            'sentiment_confidence': self.analysis.sentiment_confidence_threshold,
            'topic_confidence': self.analysis.topic_confidence_threshold,
            'bot_probability': self.analysis.bot_probability_threshold,
            'anomaly_detection': self.analysis.anomaly_detection_threshold
        }

    def is_analysis_enabled(self, analysis_type: str) -> bool:
        """Check if specific analysis type is enabled"""
        analysis_flags = {
            'sentiment': self.analysis.sentiment_enabled,
            'topic': self.analysis.topic_analysis_enabled,
            'bot_detection': self.analysis.bot_detection_enabled,
            'influence_scoring': self.analysis.influence_scoring_enabled,
            'pattern_detection': self.analysis.pattern_detection_enabled,
            'content_processing': self.analysis.content_processing_enabled,
            'media_analysis': self.analysis.media_analysis_enabled,
            'text_analysis': self.analysis.text_analysis_enabled
        }

        return analysis_flags.get(analysis_type, False) and self.analysis.enabled

    def update_notification_config(self, **kwargs):
        """Update notification configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self.notification, key):
                setattr(self.notification, key, value)
                logging.info(f"Updated notification config: {key} = {value}")
            else:
                logging.warning(f"Unknown notification config parameter: {key}")

    def get_notification_channels(self) -> List[str]:
        """Get list of enabled notification channels"""
        channels = []
        if self.notification.desktop_enabled:
            channels.append('desktop')
        if self.notification.email.enabled:
            channels.append('email')
        if self.notification.webhook.enabled:
            channels.append('webhook')
        return channels

    def is_notification_channel_enabled(self, channel: str) -> bool:
        """Check if specific notification channel is enabled"""
        if not self.notification.enabled:
            return False

        channel_flags = {
            'desktop': self.notification.desktop_enabled,
            'email': self.notification.email.enabled,
            'webhook': self.notification.webhook.enabled
        }

        return channel_flags.get(channel, False)

    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get alert thresholds for easy access"""
        return {
            'rate_limit_warning': self.notification.alert_thresholds.rate_limit_warning_percent,
            'rate_limit_critical': self.notification.alert_thresholds.rate_limit_critical_percent,
            'failed_requests': self.notification.alert_thresholds.failed_requests_threshold,
            'data_quality': self.notification.alert_thresholds.data_quality_threshold,
            'memory_usage': self.notification.alert_thresholds.memory_usage_threshold,
            'disk_usage': self.notification.alert_thresholds.disk_usage_threshold,
            'response_time': self.notification.alert_thresholds.response_time_threshold,
            'follower_change': self.notification.alert_thresholds.follower_change_threshold,
            'engagement_drop': self.notification.alert_thresholds.engagement_drop_threshold,
            'suspicious_activity': self.notification.alert_thresholds.suspicious_activity_threshold
        }

    def is_dnd_active(self) -> bool:
        """Check if Do Not Disturb is currently active"""
        if not self.notification.dnd_enabled:
            return False

        from datetime import datetime
        current_hour = datetime.now().hour
        start_hour = self.notification.dnd_start_hour
        end_hour = self.notification.dnd_end_hour

        if start_hour <= end_hour:
            # Same day range (e.g., 9 AM to 5 PM)
            return start_hour <= current_hour < end_hour
        else:
            # Overnight range (e.g., 10 PM to 8 AM)
            return current_hour >= start_hour or current_hour < end_hour

    def save_encrypted_email_credentials(self, username: str, password: str):
        """Save encrypted email credentials"""
        try:
            self.notification.email.username = username
            self.notification.email.password = self.encrypt_data(password)
            logging.info("Email credentials saved successfully")
        except Exception as e:
            logging.error(f"Error saving email credentials: {e}")

    def get_decrypted_email_credentials(self) -> Optional[tuple]:
        """Get decrypted email credentials"""
        try:
            if self.notification.email.username and self.notification.email.password:
                username = self.notification.email.username
                password = self.decrypt_data(self.notification.email.password)
                return username, password
        except Exception as e:
            logging.error(f"Error decrypting email credentials: {e}")
        return None

# Global configuration instance
config = ConfigManager()
