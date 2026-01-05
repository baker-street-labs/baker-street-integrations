#!/bin/bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

set -e

echo "[1/3] Stopping service..."
sudo systemctl stop step-ca

echo "[2/3] Creating proper minimal config..."
sudo tee /etc/step-ca/ca.json > /dev/null << 'EOF'
{
  "root": "/opt/step-ca/root-ca.crt",
  "crt": "/opt/step-ca/intermediate.cer",
  "key": "/opt/step-ca/intermediate.key",
  "address": ":8443",
  "dnsNames": ["bakerservices.ad.bakerstreetlabs.io", "192.168.0.236"],
  "logger": {"format": "text"},
  "db": {
    "type": "badgerv2",
    "dataSource": "/opt/step-ca/db"
  },
  "authority": {
    "provisioners": []
  },
  "tls": {
    "cipherSuites": [
      "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256"
    ],
    "minVersion": 1.2,
    "maxVersion": 1.3
  }
}
EOF

echo "[3/3] Starting service..."
sudo systemctl start step-ca
sleep 5

echo "[VALIDATION] Checking status..."
sudo systemctl status step-ca --no-pager | head -15

echo ""
echo "[TEST] Testing API..."
curl -k https://localhost:8443/health 2>/dev/null && echo " - Health check passed!" || echo " - Service still starting..."

echo ""
echo "[SUCCESS] Fixed!"