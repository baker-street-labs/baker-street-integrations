#!/bin/bash
#
# Phase 2: Database TLS Encryption Script
# Baker Street Labs PKI Gap Closure
#
# Purpose: Enable TLS for PostgreSQL connections
# Prerequisites: CA chain distributed (Phase 1 complete), step-ca operational
# Execution: Run on database host (e.g., directory01 for Mythic PostgreSQL)
#

set -e

# Configuration
DB_HOST=$(hostname -f)
DB_SERVICE_NAME="postgres"
CN="${DB_SERVICE_NAME}.${DB_HOST}"
STEP_CA_URL="https://192.168.0.236:8443"
CERT_DIR="/opt/pki-certs/postgres"
KEY_FILE="$CERT_DIR/postgres-server.key"
CERT_FILE="$CERT_DIR/postgres-server.crt"
CA_FILE="/etc/ssl/certs/baker-street-root-ca.crt"
POSTGRES_CONF="/etc/postgresql/*/main/postgresql.conf"  # Adjust version as needed

echo "🔐 Phase 2: Database TLS Encryption"
echo "===================================="
echo ""
echo "Target: PostgreSQL on $DB_HOST"
echo "Certificate CN: $CN"
echo ""

# Step 1: Create certificate directory
echo "📁 Step 1: Creating certificate directory..."
sudo mkdir -p "$CERT_DIR"
sudo chmod 755 "$CERT_DIR"
echo "   ✅ Directory created: $CERT_DIR"

# Step 2: Generate CSR
echo ""
echo "🔑 Step 2: Generating CSR for PostgreSQL..."

# Generate private key
openssl genrsa -out "/tmp/postgres-server.key" 2048
echo "   ✅ Private key generated"

# Generate CSR with SANs
cat > /tmp/openssl-postgres.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = $CN
O = Baker Street Labs
C = US

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $CN
DNS.2 = localhost
DNS.3 = ${DB_HOST}
IP.1 = 127.0.0.1
IP.2 = $(hostname -I | awk '{print $1}')
EOF

openssl req -new -key "/tmp/postgres-server.key" \
    -out "/tmp/postgres-server.csr" \
    -config /tmp/openssl-postgres.cnf

echo "   ✅ CSR generated with SANs"

# Step 3: Submit CSR to step-ca
echo ""
echo "📤 Step 3: Submitting CSR to step-ca..."

# Using step CLI (preferred)
if command -v step >/dev/null 2>&1; then
    echo "   Using step CLI..."
    
    # Request certificate with 90-day validity
    step ca certificate "$CN" "$CERT_FILE" --csr="/tmp/postgres-server.csr" \
        --ca-url="$STEP_CA_URL" \
        --root="$CA_FILE" \
        --not-after=2160h  # 90 days
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Certificate issued by step-ca"
        sudo mv "/tmp/postgres-server.key" "$KEY_FILE"
        sudo chmod 600 "$KEY_FILE"
        sudo chown postgres:postgres "$KEY_FILE"
        sudo chown postgres:postgres "$CERT_FILE"
    else
        echo "   ❌ Certificate issuance failed"
        echo "   Possible reasons:"
        echo "     - step-ca not reachable"
        echo "     - Authentication required (need provisioner/token)"
        echo "     - CSR rejected by policy"
        exit 1
    fi
else
    echo "   ⚠️  step CLI not installed"
    echo ""
    echo "   Alternative: Use Python/API method or install step:"
    echo "     curl -LO https://dl.smallstep.com/cli/docs-ca-install/latest/step_linux_amd64.tar.gz"
    echo "     tar -xzf step_linux_amd64.tar.gz"
    echo "     sudo mv step /usr/local/bin/"
    exit 1
fi

# Step 4: Configure PostgreSQL for TLS
echo ""
echo "🔧 Step 4: Configuring PostgreSQL for TLS..."

# Backup postgresql.conf
POSTGRES_CONF_FILE=$(ls $POSTGRES_CONF 2>/dev/null | head -1)
if [ -z "$POSTGRES_CONF_FILE" ]; then
    echo "   ❌ PostgreSQL config not found at $POSTGRES_CONF"
    echo "   Please specify correct path for your installation"
    exit 1
fi

echo "   Found PostgreSQL config: $POSTGRES_CONF_FILE"
sudo cp "$POSTGRES_CONF_FILE" "$POSTGRES_CONF_FILE.backup.$(date +%Y%m%d)"
echo "   ✅ Backup created"

# Update configuration
echo "   Updating PostgreSQL TLS settings..."
sudo tee -a "$POSTGRES_CONF_FILE" > /dev/null <<EOF

# Baker Street Labs PKI - TLS Configuration
# Added: $(date)
ssl = on
ssl_cert_file = '$CERT_FILE'
ssl_key_file = '$KEY_FILE'
ssl_ca_file = '$CA_FILE'
ssl_min_protocol_version = 'TLSv1.2'
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
ssl_prefer_server_ciphers = on
EOF

echo "   ✅ PostgreSQL configured for TLS"

# Step 5: Restart PostgreSQL
echo ""
echo "🔄 Step 5: Restarting PostgreSQL..."
sudo systemctl restart postgresql
sleep 3

if sudo systemctl is-active --quiet postgresql; then
    echo "   ✅ PostgreSQL restarted successfully"
else
    echo "   ❌ PostgreSQL failed to start"
    echo "   Check logs: sudo journalctl -u postgresql -n 50"
    echo "   Restoring backup..."
    sudo mv "$POSTGRES_CONF_FILE.backup.$(date +%Y%m%d)" "$POSTGRES_CONF_FILE"
    sudo systemctl restart postgresql
    exit 1
fi

# Step 6: Validation
echo ""
echo "✅ Step 6: Validating TLS connection..."

# Check if SSL is enabled
echo "   Checking PostgreSQL SSL status..."
sudo -u postgres psql -c "SHOW ssl;" 2>/dev/null | grep -q "on" && \
    echo "   ✅ SSL enabled in PostgreSQL" || \
    echo "   ❌ SSL not enabled"

# Test SSL connection (requires psql client)
if command -v psql >/dev/null 2>&1; then
    echo ""
    echo "   Testing SSL connection..."
    PGPASSWORD="your_password" psql -h localhost -U postgres -d postgres \
        -c "SELECT version();" \
        "sslmode=require" 2>/dev/null && \
        echo "   ✅ SSL connection successful" || \
        echo "   ⚠️  SSL connection test failed (check credentials)"
        
    echo ""
    echo "   Checking SSL statistics..."
    sudo -u postgres psql -d postgres -c "SELECT * FROM pg_stat_ssl;" 2>/dev/null
fi

# Summary
echo ""
echo "================================================================"
echo "  PostgreSQL TLS Configuration Complete!"
echo "================================================================"
echo ""
echo "Summary:"
echo "  ✅ Certificate issued by step-ca (90-day validity)"
echo "  ✅ PostgreSQL configured for TLS 1.2+"
echo "  ✅ Service restarted and operational"
echo ""
echo "Certificate Details:"
echo "  CN: $CN"
echo "  Key: $KEY_FILE"
echo "  Cert: $CERT_FILE"
echo "  CA: $CA_FILE"
echo ""
echo "Client Connection String:"
echo "  psql 'host=$DB_HOST sslmode=verify-full sslrootcert=$CA_FILE'"
echo ""
echo "Next Steps:"
echo "  1. Update client configurations (Guacamole, Mythic, etc.):"
echo "     - Set sslmode=verify-full"
echo "     - Set sslrootcert=$CA_FILE"
echo ""
echo "  2. Test from clients:"
echo "     psql 'host=$DB_HOST dbname=yourdb user=youruser sslmode=verify-full'"
echo ""
echo "  3. Set up renewal (runs 30 days before expiration):"
echo "     Create systemd timer for: step ca renew $CERT_FILE $KEY_FILE"
echo ""
echo "  4. Repeat for other databases:"
echo "     - Guacamole PostgreSQL (portal.labinabox.net)"
echo "     - PowerDNS PostgreSQL (K8s)"
echo "     - MCP PostgreSQL"
echo "     - Redis (similar process)"
echo ""

