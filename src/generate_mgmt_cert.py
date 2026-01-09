#!/usr/bin/env python3
"""
Generate Management Certificate for PAN-OS Firewall
Creates a certificate signed by the intermediate CA and configures it for HTTPS management.

Usage:
    python generate_mgmt_cert.py --api-key YOUR_KEY --hostname rangexdr.bakerstreetlabs.io \\
        --ca-name "Baker Street Labs Issuing CA" --fqdn rangexdr.bakerstreetlabs.io

Author: Baker Street Labs
Date: October 22, 2025
"""

import argparse
import requests
import xml.etree.ElementTree as ET
import sys
from urllib.parse import urlencode
import time
import uuid
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def generate_certificate(api_key, hostname, ca_name, fqdn, cert_name):
    """
    Generates a certificate signed by the specified intermediate CA on the PAN-OS device.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.
        ca_name (str): Name of the existing intermediate CA on the firewall.
        fqdn (str): FQDN to use as the Subject Name (CN) for the certificate.
        cert_name (str): Name for the new certificate.

    Returns:
        bool: True if certificate generation is successful, False otherwise.
    """
    url = f"https://{hostname}/api/"
    # XML command to generate a certificate
    # Note: PAN-OS uses <rsa-nbits> not <modulus-length>
    cmd = f"""
    <request><certificate><generate><signed-by>{ca_name}</signed-by><certificate-name>{cert_name}</certificate-name>
    <name>{fqdn}</name><algorithm><RSA><rsa-nbits>2048</rsa-nbits></RSA></algorithm>
    <ca>no</ca></generate></certificate></request>
    """
    params = {
        'type': 'op',
        'cmd': cmd,
        'key': api_key
    }

    print(f"Generating certificate '{cert_name}' for {fqdn}...")
    print(f"  Signing CA: {ca_name}")

    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=30)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"[ERROR] Error generating certificate: {error_text}")
            return False

        print(f"[OK] Certificate '{cert_name}' generated successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error generating certificate: {e}")
        return False


def create_mgmt_profile(api_key, hostname, profile_name, cert_name, permitted_ips=None):
    """
    Creates a management profile on the management interface with the specified certificate.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.
        profile_name (str): Name for the management interface profile.
        cert_name (str): Name of the certificate to use for HTTPS.
        permitted_ips (list, optional): List of permitted IP addresses or networks (e.g., ['192.168.1.0/24']).

    Returns:
        bool: True if management profile creation is successful, False otherwise.
    """
    url = f"https://{hostname}/api/"
    
    # Build permitted IPs XML
    permitted_ips_xml = ''
    if permitted_ips:
        permitted_ips_xml = '<permitted-ip>' + ''.join(f'<entry name="{ip}"/>' for ip in permitted_ips) + '</permitted-ip>'

    # XML element to configure the management profile
    element = f"""
    <entry name="{profile_name}">
        <https>yes</https>
        <certificate>{cert_name}</certificate>
        {permitted_ips_xml}
    </entry>
    """
    
    params = {
        'type': 'config',
        'action': 'set',
        'key': api_key,
        'xpath': '/config/devices/entry[@name="localhost.localdomain"]/deviceconfig/system',
        'element': f'<mgmt-interface-profile>{element}</mgmt-interface-profile>'
    }

    print(f"Creating management profile '{profile_name}'...")
    if permitted_ips:
        print(f"  Permitted IPs: {', '.join(permitted_ips)}")

    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=30)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"[ERROR] Error creating management profile: {error_text}")
            return False

        print(f"[OK] Management profile '{profile_name}' created successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error creating management profile: {e}")
        return False


def commit_config(api_key, hostname):
    """
    Commits the candidate configuration to the running configuration.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.

    Returns:
        bool: True if commit is successful, False otherwise.
    """
    url = f"https://{hostname}/api/"
    params = {
        'type': 'commit',
        'cmd': '<commit></commit>',
        'key': api_key
    }

    print("Committing configuration...")
    print("[WAIT] This may take 30-60 seconds...")

    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=60)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"[ERROR] Error committing configuration: {error_text}")
            return False

        # Poll for commit job completion
        job_id_elem = root.find('.//job')
        if job_id_elem is not None:
            job_id = job_id_elem.text
            print(f"   Commit job ID: {job_id}")
            
            while True:
                status_params = {
                    'type': 'op',
                    'cmd': f'<show><jobs><id>{job_id}</id></jobs></show>',
                    'key': api_key
                }
                status_response = requests.get(url, params=urlencode(status_params), verify=False, timeout=30)
                status_response.raise_for_status()
                status_root = ET.fromstring(status_response.text)
                
                job_status_elem = status_root.find('.//status')
                if job_status_elem is None:
                    print("[ERROR] Error: Could not retrieve job status")
                    return False
                
                job_status = job_status_elem.text
                progress_elem = status_root.find('.//progress')
                progress = progress_elem.text if progress_elem is not None else "0"
                
                print(f"   Progress: {progress}% ({job_status})", end='\r')
                
                if job_status == 'FIN':
                    result_elem = status_root.find('.//result')
                    if result_elem is not None and result_elem.text == 'OK':
                        print("\n[OK] Configuration committed successfully")
                        return True
                    else:
                        details_elem = status_root.find('.//details')
                        details = details_elem.text if details_elem is not None else "Unknown error"
                        print(f"\n[ERROR] Commit failed: {details}")
                        return False
                
                time.sleep(2)  # Wait before polling again
        else:
            print("[OK] Configuration committed successfully")
            return True

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Error committing configuration: {e}")
        return False


if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Generate a certificate and create a management profile on PAN-OS device.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate certificate for rangexdr using Baker Street Labs Issuing CA
  python generate_mgmt_cert.py \\
    --api-key YOUR_KEY \\
    --hostname rangexdr.bakerstreetlabs.io \\
    --ca-name "Baker Street Labs Issuing CA" \\
    --fqdn rangexdr.bakerstreetlabs.io \\
    --cert-name rangexdr-mgmt-https \\
    --permitted-ips 192.168.0.0/16

  # Generate with auto-generated cert name and no IP restrictions
  python generate_mgmt_cert.py \\
    --api-key YOUR_KEY \\
    --hostname 192.168.0.52 \\
    --ca-name "Baker Street Labs Issuing CA" \\
    --fqdn rangexdr.bakerstreetlabs.io

  # Dry run mode (validate only, don't commit)
  python generate_mgmt_cert.py \\
    --api-key YOUR_KEY \\
    --hostname rangexdr.bakerstreetlabs.io \\
    --ca-name "Baker Street Labs Issuing CA" \\
    --fqdn rangexdr.bakerstreetlabs.io \\
    --no-commit

WARNING - IMPORTANT:
  - Ensure the CA name exists on the firewall (check existing certificates first)
  - The CA must be capable of signing certificates (not just SSL decryption)
  - Management interface will use this certificate for HTTPS
  - Browser will trust cert only if CA is in browser's trust store
        '''
    )
    
    parser.add_argument(
        '--api-key',
        required=True,
        help='PAN-OS API key'
    )
    
    parser.add_argument(
        '--hostname',
        required=True,
        help='PAN-OS device hostname or IP address'
    )
    
    parser.add_argument(
        '--ca-name',
        required=True,
        help='Name of the existing intermediate CA on the firewall'
    )
    
    parser.add_argument(
        '--fqdn',
        required=True,
        help='FQDN for the certificate Subject Name (CN)'
    )
    
    parser.add_argument(
        '--cert-name',
        default=f'mgmt-cert-{uuid.uuid4().hex[:8]}',
        help='Name for the new certificate (default: mgmt-cert-<random>)'
    )
    
    parser.add_argument(
        '--profile-name',
        default='mgmt-profile-https',
        help='Name for the management profile (default: mgmt-profile-https)'
    )
    
    parser.add_argument(
        '--permitted-ips',
        nargs='*',
        help='List of permitted IP addresses/networks (e.g., 192.168.0.0/16 10.0.0.0/8)'
    )
    
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Generate certificate and profile but do NOT commit (for testing)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        print("=" * 70)
        print("PAN-OS Management Certificate Generator")
        print("=" * 70)
        print(f"Hostname: {args.hostname}")
        print(f"CA Name: {args.ca_name}")
        print(f"FQDN: {args.fqdn}")
        print(f"Certificate Name: {args.cert_name}")
        print(f"Profile Name: {args.profile_name}")
        print(f"Permitted IPs: {args.permitted_ips if args.permitted_ips else 'None (all IPs allowed)'}")
        print(f"Auto-Commit: {not args.no_commit}")
        print("=" * 70)
        print()

    # Step 1: Generate the certificate
    if not generate_certificate(args.api_key, args.hostname, args.ca_name, args.fqdn, args.cert_name):
        sys.exit(1)

    # Step 2: Create the management profile
    if not create_mgmt_profile(args.api_key, args.hostname, args.profile_name, args.cert_name, args.permitted_ips):
        sys.exit(1)

    # Step 3: Commit the configuration (unless --no-commit specified)
    if not args.no_commit:
        if not commit_config(args.api_key, args.hostname):
            sys.exit(1)
    else:
        print("\n[WARNING] Configuration NOT committed (--no-commit specified)")
        print("   To commit manually:")
        print(f"   1. Log in to https://{args.hostname}")
        print("   2. Review the candidate configuration")
        print("   3. Click 'Commit' to apply changes")

    print("\n" + "=" * 70)
    print("[OK] Management certificate deployment complete!")
    print("=" * 70)
    print(f"\nNext Steps:")
    print(f"  1. Access firewall at: https://{args.fqdn}")
    print(f"  2. Browser will show the new certificate")
    print(f"  3. Import 'Baker Street Labs Issuing CA' to browser trust store if needed")
    print(f"  4. Verify certificate chain is valid")
    
    sys.exit(0)

