#!/usr/bin/env python3
"""
Create WinRM NAT Rules for Range XDR Firewall
Safely creates NAT rules following established RDP pattern

Author: Baker Street Labs
Date: October 22, 2025
"""

import argparse
import requests
import xml.etree.ElementTree as ET
import sys
import time
from urllib.parse import urlencode
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PANOSNATManager:
    def __init__(self, hostname, api_key):
        self.hostname = hostname
        self.api_key = api_key
        self.base_url = f"https://{hostname}/api/"
        
    def _make_request(self, params, method='GET'):
        """Make API request with error handling"""
        try:
            if method == 'GET':
                response = requests.get(self.base_url, params=params, verify=False, timeout=30)
            else:
                response = requests.post(self.base_url, data=params, verify=False, timeout=30)
            
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None
    
    def validate_connection(self):
        """Test API connectivity"""
        print(f"Testing connection to {self.hostname}...")
        params = {'type': 'op', 'cmd': 'show system info', 'key': self.api_key}
        response = self._make_request(params)
        if response and 'success' in response:
            print("[OK] Connection successful")
            return True
        else:
            print("[ERROR] Connection failed")
            return False
    
    def get_existing_nat_rules(self):
        """Get current NAT rules to avoid conflicts"""
        print("Retrieving existing NAT rules...")
        params = {
            'type': 'config',
            'action': 'get',
            'xpath': "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules",
            'key': self.api_key
        }
        response = self._make_request(params)
        if response:
            try:
                root = ET.fromstring(response)
                rules = root.findall('.//entry')
                existing_names = [rule.get('name') for rule in rules if rule.get('name')]
                print(f"[OK] Found {len(existing_names)} existing NAT rules")
                return existing_names
            except ET.ParseError:
                print("[ERROR] Failed to parse NAT rules response")
                return []
        return []
    
    def create_service_object(self, name, port):
        """Create service object for WinRM port"""
        print(f"Creating service object: {name} (port {port})")
        
        # Check if service already exists
        params = {
            'type': 'config',
            'action': 'get',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service/entry[@name='{name}']",
            'key': self.api_key
        }
        response = self._make_request(params)
        if response and 'entry' in response:
            print(f"[WARNING] Service {name} already exists, skipping")
            return True
        
        # Create service object
        service_xml = f"""
        <entry name="{name}">
            <protocol>
                <tcp>
                    <port>{port}</port>
                    <override>
                        <no/>
                    </override>
                </tcp>
            </protocol>
        </entry>
        """
        
        params = {
            'type': 'config',
            'action': 'set',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service/entry[@name='{name}']",
            'element': service_xml,
            'key': self.api_key
        }
        
        response = self._make_request(params, 'POST')
        if response and 'success' in response:
            print(f"[OK] Service object {name} created")
            return True
        else:
            print(f"[ERROR] Failed to create service object {name}")
            return False
    
    def create_nat_rule(self, rule_name, service_name, target_address, target_port):
        """Create NAT rule for WinRM access"""
        print(f"Creating NAT rule: {rule_name}")
        
        # Check if NAT rule already exists
        params = {
            'type': 'config',
            'action': 'get',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules/entry[@name='{rule_name}']",
            'key': self.api_key
        }
        response = self._make_request(params)
        if response and 'entry' in response:
            print(f"[WARNING] NAT rule {rule_name} already exists, skipping")
            return True
        
        # Create NAT rule XML
        nat_xml = f"""
        <entry name="{rule_name}">
            <destination-translation>
                <translated-port>{target_port}</translated-port>
                <translated-address>{target_address}</translated-address>
            </destination-translation>
            <to>
                <member>Public</member>
            </to>
            <from>
                <member>Infrastructure</member>
            </from>
            <source>
                <member>any</member>
            </source>
            <destination>
                <member>Public RDP Service</member>
            </destination>
            <tag>
                <member>Services</member>
                <member>Inbound</member>
            </tag>
            <service>{service_name}</service>
            <to-interface>ethernet1/1</to-interface>
            <group-tag>Inbound</group-tag>
        </entry>
        """
        
        params = {
            'type': 'config',
            'action': 'set',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules/entry[@name='{rule_name}']",
            'element': nat_xml,
            'key': self.api_key
        }
        
        response = self._make_request(params, 'POST')
        if response and 'success' in response:
            print(f"[OK] NAT rule {rule_name} created")
            return True
        else:
            print(f"[ERROR] Failed to create NAT rule {rule_name}")
            return False
    
    def create_security_policy(self):
        """Create security policy for WinRM services"""
        print("Creating WinRM security policy...")
        
        # Check if security policy already exists
        params = {
            'type': 'config',
            'action': 'get',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules/entry[@name='WinRM Services']",
            'key': self.api_key
        }
        response = self._make_request(params)
        if response and 'entry' in response:
            print("[WARNING] WinRM security policy already exists, skipping")
            return True
        
        # Create security policy XML
        security_xml = """
        <entry name="WinRM Services">
            <to>
                <member>Infrastructure</member>
            </to>
            <from>
                <member>Public</member>
            </from>
            <source>
                <member>DirtyNet</member>
            </source>
            <destination>
                <member>RDP Services Group</member>
            </destination>
            <source-user>
                <member>any</member>
            </source-user>
            <category>
                <member>any</member>
            </category>
            <application>
                <member>ms-rdp</member>
            </application>
            <service>
                <member>Range XDR WinRM 59801</member>
                <member>Range XDR WinRM 59802</member>
                <member>Range XDR WinRM 59803</member>
                <member>Range XDR WinRM 59805</member>
                <member>Range XDR WinRM 59806</member>
                <member>Range XDR WinRM 59807</member>
                <member>Range XDR WinRM 59808</member>
            </service>
            <source-hip>
                <member>any</member>
            </source-hip>
            <destination-hip>
                <member>any</member>
            </destination-hip>
            <action>allow</action>
        </entry>
        """
        
        params = {
            'type': 'config',
            'action': 'set',
            'xpath': f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules/entry[@name='WinRM Services']",
            'element': security_xml,
            'key': self.api_key
        }
        
        response = self._make_request(params, 'POST')
        if response and 'success' in response:
            print("[OK] WinRM security policy created")
            return True
        else:
            print("[ERROR] Failed to create WinRM security policy")
            return False
    
    def commit_changes(self):
        """Commit configuration changes"""
        print("Committing configuration changes...")
        params = {
            'type': 'commit',
            'cmd': '<commit></commit>',
            'key': self.api_key
        }
        response = self._make_request(params, 'POST')
        if response and 'success' in response:
            print("[OK] Configuration committed successfully")
            return True
        else:
            print("[ERROR] Failed to commit configuration")
            return False

def main():
    parser = argparse.ArgumentParser(description='Create WinRM NAT rules for Range XDR firewall')
    parser.add_argument('--hostname', default='rangexdr.bakerstreetlabs.io', help='Firewall hostname')
    parser.add_argument('--api-key', required=True, help='PAN-OS API key')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')
    parser.add_argument('--skip-commit', action='store_true', help='Create rules but skip commit')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Range XDR WinRM NAT Rules Creator")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()
    
    # Initialize NAT manager
    nat_manager = PANOSNATManager(args.hostname, args.api_key)
    
    # Test connection
    if not args.dry_run and not nat_manager.validate_connection():
        print("❌ Cannot connect to firewall. Exiting.")
        sys.exit(1)
    
    # Define WinRM NAT mappings
    winrm_mappings = [
        ("WinRM AD 01", "Range XDR WinRM 59801", 59801, "Range XDR AD01", 5985),
        ("WinRM AD 02", "Range XDR WinRM 59802", 59802, "Range XDR AD02", 5985),
        ("WinRM WinSrv", "Range XDR WinRM 59803", 59803, "Range Windows Services", 5985),
        ("WinRM Sherlock", "Range XDR WinRM 59805", 59805, "Range XDR Client Sherlock", 5985),
        ("WinRM Watson", "Range XDR WinRM 59806", 59806, "Range XDR Client Watson", 5985),
        ("WinRM Irene", "Range XDR WinRM 59807", 59807, "Range XDR Client Irene", 5985),
        ("WinRM Lestrade", "Range XDR WinRM 59808", 59808, "Range XDR Client Lestrade", 5985),
    ]
    
    print("WinRM NAT Mappings:")
    for rule_name, service_name, port, target, target_port in winrm_mappings:
        print(f"  {rule_name}: {args.hostname}:{port} -> {target}:{target_port}")
    print()
    
    if args.dry_run:
        print("[OK] Dry run complete - no changes made")
        return
    
    # Get existing rules to check for conflicts
    existing_rules = nat_manager.get_existing_nat_rules()
    
    success_count = 0
    total_count = len(winrm_mappings) + 1  # +1 for security policy
    
    # Create service objects
    print("Creating service objects...")
    for rule_name, service_name, port, target, target_port in winrm_mappings:
        if nat_manager.create_service_object(service_name, port):
            success_count += 1
    
    # Create NAT rules
    print("\nCreating NAT rules...")
    for rule_name, service_name, port, target, target_port in winrm_mappings:
        if nat_manager.create_nat_rule(rule_name, service_name, target, target_port):
            success_count += 1
    
    # Create security policy
    print("\nCreating security policy...")
    if nat_manager.create_security_policy():
        success_count += 1
    
    # Commit changes
    if not args.skip_commit and success_count == total_count:
        print("\nCommitting changes...")
        if nat_manager.commit_changes():
            print("\n[OK] WinRM NAT rules created and committed successfully!")
        else:
            print("\n[WARNING] Rules created but commit failed")
    elif args.skip_commit:
        print("\n[WARNING] Rules created but not committed (use --skip-commit)")
    else:
        print(f"\n[WARNING] Only {success_count}/{total_count} operations succeeded")
    
    print("\n" + "=" * 80)
    print("WinRM Access Ready")
    print("=" * 80)
    print()
    print("Access examples:")
    print("  AD01:  Invoke-Command -ComputerName 192.168.255.250 -Port 59801 -Credential $cred")
    print("  AD02:  Invoke-Command -ComputerName 192.168.255.250 -Port 59802 -Credential $cred")
    print("  WinSrv: Invoke-Command -ComputerName 192.168.255.250 -Port 59803 -Credential $cred")
    print()

if __name__ == '__main__':
    main()
