#!/usr/bin/env bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

#
# Deploy Nginx SSL Reverse Proxy for Mythic C2
# 100% Agentix Automated Solution
#
# Solution: Nginx with SSL termination â†’ Mythic (HTTP backend)
# Benefits: Proper StepCA cert, zero Mythic modifications, automated
#
# Author: Baker Street Labs
# Date: October 23, 2025
#

set -e

MYTHIC_FQDN="mythic.bakerstreetlabs.io"
MYTHIC_IP="192.168.0.236"
MYTHIC_PORT_HTTPS="7443"  # External HTTPS port
MYTHIC_PORT_HTTP="7000"   # Internal HTTP backend (if available)
CERT_DIR="/opt/mythic-ssl-proxy"
CERT_SOURCE="/tmp/mythic-cert-gen"

echo "=========================================================================="
echo "Mythic C2 SSL Reverse Proxy Deployment"
echo "=========================================================================="
echo ""
echo "Architecture: Nginx (SSL Termination) â†’ Mythic Server (HTTP backend)"
echo "Certificate: From Baker Street Labs Issuing CA (StepCA)"
echo ""

# Step 1: Create proxy directory structure
echo "[1/7] Creating SSL proxy directory structure..."
sudo mkdir -p "$CERT_DIR/ssl"
sudo mkdir -p "$CERT_DIR/conf"

echo "  [OK] Directories created"
echo ""

# Step 2: Copy certificates
echo "[2/7] Installing SSL certificates..."
if [ ! -f "$CERT_SOURCE/mythic.crt" ]; then
  echo "  [ERROR] Certificate not found at $CERT_SOURCE/mythic.crt"
  echo "  Run generate-mythic-cert-direct.sh first!"
  exit 1
fi

sudo cp "$CERT_SOURCE/mythic.crt" "$CERT_DIR/ssl/mythic.crt"
sudo cp "$CERT_SOURCE/mythic.key" "$CERT_DIR/ssl/mythic.key"
sudo cp "$CERT_SOURCE/mythic-chain.crt" "$CERT_DIR/ssl/mythic-chain.crt"
sudo chmod 644 "$CERT_DIR/ssl/mythic.crt"
sudo chmod 644 "$CERT_DIR/ssl/mythic-chain.crt"
sudo chmod 600 "$CERT_DIR/ssl/mythic.key"

echo "  [OK] Certificates installed"
echo ""

# Step 3: Create Nginx configuration
echo "[3/7] Creating Nginx configuration..."
sudo tee "$CERT_DIR/conf/nginx.conf" > /dev/null <<'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    access_log /var/log/nginx/access.log;
    
    # Mythic backend (HTTP mode on localhost:7000 or external 7443)
    upstream mythic_backend {
        server 192.168.0.236:7000;  # Try HTTP port first
        server 192.168.0.236:7443 backup;  # Fallback to HTTPS if needed
    }
    
    # HTTPS Server - SSL Termination for Mythic
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        
        server_name mythic.bakerstreetlabs.io directory01.ad.bakerstreetlabs.io;
        
        # SSL Certificates from Baker Street Labs CA
        ssl_certificate /etc/nginx/ssl/mythic-chain.crt;
        ssl_certificate_key /etc/nginx/ssl/mythic.key;
        
        # SSL Configuration (Modern, Secure)
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Reverse Proxy to Mythic
        location / {
            proxy_pass http://mythic_backend;
            proxy_http_version 1.1;
            
            # Headers for proper proxying
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $server_name;
            
            # WebSocket support (Mythic uses WS for real-time updates)
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts for long-running C2 sessions
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
            
            # Buffering settings
            proxy_buffering off;
            proxy_request_buffering off;
        }
        
        # Health check endpoint
        location /nginx-health {
            access_log off;
            return 200 "Mythic SSL Proxy OK\n";
            add_header Content-Type text/plain;
        }
    }
    
    # HTTP to HTTPS redirect
    server {
        listen 80;
        listen [::]:80;
        
        server_name mythic.bakerstreetlabs.io directory01.ad.bakerstreetlabs.io;
        
        return 301 https://$server_name$request_uri;
    }
}
EOF

echo "  [OK] Nginx configuration created"
echo ""

# Step 4: Verify certificates exist
echo "[4/7] Verifying certificate files..."
if [ -f "$CERT_DIR/ssl/mythic-chain.crt" ] && [ -f "$CERT_DIR/ssl/mythic.key" ]; then
  echo "  [OK] Certificate files present"
else
  echo "  [ERROR] Certificate files missing"
  ls -la "$CERT_DIR/ssl/"
  exit 1
fi

echo ""

# Step 5: Stop old proxy if exists
echo "[5/7] Checking for existing SSL proxy..."
if sudo docker ps -a --filter name=mythic_ssl_proxy --format "{{.Names}}" | grep -q mythic_ssl_proxy; then
  echo "  Found existing proxy, removing..."
  sudo docker stop mythic_ssl_proxy 2>/dev/null || true
  sudo docker rm mythic_ssl_proxy 2>/dev/null || true
  echo "  [OK] Old proxy removed"
else
  echo "  No existing proxy found"
fi

echo ""

# Step 6: Deploy Nginx SSL proxy
echo "[6/7] Deploying Nginx SSL reverse proxy..."
sudo docker run -d \
  --name mythic_ssl_proxy \
  --network host \
  --restart unless-stopped \
  -v "$CERT_DIR/conf/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$CERT_DIR/ssl:/etc/nginx/ssl:ro" \
  nginx:alpine

if [ $? -eq 0 ]; then
  echo "  [OK] Nginx SSL proxy deployed"
else
  echo "  [ERROR] Deployment failed"
  exit 1
fi

echo ""

# Step 7: Verify deployment
echo "[7/7] Verifying deployment..."
sleep 5

if sudo docker ps --filter name=mythic_ssl_proxy --format "{{.Status}}" | grep -q "Up"; then
  echo "  [OK] Nginx SSL proxy is running"
else
  echo "  [ERROR] Proxy not running"
  sudo docker logs mythic_ssl_proxy
  exit 1
fi

echo ""

# Test endpoints
echo "Testing endpoints..."
echo "  HTTP redirect (port 80):"
curl -sI http://localhost/ 2>&1 | grep -E "HTTP|Location" | head -3

echo ""
echo "  HTTPS endpoint (port 443):"
curl -k -sI https://localhost/ 2>&1 | grep -E "HTTP|Server" | head -3

echo ""
echo "=========================================================================="
echo "  âœ… Mythic C2 SSL Reverse Proxy DEPLOYED!"
echo "=========================================================================="
echo ""
echo "Access Points:"
echo "  Primary:   https://mythic.bakerstreetlabs.io"
echo "  Alternate: https://directory01.ad.bakerstreetlabs.io"
echo "  IP:        https://192.168.0.236"
echo ""
echo "Architecture:"
echo "  Client â†’ Nginx (443, SSL termination)"
echo "         â†’ Mythic Server (7000/7443, HTTP backend)"
echo ""
echo "Certificate:"
echo "  Subject: $MYTHIC_FQDN"
echo "  Issuer:  Baker Street Labs Issuing CA"
echo "  Validity: 365 days"
echo ""
echo "Container:"
echo "  Name: mythic_ssl_proxy"
echo "  Status:"
sudo docker ps --filter name=mythic_ssl_proxy --format "    {{.Status}}"

echo ""
echo "Verification:"
echo "  curl -k https://mythic.bakerstreetlabs.io/"
echo "  curl -I http://mythic.bakerstreetlabs.io/ (should redirect to HTTPS)"
echo ""
echo "Logs:"
echo "  sudo docker logs mythic_ssl_proxy -f"
echo ""

