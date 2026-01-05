#!/usr/bin/env bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

# Final Mythic SSL Proxy - Simple Working Version
# Port 9443 (avoids conflicts with port 80/443)

set -e

echo "Deploying Mythic SSL Proxy on port 9443..."

# Create config directory
sudo mkdir -p /opt/mythic-ssl-proxy/{conf,ssl}

# Copy certificates
sudo cp /tmp/mythic-cert-gen/mythic.crt /opt/mythic-ssl-proxy/ssl/
sudo cp /tmp/mythic-cert-gen/mythic.key /opt/mythic-ssl-proxy/ssl/
sudo chmod 644 /opt/mythic-ssl-proxy/ssl/mythic.crt
sudo chmod 600 /opt/mythic-ssl-proxy/ssl/mythic.key

# Create nginx config
cat > /tmp/nginx-mythic.conf <<'EOF'
worker_processes 1;
events { worker_connections 256; }
http {
    upstream mythic { server 127.0.0.1:7443; }
    server {
        listen 9443 ssl;
        server_name _;
        ssl_certificate /etc/nginx/ssl/mythic.crt;
        ssl_certificate_key /etc/nginx/ssl/mythic.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        location / {
            proxy_pass https://mythic;
            proxy_ssl_verify off;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
EOF

sudo mv /tmp/nginx-mythic.conf /opt/mythic-ssl-proxy/conf/nginx.conf

# Remove old container
sudo docker rm -f mythic_ssl_proxy 2>/dev/null || true

# Deploy nginx
sudo docker run -d \
  --name mythic_ssl_proxy \
  --network host \
  --restart unless-stopped \
  -v /opt/mythic-ssl-proxy/conf/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /opt/mythic-ssl-proxy/ssl:/etc/nginx/ssl:ro \
  nginx:alpine

sleep 5

# Check status
sudo docker ps --filter name=mythic_ssl_proxy
sudo docker logs mythic_ssl_proxy 2>&1 | tail -3

echo ""
echo "âœ… Mythic SSL Proxy deployed on port 9443"
echo "Test: curl -k https://mythic.bakerstreetlabs.io:9443/"

