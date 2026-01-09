#!/usr/bin/env bash
# Deploy Mythic SSL Proxy on Dedicated IP
# IP: 192.168.253.10 (no port conflicts!)
# Port: 443 (standard HTTPS)

set -e

MYTHIC_SSL_IP="192.168.253.10"
CERT_SRC="/tmp/mythic-cert-gen"
PROXY_DIR="/opt/mythic-ssl-proxy"

echo "Deploying Mythic SSL Proxy"
echo "IP: $MYTHIC_SSL_IP:443"
echo "Backend: 127.0.0.1:7443"
echo ""

# Create directories
sudo mkdir -p "$PROXY_DIR/conf" "$PROXY_DIR/ssl"

# Copy certificates
sudo cp "$CERT_SRC/mythic.crt" "$PROXY_DIR/ssl/"
sudo cp "$CERT_SRC/mythic.key" "$PROXY_DIR/ssl/"
sudo chmod 644 "$PROXY_DIR/ssl/mythic.crt"
sudo chmod 600 "$PROXY_DIR/ssl/mythic.key"

# Create nginx config
sudo tee "$PROXY_DIR/conf/nginx.conf" > /dev/null <<'EOF'
worker_processes 1;
error_log stderr warn;
pid /tmp/nginx.pid;

events {
    worker_connections 512;
}

http {
    access_log /dev/stdout;
    client_body_temp_path /tmp/client_body;
    proxy_temp_path /tmp/proxy;
    fastcgi_temp_path /tmp/fastcgi;
    
    upstream mythic_backend {
        server 127.0.0.1:7443;
    }
    
    server {
        listen 192.168.253.10:443 ssl;
        server_name mythic.bakerstreetlabs.io directory01.ad.bakerstreetlabs.io 192.168.253.10;
        
        ssl_certificate /etc/nginx/ssl/mythic.crt;
        ssl_certificate_key /etc/nginx/ssl/mythic.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        location / {
            proxy_pass https://mythic_backend;
            proxy_ssl_verify off;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 300s;
            proxy_buffering off;
        }
        
        location /health {
            access_log off;
            return 200 "Mythic SSL Proxy OK\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Deploy container
sudo docker rm -f mythic_ssl_proxy 2>/dev/null || true

sudo docker run -d \
  --name mythic_ssl_proxy \
  --network host \
  --restart unless-stopped \
  -v "$PROXY_DIR/conf/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PROXY_DIR/ssl:/etc/nginx/ssl:ro" \
  nginx:alpine

sleep 5

echo ""
echo "Status:"
sudo docker ps --filter name=mythic_ssl_proxy --format "  {{.Names}}: {{.Status}}"

echo ""
echo "Testing..."
curl -k -s https://192.168.253.10/health || echo "Health check failed"

echo ""
echo "✅ COMPLETE!"
echo ""
echo "Access Mythic C2 via:"
echo "  https://192.168.253.10/ (SSL proxy)"
echo "  https://mythic.bakerstreetlabs.io/ (add DNS record to 192.168.253.10)"
echo ""
echo "Certificate: Baker Street Labs Issuing CA"
echo "Validity: 365 days"
echo ""

