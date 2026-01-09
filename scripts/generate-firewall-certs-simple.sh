#!/usr/bin/env bash
#
# Generate Firewall Certificates - Simple Method
# Uses step-ca with offline token generation (no HTTP challenge required)
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

set -e

CERTS_DIR="/home/richard/certs"
cd "$CERTS_DIR"

echo "======================================================================="
echo "Generating Firewall Certificates (Offline Method)"
echo "======================================================================="
echo ""

# Generate certificates using step ca token + certificate commands
# This bypasses ACME HTTP challenge

FIREWALLS=("rangeplatform" "rangeagentix" "rangelande" "rangexsiam")

for NAME in "${FIREWALLS[@]}"; do
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "[${NAME}] Generating certificate for $FQDN ..."
    
    # Generate token for this FQDN
    TOKEN=$(step ca token "$FQDN" --not-after 8760h)
    
    if [ -z "$TOKEN" ]; then
        echo "  [ERROR] Failed to generate token"
        continue
    fi
    
    # Use token to get certificate
    step ca certificate "$FQDN" "${NAME}-mgmt.crt" "${NAME}-mgmt.key" --token "$TOKEN"
    
    if [ $? -eq 0 ]; then
        echo "  [OK] Certificate: ${NAME}-mgmt.crt"
        echo "  [OK] Private Key: ${NAME}-mgmt.key"
        
        # Bundle into PKCS12
        echo "  [INFO] Bundling into PKCS12..."
        openssl pkcs12 -export \
            -out "${NAME}-mgmt.pfx" \
            -inkey "${NAME}-mgmt.key" \
            -in "${NAME}-mgmt.crt" \
            -certfile ~/.step/certs/intermediate_ca.crt \
            -passout pass:BakerStreet2025
        
        echo "  [OK] PKCS12: ${NAME}-mgmt.pfx"
    else
        echo "  [ERROR] Failed to generate certificate"
    fi
    
    echo ""
done

echo "======================================================================="
echo "[OK] Certificate Generation Complete!"
echo "======================================================================="
echo ""
ls -lh *-mgmt.{crt,key,pfx} 2>/dev/null
echo ""

