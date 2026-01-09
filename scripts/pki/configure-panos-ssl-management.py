#!/usr/bin/env python3
"""
Phase 7: PAN-OS SSL/TLS Management Configuration
Baker Street Labs PKI Gap Closure

Purpose: Configure PAN-OS firewalls with proper SSL/TLS service profiles and certificates
Prerequisites: CA chain distributed to firewalls, step-ca operational
Execution: python scripts/pki/configure-panos-ssl-management.py
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path

try:
    from panos.firewall import Firewall
    from panos.errors import PanDeviceError
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("[ERROR] Required libraries not installed")
    print("Install: pip install pan-os-python requests urllib3")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PanOSSSLConfigurator:
    """Configure PAN-OS firewalls with Baker Street PKI certificates"""
    
    def __init__(self, fw_ip, username, password):
        """Initialize firewall connection"""
        self.fw_ip = fw_ip
        logger.info(f"[CONNECT] Connecting to PAN-OS: {fw_ip}")
        
        try:
            self.fw = Firewall(fw_ip, api_username=username, api_password=password)
            self.fw.refresh_system_info()
            logger.info(f"[OK] Connected to {self.fw.hostname} (Serial: {self.fw.serial})")
        except Exception as e:
            logger.error(f"[ERROR] Connection failed: {e}")
            raise
    
    def request_management_certificate(self, cert_name):
        """
        Request a certificate from step-ca for firewall management interface
        """
        logger.info(f"[CERT] Requesting management certificate: {cert_name}")
        
        # Configuration
        cn = f"{self.fw.hostname}.bakerstreetlabs.io"
        step_ca_url = "https://192.168.0.236:8443"
        ca_file = "/etc/ssl/certs/baker-street-root-ca.crt"
        
        # Generate CSR
        logger.info(f"   Generating CSR for CN={cn}")
        
        # Create OpenSSL config
        openssl_conf = f"""
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = {cn}
O = Baker Street Labs
OU = Network Security
C = US

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {cn}
DNS.2 = {self.fw.hostname}
IP.1 = {self.fw_ip}
"""
        
        with open('/tmp/panos-openssl.cnf', 'w') as f:
            f.write(openssl_conf)
        
        # Generate key and CSR
        key_file = f'/tmp/{cert_name}.key'
        csr_file = f'/tmp/{cert_name}.csr'
        cert_file = f'/tmp/{cert_name}.crt'
        
        subprocess.run([
            'openssl', 'genrsa', '-out', key_file, '2048'
        ], check=True)
        
        subprocess.run([
            'openssl', 'req', '-new',
            '-key', key_file,
            '-out', csr_file,
            '-config', '/tmp/panos-openssl.cnf'
        ], check=True)
        
        logger.info("   ✅ CSR generated")
        
        # Submit to step-ca using step CLI
        try:
            result = subprocess.run([
                'step', 'ca', 'certificate', cn, cert_file,
                '--csr', csr_file,
                '--ca-url', step_ca_url,
                '--root', ca_file,
                '--not-after', '8760h'  # 365 days
            ], check=True, capture_output=True, text=True)
            
            logger.info("   ✅ Certificate issued by step-ca")
            
            # Create PFX for PAN-OS import
            pfx_file = f'/tmp/{cert_name}.pfx'
            passphrase = 'BakerStreet2025'
            
            subprocess.run([
                'openssl', 'pkcs12', '-export',
                '-out', pfx_file,
                '-inkey', key_file,
                '-in', cert_file,
                '-passout', f'pass:{passphrase}'
            ], check=True)
            
            logger.info(f"   ✅ PFX created: {pfx_file}")
            
            return pfx_file, passphrase
            
        except subprocess.CalledProcessError as e:
            logger.error(f"   ❌ step-ca request failed: {e}")
            logger.error(f"   stdout: {e.stdout}")
            logger.error(f"   stderr: {e.stderr}")
            return None, None
    
    def import_certificate(self, cert_name, pfx_path, passphrase):
        """Import certificate to PAN-OS"""
        logger.info(f"[IMPORT] Importing certificate: {cert_name}")
        
        if not os.path.exists(pfx_path):
            logger.error(f"[ERROR] PFX not found: {pfx_path}")
            return False
        
        try:
            url = f"https://{self.fw_ip}/api/"
            params = {
                'type': 'import',
                'category': 'certificate',
                'certificate-name': cert_name,
                'format': 'pkcs12',
                'passphrase': passphrase,
                'key': self.fw.api_key
            }
            
            with open(pfx_path, 'rb') as f:
                files = {'file': (os.path.basename(pfx_path), f, 'application/x-pkcs12')}
                response = requests.post(url, params=params, files=files, verify=False)
            
            if response.status_code == 200 and 'success' in response.text.lower():
                logger.info(f"[OK] Certificate imported successfully")
                return True
            else:
                logger.error(f"[ERROR] Import failed: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Import exception: {e}")
            return False
    
    def configure_ssl_tls_profile(self, cert_name):
        """
        Configure SSL/TLS Service Profile for management interface
        """
        logger.info(f"[CONFIG] Creating SSL/TLS Service Profile...")
        
        # Create SSL/TLS Service Profile via XML API
        profile_xml = f'''<entry name="BSL-Management-Profile">
            <protocol-settings>
                <min-version>tls1-2</min-version>
                <max-version>tls1-3</max-version>
            </protocol-settings>
            <certificate>{cert_name}</certificate>
        </entry>'''
        
        try:
            # This requires the full XML API path - simplified for example
            logger.info("   Creating profile via API...")
            logger.info("   ⚠️  NOTE: Full profile configuration requires GUI or complete XML")
            logger.info("   This is a placeholder for the full implementation")
            logger.info("   Manual step: Device > Certificate Management > SSL/TLS Service Profile")
            
            return True
        except Exception as e:
            logger.error(f"   ❌ Profile creation failed: {e}")
            return False
    
    def commit_config(self):
        """Commit configuration"""
        logger.info("[COMMIT] Committing configuration...")
        
        try:
            result = self.fw.commit(sync=True)
            logger.info(f"[OK] Configuration committed")
            logger.info(f"     Job ID: {result.get('jobid', 'N/A')}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Commit failed: {e}")
            return False


def main():
    """Main execution"""
    print("="*70)
    print("  Phase 7: PAN-OS SSL/TLS Management Configuration")
    print("  Baker Street Labs PKI Gap Closure")
    print("="*70)
    print("")
    
    # Load credentials from .secrets
    secrets_file = '.secrets'
    if not os.path.exists(secrets_file):
        print(f"[ERROR] .secrets file not found: {secrets_file}")
        return 1
    
    with open(secrets_file, 'r') as f:
        secrets = json.load(f)
    
    # Process each firewall
    firewalls = [
        {'ip': '192.168.0.7', 'name': 'rangengfw'},
        {'ip': '192.168.0.52', 'name': 'xdrngfw'}
    ]
    
    for fw_config in firewalls:
        ip = fw_config['ip']
        name = fw_config['name']
        
        if ip not in secrets:
            logger.warning(f"[WARN] No credentials for {ip} in .secrets")
            continue
        
        print(f"\n{'='*70}")
        print(f"  Processing: {name} ({ip})")
        print(f"{'='*70}\n")
        
        try:
            # Initialize configurator
            configurator = PanOSSSLConfigurator(
                fw_ip=ip,
                username=secrets[ip]['username'],
                password=secrets[ip]['password']
            )
            
            # Request management certificate
            cert_name = f"{name}-Management-Cert"
            pfx_path, passphrase = configurator.request_management_certificate(cert_name)
            
            if not pfx_path:
                logger.error(f"[ERROR] Certificate request failed for {name}")
                continue
            
            # Import certificate
            if not configurator.import_certificate(cert_name, pfx_path, passphrase):
                logger.error(f"[ERROR] Import failed for {name}")
                continue
            
            # Configure SSL/TLS profile
            configurator.configure_ssl_tls_profile(cert_name)
            
            # Commit
            if configurator.commit_config():
                logger.info(f"[SUCCESS] {name} configured successfully!")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to process {name}: {e}")
            continue
    
    print("\n" + "="*70)
    print("  Configuration Complete!")
    print("="*70)
    print("")
    print("Next Steps (Manual):")
    print("  1. Apply SSL/TLS Profile to management interface:")
    print("     Device > Setup > Management > General Settings")
    print("     SSL/TLS Service Profile: BSL-Management-Profile")
    print("")
    print("  2. Create Certificate Profile for OCSP/CRL:")
    print("     Device > Certificate Management > Certificate Profile")
    print("     Add Root CA, enable OCSP")
    print("")
    print("  3. Test management interface:")
    print("     https://192.168.0.7 (should use Baker Street cert)")
    print("     https://192.168.0.52 (should use Baker Street cert)")
    print("")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

