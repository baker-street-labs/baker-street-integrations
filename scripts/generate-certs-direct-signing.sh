#!/usr/bin/env bash
#
# Generate Firewall SSL Certificates - Direct CA Signing
# Uses step-ca intermediate CA to sign certificates directly (no ACME)
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

CERTS_DIR="/home/richard/certs"
CA_CERT="/opt/step-ca/intermediate.cer"
CA_KEY="/opt/step-ca/intermediate.key"
ROOT_CERT="/opt/step-ca/root-ca.crt"
PFX_PASSPHRASE="BakerStreet2025"

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "======================================================================="
echo "Baker Street Labs - Firewall Certificate Generation"
echo "======================================================================="
echo ""
echo "Method: Direct CA Signing (OpenSSL)"
echo "CA Certificate: $CA_CERT"
echo "CA Key: $CA_KEY"
echo ""

# Firewall definitions: name:fqdn:ip
FIREWALLS=(
    "rangeplatform:rangeplatform.bakerstreetlabs.io:192.168.0.68"
    "rangeagentix:rangeagentix.bakerstreetlabs.io:192.168.0.64"
    "rangelande:rangelande.bakerstreetlabs.io:192.168.0.67"
    "rangexsiam:rangexsiam.bakerstreetlabs.io:192.168.0.62"
)

SUCCESS=0
FAILED=0

for FW in "${FIREWALLS[@]}"; do
    NAME="${FW%%:*}"
    TEMP="${FW#*:}"
    FQDN="${TEMP%%:*}"
    IP="${FW##*:}"
    
    echo "[$NAME] Generating certificate for $FQDN ..."
    
    # 1. Generate private key
    echo "  [1/4] Generating RSA private key..."
    sudo openssl genrsa -out "${NAME}-mgmt.key" 2048 2>/dev/null
    sudo chown richard:richard "${NAME}-mgmt.key"
    echo "    [OK] Private key: ${NAME}-mgmt.key"
    
    # 2. Create CSR
    echo "  [2/4] Creating certificate signing request..."
    sudo openssl req -new -key "${NAME}-mgmt.key" -out "${NAME}-mgmt.csr" \
        -subj "/C=US/ST=California/L=Los Angeles/O=Baker Street Labs/OU=Cyber Range/CN=${FQDN}" 2>/dev/null
    sudo chown richard:richard "${NAME}-mgmt.csr"
    echo "    [OK] CSR created"
    
    # 3. Create extensions file for SAN
    cat > "${NAME}-ext.cnf" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${FQDN}
DNS.2 = ${NAME}
IP.1 = ${IP}
EOF
    
    # 4. Sign certificate with intermediate CA
    echo "  [3/4] Signing certificate with Baker Street Labs Issuing CA..."
    sudo openssl x509 -req -in "${NAME}-mgmt.csr" \
        -CA "$CA_CERT" -CAkey "$CA_KEY" \
        -CAcreateserial -out "${NAME}-mgmt.crt" \
        -days 365 -sha256 \
        -extfile "${NAME}-ext.cnf" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        sudo chown richard:richard "${NAME}-mgmt.crt"
        echo "    [OK] Certificate signed: ${NAME}-mgmt.crt"
        
        # 5. Bundle into PKCS12 with full chain
        echo "  [4/4] Creating PKCS12 bundle..."
        
        # Create full chain file (cert + intermediate + root)
        cat "${NAME}-mgmt.crt" > "${NAME}-chain.crt"
        sudo cat "$CA_CERT" >> "${NAME}-chain.crt"
        sudo cat "$ROOT_CERT" >> "${NAME}-chain.crt"
        
        openssl pkcs12 -export \
            -out "${NAME}-mgmt.pfx" \
            -inkey "${NAME}-mgmt.key" \
            -in "${NAME}-chain.crt" \
            -passout pass:"$PFX_PASSPHRASE" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "    [OK] PKCS12 bundle: ${NAME}-mgmt.pfx"
            echo "    [OK] Passphrase: $PFX_PASSPHRASE"
            
            # Cleanup temp files
            rm -f "${NAME}-mgmt.csr" "${NAME}-ext.cnf" "${NAME}-chain.crt"
            
            # Verify certificate
            echo "    [INFO] Certificate details:"
            openssl x509 -in "${NAME}-mgmt.crt" -noout -subject -issuer -dates | sed 's/^/      /'
            
            ((SUCCESS++))
        else
            echo "    [ERROR] Failed to create PKCS12 bundle"
            ((FAILED++))
        fi
    else
        echo "    [ERROR] Failed to sign certificate"
        ((FAILED++))
    fi
    
    echo ""
done

echo "======================================================================="
echo "Certificate Generation Summary"
echo "======================================================================="
echo ""
echo "Success: $SUCCESS / ${#FIREWALLS[@]}"
echo "Failed: $FAILED / ${#FIREWALLS[@]}"
echo ""

if [ $SUCCESS -gt 0 ]; then
    echo "Generated Files:"
    ls -lh *-mgmt.{crt,key,pfx} 2>/dev/null
    echo ""
    echo "Certificate Details:"
    for FW in "${FIREWALLS[@]}"; do
        NAME="${FW%%:*}"
        if [ -f "${NAME}-mgmt.crt" ]; then
            echo ""
            echo "  [$NAME]"
            openssl x509 -in "${NAME}-mgmt.crt" -noout -text | grep -E "Subject:|Issuer:|Not Before|Not After|DNS:" | sed 's/^/    /'
        fi
    done
    echo ""
    echo "======================================================================="
    echo "[OK] Certificates ready for import!"
    echo "======================================================================="
    echo ""
    echo "Next Steps:"
    echo "  1. Copy PKCS12 files (.pfx) to local machine"
    echo "  2. Use import_mgmt_cert.py to import to each firewall"
    echo "  3. Passphrase for all PKCS12 files: $PFX_PASSPHRASE"
else
    echo "[ERROR] No certificates were successfully generated"
    exit 1
fi

echo ""

