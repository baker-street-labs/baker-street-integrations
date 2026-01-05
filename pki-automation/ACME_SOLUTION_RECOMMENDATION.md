# ACME Automation Solution - Baker Street Labs PKI

**Date**: 2025-10-22  
**Problem**: Need permanent ACME HTTP-01 responder without conflicting with Mythic C2  
**Discovery**: K3s Traefik already listening on port 80 (hostNetwork)  
**Solution**: Use Traefik + cert-manager for ACME automation  

---

## 🎯 **RECOMMENDED SOLUTION: Use Traefik IngressRoute**

### Why This Is Better

| Approach | Status | Complexity | Maintenance |
|----------|--------|------------|-------------|
| ~~Dedicated nginx pod~~ | ❌ **Blocked** | High | Traefik already owns port 80 |
| **Traefik IngressRoute** | ✅ **READY** | Low | Built into K3s |
| cert-manager with Traefik | ✅ **BEST** | Medium | Fully automated |

**Traefik is ALREADY running on all K3s nodes with host Network:**
- Port 80: HTTP
- Port 443: HTTPS
- Handles ingress routing for entire cluster
- Has built-in ACME challenge support

---

## 🚀 **Implementation: Option 1 - Direct Traefik ACME**

### Configure Traefik to Handle ACME Challenges

Traefik can proxy `/.well-known/acme-challenge/` requests to StepCA or serve them directly.

**Deployment:**

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: stepca-acme-challenge
  namespace: baker-street-pki
spec:
  entryPoints:
    - web  # Port 80
  routes:
  - match: PathPrefix(`/.well-known/acme-challenge/`)
    kind: Rule
    services:
    - name: acme-challenge-responder
      port: 80
```

**Benefits:**
- ✅ No port conflicts (Traefik already owns port 80)
- ✅ Works on ANY K3s node IP
- ✅ Automatic routing to challenge responder
- ✅ No additional IP aliases needed

---

## 🏆 **BEST SOLUTION: Option 2 - cert-manager with Traefik**

### Use cert-manager for Fully Automated Certificate Management

**You already have the configuration started!** (`baker-street-labs/scripts/pki/phase3-certmanager-k8s.yaml`)

**Complete Architecture:**

```
StepCA (192.168.0.236:8443)
    ↓
cert-manager (K8s operator)
    ↓
Traefik Ingress (port 80 HTTP-01 challenges)
    ↓
Automatic certificate issuance & renewal
```

**What cert-manager Does:**
1. Requests certificate from StepCA via ACME
2. StepCA generates HTTP-01 challenge token
3. cert-manager creates Ingress for `/.well-known/acme-challenge/<token>`
4. Traefik serves the challenge token on port 80
5. StepCA validates via HTTP
6. Certificate issued and stored in K8s Secret
7. **Automatic renewal** 15 days before expiry

---

## 📋 **Deployment Plan (Recommended)**

### Step 1: Verify StepCA ACME Provisioner

```bash
# On directory01 (192.168.0.236)
ssh richard@192.168.0.236
curl -k https://localhost:8443/acme/acme/directory | jq .

# Should show: newNonce, newAccount, newOrder endpoints
```

### Step 2: Deploy cert-manager

```bash
# Install cert-manager (if not already)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.yaml

# Wait for ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/instance=cert-manager \
  -n cert-manager \
  --timeout=300s
```

### Step 3: Create ClusterIssuer for StepCA

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: baker-street-ca
spec:
  acme:
    server: https://192.168.0.236:8443/acme/acme/directory
    skipTLSVerify: true  # Or add CA bundle
    privateKeySecretRef:
      name: acme-account-key
    solvers:
    - http01:
        ingress:
          class: traefik  # Use K3s's built-in Traefik
```

### Step 4: Request Certificates Declaratively

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: powerdns-ns1
  namespace: baker-street-dns
spec:
  secretName: powerdns-ns1-tls
  issuerRef:
    name: baker-street-ca
    kind: ClusterIssuer
  commonName: ns1.bakerstreetlabs.io
  dnsNames:
  - ns1.bakerstreetlabs.io
  - 192.168.0.11
  duration: 2160h  # 90 days
  renewBefore: 360h  # Renew 15 days before expiry
```

**Result:** Certificate automatically issued and renewed!

---

## 🔧 **Alternative: Simple Traefik Middleware**

If you want manual StepCA certificate requests (not cert-manager), just route ACME challenges through Traefik:

```bash
# On ANY K3s node, StepCA can use any node's IP for HTTP-01
step ca certificate example.com cert.crt key.key \
  --ca-url https://192.168.0.236:8443 \
  --provisioner acme \
  --san example.com \
  --http-listen :80  # Traefik will intercept and serve

# Works on: 192.168.0.28, 192.168.0.29, 192.168.0.30, 192.168.0.236
```

---

## 📊 **Comparison**

| Solution | Mythic Conflict | Automation | Renewal | Complexity |
|----------|-----------------|------------|---------|------------|
| **cert-manager + Traefik** | ✅ None | ✅ Full | ✅ Automatic | Low |
| Traefik IngressRoute | ✅ None | ⚠️ Manual | ❌ Manual | Medium |
| Dedicated nginx (attempted) | ✅ None | ⚠️ Manual | ❌ Manual | ❌ Blocked by Traefik |

---

## ✅ **IMMEDIATE RECOMMENDATION**

**Deploy cert-manager NOW:**

1. It's already planned in your phase3-certmanager-k8s.yaml
2. Works seamlessly with existing Traefik
3. Zero conflict with Mythic C2
4. Fully automated certificate lifecycle
5. No additional IPs or services needed

**Time to deploy:** ~15 minutes  
**Benefit:** Permanent solution, zero maintenance

---

## 🗑️ **Cleanup Current ACME Responder Attempt**

Since Traefik owns port 80, we don't need the dedicated nginx pod:

```bash
# Remove namespace and resources
kubectl delete namespace baker-street-pki

# Remove IP alias from services-03 (not needed)
ssh richard@192.168.0.30 "sudo nmcli connection modify 'Wired connection 1' -ipv4.addresses 192.168.255.10/16"
ssh richard@192.168.0.30 "sudo ip addr del 192.168.255.10/16 dev ens192"
```

---

## 📝 **Next Steps**

**Recommended path:**
1. ✅ Keep Mythic C2 on 192.168.0.236:80 (no changes)
2. ✅ Deploy cert-manager to K3s cluster  
3. ✅ Create ClusterIssuer pointing to StepCA
4. ✅ Request certificates via Certificate resources
5. ✅ Traefik handles HTTP-01 challenges automatically

**Implementation command:**

```bash
# Deploy cert-manager + StepCA integration
kubectl apply -f baker-street-labs/scripts/pki/phase3-certmanager-k8s.yaml
```

Would you like me to deploy cert-manager now, or do you prefer a different approach?

---

**Current Status:**
- ✅ StepCA running (192.168.0.236:8443)
- ✅ ACME provisioner configured
- ✅ Mythic C2 operational (192.168.0.236:80)  
- ✅ Traefik ready for HTTP-01 challenges (all K3s nodes:80)
- ⏳ cert-manager: Not yet deployed

