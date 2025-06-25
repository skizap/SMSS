"""
Social Media Surveillance System - Credentials Manager
Secure storage and retrieval of sensitive credentials with encryption.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64
import os

logger = logging.getLogger(__name__)

class CredentialsManager:
    """Manages encrypted storage of sensitive credentials"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = self.config_dir / "credentials.json"
        self.key_file = self.config_dir / ".encryption_key"
        
        # Initialize encryption
        self.cipher = self._get_or_create_cipher()
        
        # Load credentials
        self._credentials = self._load_credentials()
    
    def _get_or_create_cipher(self) -> Fernet:
        """Get or create encryption cipher"""
        try:
            if self.key_file.exists():
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Set file permissions to be readable only by owner
                os.chmod(self.key_file, 0o600)
                
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"Error setting up encryption: {e}")
            raise
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load and decrypt credentials from file"""
        try:
            if not self.credentials_file.exists():
                logger.info("No credentials file found, starting with empty credentials")
                return {}
            
            with open(self.credentials_file, 'r') as f:
                encrypted_data = f.read()
            
            if not encrypted_data.strip():
                return {}
            
            # Decrypt the data
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return {}
    
    def _save_credentials(self) -> bool:
        """Encrypt and save credentials to file"""
        try:
            # Encrypt the data
            json_data = json.dumps(self._credentials, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            # Save to file
            with open(self.credentials_file, 'w') as f:
                f.write(encrypted_data.decode())
            
            # Set file permissions
            os.chmod(self.credentials_file, 0o600)
            
            logger.info("Credentials saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            return False
    
    def get_instagram_credentials(self) -> Optional[Dict[str, str]]:
        """Get Instagram username and password"""
        instagram_creds = self._credentials.get('instagram', {})
        
        username = instagram_creds.get('username')
        password = instagram_creds.get('password')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        
        return None
    
    def set_instagram_credentials(self, username: str, password: str) -> bool:
        """Set Instagram credentials"""
        try:
            if 'instagram' not in self._credentials:
                self._credentials['instagram'] = {}
            
            self._credentials['instagram']['username'] = username
            self._credentials['instagram']['password'] = password
            
            return self._save_credentials()
            
        except Exception as e:
            logger.error(f"Error setting Instagram credentials: {e}")
            return False
    
    def get_deepseek_api_key(self) -> Optional[str]:
        """Get DeepSeek API key"""
        return self._credentials.get('deepseek', {}).get('api_key')
    
    def set_deepseek_api_key(self, api_key: str) -> bool:
        """Set DeepSeek API key"""
        try:
            if 'deepseek' not in self._credentials:
                self._credentials['deepseek'] = {}
            
            self._credentials['deepseek']['api_key'] = api_key
            
            return self._save_credentials()
            
        except Exception as e:
            logger.error(f"Error setting DeepSeek API key: {e}")
            return False
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration"""
        return self._credentials.get('notification', {})
    
    def set_notification_config(self, config: Dict[str, Any]) -> bool:
        """Set notification configuration"""
        try:
            self._credentials['notification'] = config
            return self._save_credentials()
            
        except Exception as e:
            logger.error(f"Error setting notification config: {e}")
            return False
    
    def has_instagram_credentials(self) -> bool:
        """Check if Instagram credentials are configured"""
        creds = self.get_instagram_credentials()
        return creds is not None
    
    def has_deepseek_api_key(self) -> bool:
        """Check if DeepSeek API key is configured"""
        return self.get_deepseek_api_key() is not None
    
    def clear_credentials(self) -> bool:
        """Clear all stored credentials"""
        try:
            self._credentials = {}
            return self._save_credentials()
            
        except Exception as e:
            logger.error(f"Error clearing credentials: {e}")
            return False
    
    def get_credential_status(self) -> Dict[str, bool]:
        """Get status of all credential types"""
        return {
            'instagram': self.has_instagram_credentials(),
            'deepseek': self.has_deepseek_api_key(),
            'notification': bool(self.get_notification_config())
        }

# Global credentials manager instance
credentials_manager = CredentialsManager()

def get_credentials_manager() -> CredentialsManager:
    """Get global credentials manager instance"""
    return credentials_manager
