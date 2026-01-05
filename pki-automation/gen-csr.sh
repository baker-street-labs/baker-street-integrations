#!/bin/bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

set -e
sudo mkdir -p /opt/step-ca
cd /opt/step-ca
sudo openssl req -new -newkey rsa:2048 -nodes -keyout intermediate.key -out intermediate.csr -subj "/C=US/ST=Virginia/L=Cybersecurity Lab/O=Baker Street Labs/CN=Baker Street Labs Issuing CA" -addext "subjectAltName=DNS:bakerservices.ad.bakerstreetlabs.io" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,digitalSignature,keyCertSign,cRLSign"
echo "[OK] CSR generated successfully"
echo "CSR Content:"
sudo cat intermediate.csr