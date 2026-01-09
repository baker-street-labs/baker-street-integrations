#!/usr/bin/env python3
"""
Configure PAN-OS Service Routes for All Baker Street Labs Firewalls

Configures service routes to ensure PAN-OS services route via public interface.
Required for licensing, updates, and cloud services.

Service domains:
- api.paloaltonetworks.com
- apitrusted.paloaltonetworks.com
- lic.lc.prod.us.cs.paloaltonetworks.com

Author: Baker Street Labs
Date: October 22, 2025
"""

import argparse
import requests
import urllib3
from xml.etree import ElementTree as ET
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FIREWALLS = {
    "rangexdr": {"fqdn": "rangexdr.bakerstreetlabs.io", "ip": "192.168.0.52"},
    "rangeplatform": {"fqdn": "rangeplatform.bakerstreetlabs.io", "ip": "192.168.0.68"},
    "rangeagentix": {"fqdn": "rangeagentix.bakerstreetlabs.io", "ip": "192.168.0.64"},
    "rangelande": {"fqdn": "rangelande.bakerstreetlabs.io", "ip": "192.168.0.67"},
    "rangexsiam": {"fqdn": "rangexsiam.bakerstreetlabs.io", "ip": "192.168.0.62"},
}

def configure_service_routes(hostname, api_key, dry_run=False):
    """
    Configure service routes on PAN-OS firewall
    
    Args:
        hostname: Firewall FQDN or IP
        api_key: PAN-OS API key
        dry_run: If True, show what would be done without making changes
        
    Returns:
        bool: True if successful, False otherwise
    """
    if dry_run:
        print(f"[DRY-RUN] Would configure service routes on {hostname}")
        return True
    
    url = f"https://{hostname}/api/"
    
    # XML to configure service routes
    service_route_xml = """
    <update-server>
      <source-interface>ethernet1/1</source-interface>
    </update-server>
    <license-api>
      <source-interface>ethernet1/1</source-interface>
    </license-api>
    <content-update>
      <source-interface>ethernet1/1</source-interface>
    </content-update>
    """
    
    params = {
        'type': 'config',
        'action': 'set',
        'xpath': '/config/devices/entry[@name="localhost.localdomain"]/deviceconfig/system/service',
        'element': service_route_xml,
        'key': api_key
    }
    
    try:
        response = requests.post(url, data=params, verify=False, timeout=30)
        root = ET.fromstring(response.text)
        
        if root.get('status') == 'success':
            print(f"[OK] Service routes configured on {hostname}")
            return True
        else:
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else 'Unknown error'
            print(f"[ERROR] Failed on {hostname}: {error_text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[WARNING] Could not connect to {hostname} - firewall may be offline")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed to {hostname}: {e}")
        return False

def commit_config(hostname, api_key, dry_run=False):
    """
    Commit configuration changes
    
    Args:
        hostname: Firewall FQDN or IP
        api_key: PAN-OS API key
        dry_run: If True, skip commit
        
    Returns:
        bool: True if successful, False otherwise
    """
    if dry_run:
        print(f"[DRY-RUN] Would commit configuration on {hostname}")
        return True
    
    url = f"https://{hostname}/api/"
    
    params = {
        'type': 'commit',
        'cmd': '<commit></commit>',
        'key': api_key
    }
    
    try:
        response = requests.post(url, data=params, verify=False, timeout=30)
        root = ET.fromstring(response.text)
        
        if root.get('status') == 'success':
            job_id = root.find('.//job').text if root.find('.//job') is not None else 'N/A'
            print(f"[OK] Commit initiated on {hostname} (Job ID: {job_id})")
            return True
        else:
            error_msg = root.find('.//msg')
            error_text = error_msg.text if error_msg is not None else 'Unknown error'
            print(f"[ERROR] Commit failed on {hostname}: {error_text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[WARNING] Could not connect to {hostname} - firewall may be offline")
        return False
    except Exception as e:
        print(f"[ERROR] Commit failed on {hostname}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Configure service routes on all Baker Street Labs firewalls',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Service domains configured:
  - api.paloaltonetworks.com
  - apitrusted.paloaltonetworks.com
  - lic.lc.prod.us.cs.paloaltonetworks.com
  
All services will route via ethernet1/1 (Public/WAN interface)

Examples:
  python configure-service-routes.py --api-key YOUR_KEY --dry-run
  python configure-service-routes.py --api-key YOUR_KEY
  python configure-service-routes.py --api-key YOUR_KEY --skip-commit
        """
    )
    parser.add_argument('--api-key', required=True, help='PAN-OS API key')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--skip-commit', action='store_true', help='Configure but do not commit')
    parser.add_argument('--firewall', help='Configure only specific firewall (e.g., rangexdr)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PAN-OS Service Route Configuration")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("[DRY-RUN MODE] No changes will be made")
        print()
    
    # Filter firewalls if specific one requested
    if args.firewall:
        if args.firewall not in FIREWALLS:
            print(f"[ERROR] Unknown firewall: {args.firewall}")
            print(f"Valid options: {', '.join(FIREWALLS.keys())}")
            sys.exit(1)
        firewalls_to_configure = {args.firewall: FIREWALLS[args.firewall]}
    else:
        firewalls_to_configure = FIREWALLS
    
    print(f"Configuring {len(firewalls_to_configure)} firewall(s)...")
    print()
    
    success_count = 0
    total_count = len(firewalls_to_configure)
    
    for name, details in firewalls_to_configure.items():
        print(f"[{name}] Configuring {details['fqdn']} ({details['ip']})...")
        
        if configure_service_routes(details['fqdn'], args.api_key, args.dry_run):
            success_count += 1
            
            if not args.skip_commit and not args.dry_run:
                commit_config(details['fqdn'], args.api_key, args.dry_run)
        
        print()
    
    print("=" * 80)
    print(f"Configuration Summary: {success_count}/{total_count} firewalls configured")
    print("=" * 80)
    print()
    
    if success_count == total_count:
        print("[SUCCESS] All firewalls configured successfully")
    elif success_count > 0:
        print(f"[PARTIAL] {success_count} of {total_count} firewalls configured")
    else:
        print("[FAILED] No firewalls were configured")
        sys.exit(1)
    
    print()
    print("Service routes configured for:")
    print("  - api.paloaltonetworks.com")
    print("  - apitrusted.paloaltonetworks.com")
    print("  - lic.lc.prod.us.cs.paloaltonetworks.com")
    print()
    print("All PAN-OS services will now route via ethernet1/1 (Public interface)")
    print()

if __name__ == '__main__':
    main()

