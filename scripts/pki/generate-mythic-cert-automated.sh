#!/usr/bin/env bash
#
# Generate Mythic C2 SSL Certificate - Automated
# Uses StepCA token method (no HTTP challenge required)
# 100% agentix style automation
#
# Author: Baker Street Labs
# Date: October 23, 2025
#

set -e

FQDN="mythic.bakerstreetlabs.io"
CERT_DIR="/opt/mythic/nginx-docker/ssl"
TEMP_DIR="/tmp/mythic-certs"

echo "=========================================================================="
echo "Mythic C2 Certificate Generation - Automated (Agentix Style)"
echo "=========================================================================="
echo ""
echo "FQDN: $FQDN"
echo "Target: $CERT_DIR"
echo ""

# Step 1: Create temp directory
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Step 2: Generate one-time token from StepCA
echo "[1/5] Generating StepCA one-time token..."
TOKEN=$(sudo step ca token "$FQDN" \
  --ca-url https://192.168.0.236:8443 \
  --root /opt/step-ca/root-ca.crt \
  --provisioner acme \
  --not-after 8760h)

if [ -z "$TOKEN" ]; then
  echo "  [ERROR] Failed to generate token"
  exit 1
fi

echo "  [OK] Token generated"
echo ""

# Step 3: Request certificate using token (bypasses HTTP-01 challenge)
echo "[2/5] Requesting certificate from StepCA..."
sudo step ca certificate "$FQDN" \
  mythic-cert-new.crt mythic-key-new.key \
  --token "$TOKEN" \
  --ca-url https://192.168.0.236:8443 \
  --root /opt/step-ca/root-ca.crt \
  --san mythic.bakerstreetlabs.io \
  --san 192.168.0.236 \
  --san directory01.ad.bakerstreetlabs.io \
  --san localhost \
  --kty RSA --size 2048 \
  --not-after 2160h

if [ $? -eq 0 ]; then
  echo "  [OK] Certificate issued"
else
  echo "  [ERROR] Certificate generation failed"
  exit 1
fi

echo ""

# Step 4: Verify certificate
echo "[3/5] Verifying certificate..."
openssl x509 -in mythic-cert-new.crt -noout -text | grep -A5 "Subject:"
openssl x509 -in mythic-cert-new.crt -noout -dates
openssl x509 -in mythic-cert-new.crt -noout -issuer

echo ""

# Step 5: Backup existing certificates
echo "[4/5] Backing up existing Mythic certificates..."
sudo cp -f "$CERT_DIR/mythic-cert.crt" "$CERT_DIR/mythic-cert.crt.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || echo "  No existing cert to backup"
sudo cp -f "$CERT_DIR/mythic-ssl.key" "$CERT_DIR/mythic-ssl.key.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || echo "  No existing key to backup"

echo "  [OK] Backups created"
echo ""

# Step 6: Install new certificates
echo "[5/5] Installing new certificates..."
sudo cp mythic-cert-new.crt "$CERT_DIR/mythic-cert.crt"
sudo cp mythic-key-new.key "$CERT_DIR/mythic-ssl.key"
sudo chmod 644 "$CERT_DIR/mythic-cert.crt"
sudo chmod 600 "$CERT_DIR/mythic-ssl.key"

echo "  [OK] Certificates installed"
echo ""

# Step 7: Restart Mythic nginx to load new certificate
echo "Restarting Mythic nginx container..."
sudo docker restart mythic_nginx

echo ""
echo "Waiting for container to be healthy..."
sleep 5

if sudo docker ps --filter name=mythic_nginx --format "{{.Status}}" | grep -q "healthy"; then
  echo "  [OK] mythic_nginx restarted and healthy"
else
  echo "  [WARNING] mythic_nginx may not be fully ready yet"
fi

echo ""
echo "=========================================================================="
echo "  ✅ Mythic C2 Certificate Installation Complete!"
echo "=========================================================================="
echo ""
echo "Certificate Details:"
openssl x509 -in "$CERT_DIR/mythic-cert.crt" -noout -subject -dates -issuer
echo ""
echo "Verification:"
echo "  1. Test HTTPS:"
echo "     curl -k https://mythic.bakerstreetlabs.io:7443/"
echo ""
echo "  2. Check certificate via browser:"
echo "     https://mythic.bakerstreetlabs.io:7443"
echo ""
echo "  3. View nginx logs:"
echo "     sudo docker logs mythic_nginx --tail 20"
echo ""
echo "Certificate files:"
ls -lah "$CERT_DIR/"
echo ""

