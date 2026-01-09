#!/usr/bin/env python3
"""
Import Management Certificate to PAN-OS Firewall
Simple requests-based import for PKCS12 certificates with private keys
"""
import argparse
import requests
import xml.etree.ElementTree as ET
import base64
import sys
import urllib3
from urllib.parse import urlencode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def import_pkcs12_certificate(api_key, hostname, cert_name, pfx_path, passphrase):
    """Import PKCS12 certificate (with private key) to PAN-OS"""
    
    url = f"https://{hostname}/api/"
    
    print(f"Importing certificate '{cert_name}' to {hostname}...")
    
    try:
        # Read PFX file
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()
        
        # Base64 encode for XML API
        pfx_b64 = base64.b64encode(pfx_data).decode('utf-8')
        
        # Use import API endpoint with multipart/form-data
        params = {
            'type': 'import',
            'category': 'keypair',
            'certificate-name': cert_name,
            'format': 'pkcs12',
            'passphrase': passphrase,
            'key': api_key
        }
        
        # Send PFX file as multipart/form-data
        files = {'file': ('cert.pfx', pfx_data, 'application/x-pkcs12')}
        
        response = requests.post(url, params=params, files=files, verify=False, timeout=60)
        response.raise_for_status()
        
        # Parse response
        root = ET.fromstring(response.text)
        
        if root.get('status') == 'success':
            print(f"[OK] Certificate '{cert_name}' imported successfully (WITH private key)")
            return True
        else:
            error_msg = root.find('.//msg')
            if error_msg is not None:
                for line in error_msg.findall('.//line'):
                    print(f"[ERROR] {line.text}")
            else:
                print(f"[ERROR] Unknown error")
            return False
    
    except FileNotFoundError:
        print(f"[ERROR] Certificate file not found: {pfx_path}")
        return False
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False


def configure_mgmt_interface(api_key, hostname, cert_name):
    """Configure management interface to use the certificate"""
    
    url = f"https://{hostname}/api/"
    
    print(f"Configuring management interface to use '{cert_name}'...")
    
    # Set certificate for HTTPS service
    xpath = "/config/devices/entry[@name='localhost.localdomain']/deviceconfig/system/service"
    element = f"<https-cert>{cert_name}</https-cert>"
    
    params = {
        'type': 'config',
        'action': 'set',
        'key': api_key,
        'xpath': xpath,
        'element': element
    }
    
    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        
        if root.get('status') == 'success':
            print(f"[OK] Management interface configured to use certificate")
            return True
        else:
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"[ERROR] Configuration failed: {error_text}")
            return False
    
    except Exception as e:
        print(f"[ERROR] Configuration failed: {e}")
        return False


def commit_config(api_key, hostname):
    """Commit the configuration"""
    
    url = f"https://{hostname}/api/"
    params = {
        'type': 'commit',
        'cmd': '<commit></commit>',
        'key': api_key
    }
    
    print("Committing configuration...")
    
    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=120)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"[ERROR] Commit failed: {error_text}")
            return False
        
        # Monitor commit job
        job_id_elem = root.find('.//job')
        if job_id_elem is not None:
            job_id = job_id_elem.text
            print(f"  Commit job ID: {job_id}")
            
            import time
            while True:
                status_params = {
                    'type': 'op',
                    'cmd': f'<show><jobs><id>{job_id}</id></jobs></show>',
                    'key': api_key
                }
                
                status_response = requests.get(url, params=urlencode(status_params), verify=False, timeout=30)
                status_root = ET.fromstring(status_response.text)
                
                job_status = status_root.find('.//status').text
                progress = status_root.find('.//progress')
                progress_pct = progress.text if progress is not None else "0"
                
                print(f"  Progress: {progress_pct}% ({job_status})", end='\r')
                
                if job_status == 'FIN':
                    result = status_root.find('.//result')
                    if result is not None and result.text == 'OK':
                        print("\n[OK] Configuration committed successfully")
                        details = status_root.find('.//details/line')
                        if details is not None:
                            print(f"  Details: {details.text}")
                        return True
                    else:
                        details = status_root.find('.//details/line')
                        details_text = details.text if details is not None else "Unknown error"
                        print(f"\n[ERROR] Commit failed: {details_text}")
                        return False
                
                time.sleep(2)
        else:
            print("[OK] Configuration committed")
            return True
    
    except Exception as e:
        print(f"[ERROR] Commit failed: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Import management certificate to PAN-OS firewall',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example:
  python import_mgmt_cert.py \\
    --api-key YOUR_KEY \\
    --hostname 192.168.0.52 \\
    --cert-name rangexdr-mgmt-https \\
    --pfx-path rangexdr-mgmt.pfx \\
    --passphrase BakerStreet2025 \\
    --commit
        '''
    )
    
    parser.add_argument('--api-key', required=True, help='PAN-OS API key')
    parser.add_argument('--hostname', required=True, help='Firewall hostname or IP')
    parser.add_argument('--cert-name', required=True, help='Certificate name in PAN-OS')
    parser.add_argument('--pfx-path', required=True, help='Path to PKCS12 (.pfx) file')
    parser.add_argument('--passphrase', required=True, help='PFX passphrase')
    parser.add_argument('--commit', action='store_true', help='Commit configuration')
    parser.add_argument('--configure-mgmt', action='store_true', help='Configure management interface to use cert')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("PAN-OS Management Certificate Import")
    print("=" * 70)
    print(f"Firewall: {args.hostname}")
    print(f"Certificate: {args.cert_name}")
    print(f"PFX File: {args.pfx_path}")
    print("=" * 70)
    print()
    
    # Step 1: Import certificate
    if not import_pkcs12_certificate(args.api_key, args.hostname, args.cert_name, 
                                     args.pfx_path, args.passphrase):
        sys.exit(1)
    
    # Step 2: Configure management interface (if requested)
    if args.configure_mgmt:
        if not configure_mgmt_interface(args.api_key, args.hostname, args.cert_name):
            print("[WARNING] Management interface configuration failed")
            print("  You can configure manually: Device -> Setup -> Management -> Management Interface Settings")
    
    # Step 3: Commit (if requested)
    if args.commit:
        if not commit_config(args.api_key, args.hostname):
            sys.exit(1)
    else:
        print("\n[WARNING] Configuration NOT committed (use --commit to commit)")
    
    print("\n" + "=" * 70)
    print("[OK] Certificate import complete!")
    print("=" * 70)
    print(f"\nNext Steps:")
    print(f"  1. Access: https://{args.hostname}")
    print(f"  2. Browser will use new certificate")
    print(f"  3. Import Baker Street Labs Root CA to browser if needed")
    
    sys.exit(0)

