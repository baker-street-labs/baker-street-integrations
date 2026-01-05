# Cross-Platform PKI Architecture for Baker Street Labs

## 🎯 **Architecture Decision: Single Windows Subordinate CA**

**Date**: 2025-09-29  
**Decision**: Single Windows Subordinate CA supporting both Windows and Linux systems  
**Rationale**: Optimal for lab environment with mixed Windows/Linux infrastructure  

---

## 🏗️ **Recommended Architecture**

### **Two-Tier PKI Hierarchy**
```
Root CA (Windows, Online for Lab)
├── Issuing CA (Windows, Cross-Platform Support)
    ├── Windows Systems (AD Integrated)
    ├── Linux Systems (OpenSSL Integration)
    ├── Kubernetes (cert-manager)
    └── Containers (Docker/Podman)
```

### **Why Single Windows Subordinate CA?**

#### **✅ Advantages for Lab Environment**
- **Simplified Management**: One CA to maintain and monitor
- **Cost Effective**: No additional infrastructure required
- **Educational Value**: Students learn PKI concepts without complexity
- **Rapid Deployment**: Faster setup and rebuild for lab scenarios
- **Full AD Integration**: Native Windows features and Group Policy

#### **✅ Cross-Platform Compatibility**
- **Linux Support**: OpenSSL CSR generation and web enrollment
- **Kubernetes Integration**: cert-manager with HTTP-01 challenges
- **Container Support**: Certificate mounting and auto-renewal
- **SSH Integration**: Certificate-based authentication via SSSD

---

## 🔧 **Technical Implementation**

### **Windows Subordinate CA Configuration**

#### **Certificate Templates (Cross-Platform)**
| Template | Purpose | Windows | Linux | K8s | Validity |
|----------|---------|---------|-------|-----|----------|
| **BSLMachineAuth** | Machine certificates | ✅ | ✅ | ✅ | 2 years |
| **BSLUserAuth** | User authentication | ✅ | ✅ | ❌ | 1 year |
| **BSLWebServer** | Web server TLS | ✅ | ✅ | ✅ | 1 year |
| **BSLK8sSigner** | K8s signing certs | ❌ | ✅ | ✅ | 5 years |

#### **Key Configuration Settings**
```powershell
# Subject Name: "Supply in the request" (enables Linux CSR support)
# Key Usage: Digital Signature, Key Encipherment
# Enhanced Key Usage: Server Authentication, Client Authentication
# Template Compatibility: Windows Server 2016+
```

### **Linux Integration Methods**

#### **1. Web Enrollment Interface**
- **URL**: `http://192.168.0.61/certsrv/`
- **Process**: Generate CSR locally → Submit via web → Download certificate
- **Tools**: `openssl`, `curl`, `certmonger`

#### **2. Certificate Auto-Renewal**
```bash
# certmonger configuration for auto-renewal
certmonger -d -n "Baker Street Labs CA" \
  -c "openssl req -new -key %k -out %r -config %c" \
  -C "openssl x509 -req -in %r -CA %a -CAkey %A -out %o -days 365"
```

#### **3. SSSD Certificate Authentication**
```ini
[domain/bakerstreet.local]
id_provider = ad
auth_provider = ad
ldap_user_certificate = userCertificate;binary

[pam]
pam_cert_auth = True
```

### **Kubernetes Integration**

#### **cert-manager Configuration**
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: baker-street-ca
spec:
  acme:
    server: http://192.168.0.61/certsrv/
    privateKeySecretRef:
      name: baker-street-ca-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

---

## 📊 **Comparison: Single vs Dual CA Architecture**

| Aspect | Single Windows CA | Dual CA (Win + Linux) |
|--------|-------------------|----------------------|
| **Complexity** | Low | High |
| **Management** | Simple | Complex |
| **Cost** | Low | High |
| **Windows Integration** | Excellent | Excellent |
| **Linux Integration** | Good | Excellent |
| **K8s Integration** | Good | Excellent |
| **Lab Suitability** | **Optimal** | Over-engineered |
| **Educational Value** | High | Medium |
| **Deployment Time** | Fast | Slow |
| **Maintenance** | Easy | Complex |

---

## 🚀 **Deployment Strategy**

### **Phase 1: Windows Subordinate CA (Current)**
- ✅ Root CA deployed on 192.168.0.61
- 🔄 Deploy Windows Subordinate CA
- 🔄 Configure cross-platform certificate templates
- 🔄 Set up web enrollment interface

### **Phase 2: Linux Integration**
- 🔄 Deploy Linux integration scripts
- 🔄 Configure SSSD for certificate authentication
- 🔄 Set up certmonger for auto-renewal
- 🔄 Test certificate enrollment from Linux

### **Phase 3: Kubernetes Integration**
- 🔄 Deploy cert-manager
- 🔄 Configure ClusterIssuer
- 🔄 Set up Ingress TLS
- 🔄 Test Pod-to-Pod mTLS

### **Phase 4: Monitoring and Automation**
- 🔄 Set up certificate monitoring
- 🔄 Configure automated renewal
- 🔄 Implement alerting
- 🔄 Document procedures

---

## 🔒 **Security Considerations**

### **Lab Environment Security Model**
- **Root CA**: Online for operational convenience
- **Network Isolation**: Lab network segmentation
- **Access Controls**: Limited administrative access
- **Monitoring**: Basic logging and alerting

### **Certificate Security**
- **Key Size**: 4096-bit RSA for Root CA, 2048-bit for end entities
- **Hash Algorithm**: SHA256
- **Validity Periods**: Conservative (1-2 years for end entities)
- **Revocation**: CRL + OCSP hybrid approach

---

## 📋 **Implementation Scripts**

### **Windows CA Deployment**
- `deploy-cross-platform-issuing-ca.ps1` - Deploy Windows Subordinate CA
- `configure-certificate-templates.ps1` - Configure cross-platform templates
- `configure-pki-revocation.ps1` - Set up revocation infrastructure

### **Linux Integration**
- `linux-integration-example.sh` - Linux integration demonstration
- `install-root-ca-linux.sh` - Root CA installation script
- `configure-sssd-cert-auth.sh` - SSSD certificate authentication

### **Kubernetes Integration**
- `deploy-cert-manager.yaml` - cert-manager deployment
- `configure-cluster-issuer.yaml` - ClusterIssuer configuration
- `test-k8s-certificates.sh` - Certificate testing script

---

## 🎯 **Success Metrics**

### **Functional Requirements**
- ✅ Windows systems can enroll certificates automatically
- ✅ Linux systems can enroll certificates via web interface
- ✅ Kubernetes can obtain certificates via cert-manager
- ✅ Certificate auto-renewal works on all platforms
- ✅ Certificate-based authentication works on Linux

### **Performance Requirements**
- ✅ Certificate enrollment completes within 30 seconds
- ✅ Certificate validation completes within 5 seconds
- ✅ Web enrollment interface responds within 10 seconds
- ✅ CRL publication completes within 2 minutes

### **Security Requirements**
- ✅ All certificates use strong cryptography (2048+ bit RSA)
- ✅ Certificate revocation works properly
- ✅ Private keys are protected appropriately
- ✅ Audit logging captures all CA operations

---

## 🔄 **Future Considerations**

### **Potential Upgrades**
- **HSM Integration**: Hardware security modules for key protection
- **OCSP Responder**: Dedicated OCSP responder for better performance
- **Certificate Transparency**: CT logs for certificate monitoring
- **Automated Renewal**: Advanced renewal automation

### **Scaling Considerations**
- **Load Balancing**: Multiple CA servers for high availability
- **Geographic Distribution**: Regional CAs for global deployment
- **Performance Optimization**: Caching and CDN for CRL distribution

---

## 📚 **Documentation and Training**

### **Administrator Documentation**
- PKI operations procedures
- Certificate enrollment guides
- Troubleshooting playbooks
- Security incident response

### **User Documentation**
- Linux certificate enrollment guide
- Kubernetes certificate management
- Certificate-based authentication setup
- Common issues and solutions

### **Training Materials**
- PKI concepts and architecture
- Cross-platform integration techniques
- Security best practices
- Hands-on lab exercises

---

## ✅ **Recommendation Summary**

**For the Baker Street Labs cyber range, implement a single Windows Subordinate CA with cross-platform support.**

This approach provides:
- **Optimal balance** of functionality and simplicity
- **Full compatibility** with both Windows and Linux systems
- **Educational value** for students learning PKI concepts
- **Cost effectiveness** for lab environment
- **Rapid deployment** and easy maintenance

The architecture supports all required use cases while maintaining the simplicity needed for an educational cyber range environment.

---

**Document Version**: 1.0  
**Last Updated**: 2025-09-29  
**Next Review**: 2026-09-29  
**Owner**: Baker Street Labs Security Team
