# Baker Street Integrations

**Vendor Integrations and SDK Automation for Baker Street Labs Cyber Range**  
**Status**: 🟢 **OPERATIONAL**  
**Last Updated**: January 8, 2026

---

## Quick Start

### PKI Automation

```powershell
# Create all certificate templates
.\create_all_templates.ps1

# Verify and publish templates
.\verify_and_publish_templates.ps1 -CreateGroups
```

### PANOS PKI Manager

```bash
# Deploy certificates to firewalls
python main.py --firewalls hub spoke

# Dry run to preview changes
python main.py --dry-run --verbose
```

### PANOS Object Creator

```bash
# Create single object
python panos_object_creator.py --hostname 192.168.1.1 --username admin --object-type address --name MyIP --value 192.168.1.1/24

# Batch creation from CSV
python panos_object_creator.py --hostname 192.168.1.1 --api-key YOUR_KEY --csv-file objects.csv --commit
```

---

## Components

### PKI Automation

**Certificate Infrastructure Automation** for Baker Street Labs:
- Enterprise Root CA (AD-integrated)
- 10 custom certificate templates
- Cross-platform support (Windows, Linux, Kubernetes)
- Automated template creation and publishing

**Templates**:
- BSLMachineAuth - Machine authentication (2yr)
- BSLUserAuth - User authentication (1yr)
- BSLWebServer - Web server TLS (1yr)
- BSLK8sSigner - Kubernetes CA (5yr)
- BSLK8sService - Kubernetes services (90-day)
- BSLLinuxAuth - Linux systems (2yr)
- BSLCodeSigning - Code signing (3yr)
- BSLVPNAuth - VPN authentication (1yr)
- BSLRedTeam - Red team operations (6mo)
- BSLShortLived - Training certificates (7-day)

### PANOS PKI Manager

**Automated Certificate Management** for Palo Alto Networks Firewalls:
- Intermediate CA creation
- CSR generation on firewalls
- Automated certificate signing
- Certificate import and chain building
- Multi-firewall support

**Features**:
- Automated intermediate CA creation
- Certificate template management
- PAN-OS XML API integration
- WinRM integration with Windows CA
- Full certificate chain support

### PANOS Object Creator

**Automated Object Creation** using pan-os-python SDK:
- Address objects and groups
- Service objects and groups
- Application objects and groups
- Tags, custom URL categories, EDLs
- Batch creation from CSV

**Features**:
- pan-os-python SDK integration
- CSV batch import support
- Dry-run mode
- Commit control
- Comprehensive error handling

### Torq Integration

**Workflow Automation** for lab environment management:
- Event-driven workflows
- Self-hosted step runners
- Hybrid cloud support
- Integration with GitLab, Slack, monitoring

**Workflows**:
- DNS Management
- Traffic Generation
- Mythic C2 Deployment
- Lab Provisioning
- Cost Management

### GlobalProtect SAML

**SAML Metadata Import** for GlobalProtect VPN:
- Automated SAML provider configuration
- Metadata import via PAN-OS API
- Certificate management for SAML signing

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture
- **[DESIGN.md](DESIGN.md)** - Integration workflow diagrams
- **[STATUS.md](STATUS.md)** - Current operational status
- **[CHANGES.md](CHANGES.md)** - Development history and changes
- **[ROADMAP.md](ROADMAP.md)** - Future development plans

---

## Key Features

- ✅ PKI automation with Windows AD CS
- ✅ PANOS certificate lifecycle management
- ✅ PANOS object creation automation
- ✅ Torq workflow orchestration
- ✅ Cross-platform certificate support
- ✅ Event-driven automation

---

**Version**: 1.0  
**Environment**: Baker Street Labs Cyber Range

