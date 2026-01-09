#!/bin/bash
set -e

cd /opt/step-ca
sudo mkdir -p /opt/step-ca/firewall-certs
cd /opt/step-ca/firewall-certs

echo "[1/6] Generating rangengfw SSL Decryption CA..."
sudo openssl genrsa -out rangengfw.key 2048
sudo openssl req -new -key rangengfw.key -out rangengfw.csr -subj "/C=US/ST=Virginia/O=Baker Street Labs/CN=rangengfw SSL Decryption CA" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,digitalSignature,keyCertSign,cRLSign"

echo "[2/6] Signing rangengfw certificate with Subordinate CA..."
sudo openssl x509 -req -in rangengfw.csr -CA /opt/step-ca/intermediate.cer -CAkey /opt/step-ca/intermediate.key -CAcreateserial -out rangengfw.crt -days 365 -sha256 -extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,digitalSignature,keyCertSign,cRLSign")

echo "[3/6] Creating rangengfw PFX bundle..."
sudo openssl pkcs12 -export -out rangengfw.pfx -inkey rangengfw.key -in rangengfw.crt -certfile /opt/step-ca/intermediate.cer -passout pass:BakerStreet2025

echo "[4/6] Generating xdrngfw SSL Decryption CA..."
sudo openssl genrsa -out xdrngfw.key 2048
sudo openssl req -new -key xdrngfw.key -out xdrngfw.csr -subj "/C=US/ST=Virginia/O=Baker Street Labs/CN=xdrngfw SSL Decryption CA" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,digitalSignature,keyCertSign,cRLSign"

echo "[5/6] Signing xdrngfw certificate with Subordinate CA..."
sudo openssl x509 -req -in xdrngfw.csr -CA /opt/step-ca/intermediate.cer -CAkey /opt/step-ca/intermediate.key -CAcreateserial -out xdrngfw.crt -days 365 -sha256 -extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,digitalSignature,keyCertSign,cRLSign")

echo "[6/6] Creating xdrngfw PFX bundle..."
sudo openssl pkcs12 -export -out xdrngfw.pfx -inkey xdrngfw.key -in xdrngfw.crt -certfile /opt/step-ca/intermediate.cer -passout pass:BakerStreet2025

echo ""
echo "[VALIDATION] Listing generated certificates..."
ls -lh /opt/step-ca/firewall-certs/*.{crt,pfx} 2>/dev/null

echo ""
echo "[VALIDATION] Verifying certificate chains..."
openssl verify -CAfile /opt/step-ca/root-ca.crt -untrusted /opt/step-ca/intermediate.cer /opt/step-ca/firewall-certs/rangengfw.crt
openssl verify -CAfile /opt/step-ca/root-ca.crt -untrusted /opt/step-ca/intermediate.cer /opt/step-ca/firewall-certs/xdrngfw.crt

echo ""
echo "[SUCCESS] SSL Decryption certificates generated!"
echo "Password for PFX files: BakerStreet2025"