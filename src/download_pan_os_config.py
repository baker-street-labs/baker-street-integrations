#!/usr/bin/env python3
"""
Download PAN-OS Configuration
Downloads the running configuration from a PAN-OS firewall using the API.

Usage:
    python download_pan_os_config.py --api-key YOUR_API_KEY --hostname 192.168.0.52 --output rangexdr_backup.xml

Author: Baker Street Labs
Date: October 22, 2025
"""

import argparse
import requests
import xml.etree.ElementTree as ET
import sys
from urllib.parse import urlencode
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_pan_os_config(api_key, hostname, output_file):
    """
    Downloads the running configuration from a PAN-OS device using the provided API key
    and saves it to the specified output file.

    Args:
        api_key (str): PAN-OS API key.
        hostname (str): Hostname or IP address of the PAN-OS device.
        output_file (str): Path to save the XML configuration file.

    Returns:
        bool: True if successful, False otherwise.
    """
    # Construct the API URL for getting the running configuration
    url = f"https://{hostname}/api/"
    params = {
        'type': 'config',
        'action': 'show',  # Use 'show' for running config, 'get' for candidate
        'key': api_key
    }

    print(f"Downloading configuration from {hostname}...")

    try:
        # Make the API request
        response = requests.get(url, params=urlencode(params), verify=False, timeout=30)
        response.raise_for_status()

        # Parse the response to ensure it's valid XML
        try:
            root = ET.fromstring(response.text)
            # Check if the API call was successful
            if root.get('status') != 'success':
                error_msg = root.find('.//msg')
                error_text = error_msg.text if error_msg is not None else "Unknown error"
                print(f"Error: API returned status '{root.get('status')}': {error_text}")
                return False
        except ET.ParseError as e:
            print(f"Error: Response is not valid XML: {e}")
            return False

        # Save the configuration to the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        file_size = len(response.text)
        print(f"✅ Configuration saved to {output_file}")
        print(f"   File size: {file_size:,} bytes")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching configuration: {e}")
        return False
    except IOError as e:
        print(f"❌ Error writing to file {output_file}: {e}")
        return False


if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Download PAN-OS running configuration using API key.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Download rangexdr configuration
  python download_pan_os_config.py --api-key YOUR_KEY --hostname 192.168.0.52 --output rangexdr_backup.xml
  
  # Download using credentials from .secrets file
  python download_pan_os_config.py --api-key $(cat ../../.secrets | grep PANOS_API_KEY | cut -d'=' -f2) \\
    --hostname rangexdr.bakerstreetlabs.io --output range_baseline.xml

Notes:
  - This script uses 'action=show' to download the running configuration
  - Use 'action=get' if you need the candidate configuration instead
  - API key can be generated via: https://<firewall>/api/?type=keygen&user=<username>&password=<password>
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
        help='PAN-OS device hostname or IP address (e.g., 192.168.0.52 or rangexdr.bakerstreetlabs.io)'
    )
    
    parser.add_argument(
        '--output',
        default='running-config.xml',
        help='Output file for the configuration (default: running-config.xml)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        print(f"API Key: {args.api_key[:20]}...")
        print(f"Hostname: {args.hostname}")
        print(f"Output: {args.output}")
        print()

    # Call the function to download the configuration
    success = get_pan_os_config(args.api_key, args.hostname, args.output)
    
    if success:
        print("\n🎯 Next Steps:")
        print("  1. Review the downloaded configuration")
        print("  2. Use create_range_ngfw.py to generate new range configs")
        print("  3. Use upload_pan_os_config.py to deploy to target firewall")
    
    sys.exit(0 if success else 1)

