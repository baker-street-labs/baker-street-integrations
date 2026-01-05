#!/usr/bin/env bash
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

#
# Deploy STANDALONE Nginx for Mythic C2
# ZERO Traefik, ZERO K8s involvement
# Direct docker container on 192.168.253.10:443
#

set -e

MYTHIC_SSL_IP="192.168.253.10"
MYTHIC_BACKEND="127.0.0.1:7443"
PROXY_DIR="/opt/mythic-nginx-standalone"

echo "=========================================="
echo "Standalone Mythic Nginx - NO TRAEFIK"
echo "=========================================="
echo "IP: $MYTHIC_SSL_IP:443"
echo "Backend: $MYTHIC_BACKEND"
echo ""

# Clean slate
sudo docker rm -f mythic_standalone_nginx 2>/dev/null || true
sudo rm -rf "$PROXY_DIR"

# Create directories
sudo mkdir -p "$PROXY_DIR/ssl"
sudo mkdir -p "$PROXY_DIR/html"

# Copy certificates  
sudo cp /tmp/mythic-cert-gen/mythic.crt "$PROXY_DIR/ssl/"
sudo cp /tmp/mythic-cert-gen/mythic.key "$PROXY_DIR/ssl/"
sudo chmod 644 "$PROXY_DIR/ssl/mythic.crt"
sudo chmod 600 "$PROXY_DIR/ssl/mythic.key"

echo "Certificates installed"

# Create COMPLETE nginx config
sudo tee "$PROXY_DIR/nginx.conf" > /dev/null <<'ENDCONF'
user nginx;
worker_processes 2;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    keepalive_timeout 65;
    
    # Mythic backend
    upstream mythic_server {
        server 127.0.0.1:7443;
        keepalive 32;
    }
    
    # HTTPS server for Mythic
    server {
        listen 192.168.253.10:443 ssl;
        server_name mythic.bakerstreetlabs.io 192.168.253.10;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/mythic.crt;
        ssl_certificate_key /etc/nginx/ssl/mythic.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:HIGH:!aNULL:!MD5';
        ssl_prefer_server_ciphers on;
        
        # Proxy to Mythic
        location / {
            proxy_pass https://mythic_server;
            proxy_ssl_verify off;
            proxy_ssl_server_name on;
            
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
            
            proxy_buffering off;
            proxy_request_buffering off;
        }
    }
}
ENDCONF

echo "Nginx config created"

# Deploy standalone nginx container
echo "Deploying nginx container..."
sudo docker run -d \
  --name mythic_standalone_nginx \
  --network host \
  --restart unless-stopped \
  -v "$PROXY_DIR/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PROXY_DIR/ssl:/etc/nginx/ssl:ro" \
  nginx:latest

sleep 8

echo ""
echo "Container status:"
sudo docker ps --filter name=mythic_standalone_nginx

echo ""
echo "Logs:"
sudo docker logs mythic_standalone_nginx 2>&1 | tail -10

echo ""
echo "Testing..."
curl -k -I https://192.168.253.10/ 2>&1 | head -10

echo ""
echo "=========================================="
echo "âœ… Standalone Mythic Nginx Deployed"
echo "=========================================="
echo ""
echo "Access:"
echo "  https://192.168.253.10/"
echo "  https://mythic.bakerstreetlabs.io/ (DNS points to 192.168.253.10)"
echo ""
echo "This is 100% independent of Traefik/K8s"
echo ""

