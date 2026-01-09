#!/usr/bin/env python3
"""
PAN-OS Configuration Parser - Address Objects
Baker Street Labs - Range Prep Tool

Purpose: Parse PAN-OS XML configuration and extract address objects to JSON
Usage: python parse_pan_os_addresses.py <path_to_xml_config>
Output: JSON dictionary of all address objects

Context7 MCP Validation: Oct 21, 2025
- Query: Python XML parsing with ElementTree
- Result: Standard library ElementTree is appropriate for XML parsing
- Validation: Code structure follows Python best practices
"""

import xml.etree.ElementTree as ET
import json
import sys
from pathlib import Path


def parse_pan_os_addresses(xml_file):
    """
    Parses a PAN-OS XML configuration file and extracts all address objects into a JSON-compatible dictionary.
    
    Address objects are found under //address/entry in the XML structure.
    Each address object includes name, type (e.g., ip-netmask, fqdn), value, description, and tags if present.
    
    Args:
        xml_file (str): Path to the PAN-OS XML configuration file.
    
    Returns:
        dict: A dictionary where keys are address object names and values are details dictionaries.
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[ERROR] XML parsing failed: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {xml_file}", file=sys.stderr)
        sys.exit(1)
    
    addresses = {}
    
    # Find all address entries in the config (handles shared and vsys scopes)
    for addr_entry in root.findall('.//address/entry'):
        name = addr_entry.get('name')
        if not name:
            continue  # Skip if no name
        
        addr_details = {
            'name': name,
            'type': None,
            'value': None,
            'description': None,
            'tags': []
        }
        
        # Extract child elements
        for child in addr_entry:
            if child.tag in ['ip-netmask', 'ip-range', 'ip-wildcard', 'fqdn']:
                addr_details['type'] = child.tag
                addr_details['value'] = child.text.strip() if child.text else None
            elif child.tag == 'description':
                addr_details['description'] = child.text.strip() if child.text else None
            elif child.tag == 'tag':
                # Tags are under <tag><member>tag1</member>...</tag>
                addr_details['tags'] = [member.text.strip() for member in child.findall('member') if member.text]
        
        addresses[name] = addr_details
    
    return addresses


def main():
    """Main execution function"""
    if len(sys.argv) != 2:
        print("Usage: python parse_pan_os_addresses.py <path_to_xml_config>")
        print("\nExample:")
        print("  python parse_pan_os_addresses.py range_baseline.xml")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    
    # Validate file exists
    if not Path(xml_file).exists():
        print(f"[ERROR] File not found: {xml_file}")
        sys.exit(1)
    
    print(f"[INFO] Parsing PAN-OS configuration: {xml_file}")
    
    # Parse addresses
    addresses = parse_pan_os_addresses(xml_file)
    
    print(f"[INFO] Found {len(addresses)} address objects")
    
    # Output as JSON
    json_output = json.dumps(addresses, indent=4, sort_keys=True)
    print(json_output)
    
    # Also save to file
    output_file = "baseline_objects.json"
    with open(output_file, 'w') as f:
        f.write(json_output)
    
    print(f"\n[SUCCESS] Address objects saved to: {output_file}", file=sys.stderr)
    print(f"[INFO] Total objects: {len(addresses)}", file=sys.stderr)


if __name__ == '__main__':
    main()

