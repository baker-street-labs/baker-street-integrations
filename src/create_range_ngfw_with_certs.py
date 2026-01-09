#!/usr/bin/env python3
"""
Enhanced Range NGFW Configuration Generator
Creates PAN-OS firewall configurations with pre-inserted SSL certificates
Baker Street Labs - October 23, 2025
"""

import argparse
import sys
import re
from pathlib import Path

def load_certificate_data(cert_dir, range_name):
    """Load all certificate data from files"""
    cert_data = {}
    cert_path = Path(cert_dir)
    
    try:
        cert_data['cert_pem'] = (cert_path / f"{range_name}-mgmt.crt").read_text()
        cert_data['key_b64'] = (cert_path / f"{range_name}-mgmt.key.b64").read_text().strip()
        cert_data['subject_hash'] = (cert_path / f"{range_name}-subject-hash.txt").read_text().strip()
        cert_data['issuer_hash'] = (cert_path / f"{range_name}-issuer-hash.txt").read_text().strip()
        cert_data['not_before'] = (cert_path / f"{range_name}-not-before.txt").read_text().strip()
        cert_data['not_after'] = (cert_path / f"{range_name}-not-after.txt").read_text().strip()
        cert_data['expiry_epoch'] = (cert_path / f"{range_name}-expiry-epoch.txt").read_text().strip()
        cert_data['issuer'] = (cert_path / f"{range_name}-issuer.txt").read_text().strip()
        cert_data['subject'] = (cert_path / f"{range_name}-subject.txt").read_text().strip()
        cert_data['cn'] = (cert_path / f"{range_name}-cn.txt").read_text().strip()
        
        return cert_data
    except Exception as e:
        print(f"ERROR: Failed to load certificate data for {range_name}: {e}")
        sys.exit(1)

def replace_network_params(config, old_third_octet, new_third_octet):
    """Replace all 172.29.x.x with 172.{new}.x.x"""
    print(f"  Replacing 172.{old_third_octet}.x.x -> 172.{new_third_octet}.x.x")
    return config.replace(f'172.{old_third_octet}.', f'172.{new_third_octet}.')

def replace_ethernet1_1_ips(config, new_gateway_ip, new_rdp_ip):
    """Replace ethernet1/1 IP addresses"""
    print(f"  Replacing ethernet1/1 IPs: {new_gateway_ip}, {new_rdp_ip}")
    
    # Replace Public Gateway address object
    config = re.sub(
        r'(<entry name="Public Gateway">\s*<ip-netmask>)192\.168\.255\.242/16(</ip-netmask>)',
        rf'\g<1>{new_gateway_ip}/24\g<2>',
        config,
        flags=re.DOTALL
    )
    
    # Replace Public RDP Service address object
    config = re.sub(
        r'(<entry name="Public RDP Service">\s*<ip-netmask>)192\.168\.255\.250(</ip-netmask>)',
        rf'\g<1>{new_rdp_ip}\g<2>',
        config,
        flags=re.DOTALL
    )
    
    # Also replace RDP Services Address (duplicate entry)
    config = re.sub(
        r'(<entry name="RDP Services Address">\s*<ip-netmask>)192\.168\.255\.250(</ip-netmask>)',
        rf'\g<1>{new_rdp_ip}\g<2>',
        config,
        flags=re.DOTALL
    )
    
    return config

def replace_range_strings(config, range_name, range_display):
    """Replace all XDR/xdr/rangexdr references"""
    print(f"  Replacing XDR references -> {range_display}")
    
    # Replace certificate name
    config = config.replace('rangexdr-mgmt-https', f'{range_name}-mgmt-https')
    
    # Replace SSL Decrypt CA name
    config = config.replace('xdrngfw-SSL-Decrypt-CA', f'{range_display.lower()}ngfw-SSL-Decrypt-CA')
    config = config.replace('xdrngfw SSL Decryption CA', f'{range_display.lower()}ngfw SSL Decryption CA')
    
    # Replace hostname
    config = config.replace('rangexdr', range_name)
    
    # Replace "Range XDR" in names
    config = config.replace('Range XDR', f'Range {range_display}')
    
    # Replace "XDR Lab" in profiles
    config = config.replace('XDR Lab', f'{range_display} Lab')
    
    return config

def insert_certificate(config, range_name, cert_data):
    """Insert pre-generated certificate into XML"""
    print(f"  Inserting SSL certificate for {range_name}")
    
    # Find and replace the existing rangexdr-mgmt-https certificate
    # This pattern matches the entire certificate entry
    cert_pattern = r'<entry name="rangexdr-mgmt-https">.*?</entry>'
    
    # Build the new certificate XML
    new_cert_xml = f'''<entry name="{range_name}-mgmt-https">
        <subject-hash>{cert_data['subject_hash']}</subject-hash>
        <issuer-hash>{cert_data['issuer_hash']}</issuer-hash>
        <not-valid-before>{cert_data['not_before']}</not-valid-before>
        <issuer>{cert_data['issuer']}</issuer>
        <not-valid-after>{cert_data['not_after']}</not-valid-after>
        <common-name>{cert_data['cn']}</common-name>
        <expiry-epoch>{cert_data['expiry_epoch']}</expiry-epoch>
        <ca>no</ca>
        <subject>{cert_data['subject']}</subject>
        <public-key>{cert_data['cert_pem']}</public-key>
        <algorithm>RSA</algorithm>
        <private-key>{cert_data['key_b64']}</private-key>
      </entry>'''
    
    config = re.sub(cert_pattern, new_cert_xml, config, flags=re.DOTALL)
    
    return config

def create_range_config_with_certs(
    baseline_file,
    range_name,
    range_display,
    third_octet,
    gateway_ip,
    rdp_ip,
    cert_dir,
    output_file
):
    """Main function to create range config with certificates"""
    print(f"\n{'='*70}")
    print(f"Creating {range_name} configuration")
    print(f"{'='*70}")
    
    # Read baseline
    try:
        with open(baseline_file, 'r', encoding='utf-8') as f:
            config = f.read()
        print(f"[OK] Loaded baseline: {baseline_file} ({len(config)} bytes)")
    except Exception as e:
        print(f"ERROR: Failed to read baseline file: {e}")
        sys.exit(1)
    
    # Load certificate data
    print(f"  Loading certificate data...")
    cert_data = load_certificate_data(cert_dir, range_name)
    print(f"[OK] Certificate data loaded")
    
    # Perform replacements
    print(f"  Applying transformations...")
    config = replace_network_params(config, 29, third_octet)
    config = replace_ethernet1_1_ips(config, gateway_ip, rdp_ip)
    config = replace_range_strings(config, range_name, range_display)
    config = insert_certificate(config, range_name, cert_data)
    
    # Write output
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(config)
        print(f"[OK] Configuration written: {output_file} ({len(config)} bytes)")
    except Exception as e:
        print(f"ERROR: Failed to write output file: {e}")
        sys.exit(1)
    
    print(f"{'='*70}")
    print(f"[SUCCESS] {range_name} configuration complete!")
    print(f"{'='*70}\n")
    
    return output_file

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate PAN-OS NGFW config with SSL certificates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python create_range_ngfw_with_certs.py \\
    --range-name rangexsiam \\
    --range-display XSIAM \\
    --third-octet 30 \\
    --gateway-ip 192.168.255.243 \\
    --rdp-ip 192.168.255.251

  python create_range_ngfw_with_certs.py \\
    --range-name rangeagentix \\
    --range-display AGENTIX \\
    --third-octet 23 \\
    --gateway-ip 192.168.255.244 \\
    --rdp-ip 192.168.255.252
        '''
    )
    
    parser.add_argument('--range-name', required=True, help='Range name (e.g., rangexsiam)')
    parser.add_argument('--range-display', required=True, help='Range display name (e.g., XSIAM)')
    parser.add_argument('--third-octet', type=int, required=True, help='Third octet (e.g., 30 for 172.30.x.x)')
    parser.add_argument('--gateway-ip', required=True, help='ethernet1/1 gateway IP (e.g., 192.168.255.243)')
    parser.add_argument('--rdp-ip', required=True, help='ethernet1/1 RDP NAT IP (e.g., 192.168.255.251)')
    parser.add_argument('--cert-dir', default='./certificates', help='Certificate directory')
    parser.add_argument('--baseline', default='range_baseline.xml', help='Baseline XML file')
    parser.add_argument('--output', help='Output file (default: {range_name}.xml)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.third_octet < 0 or args.third_octet > 255:
        print(f"ERROR: Invalid third octet: {args.third_octet} (must be 0-255)")
        sys.exit(1)
    
    if not args.range_name.startswith('range'):
        print(f"WARNING: Range name '{args.range_name}' does not start with 'range'")
    
    output_file = args.output or f"{args.range_name}.xml"
    
    # Create the configuration
    create_range_config_with_certs(
        baseline_file=args.baseline,
        range_name=args.range_name,
        range_display=args.range_display,
        third_octet=args.third_octet,
        gateway_ip=args.gateway_ip,
        rdp_ip=args.rdp_ip,
        cert_dir=args.cert_dir,
        output_file=output_file
    )
    
    print("Next steps:")
    print(f"  1. Validate XML: xmllint --noout {output_file}")
    print(f"  2. Upload to firewall: python upload_pan_os_config.py --config-file {output_file}")
    print()

if __name__ == '__main__':
    main()

