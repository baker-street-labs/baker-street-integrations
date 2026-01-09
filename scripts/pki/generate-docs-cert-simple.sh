#!/usr/bin/env bash
#
# Generate SSL Certificate for docs.bakerstreetlabs.io
# Using StepCA direct signing
#

set -e

CERT_CN="docs.bakerstreetlabs.io"
CERT_IP="192.168.253.11"
WORK_DIR="/tmp/docs-cert-gen"
CA_CERT="/opt/step-ca/intermediate.cer"
CA_KEY="/opt/step-ca/intermediate.key"
OUTPUT_DIR="/opt/docs-ssl"

echo "=========================================="
echo "Generate SSL Certificate for Docs Site"
echo "=========================================="
echo "CN: $CERT_CN"
echo "IP: $CERT_IP"
echo ""

# Create working directory
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Create output directory
sudo mkdir -p "$OUTPUT_DIR"

echo "Generating private key..."
openssl genrsa -out docs.key 2048

echo "Creating OpenSSL config..."
cat > openssl.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
CN = $CERT_CN
O = Baker Street Labs
OU = Documentation Services

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $CERT_CN
DNS.2 = docs.ad.bakerstreetlabs.io
DNS.3 = documentation.bakerstreetlabs.io
IP.1 = $CERT_IP
IP.2 = 192.168.0.236
EOF

echo "Creating certificate request..."
openssl req -new -key docs.key -out docs.csr -config openssl.cnf

echo "Creating signing extensions..."
cat > signing.cnf <<EOF
subjectAltName = DNS:$CERT_CN,DNS:docs.ad.bakerstreetlabs.io,DNS:documentation.bakerstreetlabs.io,IP:$CERT_IP,IP:192.168.0.236
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF

echo "Signing certificate..."
sudo openssl x509 -req -in docs.csr \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out docs.crt \
    -days 365 \
    -sha256 \
    -extfile signing.cnf

echo "Installing certificates..."
sudo cp docs.crt "$OUTPUT_DIR/"
sudo cp docs.key "$OUTPUT_DIR/"
sudo chmod 644 "$OUTPUT_DIR/docs.crt"
sudo chmod 600 "$OUTPUT_DIR/docs.key"

# Create chain
sudo bash -c "cat docs.crt '$CA_CERT' > '$OUTPUT_DIR/docs-chain.crt'"

echo ""
echo "Certificate Details:"
openssl x509 -in docs.crt -noout -subject
openssl x509 -in docs.crt -noout -issuer
openssl x509 -in docs.crt -noout -dates

echo ""
echo "=========================================="
echo "✅ Certificate Generated"
echo "=========================================="
echo "Location: $OUTPUT_DIR/"
echo "  - docs.crt"
echo "  - docs.key"
echo "  - docs-chain.crt"
echo ""

