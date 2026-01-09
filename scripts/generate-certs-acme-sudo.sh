#!/usr/bin/env bash
#
# Generate Firewall Certificates Using ACME with sudo
# Runs step ca certificate with sudo to bind to port 80
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

set -e

CERTS_DIR="/home/richard/certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "======================================================================="
echo "Generating Firewall Certificates via ACME (HTTP Challenge)"
echo "======================================================================="
echo ""

FIREWALLS=("rangeplatform:192.168.0.62" "rangeagentix:192.168.0.64" "rangelande:192.168.0.67" "rangexsiam:192.168.0.62")

for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    IP="${FW##*:}"
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "[$NAME] Generating certificate for $FQDN ..."
    echo "  [INFO] This will use HTTP challenge on port 80 (requires sudo)"
    
    # Use sudo to run step ca certificate (needs port 80)
    sudo -E step ca certificate "$FQDN" "${NAME}-mgmt.crt" "${NAME}-mgmt.key" --not-after 8760h
    
    if [ $? -eq 0 ]; then
        # Fix ownership
        sudo chown richard:richard "${NAME}-mgmt.crt" "${NAME}-mgmt.key"
        
        echo "  [OK] Certificate: ${NAME}-mgmt.crt"
        echo "  [OK] Private Key: ${NAME}-mgmt.key"
        
        # Bundle into PKCS12
        openssl pkcs12 -export \
            -out "${NAME}-mgmt.pfx" \
            -inkey "${NAME}-mgmt.key" \
            -in "${NAME}-mgmt.crt" \
            -certfile ~/.step/certs/intermediate_ca.crt \
            -passout pass:BakerStreet2025
        
        echo "  [OK] PKCS12: ${NAME}-mgmt.pfx"
    else
        echo "  [ERROR] Failed to generate certificate for $NAME"
    fi
    
    echo ""
done

echo "======================================================================="
echo "[OK] Certificate Generation Complete!"
echo "======================================================================="
echo ""
ls -lh *-mgmt.{crt,key,pfx} 2>/dev/null
echo ""

