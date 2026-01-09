#!/bin/bash
# Generate SSL certificates for all ranges using direct OpenSSL signing
# Baker Street Labs - October 23, 2025

set -e  # Exit on error

RANGES=("rangexsiam" "rangeagentix" "rangelande" "rangeplatform")
OUTPUT_DIR="/opt/step-ca/certificates"
INTERMEDIATE_CERT="/opt/step-ca/intermediate.cer"
INTERMEDIATE_KEY="/opt/step-ca/intermediate.key"

echo "========================================="
echo "Baker Street Labs - Range Certificate Generation"
echo "Using Direct Certificate Signing Method"
echo "========================================="
echo ""

# Check prerequisites
if [ ! -f "$INTERMEDIATE_CERT" ] || [ ! -f "$INTERMEDIATE_KEY" ]; then
    echo "ERROR: Intermediate CA cert or key not found"
    echo "  Cert: $INTERMEDIATE_CERT"
    echo "  Key: $INTERMEDIATE_KEY"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
chmod 755 "$OUTPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Generate certificates for each range
for range in "${RANGES[@]}"; do
    echo "========================================="
    echo "Generating certificate for ${range}.bakerstreetlabs.io"
    echo "========================================="
    
    FQDN="${range}.bakerstreetlabs.io"
    CERT_FILE="${OUTPUT_DIR}/${range}-mgmt.crt"
    KEY_FILE="${OUTPUT_DIR}/${range}-mgmt.key"
    CSR_FILE="${OUTPUT_DIR}/${range}-mgmt.csr"
    
    # Check if certificate already exists and is valid
    if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
        echo "  Checking existing certificate..."
        
        if openssl x509 -in "$CERT_FILE" -noout -checkend 86400 2>/dev/null; then
            echo "  ✓ Existing certificate is valid, skipping generation"
            echo ""
            continue
        else
            echo "  ⚠ Existing certificate expired or invalid, regenerating..."
        fi
    fi
    
    # Step 1: Generate private key
    echo "  [1/10] Generating RSA private key..."
    openssl genrsa -out "$KEY_FILE" 2048 2>/dev/null
    chmod 600 "$KEY_FILE"
    echo "  ✓ Private key generated"
    
    # Step 2: Generate CSR
    echo "  [2/10] Generating certificate signing request..."
    openssl req -new -key "$KEY_FILE" \
        -out "$CSR_FILE" \
        -subj "/CN=${FQDN}" \
        2>/dev/null
    echo "  ✓ CSR generated"
    
    # Step 3: Sign certificate with Intermediate CA
    echo "  [3/10] Signing certificate with Baker Street Labs Issuing CA..."
    openssl x509 -req \
        -in "$CSR_FILE" \
        -CA "$INTERMEDIATE_CERT" \
        -CAkey "$INTERMEDIATE_KEY" \
        -CAcreateserial \
        -out "$CERT_FILE" \
        -days 365 \
        -sha256 \
        -extensions v3_req \
        -extfile <(cat <<EOF
[v3_req]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = DNS:${FQDN}
EOF
) 2>/dev/null
    
    chmod 644 "$CERT_FILE"
    echo "  ✓ Certificate signed"
    
    # Clean up CSR
    rm -f "$CSR_FILE"
    
    # Step 4: Convert private key to BASE64 DER format (PAN-OS requirement)
    echo "  [4/10] Converting private key to BASE64 DER format..."
    openssl rsa -in "$KEY_FILE" -outform DER 2>/dev/null | base64 -w 0 > "${OUTPUT_DIR}/${range}-mgmt.key.b64"
    echo "  ✓ Private key converted"
    
    # Step 5-10: Extract certificate metadata
    echo "  [5/10] Extracting subject hash..."
    openssl x509 -in "$CERT_FILE" -noout -subject_hash 2>/dev/null > "${OUTPUT_DIR}/${range}-subject-hash.txt"
    
    echo "  [6/10] Extracting issuer hash..."
    openssl x509 -in "$CERT_FILE" -noout -issuer_hash 2>/dev/null > "${OUTPUT_DIR}/${range}-issuer-hash.txt"
    
    echo "  [7/10] Extracting validity dates..."
    openssl x509 -in "$CERT_FILE" -noout -startdate 2>/dev/null | cut -d= -f2 > "${OUTPUT_DIR}/${range}-not-before.txt"
    openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2 > "${OUTPUT_DIR}/${range}-not-after.txt"
    
    echo "  [8/10] Calculating expiry epoch..."
    NOT_AFTER=$(cat "${OUTPUT_DIR}/${range}-not-after.txt")
    date -d "$NOT_AFTER" +%s > "${OUTPUT_DIR}/${range}-expiry-epoch.txt" 2>/dev/null
    
    echo "  [9/10] Extracting issuer and subject DNs..."
    openssl x509 -in "$CERT_FILE" -noout -issuer 2>/dev/null | sed 's/issuer=//' > "${OUTPUT_DIR}/${range}-issuer.txt"
    openssl x509 -in "$CERT_FILE" -noout -subject 2>/dev/null | sed 's/subject=//' > "${OUTPUT_DIR}/${range}-subject.txt"
    
    echo "  [10/10] Extracting common name..."
    echo "$FQDN" > "${OUTPUT_DIR}/${range}-cn.txt"
    
    echo ""
    echo "  ✓ ${range} certificate complete!"
    echo "    - Certificate: $CERT_FILE"
    echo "    - Private Key: $KEY_FILE"
    echo "    - BASE64 Key: ${OUTPUT_DIR}/${range}-mgmt.key.b64"
    echo "    - Metadata: 7 files"
    
    # Display certificate info
    echo "    - Valid from: $(cat ${OUTPUT_DIR}/${range}-not-before.txt)"
    echo "    - Valid until: $(cat ${OUTPUT_DIR}/${range}-not-after.txt)"
    echo ""
done

echo "========================================="
echo "Certificate Generation Complete!"
echo "========================================="
echo ""
echo "Generated certificates for:"
for range in "${RANGES[@]}"; do
    if [ -f "${OUTPUT_DIR}/${range}-mgmt.crt" ]; then
        echo "  ✓ ${range}.bakerstreetlabs.io"
    else
        echo "  ✗ ${range}.bakerstreetlabs.io (FAILED)"
    fi
done
echo ""
echo "All certificate files stored in: $OUTPUT_DIR/"
echo ""
echo "Next step: Run create_range_ngfw_with_certs.py to generate configs"
echo "========================================="
