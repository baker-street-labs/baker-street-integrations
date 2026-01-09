#!/usr/bin/env python3
"""
Unit Tests for PAN-OS PKI Manager
Baker Street Labs - Test Suite

Tests for configuration, CSR generation, signing, and firewall operations.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import modules to test
from config_manager import ConfigManager, ConfigurationError
from pki_intermediate import PKIIntermediateCA
from csr_signing import CSRSigner
from firewall_api import FirewallAPI
import utils


class TestConfigManager:
    """Test configuration management."""
    
    def test_config_loading(self, tmp_path):
        """Test loading configuration from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_content = """
certificate_authority:
  fqdn: "bakerstreeta.ad.bakerstreetlabs.io"
  ca_name: "Baker Street Labs Root CA"
  domain: "ad.bakerstreetlabs.io"
  
firewalls:
  - name: "test"
    ip_address: "192.168.0.1"
"""
        config_file.write_text(config_content)
        
        config = ConfigManager(str(config_file))
        
        assert config.get_ca_config()['fqdn'] == "bakerstreeta.ad.bakerstreetlabs.io"
        assert len(config.get_firewalls()) == 1
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(ConfigurationError):
            ConfigManager("nonexistent.yaml")
    
    def test_environment_variables(self, tmp_path, monkeypatch):
        """Test loading credentials from environment variables."""
        config_file = tmp_path / "test_config.yaml"
        config_content = """
certificate_authority:
  fqdn: "test.local"
  ca_name: "Test CA"
firewalls:
  - name: "hub"
    ip_address: "192.168.0.7"
"""
        config_file.write_text(config_content)
        
        monkeypatch.setenv('WINRM_USER', 'testuser')
        monkeypatch.setenv('WINRM_PASS', 'testpass')
        monkeypatch.setenv('PAN_HUB_API_KEY', 'testapikey')
        
        config = ConfigManager(str(config_file))
        
        assert config.get_ca_config()['winrm']['username'] == 'testuser'
        assert config.get_firewall('hub')['api_key'] == 'testapikey'


class TestPKIIntermediate:
    """Test PKI intermediate CA operations."""
    
    @patch('pki_intermediate.winrm.Session')
    def test_check_template_exists(self, mock_session):
        """Test checking if template exists."""
        ca_config = {
            'fqdn': 'test.local',
            'ca_name': 'Test CA',
            'winrm': {'username': 'user', 'password': 'pass'}
        }
        intermediate_config = {'template_name': 'TestTemplate'}
        
        pki = PKIIntermediateCA(ca_config, intermediate_config)
        
        # Mock WinRM response
        mock_result = Mock()
        mock_result.std_out = b"EXISTS"
        mock_result.status_code = 0
        mock_session.return_value.run_ps.return_value = mock_result
        
        exists = pki.check_template_exists('TestTemplate')
        assert exists is True
    
    def test_generate_intermediate_csr(self):
        """Test CSR generation for intermediate CA."""
        ca_config = {
            'fqdn': 'test.local',
            'ca_name': 'Test CA',
            'winrm': {}
        }
        intermediate_config = {
            'subject': {
                'common_name': 'Test Intermediate CA',
                'organization': 'Test Org',
                'country': 'US'
            },
            'key_config': {
                'key_size': 2048,
                'hash_algorithm': 'SHA256'
            }
        }
        
        pki = PKIIntermediateCA(ca_config, intermediate_config)
        
        private_key_pem, csr_pem = pki.generate_intermediate_csr()
        
        assert b'BEGIN PRIVATE KEY' in private_key_pem
        assert b'BEGIN CERTIFICATE REQUEST' in csr_pem
        
        # Verify CSR is valid
        assert utils.validate_csr(csr_pem.decode())


class TestCSRSigner:
    """Test CSR signing operations."""
    
    def test_validate_csr(self):
        """Test CSR validation."""
        # This would need a valid CSR for testing
        # For now, test with invalid input
        ca_config = {
            'fqdn': 'test.local',
            'ca_name': 'Test CA',
            'winrm': {}
        }
        
        signer = CSRSigner(ca_config)
        
        # Invalid CSR should fail
        assert signer.validate_csr("INVALID CSR") is False


class TestFirewallAPI:
    """Test firewall API operations."""
    
    @patch('firewall_api.firewall.Firewall')
    def test_connect_with_api_key(self, mock_firewall_class):
        """Test connecting to firewall with API key."""
        fw_config = {
            'name': 'test',
            'ip_address': '192.168.0.7',
            'api_key': 'test_api_key'
        }
        
        # Mock system info response
        mock_fw = Mock()
        mock_result = Mock()
        mock_result.findtext = Mock(side_effect=lambda x: {
            './/hostname': 'test-fw',
            './/sw-version': '11.1.0'
        }.get(x, 'Unknown'))
        mock_fw.op.return_value = mock_result
        mock_firewall_class.return_value = mock_fw
        
        fw_api = FirewallAPI(fw_config)
        
        assert fw_api.firewall is not None
        mock_firewall_class.assert_called_once()


class TestUtils:
    """Test utility functions."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert utils.sanitize_filename("test:file/name") == "test_file_name"
        assert utils.sanitize_filename("normal_name") == "normal_name"
    
    def test_format_subject_name(self):
        """Test subject name formatting."""
        subject = utils.format_subject_name(
            common_name="test.example.com",
            organization="Test Org",
            country="US"
        )
        
        assert "CN=test.example.com" in subject
        assert "O=Test Org" in subject
        assert "C=US" in subject
    
    def test_ensure_directories(self, tmp_path):
        """Test directory creation."""
        output_config = {
            'cert_directory': str(tmp_path / 'certs'),
            'csr_directory': str(tmp_path / 'csrs'),
            'backup_directory': str(tmp_path / 'backups'),
            'create_directories': True
        }
        
        utils.ensure_directories(output_config)
        
        assert Path(tmp_path / 'certs').exists()
        assert Path(tmp_path / 'csrs').exists()
        assert Path(tmp_path / 'backups').exists()


class TestIntegration:
    """Integration tests (require actual infrastructure)."""
    
    @pytest.mark.skipif(
        not os.getenv('INTEGRATION_TESTS'),
        reason="Set INTEGRATION_TESTS=1 to run integration tests"
    )
    def test_full_workflow(self):
        """
        Test complete workflow with real infrastructure.
        
        Note: Requires:
        - WINRM_USER and WINRM_PASS set
        - PAN_HUB_API_KEY or PAN_HUB_PASSWORD set
        - Access to bakerstreeta.ad.bakerstreetlabs.io
        - Access to firewall at 192.168.0.7
        """
        # This would test the complete workflow
        # Kept as placeholder for actual integration testing
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

