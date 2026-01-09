#!/bin/bash
set -e
cd /opt/step-ca

echo "[1/5] Setting up directories..."
sudo mkdir -p /etc/step-ca
sudo chown -R root:root /opt/step-ca

echo "[2/5] Generating password file..."
openssl rand -hex 32 | sudo tee /opt/step-ca/password.txt > /dev/null
sudo chmod 600 /opt/step-ca/password.txt

echo "[3/5] Creating step-ca config..."
sudo tee /etc/step-ca/ca.json > /dev/null << 'EOF'
{
  "root": "/opt/step-ca/root-ca.crt",
  "federatedRoots": null,
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
    "provisioners": [
      {
        "type": "JWK",
        "name": "admin",
        "key": {
          "use": "sig",
          "kty": "EC",
          "kid": "admin",
          "crv": "P-256",
          "alg": "ES256",
          "x": "$(openssl rand -base64 32 | tr -d '\n')",
          "y": "$(openssl rand -base64 32 | tr -d '\n')"
        },
        "encryptedKey": "$(openssl rand -base64 64 | tr -d '\n')"
      }
    ]
  },
  "tls": {
    "cipherSuites": [
      "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256"
    ],
    "minVersion": 1.2,
    "maxVersion": 1.3,
    "renegotiation": false
  }
}
EOF

echo "[4/5] Creating database directory..."
sudo mkdir -p /opt/step-ca/db
sudo chown -R root:root /opt/step-ca/db

echo "[5/5] Validating certificates..."
openssl x509 -in /opt/step-ca/root-ca.crt -text -noout | grep "Subject:"
openssl x509 -in /opt/step-ca/intermediate.cer -text -noout | grep "Subject:"

echo "[SUCCESS] step-ca initialized!"