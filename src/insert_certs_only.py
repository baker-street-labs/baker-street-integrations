#!/usr/bin/env python3
"""
Insert SSL certificate into baseline config (NO OTHER CHANGES)
"""

import sys
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

def insert_certificate_only(input_file, output_file, range_name, cert_dir):
    """Insert certificate into config - NO OTHER CHANGES"""
    print(f"Processing {range_name}...")
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        config = f.read()
    
    # Load certificate data
    print(f"  Loading certificate data...")
    cert_data = load_certificate_data(cert_dir, range_name)
    
    # Find the rangexdr-mgmt-https certificate and replace ONLY the certificate content
    # We need to find it and replace cert/key while keeping the name as rangexdr-mgmt-https
    
    # Build replacement certificate with ORIGINAL name (rangexdr-mgmt-https)
    new_cert_xml = f'''<entry name="rangexdr-mgmt-https">
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
    
    # Find and replace the certificate entry
    import re
    cert_pattern = r'<entry name="rangexdr-mgmt-https">.*?</entry>'
    config = re.sub(cert_pattern, new_cert_xml, config, flags=re.DOTALL)
    
    print(f"  Certificate inserted for {cert_data['cn']}")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(config)
    
    print(f"  [OK] {output_file} created ({len(config)} bytes)")
    return True

if __name__ == '__main__':
    cert_dir = './certificates'
    
    ranges = [
        ('rangexsiam-v2.xml', 'rangexsiam'),
        ('rangeagentix-v2.xml', 'rangeagentix'),
        ('rangelande-v2.xml', 'rangelande'),
        ('rangeplatform-v2.xml', 'rangeplatform'),
    ]
    
    print("="*70)
    print("Inserting SSL Certificates (NO other changes)")
    print("="*70)
    print()
    
    for output_file, range_name in ranges:
        insert_certificate_only(output_file, output_file, range_name, cert_dir)
        print()
    
    print("="*70)
    print("[SUCCESS] All v2 configs ready with embedded certificates")
    print("="*70)
    print()
    print("Configs are IDENTICAL to baseline except for SSL cert")
    print("Manual changes needed on each firewall after upload:")
    print("  - Network parameters (IP addresses)")
    print("  - Hostname")
    print("  - Interface assignments")
    print()

