#!/bin/bash
set -e

cd /opt/step-ca
sudo mkdir -p /opt/step-ca/firewall-certs
cd /opt/step-ca/firewall-certs

# Create extension file
cat > /tmp/ca_ext.cnf << 'EOF'
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,digitalSignature,keyCertSign,cRLSign
EOF

echo "[1/6] Generating rangengfw SSL Decryption CA..."
sudo openssl genrsa -out rangengfw.key 2048
sudo openssl req -new -key rangengfw.key -out rangengfw.csr -subj "/C=US/ST=Virginia/O=Baker Street Labs/CN=rangengfw SSL Decryption CA"

echo "[2/6] Signing rangengfw certificate..."
sudo openssl x509 -req -in rangengfw.csr -CA /opt/step-ca/intermediate.cer -CAkey /opt/step-ca/intermediate.key -CAcreateserial -out rangengfw.crt -days 365 -sha256 -extfile /tmp/ca_ext.cnf

echo "[3/6] Creating rangengfw PFX..."
sudo openssl pkcs12 -export -out rangengfw.pfx -inkey rangengfw.key -in rangengfw.crt -certfile /opt/step-ca/intermediate.cer -passout pass:BakerStreet2025

echo "[4/6] Generating xdrngfw SSL Decryption CA..."
sudo openssl genrsa -out xdrngfw.key 2048
sudo openssl req -new -key xdrngfw.key -out xdrngfw.csr -subj "/C=US/ST=Virginia/O=Baker Street Labs/CN=xdrngfw SSL Decryption CA"

echo "[5/6] Signing xdrngfw certificate..."
sudo openssl x509 -req -in xdrngfw.csr -CA /opt/step-ca/intermediate.cer -CAkey /opt/step-ca/intermediate.key -CAcreateserial -out xdrngfw.crt -days 365 -sha256 -extfile /tmp/ca_ext.cnf

echo "[6/6] Creating xdrngfw PFX..."
sudo openssl pkcs12 -export -out xdrngfw.pfx -inkey xdrngfw.key -in xdrngfw.crt -certfile /opt/step-ca/intermediate.cer -passout pass:BakerStreet2025

sudo chmod 644 *.pfx

echo ""
echo "[SUCCESS] Generated certificates:"
ls -lh /opt/step-ca/firewall-certs/*.{crt,pfx}

echo ""
echo "[VERIFY] Checking certificate chains..."
openssl verify -CAfile /opt/step-ca/root-ca.crt -untrusted /opt/step-ca/intermediate.cer rangengfw.crt
openssl verify -CAfile /opt/step-ca/root-ca.crt -untrusted /opt/step-ca/intermediate.cer xdrngfw.crt

echo ""
echo "PFX Password: BakerStreet2025"