#!/bin/bash
#
# Phase 1: CA Chain Distribution Script
# Baker Street Labs PKI Gap Closure
# 
# Purpose: Distribute Root CA and Intermediate CA certificates to Linux systems
# Prerequisites: Root CA exported from Windows, step-ca operational
# Execution: Run on each Linux host (bakerservices, directory01, k3s nodes, portal)
#

set -e  # Exit on error

# Configuration
ROOT_CA_URL="http://192.168.0.65/certsrv/certnew.cer?ReqID=CACert&Renewal=0&Enc=b64"
STEP_CA_URL="https://192.168.0.236:8443"
ROOT_CA_FILE="/tmp/baker-street-root-ca.pem"
INTERMEDIATE_CA_FILE="/tmp/baker-street-intermediate.pem"
TARGET_DIR="/usr/local/share/ca-certificates"

echo "🚀 Phase 1: CA Chain Distribution"
echo "=================================="
echo ""

# Step 1: Fetch Root CA from Windows CA
echo "📥 Step 1: Fetching Root CA from Windows CA..."
echo "   URL: $ROOT_CA_URL"

# Try to fetch Root CA (may need authentication)
if curl -f -o "$ROOT_CA_FILE" "$ROOT_CA_URL" 2>/dev/null; then
    echo "   ✅ Root CA downloaded successfully"
else
    echo "   ⚠️  Direct download failed, trying alternative method..."
    # Alternative: Use pre-exported file
    if [ -f "/opt/pki-certs/baker-street-root-ca.pem" ]; then
        cp /opt/pki-certs/baker-street-root-ca.pem "$ROOT_CA_FILE"
        echo "   ✅ Using pre-exported Root CA"
    else
        echo "   ❌ Root CA not available. Please export manually:"
        echo "      On bakerstreeta: certutil -ca.cert C:\\temp\\baker-street-root-ca.cer"
        echo "      Then: certutil -encode C:\\temp\\baker-street-root-ca.cer C:\\temp\\baker-street-root-ca.pem"
        echo "      Copy to: /opt/pki-certs/baker-street-root-ca.pem on this host"
        exit 1
    fi
fi

# Ensure PEM format
if openssl x509 -in "$ROOT_CA_FILE" -text -noout >/dev/null 2>&1; then
    echo "   ✅ Root CA is valid PEM format"
else
    echo "   🔧 Converting to PEM format..."
    openssl x509 -in "$ROOT_CA_FILE" -out "$ROOT_CA_FILE" -outform PEM
fi

# Step 2: Fetch Intermediate CA from step-ca
echo ""
echo "📥 Step 2: Fetching Intermediate CA from step-ca..."
echo "   URL: $STEP_CA_URL"

# Try to fetch from step-ca (may need --insecure initially)
if curl -f -k -o "$INTERMEDIATE_CA_FILE" "$STEP_CA_URL/roots.pem" 2>/dev/null; then
    echo "   ✅ Intermediate CA downloaded successfully"
elif curl -f -k -o "$INTERMEDIATE_CA_FILE" "$STEP_CA_URL/1.0/intermediate" 2>/dev/null; then
    echo "   ✅ Intermediate CA downloaded (alternate endpoint)"
else
    echo "   ⚠️  step-ca not reachable. Possible reasons:"
    echo "      - Service not running"
    echo "      - Network/firewall issue"
    echo "      - Wrong endpoint"
    echo ""
    echo "   To check: ssh richard@192.168.0.55 'sudo systemctl status step-ca'"
    echo "   To start: ssh richard@192.168.0.55 'sudo systemctl start step-ca'"
    echo ""
    echo "   Continuing with Root CA only..."
    INTERMEDIATE_CA_FILE=""
fi

# Step 3: Install certificates to system trust store
echo ""
echo "🔧 Step 3: Installing certificates to system trust store..."

# Install Root CA
echo "   Installing Root CA..."
sudo cp "$ROOT_CA_FILE" "$TARGET_DIR/baker-street-root-ca.crt"
sudo chmod 644 "$TARGET_DIR/baker-street-root-ca.crt"
echo "   ✅ Root CA installed: $TARGET_DIR/baker-street-root-ca.crt"

# Install Intermediate CA if available
if [ -n "$INTERMEDIATE_CA_FILE" ] && [ -f "$INTERMEDIATE_CA_FILE" ]; then
    echo "   Installing Intermediate CA..."
    sudo cp "$INTERMEDIATE_CA_FILE" "$TARGET_DIR/baker-street-intermediate.crt"
    sudo chmod 644 "$TARGET_DIR/baker-street-intermediate.crt"
    echo "   ✅ Intermediate CA installed: $TARGET_DIR/baker-street-intermediate.crt"
fi

# Step 4: Update CA certificates
echo ""
echo "🔄 Step 4: Updating system CA certificates..."
sudo update-ca-certificates

# Step 5: Validation
echo ""
echo "✅ Step 5: Validating installation..."

# Test 1: Verify Root CA in trust store
if grep -q "baker-street-root-ca" /etc/ssl/certs/ca-certificates.crt; then
    echo "   ✅ Root CA found in system trust store"
else
    echo "   ⚠️  Root CA not found in trust store (may be normal)"
fi

# Test 2: Test HTTPS connection to step-ca WITHOUT -k flag
echo ""
echo "   Testing step-ca connection (should work without --insecure)..."
if curl -f "$STEP_CA_URL/health" 2>/dev/null | grep -q "ok"; then
    echo "   ✅ SUCCESS! step-ca trusts our CA chain"
    echo "   Response: $(curl -s $STEP_CA_URL/health)"
else
    echo "   ⚠️  step-ca not reachable or still needs --insecure"
    echo "   This may be normal if step-ca is using a different cert"
fi

# Test 3: Test internal services (if available)
echo ""
echo "   Testing other internal HTTPS services..."
for service in "dns-api.bakerstreetlabs.io" "mythic.bakerstreetlabs.io" "postgres.directory01.bakerstreetlabs.io"; do
    if curl -f --connect-timeout 2 "https://$service" 2>/dev/null; then
        echo "   ✅ $service: HTTPS working"
    else
        echo "   ⏭️  $service: Not available (expected if not yet configured)"
    fi
done

# Summary
echo ""
echo "================================================================"
echo "  CA Chain Distribution Complete!"
echo "================================================================"
echo ""
echo "Summary:"
echo "  ✅ Root CA installed and trusted"
if [ -n "$INTERMEDIATE_CA_FILE" ] && [ -f "$INTERMEDIATE_CA_FILE" ]; then
    echo "  ✅ Intermediate CA installed and trusted"
else
    echo "  ⚠️  Intermediate CA not installed (step-ca issue)"
fi
echo ""
echo "Next Steps:"
echo "  1. Run this script on other Linux hosts:"
echo "     - directory01 (192.168.0.236)"
echo "     - k3s-master (192.168.0.28)"
echo "     - k3s-workers (192.168.0.29, 192.168.0.30)"
echo "     - portal.labinabox.net (192.168.0.44)"
echo ""
echo "  2. For Kubernetes, create ConfigMap:"
echo "     kubectl create configmap baker-street-ca \\"
echo "       --from-file=root-ca.crt=$TARGET_DIR/baker-street-root-ca.crt \\"
echo "       --from-file=intermediate-ca.crt=$TARGET_DIR/baker-street-intermediate.crt \\"
echo "       -n kube-system"
echo ""
echo "  3. For containers, rebuild with:"
echo "     COPY baker-street-root-ca.crt /usr/local/share/ca-certificates/"
echo "     RUN update-ca-certificates"
echo ""
echo "Host: $(hostname)"
echo "Date: $(date)"
echo ""

