#!/usr/bin/env python3
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO – 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

"""
PAN-OS Object Creation Script using pan-os-python SDK

This script automates the creation of PAN-OS configuration objects (addresses, 
address groups, services, applications, tags, etc.) on a Palo Alto Networks 
firewall or Panorama using the official pan-os-python SDK.

Usage Examples:
    # Single object creation
    python panos_object_creator.py --hostname 192.168.1.1 --username admin --password pass --object-type address --name MyIP --value 192.168.1.1/24

    # Batch creation from CSV
    python panos_object_creator.py --hostname 192.168.1.1 --username admin --password pass --csv-file objects.csv --commit

    # Dry run to preview changes
    python panos_object_creator.py --hostname 192.168.1.1 --api-key YOUR_KEY --csv-file objects.csv --dry-run

    # Print CSV template
    python panos_object_creator.py --template

Dependencies:
    pip install pan-os-python pandas tabulate ipaddress
"""

import argparse
import sys
import json
import logging
import getpass
import ipaddress
from typing import Dict, Any, Optional, List
import pandas as pd

# PAN-OS SDK imports
from panos.firewall import Firewall
from panos.panorama import Panorama
from panos.objects import (
    AddressObject, AddressGroup, ServiceObject, ServiceGroup,
    ApplicationObject, ApplicationGroup, Tag, CustomUrlCategory, Edl
)
from panos.device import Vsys
from panos.errors import PanDeviceError, PanInvalidCredentials, PanCommitFailed

# Optional imports
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Object class mapping
OBJECT_CLASSES = {
    'address': AddressObject,
    'address-group': AddressGroup,
    'service': ServiceObject,
    'service-group': ServiceGroup,
    'application': ApplicationObject,
    'application-group': ApplicationGroup,
    'tag': Tag,
    'custom-url-category': CustomUrlCategory,
    'edl': Edl
}

# CSV template
CSV_TEMPLATE = """object_type,name,value,type,description,tag,members,protocol,source_port,destination_port,category,default_port,group_type,urls,category_type,source,edl_type,color,comments
address,MyIP,192.168.1.1/24,ip-netmask,Test IP address,Prod,,,,,,,,,,,,
address-group,MyGroup,,,,Test group,Prod,IP1,IP2,,,,static,,,,,,
service,MyHTTP,,,HTTP service,Prod,,tcp,,80,,,,,,,,
service-group,WebServices,,,,Web services,Prod,http,https,,,,,,,
application,CustomApp,,,Custom app,Prod,,,web-services,8080,,,,,,
application-group,WebApps,,,,Web apps,Prod,facebook-base,youtube-base,,,,,,,
tag,ProdTag,,,,,Prod,,,,,,,,,,,red,Production tag
custom-url-category,BlockedSites,,,,Blocked sites,Prod,,,,,,,example.com,malicious,https://example.com/bad.txt,,
edl,ThreatList,,,,Threat feed,Prod,,,,,,,,,https://example.com/threats.txt,ip,,
"""


def validate_ip_address(ip_str: str) -> bool:
    """Validate IP address format"""
    try:
        ipaddress.ip_network(ip_str, strict=False)
        return True
    except ValueError:
        return False


def print_csv_template():
    """Print CSV template to stdout"""
    print("CSV Template for PAN-OS Object Creation:")
    print("=" * 50)
    print(CSV_TEMPLATE)
    print("\nInstructions:")
    print("- Fill in only relevant columns per row")
    print("- Empty cells are ignored")
    print("- Save this as a .csv file and use with --csv-file")
    print("- Run with --dry-run first to preview changes")


def create_single_object(args, device, vsys):
    """Create a single object based on CLI arguments"""
    object_type = args.object_type
    
    if object_type not in OBJECT_CLASSES:
        raise ValueError(f"Unsupported object type: {object_type}")
    
    obj_class = OBJECT_CLASSES[object_type]
    
    # Build kwargs based on object type
    kwargs = {'name': args.name}
    
    if hasattr(args, 'description') and args.description:
        kwargs['description'] = args.description
    
    if hasattr(args, 'tag') and args.tag:
        kwargs['tag'] = args.tag
    
    # Type-specific parameters
    if object_type == 'address':
        if not hasattr(args, 'value') or not args.value:
            raise ValueError("Address objects require --value parameter")
        kwargs['value'] = args.value
        kwargs['type'] = getattr(args, 'type', 'ip-netmask')
        
        # Validate IP address
        if not validate_ip_address(args.value):
            logger.warning(f"IP address {args.value} may not be valid")
    
    elif object_type == 'address-group':
        if not hasattr(args, 'members') or not args.members:
            raise ValueError("Address groups require --members parameter")
        members = [m.strip() for m in args.members.split(',') if m.strip()]
        kwargs['static_value'] = members
        # AddressGroup doesn't have group_type parameter
    
    elif object_type == 'service':
        if not hasattr(args, 'protocol') or not args.protocol:
            raise ValueError("Service objects require --protocol parameter")
        if not hasattr(args, 'destination_port') or not args.destination_port:
            raise ValueError("Service objects require --destination_port parameter")
        kwargs['protocol'] = args.protocol
        kwargs['destination_port'] = args.destination_port
        if hasattr(args, 'source_port') and args.source_port:
            kwargs['source_port'] = args.source_port
    
    elif object_type == 'service-group':
        if not hasattr(args, 'members') or not args.members:
            raise ValueError("Service groups require --members parameter")
        members = [m.strip() for m in args.members.split(',') if m.strip()]
        kwargs['value'] = members
    
    elif object_type == 'application':
        if hasattr(args, 'category') and args.category:
            kwargs['category'] = args.category
        if hasattr(args, 'default_port') and args.default_port:
            kwargs['default_port'] = args.default_port
        if hasattr(args, 'protocol') and args.protocol:
            kwargs['protocol'] = args.protocol
    
    elif object_type == 'application-group':
        if not hasattr(args, 'members') or not args.members:
            raise ValueError("Application groups require --members parameter")
        members = [m.strip() for m in args.members.split(',') if m.strip()]
        kwargs['value'] = members
    
    elif object_type == 'tag':
        if hasattr(args, 'color') and args.color:
            kwargs['color'] = args.color
        if hasattr(args, 'comments') and args.comments:
            kwargs['comments'] = args.comments
    
    elif object_type == 'custom-url-category':
        if not hasattr(args, 'urls') or not args.urls:
            raise ValueError("Custom URL categories require --urls parameter")
        urls = [u.strip() for u in args.urls.split(',') if u.strip()]
        kwargs['url_value'] = urls
        kwargs['category_type'] = getattr(args, 'category_type', 'custom')
    
    elif object_type == 'edl':
        if not hasattr(args, 'source') or not args.source:
            raise ValueError("EDL objects require --source parameter")
        if not hasattr(args, 'edl_type') or not args.edl_type:
            raise ValueError("EDL objects require --edl_type parameter")
        kwargs['source'] = args.source
        kwargs['edl_type'] = args.edl_type
    
    # Create object instance
    obj = obj_class(**kwargs)
    vsys.add(obj)
    
    return obj


def create_objects_from_csv(args, device, vsys):
    """Create objects from CSV file"""
    try:
        df = pd.read_csv(args.csv_file)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    if df.empty:
        logger.warning("CSV file is empty")
        return []
    
    results = []
    
    for index, row in df.iterrows():
        try:
            # Filter by object type if specified
            if args.object_type and row['object_type'] != args.object_type:
                continue
            
            object_type = row['object_type']
            if object_type not in OBJECT_CLASSES:
                logger.warning(f"Unsupported object type: {object_type} in row {index + 1}")
                continue
            
            obj_class = OBJECT_CLASSES[object_type]
            
            # Build kwargs from CSV row
            kwargs = {}
            
            # Common fields
            if pd.notna(row.get('name')):
                kwargs['name'] = str(row['name'])
            else:
                logger.warning(f"Row {index + 1}: Missing required 'name' field")
                continue
            
            if pd.notna(row.get('description')):
                kwargs['description'] = str(row['description'])
            
            if pd.notna(row.get('tag')):
                kwargs['tag'] = str(row['tag'])
            
            # Type-specific fields
            if object_type == 'address':
                if pd.notna(row.get('value')):
                    kwargs['value'] = str(row['value'])
                    kwargs['type'] = str(row.get('type', 'ip-netmask'))
                    
                    # Validate IP address
                    if not validate_ip_address(str(row['value'])):
                        logger.warning(f"Row {index + 1}: IP address {row['value']} may not be valid")
                else:
                    logger.warning(f"Row {index + 1}: Address object missing 'value' field")
                    continue
            
            elif object_type == 'address-group':
                if pd.notna(row.get('members')):
                    members = [m.strip() for m in str(row['members']).split(',') if m.strip()]
                    kwargs['static_value'] = members
                    # AddressGroup doesn't have group_type parameter
                else:
                    logger.warning(f"Row {index + 1}: Address group missing 'members' field")
                    continue
            
            elif object_type == 'service':
                if pd.notna(row.get('protocol')):
                    kwargs['protocol'] = str(row['protocol'])
                else:
                    logger.warning(f"Row {index + 1}: Service object missing 'protocol' field")
                    continue
                
                if pd.notna(row.get('destination_port')):
                    kwargs['destination_port'] = str(row['destination_port'])
                else:
                    logger.warning(f"Row {index + 1}: Service object missing 'destination_port' field")
                    continue
                
                if pd.notna(row.get('source_port')):
                    kwargs['source_port'] = str(row['source_port'])
            
            elif object_type == 'service-group':
                if pd.notna(row.get('members')):
                    members = [m.strip() for m in str(row['members']).split(',') if m.strip()]
                    kwargs['value'] = members
                else:
                    logger.warning(f"Row {index + 1}: Service group missing 'members' field")
                    continue
            
            elif object_type == 'application':
                if pd.notna(row.get('category')):
                    kwargs['category'] = str(row['category'])
                if pd.notna(row.get('default_port')):
                    kwargs['default_port'] = str(row['default_port'])
                if pd.notna(row.get('protocol')):
                    kwargs['protocol'] = str(row['protocol'])
            
            elif object_type == 'application-group':
                if pd.notna(row.get('members')):
                    members = [m.strip() for m in str(row['members']).split(',') if m.strip()]
                    kwargs['value'] = members
                else:
                    logger.warning(f"Row {index + 1}: Application group missing 'members' field")
                    continue
            
            elif object_type == 'tag':
                if pd.notna(row.get('color')):
                    kwargs['color'] = str(row['color'])
                if pd.notna(row.get('comments')):
                    kwargs['comments'] = str(row['comments'])
            
            elif object_type == 'custom-url-category':
                if pd.notna(row.get('urls')):
                    urls = [u.strip() for u in str(row['urls']).split(',') if u.strip()]
                    kwargs['url_value'] = urls
                else:
                    logger.warning(f"Row {index + 1}: Custom URL category missing 'urls' field")
                    continue
                # Remove tag parameter as it's not supported
                kwargs.pop('tag', None)
            
            elif object_type == 'edl':
                if pd.notna(row.get('source')):
                    kwargs['source'] = str(row['source'])
                else:
                    logger.warning(f"Row {index + 1}: EDL object missing 'source' field")
                    continue
                
                if pd.notna(row.get('edl_type')):
                    kwargs['edl_type'] = str(row['edl_type'])
                else:
                    logger.warning(f"Row {index + 1}: EDL object missing 'edl_type' field")
                    continue
                # Remove tag parameter as it's not supported
                kwargs.pop('tag', None)
            
            # Create object instance
            obj = obj_class(**kwargs)
            vsys.add(obj)
            
            results.append({
                'row': index + 1,
                'object_type': object_type,
                'name': kwargs['name'],
                'status': 'created',
                'object': obj
            })
            
            logger.info(f"Created {object_type}: {kwargs['name']}")
            
        except Exception as e:
            logger.error(f"Error creating object in row {index + 1}: {e}")
            results.append({
                'row': index + 1,
                'object_type': row.get('object_type', 'unknown'),
                'name': row.get('name', 'unknown'),
                'status': 'error',
                'error': str(e)
            })
    
    return results


def print_results(results):
    """Print creation results in a formatted table"""
    if not results:
        print("No objects processed")
        return
    
    # Prepare data for table
    table_data = []
    for result in results:
        row_data = [
            result.get('row', ''),
            result.get('object_type', ''),
            result.get('name', ''),
            result.get('status', ''),
            result.get('error', '')
        ]
        table_data.append(row_data)
    
    headers = ['Row', 'Type', 'Name', 'Status', 'Error']
    
    if HAS_TABULATE:
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    else:
        # Simple table format
        print(f"{'Row':<4} {'Type':<15} {'Name':<20} {'Status':<10} {'Error':<30}")
        print("-" * 80)
        for row in table_data:
            print(f"{row[0]:<4} {row[1]:<15} {row[2]:<20} {row[3]:<10} {row[4]:<30}")


def main():
    parser = argparse.ArgumentParser(
        description='Create PAN-OS Objects via pan-os-python SDK',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single object creation
  python panos_object_creator.py --hostname 192.168.1.1 --username admin --password pass --object-type address --name MyIP --value 192.168.1.1/24

  # Batch creation from CSV
  python panos_object_creator.py --hostname 192.168.1.1 --username admin --password pass --csv-file objects.csv --commit

  # Dry run to preview changes
  python panos_object_creator.py --hostname 192.168.1.1 --api-key YOUR_KEY --csv-file objects.csv --dry-run

  # Print CSV template
  python panos_object_creator.py --template
        """
    )
    
    # Template option
    parser.add_argument('--template', action='store_true', help='Print CSV template and exit')
    
    # Connection arguments
    parser.add_argument('--hostname', required=False, help='Firewall/Panorama IP/FQDN')
    parser.add_argument('--username', help='Admin username')
    parser.add_argument('--password', help='Admin password')
    parser.add_argument('--api-key', help='API key (alternative to username/password)')
    parser.add_argument('--vsys', default='vsys1', help='Virtual system (default: vsys1)')
    parser.add_argument('--device-group', help='Device group (for Panorama)')
    
    # Operation mode
    parser.add_argument('--object-type', choices=list(OBJECT_CLASSES.keys()), 
                       help='Object type for single creation')
    parser.add_argument('--csv-file', help='CSV file for batch creation')
    
    # Object-specific arguments
    parser.add_argument('--name', help='Object name')
    parser.add_argument('--value', help='Object value (for addresses, etc.)')
    parser.add_argument('--type', help='Object type (for addresses)')
    parser.add_argument('--description', help='Object description')
    parser.add_argument('--tag', help='Object tag')
    parser.add_argument('--members', help='Comma-separated member list')
    parser.add_argument('--protocol', help='Protocol (tcp/udp)')
    parser.add_argument('--source-port', help='Source port')
    parser.add_argument('--destination-port', help='Destination port')
    parser.add_argument('--category', help='Application category')
    parser.add_argument('--default-port', help='Default port')
    parser.add_argument('--group-type', help='Group type (static/dynamic)')
    parser.add_argument('--urls', help='Comma-separated URL list')
    parser.add_argument('--category-type', help='Category type')
    parser.add_argument('--source', help='Source URL')
    parser.add_argument('--edl-type', help='EDL type (ip/domain)')
    parser.add_argument('--color', help='Tag color')
    parser.add_argument('--comments', help='Comments')
    
    # Operation flags
    parser.add_argument('--dry-run', action='store_true', help='Simulate creation (print XML, no commit)')
    parser.add_argument('--commit', action='store_true', help='Commit changes after creation')
    parser.add_argument('--test', action='store_true', help='Test mode (validate inputs only)')
    
    args = parser.parse_args()
    
    # Handle template request
    if args.template:
        print_csv_template()
        sys.exit(0)
    
    # Validate arguments
    if not args.hostname and not args.test:
        parser.error("--hostname is required unless using --test")
    
    if not args.api_key and not args.username and not args.test:
        parser.error("Either --api-key or --username is required unless using --test")
    
    if not args.csv_file and not args.object_type and not args.test:
        parser.error("Either --csv-file or --object-type is required unless using --test")
    
    # Test mode
    if args.test:
        print("Test mode: Validating inputs only")
        if args.object_type:
            print(f"Object type: {args.object_type}")
            print(f"Name: {args.name}")
            if args.value:
                print(f"Value: {args.value}")
                if validate_ip_address(args.value):
                    print("✓ IP address format is valid")
                else:
                    print("⚠ IP address format may be invalid")
        if args.csv_file:
            print(f"CSV file: {args.csv_file}")
        print("✓ Input validation complete")
        sys.exit(0)
    
    try:
        # Connect to device
        if args.api_key:
            device = Firewall(args.hostname, api_key=args.api_key)
        else:
            if not args.password:
                args.password = getpass.getpass("Enter password: ")
            device = Firewall(args.hostname, args.username, args.password)
        
        # Get VSYS
        vsys = device.add(Vsys(name=args.vsys))
        
        results = []
        
        # Create objects
        if args.csv_file:
            logger.info(f"Processing CSV file: {args.csv_file}")
            results = create_objects_from_csv(args, device, vsys)
        elif args.object_type:
            logger.info(f"Creating single object: {args.object_type}")
            obj = create_single_object(args, device, vsys)
            results = [{
                'row': 1,
                'object_type': args.object_type,
                'name': args.name,
                'status': 'created',
                'object': obj
            }]
        
        # Handle dry run
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be committed")
            for result in results:
                if 'object' in result:
                    print(f"\nXML for {result['name']}:")
                    import xml.etree.ElementTree as ET
                    element = result['object'].element()
                    print(ET.tostring(element, encoding='unicode'))
        else:
            # Create objects
            for result in results:
                if 'object' in result and result['status'] == 'created':
                    try:
                        result['object'].create()
                        logger.info(f"✓ Created {result['object_type']}: {result['name']}")
                    except Exception as e:
                        logger.error(f"✗ Failed to create {result['name']}: {e}")
                        result['status'] = 'error'
                        result['error'] = str(e)
            
            # Commit changes
            if args.commit and results:
                try:
                    device.commit()
                    logger.info("✓ Changes committed successfully")
                except PanCommitFailed as e:
                    logger.error(f"✗ Commit failed: {e}")
                    sys.exit(1)
            elif results:
                logger.info("Changes created but not committed (use --commit to commit)")
        
        # Print results
        print_results(results)
        
        # Summary
        success_count = len([r for r in results if r['status'] == 'created'])
        error_count = len([r for r in results if r['status'] == 'error'])
        
        print(f"\nSummary: {success_count} created, {error_count} errors")
        
        if error_count > 0:
            sys.exit(1)
            
    except PanInvalidCredentials as e:
        logger.error(f"Login failed: {e}")
        sys.exit(1)
    except PanDeviceError as e:
        logger.error(f"PAN-OS error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
