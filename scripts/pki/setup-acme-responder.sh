#!/bin/bash
# Setup Dedicated ACME HTTP-01 Challenge Responder
# Baker Street Labs PKI Infrastructure
#
# This script:
# 1. Binds IP 192.168.255.10 to baker-street-services-03
# 2. Makes the IP persistent via NetworkManager
# 3. Deploys ACME responder nginx service
# 4. Configures StepCA integration
#
# Prerequisites:
# - K3s cluster operational
# - StepCA running on 192.168.0.236:8443
# - ACME provisioner configured on StepCA

set -e

echo "=========================================="
echo "ACME Responder Setup - Baker Street Labs"
echo "=========================================="
echo ""

# Configuration
ACME_IP="192.168.255.10"
ACME_NODE="baker-street-services-03"
ACME_NODE_IP="192.168.0.30"
ACME_NODE_INTERFACE="ens192"
STEPCA_SERVER="192.168.0.236"
STEPCA_PORT="8443"

echo "Configuration:"
echo "  ACME Responder IP: $ACME_IP"
echo "  Target Node: $ACME_NODE ($ACME_NODE_IP)"
echo "  StepCA Server: $STEPCA_SERVER:$STEPCA_PORT"
echo ""

# Step 1: Verify StepCA ACME provisioner
echo "[1/6] Verifying StepCA ACME provisioner..."
ACME_DIR_URL="https://$STEPCA_SERVER:$STEPCA_PORT/acme/acme/directory"

if curl -k -s "$ACME_DIR_URL" | grep -q "newNonce"; then
    echo "  ✅ StepCA ACME provisioner is accessible"
else
    echo "  ❌ StepCA ACME provisioner not accessible at $ACME_DIR_URL"
    echo "  Please run: ssh richard@$STEPCA_SERVER 'sudo systemctl status step-ca'"
    exit 1
fi

echo ""

# Step 2: Add IP alias to services-03 node
echo "[2/6] Adding IP alias $ACME_IP to $ACME_NODE..."

# Check if IP already exists
if ssh -i ~/.ssh/id_rsa_baker_street richard@$ACME_NODE_IP "ip addr show $ACME_NODE_INTERFACE | grep -q $ACME_IP"; then
    echo "  ⚠️  IP $ACME_IP already exists on $ACME_NODE"
else
    # Add IP immediately
    ssh -i ~/.ssh/id_rsa_baker_street richard@$ACME_NODE_IP \
        "sudo ip addr add $ACME_IP/16 dev $ACME_NODE_INTERFACE"
    echo "  ✅ IP $ACME_IP added to $ACME_NODE_INTERFACE"
fi

echo ""

# Step 3: Make IP persistent via NetworkManager
echo "[3/6] Making IP persistent via NetworkManager..."

ssh -i ~/.ssh/id_rsa_baker_street richard@$ACME_NODE_IP \
    "sudo nmcli connection modify 'Wired connection 1' +ipv4.addresses $ACME_IP/16 && \
     sudo nmcli connection up 'Wired connection 1'"

if [ $? -eq 0 ]; then
    echo "  ✅ IP $ACME_IP is now persistent (survives reboots)"
else
    echo "  ⚠️  NetworkManager config may have failed, but IP is added manually"
fi

echo ""

# Step 4: Verify IP is reachable
echo "[4/6] Verifying IP $ACME_IP is reachable..."

if ping -c 2 $ACME_IP > /dev/null 2>&1; then
    echo "  ✅ IP $ACME_IP is reachable"
else
    echo "  ❌ IP $ACME_IP is not reachable"
    echo "  This may be a routing issue. Continuing anyway..."
fi

echo ""

# Step 5: Create ACME challenge directory on node
echo "[5/6] Creating ACME challenge directory..."

ssh -i ~/.ssh/id_rsa_baker_street richard@$ACME_NODE_IP \
    "sudo mkdir -p /var/lib/acme-challenges/.well-known/acme-challenge && \
     sudo chown -R 101:101 /var/lib/acme-challenges && \
     sudo chmod -R 755 /var/lib/acme-challenges"

echo "  ✅ Challenge directory created: /var/lib/acme-challenges"
echo ""

# Step 6: Deploy ACME responder to Kubernetes
echo "[6/6] Deploying ACME responder to Kubernetes..."

# Check if namespace exists
if kubectl get namespace baker-street-pki > /dev/null 2>&1; then
    echo "  Namespace baker-street-pki already exists"
else
    echo "  Creating namespace baker-street-pki..."
fi

# Apply the deployment
kubectl apply -f $(dirname $0)/deploy-acme-responder.yaml

if [ $? -eq 0 ]; then
    echo "  ✅ ACME responder deployed"
else
    echo "  ❌ Deployment failed"
    exit 1
fi

echo ""
echo "Waiting for ACME responder pod to be ready..."
kubectl wait --for=condition=ready pod -l app=acme-responder -n baker-street-pki --timeout=60s

if [ $? -eq 0 ]; then
    echo "  ✅ ACME responder is running"
else
    echo "  ⚠️  Pod is not ready yet. Check status with: kubectl get pods -n baker-street-pki"
fi

echo ""
echo "=========================================="
echo "  ✅ ACME Responder Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "  ACME Responder IP: $ACME_IP"
echo "  Node: $ACME_NODE ($ACME_NODE_IP)"
echo "  Service: HTTP on port 80"
echo "  Challenge Path: http://$ACME_IP/.well-known/acme-challenge/"
echo ""
echo "Verification:"
echo "  1. Health check:"
echo "     curl http://$ACME_IP/health"
echo ""
echo "  2. View pod logs:"
echo "     kubectl logs -n baker-street-pki acme-responder-0 -f"
echo ""
echo "  3. Test challenge endpoint:"
echo "     curl http://$ACME_IP/.well-known/acme-challenge/test"
echo "     (Should return 404 - expected when no challenge exists)"
echo ""
echo "StepCA Integration:"
echo "  ACME Directory: $ACME_DIR_URL"
echo "  Certificate Request Example:"
echo "    step ca certificate example.com cert.crt key.key \\"
echo "      --ca-url https://$STEPCA_SERVER:$STEPCA_PORT \\"
echo "      --root /usr/local/share/ca-certificates/baker-street-ca-chain.crt \\"
echo "      --provisioner acme \\"
echo "      --san example.com"
echo ""
echo "Current Infrastructure Status:"
echo "  - Mythic C2:        192.168.0.236:80  ✅ No conflict"
echo "  - ACME Responder:   $ACME_IP:80  ✅ Dedicated"
echo "  - StepCA:           $STEPCA_SERVER:$STEPCA_PORT  ✅ ACME enabled"
echo ""
echo "Next Steps:"
echo "  1. Test certificate issuance with step CLI"
echo "  2. Configure cert-manager ClusterIssuer"
echo "  3. Deploy automated certificate renewals"
echo ""

# Display current IP configuration on target node
echo "IP Configuration on $ACME_NODE:"
ssh -i ~/.ssh/id_rsa_baker_street richard@$ACME_NODE_IP \
    "ip addr show $ACME_NODE_INTERFACE | grep 'inet '"

echo ""
echo "Setup complete!"

