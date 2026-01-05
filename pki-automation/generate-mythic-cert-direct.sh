#!/usr/bin/env bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

#
# Generate Mythic C2 SSL Certificate Using Direct CA Signing
# 100% Automated - Agentix Style
#
# Method: Direct signing with step-ca intermediate CA
# No HTTP challenge, no token auth, pure automation
#
# Author: Baker Street Labs
# Date: October 23, 2025
#

set -e

# Configuration
FQDN="mythic.bakerstreetlabs.io"
CERT_DIR="/opt/mythic/nginx-docker/ssl"
TEMP_DIR="/tmp/mythic-cert-gen"
CA_CERT="/opt/step-ca/intermediate.cer"
CA_KEY="/opt/step-ca/intermediate.key"
ROOT_CA="/opt/step-ca/root-ca.crt"

echo "=========================================================================="
echo "Mythic C2 Certificate Generation - Agentix Automated"
echo "=========================================================================="
echo ""
echo "FQDN:       $FQDN"
echo "Target Dir: $CERT_DIR"
echo "CA Cert:    $CA_CERT"
echo ""

# Step 1: Create temp directory
sudo mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Step 2: Generate private key
echo "[1/6] Generating RSA private key..."
sudo openssl genrsa -out mythic.key 2048
echo "  [OK] Private key generated"
echo ""

# Step 3: Create CSR
echo "[2/6] Creating Certificate Signing Request..."
sudo openssl req -new -key mythic.key -out mythic.csr \
  -subj "/C=US/ST=California/L=Baker Street/O=Baker Street Labs/OU=Cyber Range/CN=mythic.bakerstreetlabs.io"

echo "  [OK] CSR created"
echo ""

# Step 4: Create SAN extension file
echo "[3/6] Creating SAN extension configuration..."
sudo tee mythic-san.cnf > /dev/null <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]

[v3_req]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = mythic.bakerstreetlabs.io
DNS.2 = directory01.ad.bakerstreetlabs.io
DNS.3 = directory01
DNS.4 = localhost
IP.1 = 192.168.0.236
IP.2 = 127.0.0.1
EOF

echo "  [OK] SAN config created"
echo ""

# Step 5: Sign certificate with intermediate CA
echo "[4/6] Signing certificate with Baker Street Labs Issuing CA..."
sudo openssl x509 -req -in mythic.csr \
  -CA "$CA_CERT" \
  -CAkey "$CA_KEY" \
  -CAcreateserial \
  -out mythic.crt \
  -days 365 \
  -sha256 \
  -extensions v3_req \
  -extfile mythic-san.cnf

if [ $? -eq 0 ]; then
  echo "  [OK] Certificate signed"
else
  echo "  [ERROR] Certificate signing failed"
  exit 1
fi

echo ""

# Step 6: Create certificate chain
echo "[5/6] Creating certificate chain..."
sudo bash -c "cat mythic.crt \"$CA_CERT\" \"$ROOT_CA\" > mythic-chain.crt"
echo "  [OK] Certificate chain created"
echo ""

# Step 7: Verify certificate
echo "Certificate verification:"
openssl x509 -in mythic.crt -noout -subject
openssl x509 -in mythic.crt -noout -dates
openssl x509 -in mythic.crt -noout -issuer
echo ""

# Step 8: Backup existing Mythic certs
echo "[6/6] Backing up and installing certificates..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo cp -f "$CERT_DIR/mythic-cert.crt" "$CERT_DIR/mythic-cert.crt.bak.$TIMESTAMP" 2>/dev/null || echo "  No existing cert"
sudo cp -f "$CERT_DIR/mythic-ssl.key" "$CERT_DIR/mythic-ssl.key.bak.$TIMESTAMP" 2>/dev/null || echo "  No existing key"

# Install new certificates
sudo cp mythic-chain.crt "$CERT_DIR/mythic-cert.crt"
sudo cp mythic.key "$CERT_DIR/mythic-ssl.key"
sudo chmod 644 "$CERT_DIR/mythic-cert.crt"
sudo chmod 600 "$CERT_DIR/mythic-ssl.key"

echo "  [OK] Certificates installed"
echo ""

# Step 9: Restart Mythic nginx
echo "Restarting Mythic nginx..."
sudo docker restart mythic_nginx

echo "Waiting for health check..."
sleep 8

if sudo docker ps --filter name=mythic_nginx --format "{{.Status}}" | grep -q "healthy"; then
  echo "  [OK] mythic_nginx is healthy"
else
  echo "  [WARNING] mythic_nginx not yet healthy (may take 30 seconds)"
fi

echo ""
echo "=========================================================================="
echo "  âœ… Mythic C2 Certificate Deployment COMPLETE!"
echo "=========================================================================="
echo ""
echo "Mythic C2 Access:"
echo "  HTTPS: https://mythic.bakerstreetlabs.io:7443"
echo "  IP:    https://192.168.0.236:7443"
echo ""
echo "Certificate Details:"
echo "  Subject: mythic.bakerstreetlabs.io"
echo "  Issuer:  Baker Street Labs Issuing CA"
echo "  Validity: 365 days"
echo "  SANs:    mythic.bakerstreetlabs.io, directory01.ad.bakerstreetlabs.io, 192.168.0.236"
echo ""
echo "Verification:"
echo "  curl -k https://mythic.bakerstreetlabs.io:7443/ | head -10"
echo "  openssl s_client -connect mythic.bakerstreetlabs.io:7443 -servername mythic.bakerstreetlabs.io"
echo ""
echo "Files in $CERT_DIR:"
sudo ls -lah "$CERT_DIR"
echo ""

