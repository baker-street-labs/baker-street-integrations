# Changelog

All updates, changes, and summaries are recorded here (append-only).

---

## 2026-01-08 - Documentation Migration

- Consolidated all integration documentation from monorepo
- Created 6 root documentation files per strict rules
- Migrated PKI automation, PANOS PKI Manager, PANOS Object Creator, Torq integration, and GlobalProtect SAML content

---

## PKI Automation Development

### Certificate Infrastructure Automation

**Status**: ✅ Production Ready  
**Date**: October 8, 2025

**Deployment**:
- Enterprise Root CA on 192.168.0.65
- 10 custom certificate templates created
- Auto-enrollment GPO configured
- Cross-platform support enabled

**Templates Created**:
1. BSLMachineAuth - Machine authentication (2yr)
2. BSLUserAuth - User authentication (1yr)
3. BSLWebServer - Web server TLS (1yr)
4. BSLK8sSigner - Kubernetes CA (5yr)
5. BSLK8sService - Kubernetes services (90-day)
6. BSLLinuxAuth - Linux systems (2yr)
7. BSLCodeSigning - Code signing (3yr)
8. BSLVPNAuth - VPN authentication (1yr)
9. BSLRedTeam - Red team operations (6mo)
10. BSLShortLived - Training certificates (7-day)

**Key Scripts**:
- `create_all_templates.ps1` - Primary template creation script
- `verify_and_publish_templates.ps1` - Template verification and publishing
- Linux integration scripts for cross-platform support

---

## PANOS PKI Manager Development

### Automated Certificate Management

**Status**: ✅ Production Ready  
**Date**: October 8, 2025

**Deployment**:
- Intermediate CA created for NGFW certificates
- Automated CSR generation on firewalls
- WinRM integration with Windows CA
- Certificate import and chain building

**Features**:
- Automated intermediate CA creation
- Certificate template management
- PAN-OS XML API integration
- Multi-firewall support
- Dry-run mode for testing

**Integration**:
- Windows Active Directory Certificate Services
- Palo Alto Networks PAN-OS firewalls
- Baker Street Labs PKI infrastructure

---

## PANOS Object Creator Development

### Configuration Object Automation

**Status**: ✅ Production Ready

**Features**:
- pan-os-python SDK integration
- Address, service, and application object creation
- Batch creation from CSV files
- Tag and EDL management
- Dry-run mode and commit control

**Usage**:
- Single object creation via CLI
- Batch import from CSV
- Template generation for CSV format
- Comprehensive error handling

---

## Torq Integration Development

### Workflow Orchestration

**Status**: ✅ Operational  
**Date**: October 9, 2025

**Deployment**:
- Torq.io workspace configured
- Self-hosted step runners deployed
- Workflows operational for lab management

**Workflows**:
- DNS Management Workflow
- Traffic Generation Workflow
- Mythic C2 Deployment Workflow
- Lab Provisioning Workflow
- Cost Management Workflow

**Integrations**:
- GitLab webhook integration
- Slack notifications
- Prometheus/Grafana monitoring
- Elasticsearch integration

---

## GlobalProtect SAML Development

### VPN SAML Configuration

**Status**: ✅ Operational

**Features**:
- Automated SAML metadata import
- PAN-OS API integration
- Certificate management for SAML signing
- Multi-provider support

**Integration**:
- Active Directory Federation Services (ADFS)
- Okta SAML providers
- Generic SAML 2.0 providers

---

*"Automation transforms complexity into simplicity." - Baker Street Labs Integrations*

