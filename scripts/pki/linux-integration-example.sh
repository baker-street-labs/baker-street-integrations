#!/bin/bash
# =============================================================================
# Linux PKI Integration Example
# =============================================================================
# This script demonstrates how Linux systems integrate with the Windows
# Subordinate CA for the Baker Street Labs cyber range.
# 
# Author: Baker Street Labs
# Version: 1.0
# Last Updated: 2025-09-29
# =============================================================================

set -euo pipefail

# Configuration
CA_SERVER="192.168.0.61"
CA_WEB_URL="http://${CA_SERVER}/certsrv"
CA_NAME="Baker Street Labs Issuing CA"
CERT_TEMPLATE="BSLWebServer"
CERT_VALIDITY_DAYS=365
KEY_SIZE=2048

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local message="$1"
    local color="${2:-$NC}"
    echo -e "${color}${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "=== Checking Prerequisites ===" "$BLUE"
    
    # Check if required tools are installed
    local tools=("openssl" "curl" "certutil" "sssd")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            print_status "✓ $tool is installed" "$GREEN"
        else
            print_status "✗ $tool is not installed" "$RED"
            print_status "Install with: sudo dnf install $tool (RHEL/CentOS) or sudo apt install $tool (Ubuntu/Debian)" "$YELLOW"
        fi
    done
}

# Function to download and install Root CA certificate
install_root_ca() {
    print_status "=== Installing Root CA Certificate ===" "$BLUE"
    
    local root_ca_url="${CA_WEB_URL}/certnew.p7b?ReqID=CACert&Renewal=0&Mode=inst&Enc=b64"
    local root_ca_file="/tmp/root-ca.p7b"
    local root_ca_crt="/tmp/root-ca.crt"
    
    # Download Root CA certificate
    print_status "Downloading Root CA certificate from $root_ca_url" "$YELLOW"
    if curl -s -o "$root_ca_file" "$root_ca_url"; then
        print_status "✓ Root CA certificate downloaded" "$GREEN"
    else
        print_status "✗ Failed to download Root CA certificate" "$RED"
        return 1
    fi
    
    # Convert P7B to PEM format
    print_status "Converting Root CA certificate to PEM format" "$YELLOW"
    if openssl pkcs7 -in "$root_ca_file" -print_certs -out "$root_ca_crt"; then
        print_status "✓ Root CA certificate converted" "$GREEN"
    else
        print_status "✗ Failed to convert Root CA certificate" "$RED"
        return 1
    fi
    
    # Install Root CA certificate
    print_status "Installing Root CA certificate to trust store" "$YELLOW"
    if sudo cp "$root_ca_crt" /etc/pki/ca-trust/source/anchors/; then
        sudo update-ca-trust extract
        print_status "✓ Root CA certificate installed to trust store" "$GREEN"
    else
        print_status "✗ Failed to install Root CA certificate" "$RED"
        return 1
    fi
    
    # Clean up temporary files
    rm -f "$root_ca_file" "$root_ca_crt"
}

# Function to generate certificate request
generate_certificate_request() {
    print_status "=== Generating Certificate Request ===" "$BLUE"
    
    local hostname=$(hostname)
    local fqdn="${hostname}.bakerstreet.local"
    local key_file="/etc/ssl/private/${hostname}.key"
    local csr_file="/tmp/${hostname}.csr"
    local config_file="/tmp/cert.conf"
    
    # Create certificate configuration
    cat > "$config_file" << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = Baker Street Labs
OU = Cyber Range
CN = $fqdn

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $hostname
DNS.2 = $fqdn
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF
    
    # Generate private key
    print_status "Generating private key: $key_file" "$YELLOW"
    if sudo openssl genrsa -out "$key_file" $KEY_SIZE; then
        sudo chmod 600 "$key_file"
        print_status "✓ Private key generated" "$GREEN"
    else
        print_status "✗ Failed to generate private key" "$RED"
        return 1
    fi
    
    # Generate certificate request
    print_status "Generating certificate request: $csr_file" "$YELLOW"
    if openssl req -new -key "$key_file" -out "$csr_file" -config "$config_file"; then
        print_status "✓ Certificate request generated" "$GREEN"
    else
        print_status "✗ Failed to generate certificate request" "$RED"
        return 1
    fi
    
    # Clean up config file
    rm -f "$config_file"
    
    echo "$csr_file"
}

# Function to submit certificate request
submit_certificate_request() {
    local csr_file="$1"
    local hostname=$(hostname)
    local cert_file="/etc/ssl/certs/${hostname}.crt"
    
    print_status "=== Submitting Certificate Request ===" "$BLUE"
    
    # For demonstration, we'll create a self-signed certificate
    # In production, this would submit to the Windows CA
    print_status "Creating self-signed certificate for demonstration" "$YELLOW"
    
    if sudo openssl x509 -req -in "$csr_file" -signkey "/etc/ssl/private/${hostname}.key" \
        -out "$cert_file" -days $CERT_VALIDITY_DAYS -extensions v3_req; then
        print_status "✓ Certificate created: $cert_file" "$GREEN"
    else
        print_status "✗ Failed to create certificate" "$RED"
        return 1
    fi
    
    # Clean up CSR file
    rm -f "$csr_file"
}

# Function to configure web server with certificate
configure_web_server() {
    print_status "=== Configuring Web Server ===" "$BLUE"
    
    local hostname=$(hostname)
    local cert_file="/etc/ssl/certs/${hostname}.crt"
    local key_file="/etc/ssl/private/${hostname}.key"
    
    # Check if Apache is installed
    if command -v apache2 &> /dev/null || command -v httpd &> /dev/null; then
        print_status "Configuring Apache with SSL certificate" "$YELLOW"
        
        # Create SSL virtual host configuration
        local ssl_conf="/etc/apache2/sites-available/ssl-${hostname}.conf"
        if [[ -f "/etc/httpd/conf.d/" ]]; then
            ssl_conf="/etc/httpd/conf.d/ssl-${hostname}.conf"
        fi
        
        sudo tee "$ssl_conf" > /dev/null << EOF
<VirtualHost *:443>
    ServerName ${hostname}.bakerstreet.local
    DocumentRoot /var/www/html
    
    SSLEngine on
    SSLCertificateFile ${cert_file}
    SSLCertificateKeyFile ${key_file}
    
    # Security headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
</VirtualHost>
EOF
        
        print_status "✓ Apache SSL configuration created" "$GREEN"
        print_status "Restart Apache to apply changes: sudo systemctl restart apache2" "$YELLOW"
        
    elif command -v nginx &> /dev/null; then
        print_status "Configuring Nginx with SSL certificate" "$YELLOW"
        
        # Create Nginx SSL configuration
        local nginx_conf="/etc/nginx/sites-available/ssl-${hostname}"
        sudo tee "$nginx_conf" > /dev/null << EOF
server {
    listen 443 ssl;
    server_name ${hostname}.bakerstreet.local;
    
    ssl_certificate ${cert_file};
    ssl_certificate_key ${key_file};
    
    # Security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    location / {
        root /var/www/html;
        index index.html;
    }
}
EOF
        
        # Enable the site
        sudo ln -sf "$nginx_conf" "/etc/nginx/sites-enabled/"
        print_status "✓ Nginx SSL configuration created" "$GREEN"
        print_status "Test configuration: sudo nginx -t" "$YELLOW"
        print_status "Reload Nginx: sudo systemctl reload nginx" "$YELLOW"
        
    else
        print_status "No web server detected. Certificate installed but not configured." "$YELLOW"
    fi
}

# Function to configure SSSD for certificate authentication
configure_sssd() {
    print_status "=== Configuring SSSD for Certificate Authentication ===" "$BLUE"
    
    local sssd_conf="/etc/sssd/sssd.conf"
    
    # Check if SSSD is installed
    if ! command -v sssd &> /dev/null; then
        print_status "SSSD not installed. Skipping certificate authentication setup." "$YELLOW"
        return 0
    fi
    
    print_status "Configuring SSSD for certificate authentication" "$YELLOW"
    
    # Backup existing configuration
    if [[ -f "$sssd_conf" ]]; then
        sudo cp "$sssd_conf" "${sssd_conf}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create SSSD configuration
    sudo tee "$sssd_conf" > /dev/null << EOF
[sssd]
services = nss, pam
config_file_version = 2
domains = bakerstreet.local

[domain/bakerstreet.local]
id_provider = ad
auth_provider = ad
access_provider = ad
ad_domain = bakerstreet.local
ad_server = 192.168.0.65
ad_backup_server = 192.168.0.66

# Certificate authentication
ldap_user_certificate = userCertificate;binary

[pam]
pam_cert_auth = True
EOF
    
    # Set proper permissions
    sudo chmod 600 "$sssd_conf"
    
    # Restart SSSD
    sudo systemctl restart sssd
    
    print_status "✓ SSSD configured for certificate authentication" "$GREEN"
    print_status "Enable smart card authentication: sudo authselect enable-feature with-smartcard" "$YELLOW"
}

# Function to test certificate
test_certificate() {
    print_status "=== Testing Certificate ===" "$BLUE"
    
    local hostname=$(hostname)
    local cert_file="/etc/ssl/certs/${hostname}.crt"
    
    if [[ -f "$cert_file" ]]; then
        print_status "Certificate details:" "$YELLOW"
        openssl x509 -in "$cert_file" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After|Subject Alternative Name)"
        
        print_status "✓ Certificate test completed" "$GREEN"
    else
        print_status "✗ Certificate file not found: $cert_file" "$RED"
        return 1
    fi
}

# Main execution
main() {
    print_status "=== Baker Street Labs Linux PKI Integration ===" "$BLUE"
    print_status "This script demonstrates Linux integration with Windows CA" "$YELLOW"
    print_status "===============================================" "$BLUE"
    
    # Check prerequisites
    check_prerequisites
    
    # Install Root CA certificate
    install_root_ca
    
    # Generate certificate request
    csr_file=$(generate_certificate_request)
    
    # Submit certificate request
    submit_certificate_request "$csr_file"
    
    # Configure web server
    configure_web_server
    
    # Configure SSSD
    configure_sssd
    
    # Test certificate
    test_certificate
    
    print_status "`n=== INTEGRATION COMPLETE ===" "$GREEN"
    print_status "Linux system integrated with Baker Street Labs PKI" "$WHITE"
    print_status "`nNext steps:" "$YELLOW"
    print_status "1. Test web server SSL configuration" "$WHITE"
    print_status "2. Test certificate-based authentication" "$WHITE"
    print_status "3. Configure certificate auto-renewal" "$WHITE"
    print_status "4. Set up monitoring and alerts" "$WHITE"
}

# Run main function
main "$@"
