#!/usr/bin/env python3
"""
PAN-OS PKI Manager - Main Script
Baker Street Labs - Automated Firewall Certificate Management

Orchestrates certificate lifecycle management for Palo Alto Networks firewalls
using Baker Street Labs PKI infrastructure.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import os

# Import local modules
from config_manager import ConfigManager, ConfigurationError
from pki_intermediate import PKIIntermediateCA
from firewall_api import FirewallAPI, FirewallAPIError
from csr_signing import CSRSigner, CSRSigningError
import utils

logger = logging.getLogger(__name__)


class PANOSPKIManager:
    """Main orchestrator for PAN-OS PKI certificate management."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize PAN-OS PKI Manager.
        
        Args:
            config_file: Path to configuration file
        """
        try:
            self.config = ConfigManager(config_file)
        except ConfigurationError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
        
        # Setup logging
        utils.setup_logging(self.config.get_logging_config())
        
        # Ensure output directories
        utils.ensure_directories(self.config.get_output_config())
        
        logger.info("="*70)
        logger.info("  PAN-OS PKI Manager - Baker Street Labs")
        logger.info("="*70)
        
        # Initialize components
        self.pki_manager = PKIIntermediateCA(
            self.config.get_ca_config(),
            self.config.get_intermediate_ca_config()
        )
        
        self.csr_signer = CSRSigner(self.config.get_ca_config())
        
        self.settings = self.config.get_settings()
        self.output_config = self.config.get_output_config()
        
    def setup_intermediate_ca(self) -> bool:
        """
        Setup intermediate CA if configured.
        
        Returns:
            True if successful or not needed
        """
        intermediate_config = self.config.get_intermediate_ca_config()
        
        if not intermediate_config.get('create_if_missing', False):
            logger.info("Intermediate CA creation not enabled, skipping")
            return True
        
        logger.info("Setting up intermediate CA...")
        return self.pki_manager.ensure_intermediate_ca()
    
    def process_firewall(self, firewall_config: Dict[str, Any]) -> bool:
        """
        Process all certificates for a single firewall.
        
        Args:
            firewall_config: Firewall configuration dict
            
        Returns:
            True if all certificates processed successfully
        """
        fw_name = firewall_config['name']
        logger.info(f"\n{'='*70}")
        logger.info(f"  Processing Firewall: {fw_name}")
        logger.info(f"{'='*70}\n")
        
        try:
            # Connect to firewall
            fw_api = FirewallAPI(firewall_config)
            
            # Backup if configured
            if self.settings.get('backup_before_import', True):
                timestamp = utils.generate_timestamp()
                backup_dir = self.output_config.get('backup_directory', './backups')
                backup_file = os.path.join(backup_dir, f"backup_{fw_name}_{timestamp}.xml")
                
                if not self.config.is_dry_run():
                    fw_api.backup_config(backup_file)
            
            # Process each certificate
            certificates = firewall_config.get('certificates', [])
            if not certificates:
                logger.warning(f"No certificates configured for {fw_name}")
                return True
            
            success_count = 0
            for cert_config in certificates:
                if self.process_certificate(fw_api, cert_config):
                    success_count += 1
            
            # Commit changes if configured
            if success_count > 0 and self.settings.get('commit_after_import', True):
                if not self.config.is_dry_run():
                    fw_api.commit_changes(f"PKI certificate management - {success_count} cert(s) updated")
                else:
                    logger.info("[DRY RUN] Would commit changes to firewall")
            
            fw_api.close()
            
            logger.info(f"Processed {success_count}/{len(certificates)} certificates for {fw_name}")
            return success_count == len(certificates)
            
        except FirewallAPIError as e:
            logger.error(f"Firewall API error for {fw_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Exception processing firewall {fw_name}: {e}")
            return False
    
    def process_certificate(self, fw_api: FirewallAPI, cert_config: Dict[str, Any]) -> bool:
        """
        Process a single certificate for a firewall.
        
        Args:
            fw_api: FirewallAPI instance
            cert_config: Certificate configuration dict
            
        Returns:
            True if certificate processed successfully
        """
        cert_name = cert_config.get('name', 'ngfw-cert')
        common_name = cert_config.get('common_name')
        
        if not common_name:
            logger.error(f"Certificate {cert_name} missing common_name")
            return False
        
        logger.info(f"\nProcessing certificate: {cert_name} (CN={common_name})")
        
        # Check if certificate already exists
        if self.settings.get('check_existing', True):
            if fw_api.certificate_exists(cert_name):
                logger.info(f"Certificate {cert_name} already exists on firewall")
                # TODO: Check expiration and renew if needed
                return True
        
        if self.config.is_dry_run():
            logger.info(f"[DRY RUN] Would generate CSR for {cert_name}")
            return True
        
        # Generate CSR on firewall
        logger.info(f"Generating CSR on firewall {fw_api.name}...")
        
        # Build cert config for firewall API
        fw_cert_config = {
            'name': cert_name,
            'common_name': common_name,
            'organization': cert_config.get('organization', 'Baker Street Labs'),
            'country': cert_config.get('country', 'US'),
            'key_size': cert_config.get('key_size', 2048)
        }
        
        csr_pem = fw_api.generate_certificate_csr(fw_cert_config)
        
        if not csr_pem:
            logger.error(f"Failed to generate CSR for {cert_name}")
            return False
        
        # Save CSR
        csr_dir = self.output_config.get('csr_directory', './csrs')
        csr_filename = f"{fw_api.name}_{cert_name}_{utils.generate_timestamp()}.csr"
        utils.save_pem_file(csr_pem, csr_filename, csr_dir)
        
        # Submit CSR to CA for signing
        template_name = cert_config.get('template', 'BSLWebServer')
        logger.info(f"Submitting CSR to CA using template {template_name}...")
        
        cert_pem = self.csr_signer.sign_csr(csr_pem, template_name)
        
        if not cert_pem:
            logger.error(f"Failed to get signed certificate for {cert_name}")
            return False
        
        # Build certificate chain
        if self.settings.get('verify_chain', True):
            cert_chain = self.csr_signer.get_certificate_chain(cert_pem)
            
            if not utils.validate_certificate_chain(cert_chain):
                logger.error("Certificate chain validation failed")
                return False
        else:
            cert_chain = cert_pem
        
        # Save signed certificate
        cert_dir = self.output_config.get('cert_directory', './certificates')
        cert_filename = f"{fw_api.name}_{cert_name}_{utils.generate_timestamp()}.pem"
        cert_filepath = utils.save_pem_file(cert_chain, cert_filename, cert_dir)
        
        logger.info(f"Signed certificate saved to {cert_filepath}")
        
        # Import certificate to firewall
        logger.info(f"Importing certificate to firewall {fw_api.name}...")
        
        signed_cert_name = f"{cert_name}-signed"
        if not fw_api.import_certificate(signed_cert_name, cert_chain):
            logger.error(f"Failed to import certificate {signed_cert_name}")
            return False
        
        logger.info(f"✅ Successfully processed certificate {cert_name}")
        return True
    
    def run(self, firewall_names: Optional[List[str]] = None) -> bool:
        """
        Run certificate management for configured firewalls.
        
        Args:
            firewall_names: Optional list of firewall names to process (None = all)
            
        Returns:
            True if all operations successful
        """
        if self.config.is_dry_run():
            logger.warning("="*70)
            logger.warning("  DRY RUN MODE - No changes will be made")
            logger.warning("="*70)
        
        # Setup intermediate CA
        if not self.setup_intermediate_ca():
            logger.error("Failed to setup intermediate CA")
            return False
        
        # Get firewalls to process
        all_firewalls = self.config.get_firewalls()
        
        if firewall_names:
            firewalls_to_process = [
                fw for fw in all_firewalls 
                if fw.get('name') in firewall_names
            ]
            
            if not firewalls_to_process:
                logger.error(f"No firewalls found matching: {firewall_names}")
                return False
        else:
            firewalls_to_process = all_firewalls
        
        # Process each firewall
        results = []
        for fw_config in firewalls_to_process:
            success = self.process_firewall(fw_config)
            results.append((fw_config['name'], success))
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("  Summary")
        logger.info("="*70 + "\n")
        
        for fw_name, success in results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"  {fw_name}: {status}")
        
        success_count = sum(1 for _, success in results if success)
        total_count = len(results)
        
        logger.info(f"\n  Total: {success_count}/{total_count} firewalls processed successfully\n")
        logger.info("="*70 + "\n")
        
        return success_count == total_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='PAN-OS PKI Manager - Baker Street Labs Firewall Certificate Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all firewalls
  python main.py
  
  # Process specific firewalls
  python main.py --firewalls hub spoke
  
  # Dry run mode
  python main.py --dry-run
  
  # Use custom config file
  python main.py --config custom_config.yaml
  
  # Setup intermediate CA only
  python main.py --setup-ca-only
        """
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--firewalls',
        nargs='+',
        help='Specific firewalls to process (default: all)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - no changes will be made'
    )
    
    parser.add_argument(
        '--setup-ca-only',
        action='store_true',
        help='Only setup intermediate CA, skip firewall processing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    args = parser.parse_args()
    
    # Override config with command line args
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'
    
    if args.verbose:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    try:
        # Initialize manager
        manager = PANOSPKIManager(args.config)
        
        if args.setup_ca_only:
            # Just setup intermediate CA
            logger.info("Setting up intermediate CA only...")
            success = manager.setup_intermediate_ca()
            sys.exit(0 if success else 1)
        
        # Run full certificate management
        success = manager.run(args.firewalls)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

