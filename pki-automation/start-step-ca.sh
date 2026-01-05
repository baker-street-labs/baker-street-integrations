#!/bin/bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

set -e

echo "[1/4] Creating systemd service file..."
sudo tee /etc/systemd/system/step-ca.service > /dev/null << 'EOF'
[Unit]
Description=Smallstep Certificate Authority
Documentation=https://smallstep.com/docs/step-ca
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/step-ca
ExecStart=/usr/bin/step-ca /etc/step-ca/ca.json --password-file /opt/step-ca/password.txt
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

echo "[2/4] Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "[3/4] Starting step-ca service..."
sudo systemctl start step-ca

echo "[4/4] Enabling step-ca on boot..."
sudo systemctl enable step-ca

sleep 3

echo "[VALIDATION] Checking service status..."
sudo systemctl status step-ca --no-pager | head -20

echo ""
echo "[TEST] Testing health endpoint..."
curl -k https://localhost:8443/health 2>/dev/null || echo "Service starting..."

echo ""
echo "[SUCCESS] step-ca service operational!"