#!/usr/bin/env python3
"""
CSR Signing Manager
Baker Street Labs - Certificate Signing Operations

Handles submission of CSRs to Windows CA and retrieval of signed certificates.
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
import winrm
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class CSRSigningError(Exception):
    """Raised when CSR signing operations fail."""
    pass


class CSRSigner:
    """Manages CSR signing operations with Windows CA."""
    
    def __init__(self, ca_config: Dict[str, Any]):
        """
        Initialize CSR signer.
        
        Args:
            ca_config: Certificate Authority configuration
        """
        self.ca_fqdn = ca_config['fqdn']
        self.ca_name = ca_config['ca_name']
        self.winrm_config = ca_config.get('winrm', {})
        
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
            raise CSRSigningError(
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
            logger.debug(f"Created WinRM session to {self.ca_fqdn}")
            return self.session
        except Exception as e:
            logger.error(f"Failed to create WinRM session: {e}")
            raise CSRSigningError(f"WinRM connection failed: {e}")
    
    def validate_csr(self, csr_pem: str) -> bool:
        """
        Validate CSR format and content.
        
        Args:
            csr_pem: CSR in PEM format
            
        Returns:
            True if CSR is valid
        """
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode(), default_backend())
            
            # Basic validation
            if not csr.is_signature_valid:
                logger.error("CSR signature is invalid")
                return False
            
            subject = csr.subject
            logger.debug(f"CSR Subject: {subject}")
            
            return True
            
        except Exception as e:
            logger.error(f"CSR validation failed: {e}")
            return False
    
    def sign_csr(self, csr_pem: str, template_name: str = "BSLWebServer") -> Optional[str]:
        """
        Submit CSR to Windows CA for signing.
        
        Args:
            csr_pem: CSR in PEM format
            template_name: Certificate template to use
            
        Returns:
            Signed certificate in PEM format, or None if failed
        """
        logger.info(f"Signing CSR using template {template_name}...")
        
        # Validate CSR
        if not self.validate_csr(csr_pem):
            logger.error("CSR validation failed, cannot sign")
            return None
        
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        
        # Create temp files
        $csrFile = "$env:TEMP\\firewall_$(Get-Random).csr"
        $certFile = "$env:TEMP\\firewall_$(Get-Random).cer"
        
        # Write CSR to file
        @'
{csr_pem}
'@ | Out-File -FilePath $csrFile -Encoding ASCII -Force
        
        try {{
            # Submit to CA
            $caConfig = "{self.ca_fqdn}\\{self.ca_name}"
            $output = certreq -submit -config $caConfig -attrib "CertificateTemplate:{template_name}" $csrFile $certFile 2>&1
            
            if (Test-Path $certFile) {{
                # Read certificate
                $cert = Get-Content $certFile -Raw
                Write-Output "SUCCESS"
                Write-Output $cert
                exit 0
            }} else {{
                Write-Error "Certificate file not created. Output: $output"
                exit 1
            }}
        }} finally {{
            # Cleanup
            if (Test-Path $csrFile) {{ Remove-Item $csrFile -Force -ErrorAction SilentlyContinue }}
            if (Test-Path $certFile) {{ Remove-Item $certFile -Force -ErrorAction SilentlyContinue }}
        }}
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                output = result.std_out.decode('utf-8')
                
                # Extract certificate (everything after SUCCESS marker)
                if "SUCCESS" in output:
                    cert_pem = output.split("SUCCESS", 1)[1].strip()
                    logger.info(f"Successfully obtained signed certificate using template {template_name}")
                    return cert_pem
                else:
                    logger.error("SUCCESS marker not found in output")
                    return None
            else:
                error = result.std_err.decode('utf-8')
                logger.error(f"CSR signing failed: {error}")
                logger.error(f"stdout: {result.std_out.decode('utf-8')}")
                return None
                
        except Exception as e:
            logger.error(f"Exception signing CSR: {e}")
            return None
    
    def get_certificate_chain(self, cert_pem: str) -> str:
        """
        Build complete certificate chain (cert + intermediate + root).
        
        Args:
            cert_pem: End-entity certificate in PEM format
            
        Returns:
            Complete certificate chain in PEM format
        """
        logger.info("Building certificate chain...")
        
        ps_script = """
        $ErrorActionPreference = 'Stop'
        
        # Get Root CA certificate
        $rootCertFile = "$env:TEMP\\root_ca.cer"
        certutil -ca.cert $rootCertFile
        
        if (Test-Path $rootCertFile) {
            # Convert DER to PEM if needed
            $certContent = Get-Content $rootCertFile -Raw
            
            # If already PEM, output as-is, otherwise convert
            if ($certContent -like "*BEGIN CERTIFICATE*") {
                Write-Output $certContent
            } else {
                # Convert DER to Base64
                $certBytes = [System.IO.File]::ReadAllBytes($rootCertFile)
                $base64 = [System.Convert]::ToBase64String($certBytes)
                $pem = "-----BEGIN CERTIFICATE-----`n"
                for ($i = 0; $i -lt $base64.Length; $i += 64) {
                    $len = [Math]::Min(64, $base64.Length - $i)
                    $pem += $base64.Substring($i, $len) + "`n"
                }
                $pem += "-----END CERTIFICATE-----`n"
                Write-Output $pem
            }
            
            Remove-Item $rootCertFile -Force -ErrorAction SilentlyContinue
            exit 0
        } else {
            Write-Error "Failed to get Root CA certificate"
            exit 1
        }
        """
        
        try:
            session = self._get_winrm_session()
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                root_cert_pem = result.std_out.decode('utf-8').strip()
                
                # Build chain: end-entity cert + root CA
                # If there's an intermediate, it would go between them
                chain = cert_pem.strip()
                if not chain.endswith('\n'):
                    chain += '\n'
                chain += root_cert_pem
                
                logger.info("Certificate chain built successfully")
                return chain
            else:
                logger.warning("Failed to get Root CA cert, using cert only")
                return cert_pem
                
        except Exception as e:
            logger.warning(f"Exception building chain, using cert only: {e}")
            return cert_pem
    
    def close(self):
        """Close WinRM session."""
        if self.session:
            self.session = None
            logger.debug("WinRM session closed")

