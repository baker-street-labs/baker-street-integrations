# Baker Street Integrations Architecture

**Last Updated**: 2026-01-08

---

## Infrastructure Overview

### Component Architecture

The Baker Street Integrations infrastructure consists of multiple integrated components:

1. **PKI Automation** - Windows AD CS certificate management
2. **PANOS PKI Manager** - Palo Alto Networks firewall certificate automation
3. **PANOS Object Creator** - Configuration object automation
4. **Torq Integration** - Workflow orchestration platform
5. **GlobalProtect SAML** - VPN SAML configuration

---

## PKI Automation Architecture

### Windows AD CS Deployment

**Root CA**: bakerstreeta.ad.bakerstreetlabs.io (192.168.0.65)  
**Domain**: ad.bakerstreetlabs.io  
**CA Type**: Enterprise Root CA (single-tier, AD-integrated)

### Certificate Templates

**Template Management**:
- Template creation via PowerShell and Active Directory
- Template publishing to CA
- Security group management
- Auto-enrollment configuration

**Template Types**:
- Machine authentication (BSLMachineAuth)
- User authentication (BSLUserAuth)
- Web server TLS (BSLWebServer)
- Kubernetes (BSLK8sSigner, BSLK8sService)
- Linux systems (BSLLinuxAuth)
- Code signing (BSLCodeSigning)
- VPN authentication (BSLVPNAuth)
- Red team operations (BSLRedTeam)
- Training certificates (BSLShortLived)

### Cross-Platform Support

**Linux Integration**:
- Web enrollment interface
- OpenSSL CSR generation
- Certificate auto-renewal (certmonger)
- SSSD certificate authentication

**Kubernetes Integration**:
- cert-manager HTTP-01 challenges
- Cluster CA certificates
- Service certificates with auto-renewal
- Certificate mounting and injection

---

## PANOS PKI Manager Architecture

### Intermediate CA Hierarchy

```
Root CA (bakerstreeta.ad.bakerstreetlabs.io)
├── "Baker Street Labs Root CA"
    └── Intermediate CA (NGFW)
        └── "Baker Street Labs NGFW Intermediate CA"
            ├── Hub Firewall Certificate
            ├── Spoke Firewall Certificate
            └── Additional NGFW Certificates
```

### Certificate Provisioning Workflow

1. **Intermediate CA Setup**:
   - Check/create NGFWIntermediate template
   - Generate CSR for intermediate CA
   - Submit to Root CA for signing
   - Store intermediate CA certificate and key

2. **Firewall Certificate Provisioning**:
   - Connect to firewall via PAN-OS API
   - Generate CSR on firewall
   - Submit CSR to Windows CA via WinRM
   - Retrieve signed certificate
   - Build certificate chain
   - Import to firewall

### Integration Points

**Windows CA**:
- WinRM access (Kerberos authentication)
- Certificate template enrollment
- CSR signing via certreq

**PAN-OS Firewalls**:
- XML API access
- Certificate and CSR management
- Configuration commit

---

## PANOS Object Creator Architecture

### SDK Integration

**pan-os-python SDK**:
- Firewall and Panorama connectivity
- Object creation and management
- Configuration commit operations

**Supported Object Types**:
- Address objects and groups
- Service objects and groups
- Application objects and groups
- Tags and custom URL categories
- External Dynamic Lists (EDLs)

### Batch Processing

**CSV Import**:
- Template generation
- Batch object creation
- Error handling and reporting
- Dry-run mode support

---

## Torq Integration Architecture

### Workflow Orchestration

**Torq.io Platform**:
- Event-driven workflow engine
- Visual workflow builder
- AI-powered workflow generation
- Self-hosted step runners

### Self-Hosted Runners

**Deployment**:
- Containerized agents in private network
- Outbound-only connection to Torq control plane
- Secure task execution within network boundary

**Capabilities**:
- Kubernetes operations
- Ansible playbook execution
- Docker container management
- Custom script execution

### Workflow Triggers

**Integration Triggers**:
- GitLab webhooks (merge events)
- Slack commands (ChatOps)
- Manual execution (on-demand)
- Scheduled triggers (cron-like)

### Workflow Steps

**Generic Steps**:
- HTTP request (REST API calls)
- Script execution (Python, PowerShell, Bash, JavaScript)
- CLI execution (command-line tools)

**Integration Steps**:
- Pre-built integrations (300+ services)
- Custom integration builder
- "Integrate Anything" philosophy

---

## GlobalProtect SAML Architecture

### SAML Provider Configuration

**Metadata Import**:
- SAML metadata retrieval
- PAN-OS API integration
- Provider configuration automation

**Certificate Management**:
- SAML signing certificate import
- Certificate validation
- Automatic certificate rotation

---

## Data Flow Architecture

### PKI Certificate Flow

```
Certificate Request → Template Selection → CSR Generation → CA Signing → Certificate Import → Auto-Enrollment
```

### PANOS Certificate Flow

```
Firewall CSR → WinRM → Windows CA → Certificate Signing → Certificate Chain → Firewall Import → Commit
```

### Torq Workflow Flow

```
Event Trigger → Workflow Execution → Step Processing → Self-Hosted Runner → Task Execution → Event Generation
```

---

## Security Architecture

### Authentication

**PKI Automation**: Domain credentials (Domain Admin)  
**PANOS PKI Manager**: API keys or username/password  
**PANOS Object Creator**: API keys (preferred) or credentials  
**Torq Integration**: API tokens, OAuth, webhook secrets

### Network Security

**WinRM**: Kerberos authentication (encrypted)  
**PAN-OS API**: HTTPS (TLS encryption)  
**Torq Runners**: Outbound-only connection (Zero Trust)

### Credential Management

- Environment variables for credentials
- `.env` files (not committed to git)
- Torq secrets management
- API key rotation policies

---

## Performance Architecture

### PKI Operations

- Template creation: < 30 seconds per template
- Certificate enrollment: < 10 seconds per certificate
- Auto-enrollment: Asynchronous background process

### PANOS Operations

- CSR generation: < 5 seconds
- Certificate signing: < 30 seconds (depends on CA)
- Certificate import: < 10 seconds
- Configuration commit: < 60 seconds (depends on complexity)

### Torq Workflows

- Workflow execution: Variable (depends on workflow complexity)
- Step execution: < 30 seconds per step (depends on operation)
- Runner latency: < 100ms for task delegation

---

## Related Documentation

- **STATUS.md** - Current operational status
- **CHANGES.md** - Development history and changes
- **DESIGN.md** - Integration workflow diagrams
- **ROADMAP.md** - Future development plans

---

**Maintained By**: Baker Street Labs Infrastructure Team  
**Last Architecture Review**: 2026-01-08

