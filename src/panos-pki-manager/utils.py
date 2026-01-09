#!/usr/bin/env python3
"""
Utility Functions
Baker Street Labs - PAN-OS PKI Manager Utilities

Common utility functions for certificate operations, logging, and file management.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import colorlog


def setup_logging(config: dict) -> None:
    """
    Setup logging configuration.
    
    Args:
        config: Logging configuration dict
    """
    log_level = config.get('level', 'INFO')
    log_file = config.get('file', 'panos_pki_manager.log')
    console_logging = config.get('console', True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s',
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Add console handler
    if console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)


def ensure_directories(output_config: dict) -> None:
    """
    Ensure output directories exist.
    
    Args:
        output_config: Output configuration dict
    """
    if not output_config.get('create_directories', True):
        return
    
    directories = [
        output_config.get('cert_directory', './certificates'),
        output_config.get('csr_directory', './csrs'),
        output_config.get('backup_directory', './backups')
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logging.debug(f"Ensured directory exists: {directory}")


def save_pem_file(content: str, filename: str, directory: str = '.') -> str:
    """
    Save PEM content to file.
    
    Args:
        content: PEM content
        filename: Filename
        directory: Directory to save to
        
    Returns:
        Full path to saved file
    """
    Path(directory).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(directory, filename)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    logging.debug(f"Saved PEM file: {filepath}")
    return filepath


def load_pem_file(filepath: str) -> Optional[str]:
    """
    Load PEM content from file.
    
    Args:
        filepath: Path to PEM file
        
    Returns:
        PEM content or None if file doesn't exist
    """
    if not os.path.exists(filepath):
        logging.warning(f"File not found: {filepath}")
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    logging.debug(f"Loaded PEM file: {filepath}")
    return content


def generate_timestamp() -> str:
    """
    Generate timestamp string for filenames.
    
    Returns:
        Timestamp in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(name: str) -> str:
    """
    Sanitize string for use as filename.
    
    Args:
        name: Original name
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    sanitized = name.replace('/', '_').replace('\\', '_').replace(':', '_')
    sanitized = sanitized.replace('*', '_').replace('?', '_').replace('"', '_')
    sanitized = sanitized.replace('<', '_').replace('>', '_').replace('|', '_')
    sanitized = sanitized.replace(' ', '_')
    
    return sanitized


def parse_certificate_info(cert_pem: str) -> dict:
    """
    Parse certificate and extract information.
    
    Args:
        cert_pem: Certificate in PEM format
        
    Returns:
        Dict with certificate information
    """
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        
        info = {
            'subject': cert.subject.rfc4514_string(),
            'issuer': cert.issuer.rfc4514_string(),
            'serial_number': hex(cert.serial_number),
            'not_before': cert.not_valid_before.isoformat(),
            'not_after': cert.not_valid_after.isoformat(),
            'signature_algorithm': cert.signature_algorithm_oid._name,
        }
        
        # Extract SANs if present
        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans = [str(name) for name in san_ext.value]
            info['sans'] = sans
        except x509.ExtensionNotFound:
            info['sans'] = []
        
        return info
        
    except Exception as e:
        logging.error(f"Failed to parse certificate: {e}")
        return {}


def validate_certificate_chain(cert_chain_pem: str) -> bool:
    """
    Validate certificate chain.
    
    Args:
        cert_chain_pem: Certificate chain in PEM format
        
    Returns:
        True if chain is valid (basic validation)
    """
    try:
        # Split chain into individual certificates
        certs = []
        current_cert = []
        in_cert = False
        
        for line in cert_chain_pem.split('\n'):
            if '-----BEGIN CERTIFICATE-----' in line:
                in_cert = True
                current_cert = [line]
            elif '-----END CERTIFICATE-----' in line:
                current_cert.append(line)
                certs.append('\n'.join(current_cert))
                in_cert = False
                current_cert = []
            elif in_cert:
                current_cert.append(line)
        
        if not certs:
            logging.error("No certificates found in chain")
            return False
        
        logging.info(f"Certificate chain contains {len(certs)} certificate(s)")
        
        # Parse each certificate
        for i, cert_pem in enumerate(certs):
            try:
                cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
                subject = cert.subject.rfc4514_string()
                issuer = cert.issuer.rfc4514_string()
                logging.debug(f"Cert {i+1}: Subject={subject}, Issuer={issuer}")
            except Exception as e:
                logging.error(f"Failed to parse certificate {i+1}: {e}")
                return False
        
        return True
        
    except Exception as e:
        logging.error(f"Certificate chain validation failed: {e}")
        return False


def format_subject_name(common_name: str, organization: str = "Baker Street Labs", 
                       organizational_unit: Optional[str] = None,
                       country: str = "US") -> str:
    """
    Format subject name for certificate.
    
    Args:
        common_name: Common name (CN)
        organization: Organization (O)
        organizational_unit: Organizational unit (OU)
        country: Country (C)
        
    Returns:
        Formatted subject string
    """
    parts = [f"CN={common_name}"]
    
    if organizational_unit:
        parts.append(f"OU={organizational_unit}")
    
    parts.append(f"O={organization}")
    parts.append(f"C={country}")
    
    return ", ".join(parts)


def print_summary(title: str, items: dict) -> None:
    """
    Print formatted summary.
    
    Args:
        title: Summary title
        items: Dict of items to display
    """
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")
    
    max_key_len = max(len(str(k)) for k in items.keys()) if items else 0
    
    for key, value in items.items():
        print(f"  {str(key):<{max_key_len}} : {value}")
    
    print(f"\n{'='*70}\n")

