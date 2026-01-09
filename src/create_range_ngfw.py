#!/usr/bin/env python3
"""
Create Range NGFW Configuration
Generates PAN-OS firewall configurations for Baker Street Labs cyber ranges
by cloning the rangexdr baseline and substituting network parameters.

Usage:
    python create_range_ngfw.py --range-name rangexsiam --third-octet 30 --vlan-base 3000
    python create_range_ngfw.py --range-name rangelande --third-octet 22 --vlan-base 2200
    python create_range_ngfw.py --range-name rangeagentic --third-octet 23 --vlan-base 2300
"""

import argparse
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_range_config(baseline_file, range_name, third_octet, vlan_base, output_file=None):
    """
    Create a new range configuration by replacing network parameters in baseline.
    
    Args:
        baseline_file (str): Path to the rangexdr baseline XML config
        range_name (str): Name of the new range (e.g., 'rangexsiam', 'rangelande')
        third_octet (int): Third octet for the range (e.g., 30 for 172.30.x.x)
        vlan_base (int): Base VLAN ID (e.g., 3000 for VLANs 3001, 3002, ...)
        output_file (str): Optional output filename (defaults to {range_name}.xml)
    
    Returns:
        str: Path to the generated configuration file
    """
    logger.info(f"Creating {range_name} configuration...")
    logger.info(f"  Network: 172.{third_octet}.0.0/16")
    logger.info(f"  VLAN Base: {vlan_base}")
    
    # Read baseline configuration
    try:
        with open(baseline_file, 'r', encoding='utf-8') as f:
            config_content = f.read()
    except FileNotFoundError:
        logger.error(f"Baseline file not found: {baseline_file}")
        logger.error("Please ensure range_baseline.xml exists in the current directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading baseline file: {e}")
        sys.exit(1)
    
    # Perform replacements
    logger.info("Performing network substitutions...")
    
    # Replace IP addresses (172.29.x.x → 172.{third_octet}.x.x)
    modified_config = config_content.replace('172.29.', f'172.{third_octet}.')
    logger.info(f"  ✓ Replaced 172.29.* → 172.{third_octet}.*")
    
    # Replace range names (Range XDR → Range {Name})
    range_display_name = range_name.replace('range', '').upper()
    modified_config = modified_config.replace('Range XDR', f'Range {range_display_name}')
    logger.info(f"  ✓ Replaced 'Range XDR' → 'Range {range_display_name}'")
    
    # Replace hostname (rangexdr → {range_name})
    modified_config = modified_config.replace('rangexdr', range_name)
    logger.info(f"  ✓ Replaced 'rangexdr' → '{range_name}'")
    
    # Replace service/profile names
    modified_config = modified_config.replace('XDR Lab', f'{range_display_name} Lab')
    logger.info(f"  ✓ Replaced 'XDR Lab' → '{range_display_name} Lab'")
    
    # Replace interface management profile names
    modified_config = modified_config.replace('Range XDR Ping', f'Range {range_display_name} Ping')
    
    # Replace service names (Range XDR RDP → Range {Name} RDP)
    modified_config = modified_config.replace('Range XDR RDP', f'Range {range_display_name} RDP')
    modified_config = modified_config.replace('Range XDR SSH', f'Range {range_display_name} SSH')
    
    # Note: VLAN replacement would require XML parsing since VLANs aren't explicitly
    # defined in the PAN-OS config format shown. VLANs are typically configured
    # outside this XML or would need interface-level modification.
    logger.info(f"  ⚠ VLAN configuration: Base {vlan_base} (requires manual interface config)")
    
    # Determine output filename
    if output_file is None:
        output_file = f"{range_name}.xml"
    
    # Write modified configuration
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(modified_config)
        logger.info(f"✅ Configuration written to: {output_file}")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")
        sys.exit(1)
    
    # Verify file size
    output_path = Path(output_file)
    file_size = output_path.stat().st_size
    logger.info(f"  File size: {file_size:,} bytes")
    
    # Generate summary
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Range Configuration Summary: {range_name}")
    logger.info("=" * 70)
    logger.info(f"Network:           172.{third_octet}.0.0/16")
    logger.info(f"VLAN Base:         {vlan_base}")
    logger.info(f"Suggested VLANs:   {vlan_base+1}, {vlan_base+2}, {vlan_base+3}, {vlan_base+4}, {vlan_base+5}")
    logger.info(f"  - VLAN {vlan_base+1}: Users      (172.{third_octet}.2.0/24)")
    logger.info(f"  - VLAN {vlan_base+2}: Services   (172.{third_octet}.3.0/24)")
    logger.info(f"  - VLAN {vlan_base+3}: Infrastructure (172.{third_octet}.4.0/24)")
    logger.info(f"Output File:       {output_file}")
    logger.info("=" * 70)
    
    return output_file


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Generate PAN-OS NGFW configuration for Baker Street Labs cyber ranges',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create rangexsiam configuration (172.30.x.x, VLAN 3000 series)
  python create_range_ngfw.py --range-name rangexsiam --third-octet 30 --vlan-base 3000
  
  # Create rangelande configuration (172.22.x.x, VLAN 2200 series)
  python create_range_ngfw.py --range-name rangelande --third-octet 22 --vlan-base 2200
  
  # Create rangeagentic configuration (172.23.x.x, VLAN 2300 series)
  python create_range_ngfw.py --range-name rangeagentic --third-octet 23 --vlan-base 2300

Range Naming Convention:
  rangexdr:      172.29.x.x  VLAN 1001-1005 (existing baseline)
  rangexsiam:    172.30.x.x  VLAN 3001-3005
  rangelande:    172.22.x.x  VLAN 2201-2205
  rangeagentic:  172.23.x.x  VLAN 2301-2305
        '''
    )
    
    parser.add_argument(
        '--range-name',
        type=str,
        required=True,
        help='Name of the cyber range (e.g., rangexsiam, rangelande, rangeagentic)'
    )
    
    parser.add_argument(
        '--third-octet',
        type=int,
        required=True,
        help='Third octet of the IP range (e.g., 30 for 172.30.x.x)'
    )
    
    parser.add_argument(
        '--vlan-base',
        type=int,
        required=True,
        help='Base VLAN ID (e.g., 3000 for VLANs 3001, 3002, etc.)'
    )
    
    parser.add_argument(
        '--baseline',
        type=str,
        default='range_baseline.xml',
        help='Path to the rangexdr baseline XML configuration (default: range_baseline.xml)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output filename (default: {range_name}.xml)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate inputs
    if args.third_octet < 0 or args.third_octet > 255:
        logger.error(f"Invalid third octet: {args.third_octet} (must be 0-255)")
        sys.exit(1)
    
    if args.vlan_base < 1 or args.vlan_base > 4000:
        logger.error(f"Invalid VLAN base: {args.vlan_base} (must be 1-4000)")
        sys.exit(1)
    
    if not args.range_name.startswith('range'):
        logger.warning(f"Range name '{args.range_name}' does not start with 'range'")
        logger.warning("Consider using naming convention: rangexsiam, rangelande, etc.")
    
    # Create the configuration
    create_range_config(
        baseline_file=args.baseline,
        range_name=args.range_name,
        third_octet=args.third_octet,
        vlan_base=args.vlan_base,
        output_file=args.output
    )
    
    logger.info("")
    logger.info("🎯 Next Steps:")
    logger.info("  1. Review the generated XML configuration")
    logger.info("  2. Import to PAN-OS firewall via GUI or API")
    logger.info("  3. Configure physical/virtual interfaces for VLANs")
    logger.info("  4. Update IPAM documentation")
    logger.info("  5. Deploy VMs/hosts with assigned IP addresses")
    logger.info("")


if __name__ == '__main__':
    main()

