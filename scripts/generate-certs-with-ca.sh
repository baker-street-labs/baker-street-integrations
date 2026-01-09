#!/usr/bin/env bash
#
# Generate Firewall Certificates Using CA Directly
# Signs certificates with intermediate CA using openssl
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

set -e

CERTS_DIR="/home/richard/certs"
CA_CERT="$HOME/.step/certs/intermediate_ca.crt"
CA_KEY="$HOME/.step/secrets/intermediate_ca_key"

# Check if CA key exists
if [ ! -f "$CA_KEY" ]; then
    echo "[ERROR] CA private key not found at: $CA_KEY"
    echo "[INFO] Checking alternative locations..."
    
    # Try to find in step-ca config
    CA_KEY=$(grep -r "key" ~/.step/config/ 2>/dev/null | grep -oP '"/[^"]+key[^"]*"' | tr -d '"' | head -1 || echo "")
    
    if [ -z "$CA_KEY" ] || [ ! -f "$CA_KEY" ]; then
        echo "[ERROR] Cannot find CA private key"
        echo "[INFO] step-ca with ACME-only provisioner cannot issue certs this way"
        echo ""
        echo "Alternative: Use Windows CA to issue certificates"
        echo "  1. Export CSR from firewall"
        echo "  2. Submit to Windows CA (bakerstreeta)"
        echo "  3. Import signed certificate back to firewall"
        exit 1
    fi
fi

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "======================================================================="
echo "Generating Firewall Certificates Using Intermediate CA"
echo "======================================================================="
echo ""
echo "CA Certificate: $CA_CERT"
echo "CA Key: $CA_KEY"
echo ""

FIREWALLS=("rangeplatform:192.168.0.62" "rangeagentix:192.168.0.64" "rangelande:192.168.0.67" "rangexsiam:192.168.0.62")

for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    IP="${FW##*:}"
    FQDN="${NAME}.bakerstreetlabs.io"
    
    echo "[$NAME] Generating certificate for $FQDN ($IP) ..."
    
    # Generate private key
    openssl genrsa -out "${NAME}-mgmt.key" 2048
    echo "  [OK] Private key generated"
    
    # Create certificate request
    openssl req -new -key "${NAME}-mgmt.key" -out "${NAME}-mgmt.csr" \
        -subj "/C=US/ST=California/L=Los Angeles/O=Baker Street Labs/OU=Cyber Range/CN=${FQDN}"
    echo "  [OK] CSR generated"
    
    # Create extension file for SAN
    cat > "${NAME}-ext.cnf" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${FQDN}
DNS.2 = ${NAME}
IP.1 = ${IP}
EOF
    
    # Sign with CA
    openssl x509 -req -in "${NAME}-mgmt.csr" \
        -CA "$CA_CERT" -CAkey "$CA_KEY" \
        -CAcreateserial -out "${NAME}-mgmt.crt" \
        -days 365 -sha256 \
        -extfile "${NAME}-ext.cnf"
    
    if [ $? -eq 0 ]; then
        echo "  [OK] Certificate signed"
        
        # Bundle into PKCS12
        openssl pkcs12 -export \
            -out "${NAME}-mgmt.pfx" \
            -inkey "${NAME}-mgmt.key" \
            -in "${NAME}-mgmt.crt" \
            -certfile "$CA_CERT" \
            -passout pass:BakerStreet2025
        
        echo "  [OK] PKCS12 bundle created: ${NAME}-mgmt.pfx"
        
        # Cleanup temp files
        rm -f "${NAME}-mgmt.csr" "${NAME}-ext.cnf"
    else
        echo "  [ERROR] Failed to sign certificate"
    fi
    
    echo ""
done

echo "======================================================================="
echo "[OK] Certificate Generation Complete!"
echo "======================================================================="
echo ""
ls -lh *-mgmt.{crt,key,pfx} 2>/dev/null
echo ""
echo "Certificates generated for all firewalls."
echo "Next: Import using import_mgmt_cert.py"
echo ""

