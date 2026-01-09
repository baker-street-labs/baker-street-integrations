#!/usr/bin/env python3
"""
Upload PAN-OS Configuration
Uploads a configuration file to a PAN-OS firewall, loads it, and commits it.

⚠️  WARNING: This will overwrite the firewall configuration!
    Always backup the current configuration first using download_pan_os_config.py

Usage:
    python upload_pan_os_config.py --api-key YOUR_API_KEY --hostname 192.168.0.52 --config-file rangexsiam.xml

Author: Baker Street Labs
Date: October 22, 2025
"""

import argparse
import requests
import xml.etree.ElementTree as ET
import sys
from urllib.parse import urlencode
import time
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def upload_config(api_key, hostname, config_file):
    """
    Uploads a PAN-OS configuration file to the device.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.
        config_file (str): Path to the XML configuration file to upload.

    Returns:
        bool: True if upload is successful, False otherwise.
    """
    url = f"https://{hostname}/api/"
    
    # Note: PAN-OS API doesn't use 'target' for file uploads
    # The file is uploaded to a specific location and then loaded
    params = {
        'type': 'import',
        'category': 'configuration',
        'key': api_key
    }

    try:
        # Read the configuration file
        with open(config_file, 'r', encoding='utf-8') as f:
            config_content = f.read()

        # Verify it's valid XML
        try:
            ET.fromstring(config_content)
        except ET.ParseError as e:
            print(f"❌ Error: Configuration file is not valid XML: {e}")
            return False

        print(f"Uploading configuration from {config_file}...")

        # Upload the configuration
        files = {'file': (config_file, config_content, 'application/xml')}
        response = requests.post(url, params=urlencode(params), files=files, verify=False, timeout=60)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"❌ Error uploading configuration: {error_text}")
            return False

        print("✅ Configuration uploaded successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error uploading configuration: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Error: Configuration file {config_file} not found")
        return False
    except IOError as e:
        print(f"❌ Error reading configuration file: {e}")
        return False


def load_config(api_key, hostname, config_name):
    """
    Loads the uploaded configuration into the candidate configuration.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.
        config_name (str): Name of the configuration to load (e.g., 'rangexsiam.xml').

    Returns:
        bool: True if load is successful, False otherwise.
    """
    url = f"https://{hostname}/api/"
    
    # Load the configuration from the uploaded file
    load_cmd = f'<load><config><from>{config_name}</from></config></load>'
    params = {
        'type': 'op',
        'cmd': load_cmd,
        'key': api_key
    }

    print(f"Loading configuration {config_name} into candidate...")

    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=60)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"❌ Error loading configuration: {error_text}")
            return False

        print("✅ Configuration loaded into candidate successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error loading configuration: {e}")
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
    print("⏳ This may take 30-60 seconds...")

    try:
        response = requests.get(url, params=urlencode(params), verify=False, timeout=120)
        response.raise_for_status()

        # Check if the response indicates success
        root = ET.fromstring(response.text)
        if root.get('status') != 'success':
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else "Unknown error"
            print(f"❌ Error committing configuration: {error_text}")
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
                    print("❌ Error: Could not retrieve job status")
                    return False
                
                job_status = job_status_elem.text
                progress_elem = status_root.find('.//progress')
                progress = progress_elem.text if progress_elem is not None else "0"
                
                print(f"   Progress: {progress}% ({job_status})", end='\r')
                
                if job_status == 'FIN':
                    result_elem = status_root.find('.//result')
                    if result_elem is not None and result_elem.text == 'OK':
                        print("\n✅ Configuration committed successfully")
                        return True
                    else:
                        details_elem = status_root.find('.//details')
                        details = details_elem.text if details_elem is not None else "Unknown error"
                        print(f"\n❌ Commit failed: {details}")
                        return False
                
                time.sleep(2)  # Wait before polling again
        else:
            # No job ID means instant commit (rare)
            print("✅ Configuration committed successfully")
            return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error committing configuration: {e}")
        return False


if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Upload, load, and commit a PAN-OS configuration using API key.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Upload rangexsiam configuration to a firewall
  python upload_pan_os_config.py --api-key YOUR_KEY --hostname 192.168.0.53 --config-file rangexsiam.xml
  
  # Upload without auto-commit (safer for testing)
  python upload_pan_os_config.py --api-key YOUR_KEY --hostname 192.168.0.53 \\
    --config-file rangexsiam.xml --no-commit

⚠️  WARNING:
  - This will OVERWRITE the firewall configuration!
  - ALWAYS backup the current config first using download_pan_os_config.py
  - Test in a lab environment before production deployment
  - The firewall may become unreachable during commit if network config changes

Workflow:
  1. Download current config: download_pan_os_config.py --api-key KEY --hostname FW --output backup.xml
  2. Create new config: create_range_ngfw.py --range-name rangexsiam --third-octet 30 --vlan-base 3000
  3. Upload new config: upload_pan_os_config.py --api-key KEY --hostname FW --config-file rangexsiam.xml
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
        '--config-file',
        required=True,
        help='Path to the XML configuration file to upload'
    )
    
    parser.add_argument(
        '--config-name',
        default=None,
        help='Name to save the config as on device (default: basename of config-file)'
    )
    
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Upload and load config but do NOT commit (for testing)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Determine config name on device
    if args.config_name is None:
        import os
        args.config_name = os.path.basename(args.config_file)

    if args.verbose:
        print(f"API Key: {args.api_key[:20]}...")
        print(f"Hostname: {args.hostname}")
        print(f"Config File: {args.config_file}")
        print(f"Config Name: {args.config_name}")
        print(f"Auto-Commit: {not args.no_commit}")
        print()

    print("=" * 70)
    print("WARNING: PAN-OS Configuration Upload")
    print("=" * 70)
    print(f"Target Firewall: {args.hostname}")
    print(f"Config File: {args.config_file}")
    print(f"Auto-Commit: {not args.no_commit}")
    print("=" * 70)
    print()

    # Step 1: Upload the configuration
    if not upload_config(args.api_key, args.hostname, args.config_file):
        sys.exit(1)

    # Step 2: Load the configuration
    if not load_config(args.api_key, args.hostname, args.config_name):
        sys.exit(1)

    # Step 3: Commit the configuration (unless --no-commit specified)
    if not args.no_commit:
        if not commit_config(args.api_key, args.hostname):
            sys.exit(1)
    else:
        print("\n⚠️  Configuration loaded but NOT committed (--no-commit specified)")
        print("   To commit manually:")
        print(f"   1. Log in to https://{args.hostname}")
        print("   2. Review the candidate configuration")
        print("   3. Click 'Commit' to apply changes")

    print("\n" + "=" * 70)
    print("✅ Configuration deployment complete!")
    print("=" * 70)
    
    sys.exit(0)


