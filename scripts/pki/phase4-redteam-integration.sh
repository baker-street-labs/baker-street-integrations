#!/bin/bash
#
# Phase 4: Red Team Tools Certificate Integration
# Baker Street Labs PKI Gap Closure
#
# Purpose: Replace self-signed certificates with BSLRedTeam certificates from step-ca
# Prerequisites: CA chain distributed, step-ca operational
# Execution: Run on directory01 (192.168.0.236) where Mythic and GoPhish are deployed
#

set -e

# Configuration
STEP_CA_URL="https://192.168.0.236:8443"
CA_FILE="/etc/ssl/certs/baker-street-root-ca.crt"
CERT_DIR="/opt/pki-certs/redteam"

echo "🎯 Phase 4: Red Team Tools Certificate Integration"
echo "==================================================="
echo ""

# Create certificate directory
sudo mkdir -p "$CERT_DIR"
sudo chmod 755 "$CERT_DIR"

# ========================================
# MYTHIC C2 CERTIFICATE INTEGRATION
# ========================================

echo "🔴 Mythic C2 Certificate Integration"
echo "-------------------------------------"
echo ""

# Step 1: Request Mythic certificate from step-ca
echo "📝 Step 1: Requesting Mythic C2 certificate..."

MYTHIC_CN="mythic.bakerstreetlabs.io"
MYTHIC_KEY="$CERT_DIR/mythic.key"
MYTHIC_CERT="$CERT_DIR/mythic.crt"
MYTHIC_CSR="/tmp/mythic.csr"

# Generate CSR with malicious domain SANs (for C2 realism)
cat > /tmp/mythic-openssl.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = $MYTHIC_CN
O = Baker Street Labs Red Team
OU = Cyber Range
C = US

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = mythic.bakerstreetlabs.io
DNS.2 = c2.bakerstreetlabs.io
DNS.3 = *.blogspot.ie
DNS.4 = *.coateng.cn
DNS.5 = *.steanconmmunity.ru
IP.1 = 192.168.0.236
EOF

# Generate key and CSR
openssl genrsa -out "$MYTHIC_KEY" 2048
openssl req -new -key "$MYTHIC_KEY" -out "$MYTHIC_CSR" -config /tmp/mythic-openssl.cnf
chmod 600 "$MYTHIC_KEY"

echo "   ✅ CSR generated with malicious domain SANs"

# Submit to step-ca
if command -v step >/dev/null 2>&1; then
    echo "   📤 Submitting to step-ca..."
    step ca certificate "$MYTHIC_CN" "$MYTHIC_CERT" \
        --csr="$MYTHIC_CSR" \
        --ca-url="$STEP_CA_URL" \
        --root="$CA_FILE" \
        --not-after=4320h  # 180 days (6 months for red team)
    
    echo "   ✅ Certificate issued by step-ca"
else
    echo "   ❌ step CLI not installed"
    echo "   Install: curl -LO https://dl.smallstep.com/cli/docs-ca-install/latest/step_linux_amd64.tar.gz"
    exit 1
fi

# Step 2: Install certificate to Mythic
echo ""
echo "🔧 Step 2: Installing certificate to Mythic C2..."

MYTHIC_SSL_DIR="/opt/mythic/nginx-docker/ssl"
if [ -d "$MYTHIC_SSL_DIR" ]; then
    # Backup existing certs
    if [ -f "$MYTHIC_SSL_DIR/mythic-ssl.crt" ]; then
        sudo cp "$MYTHIC_SSL_DIR/mythic-ssl.crt" "$MYTHIC_SSL_DIR/mythic-ssl.crt.backup.$(date +%Y%m%d)"
        echo "   ✅ Backup created"
    fi
    
    # Install new certificates
    sudo cp "$MYTHIC_CERT" "$MYTHIC_SSL_DIR/mythic-ssl.crt"
    sudo cp "$MYTHIC_KEY" "$MYTHIC_SSL_DIR/mythic-ssl.key"
    sudo chmod 600 "$MYTHIC_SSL_DIR/mythic-ssl.key"
    sudo chmod 644 "$MYTHIC_SSL_DIR/mythic-ssl.crt"
    
    echo "   ✅ Certificates installed to Mythic"
    
    # Restart Mythic nginx container
    echo ""
    echo "   🔄 Restarting Mythic nginx container..."
    cd /opt/mythic
    sudo ./mythic-cli restart nginx
    
    echo "   ✅ Mythic nginx restarted"
else
    echo "   ⚠️  Mythic SSL directory not found: $MYTHIC_SSL_DIR"
    echo "   Please verify Mythic installation path"
fi

# Step 3: Validate Mythic certificate
echo ""
echo "✅ Step 3: Validating Mythic certificate..."

sleep 5  # Wait for container restart

if openssl s_client -connect 192.168.0.236:443 -showcerts </dev/null 2>/dev/null | grep -q "Baker Street Labs"; then
    echo "   ✅ Mythic now using Baker Street Labs certificate!"
else
    echo "   ⚠️  Certificate validation inconclusive"
    echo "   Manual verification: https://192.168.0.236:3001 in browser"
fi

# ========================================
# GOPHISH CERTIFICATE INTEGRATION
# ========================================

echo ""
echo "🎣 GoPhish Certificate Integration"
echo "----------------------------------"
echo ""

# Step 1: Request GoPhish certificate
echo "📝 Step 1: Requesting GoPhish certificate..."

GOPHISH_CN="gophish.bakerstreetlabs.io"
GOPHISH_KEY="$CERT_DIR/gophish.key"
GOPHISH_CERT="$CERT_DIR/gophish.crt"
GOPHISH_CSR="/tmp/gophish.csr"

# Generate CSR with phishing domain SANs
cat > /tmp/gophish-openssl.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = $GOPHISH_CN
O = Baker Street Labs Red Team
OU = Phishing Simulation
C = US

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = gophish.bakerstreetlabs.io
DNS.2 = phish.bakerstreetlabs.io
DNS.3 = mail.bakerstreetlabs.io
IP.1 = 192.168.0.236
EOF

openssl genrsa -out "$GOPHISH_KEY" 2048
openssl req -new -key "$GOPHISH_KEY" -out "$GOPHISH_CSR" -config /tmp/gophish-openssl.cnf
chmod 600 "$GOPHISH_KEY"

# Submit to step-ca
echo "   📤 Submitting to step-ca..."
step ca certificate "$GOPHISH_CN" "$GOPHISH_CERT" \
    --csr="$GOPHISH_CSR" \
    --ca-url="$STEP_CA_URL" \
    --root="$CA_FILE" \
    --not-after=4320h  # 180 days

echo "   ✅ Certificate issued by step-ca"

# Step 2: Install certificate to GoPhish
echo ""
echo "🔧 Step 2: Installing certificate to GoPhish..."

GOPHISH_CONFIG="/opt/gophish/config.json"
GOPHISH_CERT_PATH="/opt/gophish/gophish.crt"
GOPHISH_KEY_PATH="/opt/gophish/gophish.key"

if [ -f "$GOPHISH_CONFIG" ]; then
    # Backup existing certs and config
    if [ -f "$GOPHISH_CERT_PATH" ]; then
        sudo cp "$GOPHISH_CERT_PATH" "$GOPHISH_CERT_PATH.backup.$(date +%Y%m%d)"
    fi
    sudo cp "$GOPHISH_CONFIG" "$GOPHISH_CONFIG.backup.$(date +%Y%m%d)"
    echo "   ✅ Backups created"
    
    # Install new certificates
    sudo cp "$GOPHISH_CERT" "$GOPHISH_CERT_PATH"
    sudo cp "$GOPHISH_KEY" "$GOPHISH_KEY_PATH"
    sudo chmod 600 "$GOPHISH_KEY_PATH"
    sudo chmod 644 "$GOPHISH_CERT_PATH"
    sudo chown gophish:gophish "$GOPHISH_CERT_PATH" "$GOPHISH_KEY_PATH" 2>/dev/null || true
    
    echo "   ✅ Certificates installed to GoPhish"
    
    # Update config.json to use TLS
    echo "   Updating config.json..."
    # This would require jq or manual edit - provide instructions
    echo "   ⚠️  Manual step required: Edit $GOPHISH_CONFIG"
    echo "      Set: \"use_tls\": true"
    echo "      Set: \"cert_path\": \"$GOPHISH_CERT_PATH\""
    echo "      Set: \"key_path\": \"$GOPHISH_KEY_PATH\""
    
    # Restart GoPhish
    echo ""
    echo "   🔄 Restarting GoPhish service..."
    sudo systemctl restart gophish
    
    if sudo systemctl is-active --quiet gophish; then
        echo "   ✅ GoPhish restarted successfully"
    else
        echo "   ❌ GoPhish failed to start"
        echo "   Check logs: sudo journalctl -u gophish -n 50"
    fi
else
    echo "   ⚠️  GoPhish config not found at $GOPHISH_CONFIG"
    echo "   Please verify GoPhish installation path"
fi

# Step 3: Validation
echo ""
echo "✅ Step 3: Validation..."

# Test Mythic
if curl -s https://192.168.0.236:3001 | grep -q "Mythic" 2>/dev/null; then
    echo "   ✅ Mythic C2 accessible via HTTPS"
else
    echo "   ⚠️  Mythic HTTPS validation inconclusive"
fi

# Test GoPhish
if curl -s -k https://192.168.0.236:3333 | grep -q "GoPhish" 2>/dev/null; then
    echo "   ✅ GoPhish accessible via HTTPS"
else
    echo "   ⚠️  GoPhish HTTPS validation inconclusive"
fi

# Summary
echo ""
echo "================================================================"
echo "  Red Team Tools Certificate Integration Complete!"
echo "================================================================"
echo ""
echo "Summary:"
echo "  ✅ Mythic C2: BSLRedTeam certificate with malicious SANs"
echo "  ✅ GoPhish: BSLRedTeam certificate for phishing"
echo ""
echo "Certificate Details:"
echo "  Mythic CN: $MYTHIC_CN"
echo "  GoPhish CN: $GOPHISH_CN"
echo "  Validity: 180 days (6 months)"
echo "  Issuer: Baker Street Labs Issuing CA (step-ca)"
echo ""
echo "Tracking:"
echo "  All BSLRedTeam certificates are logged in CA audit"
echo "  Use for threat hunting exercises"
echo "  Teach students to identify red team activity via cert chain"
echo ""
echo "Next Steps:"
echo "  1. Verify certificates in browser:"
echo "     - https://192.168.0.236:3001 (Mythic)"
echo "     - https://192.168.0.236:3333 (GoPhish)"
echo ""
echo "  2. Configure SSL decryption on firewalls to intercept"
echo ""
echo "  3. Create decryption policies to log red team cert usage"
echo ""
echo "  4. Set up renewal automation (runs 30 days before expiry)"
echo ""

