#!/usr/bin/env python3
"""
Firewall API Manager
Baker Street Labs - PAN-OS Certificate Management

Handles all interactions with Palo Alto Networks firewalls via XML API.
"""

import logging
import base64
import time
from typing import Dict, Any, Optional, List
import xml.etree.ElementTree as ET
from panos import firewall, base
from panos.errors import PanDeviceError, PanConnectionTimeout

logger = logging.getLogger(__name__)


class FirewallAPIError(Exception):
    """Raised when firewall API operations fail."""
    pass


class FirewallAPI:
    """Manages PAN-OS firewall API interactions for certificate operations."""
    
    def __init__(self, firewall_config: Dict[str, Any]):
        """
        Initialize firewall API manager.
        
        Args:
            firewall_config: Firewall configuration dict
        """
        self.config = firewall_config
        self.name = firewall_config['name']
        self.ip_address = firewall_config['ip_address']
        self.hostname = firewall_config.get('hostname', self.ip_address)
        
        self.firewall: Optional[firewall.Firewall] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to firewall."""
        logger.info(f"Connecting to firewall {self.name} ({self.ip_address})...")
        
        # Prefer API key, fall back to username/password
        api_key = self.config.get('api_key')
        username = self.config.get('username', 'admin')
        password = self.config.get('password')
        
        try:
            if api_key:
                self.firewall = firewall.Firewall(
                    self.ip_address,
                    api_key=api_key
                )
                logger.info(f"Connected to {self.name} using API key")
            elif password:
                self.firewall = firewall.Firewall(
                    self.ip_address,
                    api_username=username,
                    api_password=password
                )
                logger.info(f"Connected to {self.name} using username/password")
            else:
                raise FirewallAPIError(
                    f"No credentials configured for firewall {self.name}. "
                    f"Set PAN_{self.name.upper()}_API_KEY or "
                    f"PAN_{self.name.upper()}_PASSWORD environment variable."
                )
            
            # Test connection
            system_info = self.firewall.op('show system info')
            hostname = system_info.findtext('.//hostname')
            sw_version = system_info.findtext('.//sw-version')
            logger.info(f"Connected to {hostname} running PAN-OS {sw_version}")
            
        except PanDeviceError as e:
            logger.error(f"Failed to connect to firewall {self.name}: {e}")
            raise FirewallAPIError(f"Connection failed: {e}")
    
    def certificate_exists(self, cert_name: str) -> bool:
        """
        Check if a certificate exists on the firewall.
        
        Args:
            cert_name: Name of the certificate
            
        Returns:
            True if certificate exists
        """
        logger.debug(f"Checking if certificate {cert_name} exists on {self.name}...")
        
        cmd = f'<show><config><running><xpath>devices/entry/vsys/entry[@name="vsys1"]/certificate/entry[@name="{cert_name}"]</xpath></running></config></show>'
        
        try:
            result = self.firewall.op(cmd)
            # If we get a result with entry, certificate exists
            exists = result.find('.//entry') is not None
            
            if exists:
                logger.info(f"Certificate {cert_name} exists on {self.name}")
            else:
                logger.info(f"Certificate {cert_name} not found on {self.name}")
                
            return exists
            
        except Exception as e:
            logger.debug(f"Error checking certificate existence: {e}")
            return False
    
    def generate_certificate_csr(self, cert_config: Dict[str, Any]) -> Optional[str]:
        """
        Generate a certificate signing request on the firewall.
        
        Args:
            cert_config: Certificate configuration dict
            
        Returns:
            CSR in PEM format, or None if failed
        """
        cert_name = cert_config.get('name', 'ngfw-cert')
        common_name = cert_config.get('common_name')
        organization = cert_config.get('organization', 'Baker Street Labs')
        country = cert_config.get('country', 'US')
        key_size = cert_config.get('key_size', 2048)
        
        if not common_name:
            raise FirewallAPIError("Common name is required for CSR generation")
        
        logger.info(f"Generating CSR for {cert_name} on firewall {self.name}...")
        
        # Build XML command for CSR generation
        cmd = f"""
        <request>
            <certificate>
                <generate>
                    <name>{cert_name}</name>
                    <common-name>{common_name}</common-name>
                    <organization>{organization}</organization>
                    <country>{country}</country>
                    <algorithm>
                        <RSA>
                            <rsa-nbits>{key_size}</rsa-nbits>
                        </RSA>
                    </algorithm>
                    <signed-by>external</signed-by>
                </generate>
            </certificate>
        </request>
        """
        
        try:
            # Generate CSR
            result = self.firewall.op(cmd)
            
            # Check for errors
            if result.find('.//msg') is not None:
                msg = result.findtext('.//msg')
                if 'success' not in msg.lower() and 'already exists' not in msg.lower():
                    logger.warning(f"CSR generation message: {msg}")
            
            # Wait for CSR generation
            time.sleep(2)
            
            # Retrieve CSR
            show_cmd = f"""
            <show>
                <certificate>
                    <info>
                        <name>{cert_name}</name>
                    </info>
                </certificate>
            </show>
            """
            
            csr_result = self.firewall.op(show_cmd)
            
            # Extract CSR from XML response
            csr_text = None
            for entry in csr_result.findall('.//entry'):
                name_elem = entry.find('name')
                if name_elem is not None and name_elem.text == cert_name:
                    csr_elem = entry.find('csr')
                    if csr_elem is not None:
                        csr_text = csr_elem.text
                        break
            
            if csr_text:
                logger.info(f"Successfully generated CSR for {cert_name}")
                return csr_text
            else:
                logger.error(f"Failed to retrieve CSR for {cert_name}")
                return None
                
        except PanDeviceError as e:
            logger.error(f"PAN-OS API error generating CSR: {e}")
            return None
        except Exception as e:
            logger.error(f"Exception generating CSR: {e}")
            return None
    
    def import_certificate(self, cert_name: str, cert_chain_pem: str, 
                          private_key_pem: Optional[str] = None) -> bool:
        """
        Import signed certificate (and optionally private key) to firewall.
        
        Args:
            cert_name: Name for the certificate on firewall
            cert_chain_pem: Certificate chain in PEM format (cert + intermediates + root)
            private_key_pem: Private key in PEM format (if importing key separately)
            
        Returns:
            True if import successful
        """
        logger.info(f"Importing certificate {cert_name} to firewall {self.name}...")
        
        try:
            # Import certificate chain
            # PAN-OS expects base64-encoded PEM content
            cert_content = base64.b64encode(cert_chain_pem.encode()).decode()
            
            import_cmd = f"""
            <request>
                <certificate>
                    <import>
                        <certificate-name>{cert_name}</certificate-name>
                        <format>pem</format>
                        <content>{cert_content}</content>
                    </import>
                </certificate>
            </request>
            """
            
            result = self.firewall.op(import_cmd)
            
            # Check result
            msg = result.findtext('.//msg')
            if msg and 'success' in msg.lower():
                logger.info(f"Successfully imported certificate {cert_name}")
                return True
            else:
                logger.error(f"Certificate import may have failed: {msg}")
                return False
                
        except PanDeviceError as e:
            logger.error(f"PAN-OS API error importing certificate: {e}")
            return False
        except Exception as e:
            logger.error(f"Exception importing certificate: {e}")
            return False
    
    def commit_changes(self, description: Optional[str] = None) -> bool:
        """
        Commit configuration changes to firewall.
        
        Args:
            description: Optional commit description
            
        Returns:
            True if commit successful
        """
        logger.info(f"Committing changes to firewall {self.name}...")
        
        try:
            commit_desc = description or f"PKI certificate import - {datetime.now().isoformat()}"
            
            # Use panos library commit method
            job_result = self.firewall.commit(sync=True, description=commit_desc)
            
            logger.info(f"Commit successful on {self.name}")
            return True
            
        except PanDeviceError as e:
            logger.error(f"Commit failed on {self.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Exception during commit: {e}")
            return False
    
    def backup_config(self, backup_file: Optional[str] = None) -> bool:
        """
        Backup firewall configuration.
        
        Args:
            backup_file: Optional path to save backup
            
        Returns:
            True if backup successful
        """
        if not backup_file:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{self.name}_{timestamp}.xml"
        
        logger.info(f"Backing up configuration for {self.name} to {backup_file}...")
        
        try:
            cmd = '<show><config><running></running></config></show>'
            result = self.firewall.op(cmd)
            
            # Save XML configuration
            config_xml = ET.tostring(result, encoding='unicode')
            
            with open(backup_file, 'w') as f:
                f.write(config_xml)
            
            logger.info(f"Configuration backed up to {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return False
    
    def list_certificates(self) -> List[Dict[str, str]]:
        """
        List all certificates on the firewall.
        
        Returns:
            List of certificate dictionaries with name, subject, expiry
        """
        logger.debug(f"Listing certificates on {self.name}...")
        
        try:
            cmd = '<show><certificate><info></info></certificate></show>'
            result = self.firewall.op(cmd)
            
            certificates = []
            for entry in result.findall('.//entry'):
                name = entry.findtext('name', 'Unknown')
                subject = entry.findtext('subject', 'Unknown')
                expiry = entry.findtext('not-valid-after', 'Unknown')
                
                certificates.append({
                    'name': name,
                    'subject': subject,
                    'expiry': expiry
                })
            
            logger.debug(f"Found {len(certificates)} certificates on {self.name}")
            return certificates
            
        except Exception as e:
            logger.error(f"Failed to list certificates: {e}")
            return []
    
    def close(self):
        """Close firewall connection."""
        if self.firewall:
            # panos library doesn't require explicit close
            self.firewall = None
            logger.debug(f"Closed connection to firewall {self.name}")


# Convenience function
def connect_to_firewall(firewall_config: Dict[str, Any]) -> FirewallAPI:
    """
    Connect to a firewall using configuration.
    
    Args:
        firewall_config: Firewall configuration dict
        
    Returns:
        FirewallAPI instance
    """
    return FirewallAPI(firewall_config)

