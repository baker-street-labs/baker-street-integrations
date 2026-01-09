#!/usr/bin/env bash
#
# Generate All Firewall Certificates Using step-ca ACME
# Temporarily stops Mythic nginx to free port 80 for ACME HTTP challenge
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

set -e

CERTS_DIR="/home/richard/certs"
PFX_PASSPHRASE="BakerStreet2025"

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "======================================================================="
echo "Baker Street Labs - Firewall Certificate Generation"
echo "======================================================================="
echo ""

# Firewall definitions
FIREWALLS=("rangeplatform:192.168.0.62" "rangeagentix:192.168.0.64" "rangelande:192.168.0.67" "rangexsiam:192.168.0.62")

echo "[1/4] Stopping Mythic nginx to free port 80..."
sudo docker stop mythic_nginx
echo "  [OK] Port 80 is now available for ACME HTTP challenge"
echo ""

echo "[2/4] Generating SSL certificates via step-ca ACME..."
echo ""

for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    IP="${FW##*:}"
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "  [$NAME] Generating certificate for $FQDN ..."
    
    # Use sudo for ACME HTTP challenge on port 80
    if sudo -E step ca certificate "$FQDN" "${NAME}-mgmt.crt" "${NAME}-mgmt.key" --not-after 8760h; then
        # Fix ownership
        sudo chown richard:richard "${NAME}-mgmt.crt" "${NAME}-mgmt.key"
        echo "    [OK] Certificate: ${NAME}-mgmt.crt"
        echo "    [OK] Private Key: ${NAME}-mgmt.key"
    else
        echo "    [ERROR] Failed to generate certificate for $NAME"
        # Continue anyway
    fi
    
    echo ""
done

echo "[3/4] Restarting Mythic nginx..."
sudo docker start mythic_nginx
echo "  [OK] Mythic nginx restarted"
echo ""

echo "[4/4] Bundling certificates into PKCS12 format..."
echo ""

for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    
    if [ -f "${NAME}-mgmt.crt" ] && [ -f "${NAME}-mgmt.key" ]; then
        echo "  [$NAME] Creating PKCS12 bundle..."
        
        openssl pkcs12 -export \
            -out "${NAME}-mgmt.pfx" \
            -inkey "${NAME}-mgmt.key" \
            -in "${NAME}-mgmt.crt" \
            -certfile ~/.step/certs/intermediate_ca.crt \
            -passout pass:"$PFX_PASSPHRASE"
        
        if [ $? -eq 0 ]; then
            echo "    [OK] PKCS12: ${NAME}-mgmt.pfx"
        else
            echo "    [ERROR] Failed to create PKCS12 for $NAME"
        fi
    else
        echo "  [$NAME] SKIPPED - certificate or key missing"
    fi
    
    echo ""
done

echo "======================================================================="
echo "Certificate Generation Summary"
echo "======================================================================="
echo ""

# Count successful certificates
SUCCESS=0
for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    if [ -f "${NAME}-mgmt.pfx" ]; then
        ((SUCCESS++))
        echo "[OK] $NAME - Certificate ready for import"
    else
        echo "[FAIL] $NAME - Certificate generation failed"
    fi
done

echo ""
echo "Certificates Generated: $SUCCESS / ${#FIREWALLS[@]}"
echo ""

if [ $SUCCESS -gt 0 ]; then
    echo "Files created:"
    ls -lh *-mgmt.{crt,key,pfx} 2>/dev/null || true
    echo ""
    echo "Next Step: Import certificates to firewalls using import_mgmt_cert.py"
fi

echo ""
echo "======================================================================="

