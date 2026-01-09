#!/usr/bin/env bash
#
# Deploy Management Certificates to All Range Firewalls
# Generates certificates via step-ca and imports them to PAN-OS devices
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

set -e

echo "======================================================================="
echo "Baker Street Labs - Firewall Certificate Deployment"
echo "======================================================================="
echo ""

# Configuration
CERTS_DIR="/home/richard/certs"
PFX_PASSPHRASE="BakerStreet2025"
PANOS_PASSWORD="H4@sxXtauczXhZxWYETQ"
PANOS_USERNAME="bakerstreet"

# Firewall definitions: hostname:ip
FIREWALLS=(
    "rangeplatform:192.168.0.62"
    "rangeagentix:192.168.0.64"
    "rangelande:192.168.0.67"
    "rangexsiam:192.168.0.62"
)

# Create certs directory
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "[1/3] Generating SSL certificates via step-ca..."
echo ""

for fw in "${FIREWALLS[@]}"; do
    NAME="${fw%%:*}"
    IP="${fw##*:}"
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "  Processing: $NAME ($IP) ..."
    
    # Generate certificate and key
    if step ca certificate "$FQDN" "${NAME}-mgmt.crt" "${NAME}-mgmt.key" --not-after 8760h; then
        echo "    [OK] Certificate generated: ${NAME}-mgmt.crt"
        echo "    [OK] Private key generated: ${NAME}-mgmt.key"
    else
        echo "    [ERROR] Failed to generate certificate for $NAME"
        exit 1
    fi
    
    echo ""
done

echo "[2/3] Bundling certificates into PKCS12 format..."
echo ""

for fw in "${FIREWALLS[@]}"; do
    NAME="${fw%%:*}"
    
    echo "  Bundling: ${NAME}-mgmt.pfx ..."
    
    # Bundle cert + key + CA chain into PKCS12
    if openssl pkcs12 -export \
        -out "${NAME}-mgmt.pfx" \
        -inkey "${NAME}-mgmt.key" \
        -in "${NAME}-mgmt.crt" \
        -certfile /home/richard/.step/certs/intermediate_ca.crt \
        -passout pass:"$PFX_PASSPHRASE"; then
        echo "    [OK] PKCS12 bundle created: ${NAME}-mgmt.pfx"
    else
        echo "    [ERROR] Failed to create PKCS12 for $NAME"
        exit 1
    fi
    
    echo ""
done

echo "[3/3] Importing certificates to firewalls..."
echo ""

for fw in "${FIREWALLS[@]}"; do
    NAME="${fw%%:*}"
    IP="${fw##*:}"
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "  Importing to: $NAME ($FQDN) ..."
    
    # Generate API key for this firewall
    echo "    Generating API key..."
    API_KEY=$(curl -k -s -X POST \
        "https://${FQDN}/api/?type=keygen&user=${PANOS_USERNAME}&password=${PANOS_PASSWORD}" \
        | grep -oP '(?<=<key>)[^<]+' || echo "")
    
    if [ -z "$API_KEY" ]; then
        echo "    [ERROR] Failed to generate API key for $NAME"
        echo "    [INFO] Trying with IP address instead..."
        
        API_KEY=$(curl -k -s -X POST \
            "https://${IP}/api/?type=keygen&user=${PANOS_USERNAME}&password=${PANOS_PASSWORD}" \
            | grep -oP '(?<=<key>)[^<]+' || echo "")
        
        if [ -z "$API_KEY" ]; then
            echo "    [ERROR] Failed to generate API key with IP either"
            continue
        fi
    fi
    
    echo "    [OK] API key generated"
    
    # Import certificate using Python script
    echo "    Importing certificate..."
    python3 /home/richard/certs/import_mgmt_cert.py \
        --api-key "$API_KEY" \
        --hostname "$FQDN" \
        --cert-name "${NAME}-mgmt-https" \
        --pfx-path "${NAME}-mgmt.pfx" \
        --passphrase "$PFX_PASSPHRASE" \
        --configure-mgmt \
        --commit
    
    if [ $? -eq 0 ]; then
        echo "    [OK] Certificate imported and configured on $NAME"
    else
        echo "    [ERROR] Failed to import certificate to $NAME"
    fi
    
    echo ""
done

echo "======================================================================="
echo "Deployment Summary"
echo "======================================================================="
echo ""
echo "Certificates generated in: $CERTS_DIR"
echo ""
ls -lh "$CERTS_DIR"/*.pfx 2>/dev/null || echo "No PFX files found"
echo ""
echo "Next Steps:"
echo "  1. Verify certificates in firewall web UI"
echo "  2. Test HTTPS access to each firewall:"
for fw in "${FIREWALLS[@]}"; do
    NAME="${fw%%:*}"
    echo "     - https://${NAME}.bakerstreetlabs.io"
done
echo "  3. Import Root CA to browser trust store if needed"
echo ""
echo "======================================================================="
echo "[OK] Deployment Complete!"
echo "======================================================================="

