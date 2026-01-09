#!/usr/bin/env python3
"""
PKI Intermediate CA Manager
Baker Street Labs - NGFW Intermediate Certificate Authority Management

Manages the creation and configuration of an intermediate CA for NGFW certificates.
Uses WinRM to interact with Windows Active Directory Certificate Services.
"""

import logging
import base64
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import winrm
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class PKIIntermediateCA:
    """Manages NGFW Intermediate Certificate Authority operations."""
    
    def __init__(self, ca_config: Dict[str, Any], intermediate_config: Dict[str, Any]):
        """
        Initialize PKI Intermediate CA manager.
        
        Args:
            ca_config: Certificate Authority configuration
            intermediate_config: Intermediate CA configuration
        """
        self.ca_fqdn = ca_config['fqdn']
        self.ca_name = ca_config['ca_name']
        self.domain = ca_config['domain']
        
        self.winrm_config = ca_config.get('winrm', {})
        self.intermediate_config = intermediate_config
        
        self.session: Optional[winrm.Session] = None
        
    def _get_winrm_session(self) -> winrm.Session:
        """
        Get or create WinRM session to CA server.
        
        Returns:
            WinRM session object
        """
        if self.session:
            return self.session
            
        username = self.winrm_config.get('username')
        password = self.winrm_config.get('password')
        transport = self.winrm_config.get('transport', 'kerberos')
        port = self.winrm_config.get('port', 5985)
        
        if not username or not password:
            raise ValueError(
                "WinRM credentials not configured. "
                "Set WINRM_USER and WINRM_PASS environment variables."
            )
        
        endpoint = f'http://{self.ca_fqdn}:{port}/wsman'
        
        try:
            self.session = winrm.Session(
                endpoint,
                auth=(username, password),
                transport=transport,
                server_cert_validation='ignore'
            )
            logger.info(f"Created WinRM session to {self.ca_fqdn}")
            return self.session
        except Exception as e:
            logger.error(f"Failed to create WinRM session: {e}")
            raise
    
    def check_template_exists(self, template_name: str) -> bool:
        """
        Check if a certificate template exists in Active Directory.
        
        Args:
            template_name: Name of the template to check
            
        Returns:
            True if template exists, False otherwise
        """
        logger.info(f"Checking if template {template_name} exists...")
        
        ps_script = f"""
        try {{
            $null = certutil -v -template {template_name} 2>&1
            if ($LASTEXITCODE -eq 0) {{
                Write-Output "EXISTS"
                exit 0
            }} else {{
                Write-Output "NOT_FOUND"
                exit 0
            }}
        }} catch {{
            Write-Output "NOT_FOUND"
            exit 0
        }}
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            output = result.std_out.decode('utf-8').strip()
            exists = "EXISTS" in output
            
            if exists:
                logger.info(f"Template {template_name} exists in AD")
            else:
                logger.info(f"Template {template_name} not found in AD")
                
            return exists
            
        except Exception as e:
            logger.error(f"Error checking template existence: {e}")
            return False
    
    def create_intermediate_template(self) -> bool:
        """
        Create intermediate CA certificate template in Active Directory.
        
        Returns:
            True if created successfully or already exists
        """
        template_name = self.intermediate_config.get('template_name', 'NGFWIntermediate')
        display_name = self.intermediate_config.get('display_name', 
                                                    'Baker Street Labs NGFW Intermediate CA')
        
        if self.check_template_exists(template_name):
            logger.info(f"Template {template_name} already exists, skipping creation")
            return True
        
        logger.info(f"Creating intermediate CA template: {template_name}")
        
        # Generate unique OID
        import random
        oid = f"1.3.6.1.4.1.311.21.8.{random.randint(10000000, 99999999)}.{random.randint(1000000, 9999999)}"
        
        # 5-year validity in FileTime format (negative value, 100-nanosecond intervals)
        # ~5 years = 5 * 365.25 * 24 * 60 * 60 * 10000000 = 1,576,800,000,000,000
        validity_bytes = "0,192,171,182,130,185,250,255"  # 5 years
        
        ps_script = f"""
        Import-Module ActiveDirectory -ErrorAction Stop
        
        $templateName = "{template_name}"
        $displayName = "{display_name}"
        $configNC = (Get-ADRootDSE).configurationNamingContext
        $templatesDN = "CN=Certificate Templates,CN=Public Key Services,CN=Services,$configNC"
        $templateDN = "CN=$templateName,$templatesDN"
        
        # Check if template exists
        $existing = Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue
        if ($existing) {{
            Write-Output "Template already exists"
            exit 0
        }}
        
        # Create template attributes
        $attributes = @{{
            'cn' = $templateName
            'displayName' = $displayName
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584
            'revision' = 100
            'pKIDefaultKeySpec' = 2
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]]({validity_bytes})
            'pKIOverlapPeriod' = [byte[]](0,64,57,135,46,225,254,255)
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842752
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 4096
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = '{oid}'
        }}
        
        # Create template
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Write-Output "Template created successfully"
        
        # Publish to CA
        Start-Sleep -Seconds 2
        certutil -SetCATemplates +$templateName
        Write-Output "Template published to CA"
        
        # Restart CA service
        Restart-Service CertSvc -Force
        Write-Output "CA service restarted"
        
        exit 0
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            output = result.std_out.decode('utf-8')
            logger.info(f"Template creation output: {output}")
            
            if result.status_code == 0:
                logger.info(f"Successfully created template {template_name}")
                return True
            else:
                error_output = result.std_err.decode('utf-8')
                logger.error(f"Failed to create template: {error_output}")
                return False
                
        except Exception as e:
            logger.error(f"Exception creating template: {e}")
            return False
    
    def generate_intermediate_csr(self) -> Tuple[bytes, bytes]:
        """
        Generate CSR for intermediate CA certificate.
        
        Returns:
            Tuple of (private_key_pem, csr_pem)
        """
        logger.info("Generating CSR for intermediate CA...")
        
        subject_config = self.intermediate_config.get('subject', {})
        key_config = self.intermediate_config.get('key_config', {})
        
        # Generate private key
        key_size = key_config.get('key_size', 4096)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Build subject
        subject_parts = []
        
        if 'country' in subject_config:
            subject_parts.append(x509.NameAttribute(NameOID.COUNTRY_NAME, subject_config['country']))
        if 'organization' in subject_config:
            subject_parts.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, 
                                                    subject_config['organization']))
        if 'organizational_unit' in subject_config:
            subject_parts.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 
                                                    subject_config['organizational_unit']))
        if 'common_name' in subject_config:
            subject_parts.append(x509.NameAttribute(NameOID.COMMON_NAME, 
                                                    subject_config['common_name']))
        
        subject = x509.Name(subject_parts)
        
        # Build CSR
        builder = x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(subject)
        
        # Add basic constraints extension (CA=TRUE, path_length=0)
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True
        )
        
        # Add key usage extension (for CA operations)
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        
        # Sign CSR
        hash_algorithm = getattr(hashes, key_config.get('hash_algorithm', 'SHA256'))()
        csr = builder.sign(private_key, hash_algorithm, backend=default_backend())
        
        # Serialize
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        
        logger.info(f"Generated {key_size}-bit RSA CSR for intermediate CA")
        return private_key_pem, csr_pem
    
    def submit_csr_to_root_ca(self, csr_pem: bytes, template_name: str) -> Optional[bytes]:
        """
        Submit CSR to Root CA for signing.
        
        Args:
            csr_pem: CSR in PEM format
            template_name: Certificate template to use
            
        Returns:
            Signed certificate in PEM format, or None if failed
        """
        logger.info(f"Submitting CSR to Root CA using template {template_name}...")
        
        # Encode CSR for PowerShell
        csr_text = csr_pem.decode('utf-8')
        
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        
        # Write CSR to temp file
        $csrFile = "$env:TEMP\\intermediate_ca.csr"
        $certFile = "$env:TEMP\\intermediate_ca.cer"
        
        @'
{csr_text}
'@ | Out-File -FilePath $csrFile -Encoding ASCII -Force
        
        # Submit to CA
        $caConfig = "{self.ca_fqdn}\\{self.ca_name}"
        certreq -submit -config $caConfig -attrib "CertificateTemplate:{template_name}" $csrFile $certFile
        
        if (Test-Path $certFile) {{
            # Read and output certificate
            $cert = Get-Content $certFile -Raw
            Write-Output $cert
            
            # Cleanup
            Remove-Item $csrFile -Force -ErrorAction SilentlyContinue
            Remove-Item $certFile -Force -ErrorAction SilentlyContinue
            
            exit 0
        }} else {{
            Write-Error "Certificate file not created"
            exit 1
        }}
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                cert_pem = result.std_out.decode('utf-8')
                logger.info("Successfully retrieved signed certificate from Root CA")
                return cert_pem.encode('utf-8')
            else:
                error = result.std_err.decode('utf-8')
                logger.error(f"Failed to get signed certificate: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Exception submitting CSR to CA: {e}")
            return None
    
    def check_intermediate_ca_exists(self) -> bool:
        """
        Check if intermediate CA certificate exists on the CA server.
        
        Returns:
            True if intermediate CA exists
        """
        template_name = self.intermediate_config.get('template_name', 'NGFWIntermediate')
        
        ps_script = f"""
        # Check if any certificates issued from this template
        $count = certutil -view -restrict "CertificateTemplate={template_name}" csv | 
                 Select-Object -Skip 1 | 
                 Measure-Object | 
                 Select-Object -ExpandProperty Count
        
        Write-Output $count
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                count = int(result.std_out.decode('utf-8').strip())
                exists = count > 0
                
                if exists:
                    logger.info(f"Intermediate CA exists ({count} certificate(s) found)")
                else:
                    logger.info("Intermediate CA not found")
                    
                return exists
            else:
                return False
                
        except Exception as e:
            logger.warning(f"Error checking intermediate CA existence: {e}")
            return False
    
    def ensure_intermediate_ca(self) -> bool:
        """
        Ensure intermediate CA exists, create if missing.
        
        Returns:
            True if intermediate CA exists or was created successfully
        """
        if not self.intermediate_config.get('create_if_missing', True):
            logger.info("Intermediate CA auto-creation disabled")
            return self.check_intermediate_ca_exists()
        
        # Check if template exists
        template_name = self.intermediate_config.get('template_name', 'NGFWIntermediate')
        
        if not self.check_template_exists(template_name):
            logger.info(f"Template {template_name} doesn't exist, creating...")
            if not self.create_intermediate_template():
                logger.error("Failed to create intermediate template")
                return False
        
        # Check if intermediate CA certificate exists
        if self.check_intermediate_ca_exists():
            logger.info("Intermediate CA already exists")
            return True
        
        logger.info("Creating new intermediate CA certificate...")
        
        # Generate CSR
        private_key_pem, csr_pem = self.generate_intermediate_csr()
        
        # Save private key securely (in production, use proper key management)
        key_file = "intermediate_ca_key.pem"
        with open(key_file, 'wb') as f:
            f.write(private_key_pem)
        logger.info(f"Saved intermediate CA private key to {key_file}")
        logger.warning("IMPORTANT: Secure this private key file!")
        
        # Submit CSR to Root CA
        cert_pem = self.submit_csr_to_root_ca(csr_pem, template_name)
        
        if cert_pem:
            # Save certificate
            cert_file = "intermediate_ca_cert.pem"
            with open(cert_file, 'wb') as f:
                f.write(cert_pem)
            logger.info(f"Saved intermediate CA certificate to {cert_file}")
            logger.info("Intermediate CA created successfully!")
            return True
        else:
            logger.error("Failed to obtain signed intermediate CA certificate")
            return False
    
    def get_root_ca_certificate(self) -> Optional[bytes]:
        """
        Retrieve Root CA certificate in PEM format.
        
        Returns:
            Root CA certificate in PEM format, or None if failed
        """
        logger.info("Retrieving Root CA certificate...")
        
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        
        # Export Root CA certificate
        $certFile = "$env:TEMP\\root_ca.cer"
        certutil -ca.cert $certFile
        
        if (Test-Path $certFile) {{
            # Convert to Base64 if needed and output
            $cert = Get-Content $certFile -Raw
            Write-Output $cert
            Remove-Item $certFile -Force -ErrorAction SilentlyContinue
            exit 0
        }} else {{
            Write-Error "Failed to export Root CA certificate"
            exit 1
        }}
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                cert_data = result.std_out.decode('utf-8')
                logger.info("Successfully retrieved Root CA certificate")
                return cert_data.encode('utf-8')
            else:
                error = result.std_err.decode('utf-8')
                logger.error(f"Failed to get Root CA certificate: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Exception retrieving Root CA certificate: {e}")
            return None
    
    def close(self):
        """Close WinRM session."""
        if self.session:
            # WinRM sessions don't need explicit closing in pywinrm
            self.session = None
            logger.debug("WinRM session closed")

