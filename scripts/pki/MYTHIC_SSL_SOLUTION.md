# Mythic C2 SSL Certificate Solution - Context7 Analysis

**Date**: October 23, 2025  
**Problem**: Mythic C2 port 7443 has SSL errors, needs proper certificate from StepCA  
**Research**: Context7 MCP + Mythic documentation analysis  

---

## 🔍 **Discovery: Mythic Certificate Management**

### Current Architecture

**Mythic C2 Components:**
- `mythic_server` (port 7443) - Backend API, **generates own self-signed SSL cert**
- `mythic_nginx` (port 80) - Frontend reverse proxy
- Certificate location: `mythic_server` container (internal, not in volumes)

### The Problem

Mythic `mythic_server` container **generates its own self-signed certificate** on startup:
- Not exposed via volume mounts
- Not configurable via environment variables  
- Regenerated on container restart
- Cannot be easily replaced with custom cert

**Current Error**: `TLS connect error: packet length too long` → Indicates SSL handshake failure

---

## ✅ **RECOMMENDED SOLUTION: Nginx Reverse Proxy with SSL Termination**

### Architecture

```
Client (Browser/Agent)
    ↓ HTTPS (port 443 or 7443)
┌──────────────────────────────┐
│   Nginx Reverse Proxy        │
│   - SSL Termination          │
│   - Baker Street Labs cert   │
│   - mythic.bakerstreetlabs.io│
└───────────┬──────────────────┘
            ↓ HTTP (no SSL)
┌──────────────────────────────┐
│   Mythic Server (localhost)  │
│   - Port 7443 (HTTP mode)    │
│   - No SSL required          │
└──────────────────────────────┘
```

### Why This Is Better

| Approach | Certificate Management | Mythic Changes | Automation |
|----------|------------------------|----------------|------------|
| ~~Replace Mythic cert~~ | ❌ Hard (internal) | ❌ Requires rebuild | ❌ Manual |
| **Nginx SSL Proxy** | ✅ Easy (file-based) | ✅ None needed | ✅ Auto-renew |

**Benefits:**
1. ✅ **Zero Mythic modifications** - Use as-is
2. ✅ **Standard certificate management** - File-based like other services
3. ✅ **Automated renewal** - Can use cert-manager or StepCA automation
4. ✅ **Better security** - SSL termination at edge, internal HTTP
5. ✅ **Easier debugging** - Standard nginx SSL config
6. ✅ **Scalable** - Can load balance multiple Mythic backends later

---

## 🚀 **Implementation: Nginx Reverse Proxy for Mythic**

### Option 1: Standalone Nginx Container (RECOMMENDED)

**Deploy dedicated nginx for Mythic SSL termination:**

```yaml
version: '3'
services:
  mythic-ssl-proxy:
    image: nginx:alpine
    container_name: mythic_ssl_proxy
    ports:
      - "443:443"    # Standard HTTPS
      - "7443:7443"  # Mythic HTTPS (if keeping this port)
    volumes:
      - /opt/mythic-proxy/nginx.conf:/etc/nginx/nginx.conf:ro
      - /tmp/mythic-cert-gen/mythic.crt:/etc/nginx/ssl/mythic.crt:ro
      - /tmp/mythic-cert-gen/mythic.key:/etc/nginx/ssl/mythic.key:ro
      - /opt/step-ca/root-ca.crt:/etc/nginx/ssl/ca-chain.crt:ro
    restart: unless-stopped
    depends_on:
      - mythic_server
```

**Nginx Configuration:**
```nginx
upstream mythic_backend {
    server 127.0.0.1:7443;  # Mythic server (HTTP mode)
}

server {
    listen 443 ssl http2;
    listen 7443 ssl http2;  # Keep 7443 for compatibility
    
    server_name mythic.bakerstreetlabs.io directory01.ad.bakerstreetlabs.io;
    
    # SSL from StepCA
    ssl_certificate /etc/nginx/ssl/mythic.crt;
    ssl_certificate_key /etc/nginx/ssl/mythic.key;
    ssl_trusted_certificate /etc/nginx/ssl/ca-chain.crt;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Reverse proxy to Mythic
    location / {
        proxy_pass http://mythic_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (Mythic uses WS)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long-running C2 sessions
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

### Option 2: K8s Ingress with SSL (MOST AUTOMATED)

**Use Traefik + cert-manager:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mythic-external
  namespace: default
spec:
  type: ExternalName
  externalName: 192.168.0.236
  ports:
  - port: 7443
    targetPort: 7443

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mythic-https
  annotations:
    cert-manager.io/cluster-issuer: "baker-street-ca"
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  tls:
  - hosts:
    - mythic.bakerstreetlabs.io
    secretName: mythic-tls
  rules:
  - host: mythic.bakerstreetlabs.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mythic-external
            port:
              number: 7443
```

**Benefits:**
- ✅ Automatic certificate issuance from StepCA
- ✅ Auto-renewal (cert-manager handles it)
- ✅ No manual certificate management
- ✅ Integrated monitoring via Prometheus

---

## 📋 **Recommended Deployment Plan**

### Phase 1: Quick Fix - Standalone Nginx Proxy (30 minutes)

1. Create nginx configuration for SSL termination
2. Use already-generated certificate from `/tmp/mythic-cert-gen/`
3. Deploy nginx container
4. Test access via `https://mythic.bakerstreetlabs.io:443`

### Phase 2: Long-term - K8s Ingress + cert-manager (Next week)

1. Deploy cert-manager to K3s
2. Create Ingress resource for Mythic
3. Automatic certificate lifecycle

---

## ✅ **Current Status**

| Component | Status | Details |
|-----------|--------|---------|
| DNS Record | ✅ **DONE** | mythic.bakerstreetlabs.io → 192.168.0.236 |
| SSL Certificate | ✅ **GENERATED** | `/tmp/mythic-cert-gen/mythic.crt` (Baker Street Labs Issuing CA) |
| Mythic Server | ✅ **RUNNING** | Port 7443 (self-signed SSL) |
| Mythic Nginx | ✅ **RUNNING** | Port 80 (HTTP) |
| SSL Proxy | ⏳ **PENDING** | Needs deployment |

---

## 🎯 **Immediate Next Step**

Deploy standalone nginx SSL proxy NOW (fastest path to working HTTPS):

```bash
# Execute this script
./deploy-mythic-ssl-proxy.sh
```

This gives you:
- ✅ Proper SSL cert from your CA
- ✅ HTTPS access to Mythic
- ✅ Zero Mythic modifications
- ✅ Easy to automate renewal

---

**Recommendation**: Use nginx reverse proxy. It's the standard pattern for adding SSL to apps that don't easily support custom certs.

