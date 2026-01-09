#!/usr/bin/env python3
"""
Configuration Manager for PAN-OS PKI Manager
Baker Street Labs - Firewall Certificate Management

Handles loading and validation of configuration from YAML files and environment variables.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """Manages configuration for PAN-OS PKI Manager."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._load_secrets_from_env()
        self._validate_config()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            # Try .example file
            example_path = Path(f"{self.config_file}.example")
            if example_path.exists():
                logger.warning(
                    f"Config file {self.config_file} not found. "
                    f"Copy {example_path} to {config_path} and customize."
                )
                raise ConfigurationError(
                    f"Configuration file {self.config_file} not found. "
                    f"Please copy config.yaml.example to config.yaml and customize."
                )
            else:
                raise ConfigurationError(f"Configuration file {self.config_file} not found.")
        
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML config: {e}")
    
    def _load_secrets_from_env(self) -> None:
        """Load sensitive credentials from environment variables."""
        # WinRM credentials
        winrm_user = os.getenv('WINRM_USER')
        winrm_pass = os.getenv('WINRM_PASS')
        
        if winrm_user and winrm_pass:
            self.config.setdefault('certificate_authority', {}).setdefault('winrm', {})
            self.config['certificate_authority']['winrm']['username'] = winrm_user
            self.config['certificate_authority']['winrm']['password'] = winrm_pass
            logger.debug("Loaded WinRM credentials from environment variables")
        
        # PAN-OS credentials
        for firewall in self.config.get('firewalls', []):
            fw_name = firewall.get('name', '').upper()
            
            # Try API key first
            api_key_var = f'PAN_{fw_name}_API_KEY'
            api_key = os.getenv(api_key_var)
            
            if api_key:
                firewall['api_key'] = api_key
                logger.debug(f"Loaded API key for {firewall['name']} from {api_key_var}")
            else:
                # Fall back to username/password
                user_var = f'PAN_{fw_name}_USERNAME'
                pass_var = f'PAN_{fw_name}_PASSWORD'
                
                username = os.getenv(user_var, 'admin')
                password = os.getenv(pass_var)
                
                if password:
                    firewall['username'] = username
                    firewall['password'] = password
                    logger.debug(f"Loaded username/password for {firewall['name']}")
    
    def _validate_config(self) -> None:
        """Validate configuration structure and required fields."""
        required_sections = ['certificate_authority', 'firewalls']
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required configuration section: {section}")
        
        # Validate CA configuration
        ca_config = self.config['certificate_authority']
        required_ca_fields = ['fqdn', 'ca_name']
        
        for field in required_ca_fields:
            if field not in ca_config:
                raise ConfigurationError(f"Missing required CA field: {field}")
        
        # Validate WinRM credentials
        winrm_config = ca_config.get('winrm', {})
        if not winrm_config.get('username') or not winrm_config.get('password'):
            logger.warning(
                "WinRM credentials not configured. "
                "Set WINRM_USER and WINRM_PASS environment variables."
            )
        
        # Validate firewall configuration
        if not self.config.get('firewalls'):
            raise ConfigurationError("No firewalls configured")
        
        for firewall in self.config['firewalls']:
            if 'name' not in firewall:
                raise ConfigurationError("Firewall missing 'name' field")
            if 'ip_address' not in firewall:
                raise ConfigurationError(f"Firewall {firewall['name']} missing 'ip_address'")
            
            # Check credentials
            has_api_key = 'api_key' in firewall
            has_password = 'password' in firewall
            
            if not has_api_key and not has_password:
                logger.warning(
                    f"No credentials configured for firewall {firewall['name']}. "
                    f"Set PAN_{firewall['name'].upper()}_API_KEY or "
                    f"PAN_{firewall['name'].upper()}_PASSWORD environment variable."
                )
    
    def get_ca_config(self) -> Dict[str, Any]:
        """Get Certificate Authority configuration."""
        return self.config.get('certificate_authority', {})
    
    def get_intermediate_ca_config(self) -> Dict[str, Any]:
        """Get Intermediate CA configuration."""
        return self.config.get('intermediate_ca', {})
    
    def get_firewalls(self) -> list:
        """Get list of firewall configurations."""
        return self.config.get('firewalls', [])
    
    def get_firewall(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific firewall by name.
        
        Args:
            name: Firewall name (e.g., 'hub', 'spoke')
            
        Returns:
            Firewall configuration dict or None if not found
        """
        for fw in self.get_firewalls():
            if fw.get('name') == name:
                return fw
        return None
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.get('logging', {
            'level': 'INFO',
            'file': 'panos_pki_manager.log',
            'console': True
        })
    
    def get_settings(self) -> Dict[str, Any]:
        """Get operational settings."""
        return self.config.get('settings', {
            'dry_run': False,
            'check_existing': True,
            'backup_before_import': True,
            'commit_after_import': True,
            'verify_chain': True
        })
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output directory configuration."""
        return self.config.get('output', {
            'cert_directory': './certificates',
            'csr_directory': './csrs',
            'backup_directory': './backups',
            'create_directories': True
        })
    
    def is_dry_run(self) -> bool:
        """Check if running in dry-run mode."""
        return self.get_settings().get('dry_run', False)


# Module-level convenience function
def load_config(config_file: str = "config.yaml") -> ConfigManager:
    """
    Load configuration from file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        ConfigManager instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    return ConfigManager(config_file)

