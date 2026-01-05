This repository is one of the Nine Laboratories of Baker Street.
It shall remain focused, independent, and well-documented.
We do not rebuild Frankenstein.
— The Baker Street Compact, 2026

# Baker Street Labs PKI Scripts
## Certificate Infrastructure Automation

**Status**: ✅ PKI Fully Operational  
**Last Updated**: October 8, 2025  
**CA Type**: Enterprise Root CA (Single-tier, AD-integrated)

---

## 🎯 Overview

This directory contains PowerShell scripts for managing the Baker Street Labs PKI infrastructure. The PKI is deployed as a **single-tier Enterprise Root CA** integrated with Active Directory, appropriate for lab/cyber range environments.

---

## 🏗️ Current PKI Architecture

### Deployed Configuration
- **CA Type**: Enterprise Root CA (AD-integrated, single-tier)
- **Server**: bakerstreeta.ad.bakerstreetlabs.io (192.168.0.65)
- **Domain**: ad.bakerstreetlabs.io
- **CA Name**: "Baker Street Labs Root CA"
- **Validity**: 2 years
- **Status**: ✅ Fully operational

### Components Installed
- ✅ Active Directory Certificate Services
- ✅ Web Enrollment
- ✅ Certificate Enrollment Web Service
- ✅ Certificate Enrollment Policy Web Service
- ✅ Network Device Enrollment
- ✅ Online Responder (OCSP)

### Auto-Enrollment
- ✅ GPO: "Baker Street Labs Certificate Auto-Enrollment"
- ✅ Computer auto-enrollment enabled
- ✅ User auto-enrollment enabled

---

## 📁 Current Scripts

### Core Automation

#### **create_all_templates.ps1** ⭐ PRIMARY SCRIPT
**Purpose**: Create all 10 Baker Street Labs custom certificate templates programmatically

**Features**:
- Creates templates via Active Directory PowerShell
- Configures proper attributes and permissions
- Sets validity periods and key usage
- Generates unique template OIDs
- Assigns security permissions

**Usage**:
```powershell
# Local execution on CA server
.\create_all_templates.ps1

# Via WinRM from remote machine
Invoke-Command -ComputerName bakerstreeta.ad.bakerstreetlabs.io -FilePath .\create_all_templates.ps1
```

**Templates Created** (10):
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

---

#### **verify_and_publish_templates.ps1**
**Purpose**: Verify templates exist and publish them to the CA

**Features**:
- Checks template existence in Active Directory
- Verifies templates published to CA
- Publishes unpublished templates
- Creates AD security groups (optional)
- Generates summary report

**Usage**:
```powershell
# Verify all templates
.\verify_and_publish_templates.ps1

# Verify and create AD security groups
.\verify_and_publish_templates.ps1 -CreateGroups

# Verify specific templates
.\verify_and_publish_templates.ps1 -TemplateNames "BSLMachineAuth","BSLUserAuth"
```

**Security Groups Created** (with -CreateGroups):
- BSL-WebServer-Admins
- BSL-K8S-Admins
- BSL-Linux-Admins
- BSL-CodeSigning-Admins
- BSL-VPN-Users
- BSL-RedTeam
- BSL-Training-Admins

---

### Legacy/Service Account Scripts

#### **create-ca-webenroll-serviceaccount.ps1**
**Purpose**: Create service account for CA Web Enrollment  
**Status**: Legacy script (web enrollment already configured)

#### **execute-on-brownstone.ps1**
**Purpose**: WinRM execution wrapper  
**Status**: Legacy (references old server name "brownstone")

---

## 📚 Documentation

### Current Documentation (In `docs/` directory)

**Operator Guides**:
- `docs/instructions/pki_template_creation_guide.md` - Step-by-step template creation (GUI method)
- `docs/instructions/winrm_authentication_guide.md` - Server access procedures
- `docs/PKI_QUICK_START_OPERATOR.md` - Quick reference guide

**Planning & Specifications**:
- `docs/plans/pki_custom_template_recommendations.md` - Complete template specifications
- `docs/reports/pki_current_status_report.md` - PKI validation and status

**Architecture**:
- `CROSS_PLATFORM_PKI_ARCHITECTURE.md` - Linux/Kubernetes integration guidance

### Historical Documentation (Archived)

**Location**: `docs/archives/pki_planning_2025/`  
**Status**: Historical reference only  
**Content**: Original two-tier PKI planning documents (January 2025)  
**See**: README_ARCHIVE.md in archive directory

---

## 🚀 Quick Start

### Check PKI Status
```powershell
# Via WinRM
Invoke-Command -ComputerName bakerstreeta.ad.bakerstreetlabs.io -ScriptBlock {
    Write-Host "=== CA Status ==="
    Get-Service CertSvc | Select-Object Name, Status
    
    Write-Host "`n=== BSL Templates ==="
    certutil -CATemplates | Select-String "BSL"
    
    Write-Host "`n=== Auto-Enrollment GPO ==="
    Get-GPO -Name "Baker Street Labs Certificate Auto-Enrollment" | 
        Select-Object DisplayName, GpoStatus
}
```

### Test Auto-Enrollment
```powershell
# On any domain computer
gpupdate /force
certutil -pulse

# Verify certificates
Get-ChildItem Cert:\LocalMachine\My | Where-Object { 
    $_.Issuer -like "*Baker Street Labs*" 
}
```

### Request Manual Certificate
```powershell
# Via web enrollment
Start-Process "https://bakerstreeta.ad.bakerstreetlabs.io/certsrv"
```

---

## 🔧 Common Operations

### Recreate All Templates
```powershell
# If templates need to be recreated
Invoke-Command -ComputerName bakerstreeta.ad.bakerstreetlabs.io -FilePath .\create_all_templates.ps1
```

### Verify and Publish Templates
```powershell
# Check template status
.\verify_and_publish_templates.ps1
```

### Create AD Security Groups
```powershell
# Create template permission groups
.\verify_and_publish_templates.ps1 -CreateGroups
```

---

## 🎓 Integration Guidance

### Kubernetes cert-manager
See: `CROSS_PLATFORM_PKI_ARCHITECTURE.md` for complete integration guide

**Templates to Use**:
- BSLK8sSigner - For cluster CA certificate
- BSLK8sService - For service certificates (90-day auto-renewal)

### Linux Systems
See: `integration/linux-integration-example.sh` for complete integration example

**Template to Use**:
- BSLLinuxAuth - For Linux system certificates

### Web Services
**Template to Use**:
- BSLWebServer - For web server TLS certificates
- Supports Subject Alternative Names (SANs)
- Manual issuance for proper CN/SAN configuration

---

## 📊 Script Quality

### Standards Met
- ✅ No hardcoded credentials
- ✅ Comprehensive error handling
- ✅ Detailed logging
- ✅ Proper parameter validation
- ✅ Security best practices
- ✅ Clean session management

### Testing
- ✅ Tested on Windows Server 2025
- ✅ Tested via WinRM remote execution
- ✅ Validated template creation
- ✅ Verified CA publishing

---

## 🔍 Troubleshooting

### Templates Not Creating
```powershell
# Check AD connectivity
Test-Connection -ComputerName bakerstreeta.ad.bakerstreetlabs.io

# Verify permissions
whoami /groups | Select-String "Domain Admins"

# Check template DN
$configNC = (Get-ADRootDSE).configurationNamingContext
Get-ADObject -SearchBase "CN=Certificate Templates,CN=Public Key Services,CN=Services,$configNC" -Filter {objectClass -eq "pKICertificateTemplate"}
```

### Templates Not Publishing
```powershell
# Manually publish template
certutil -SetCATemplates +BSLMachineAuth

# Restart CA service
Restart-Service CertSvc

# Verify
certutil -CATemplates | Select-String "BSL"
```

### Auto-Enrollment Not Working
```powershell
# Force GPO update
gpupdate /force

# Trigger enrollment
certutil -pulse

# Check event logs
Get-EventLog -LogName Application -Source "*Certificate*" -Newest 20
```

---

## 📞 Support

### Documentation
- **Main Index**: `docs/PKI_DOCUMENTATION_INDEX.md`
- **Operator Guide**: `docs/instructions/pki_template_creation_guide.md`
- **WinRM Guide**: `docs/instructions/winrm_authentication_guide.md`
- **AI Context**: `CURSOR_CONTEXT_PKI_PROJECT.md`

### Scripts Location
- **This Directory**: `E:\projects\baker-street-labs\scripts\pki\`
- **Repository**: https://github.com/packetalien/baker-street-labs

---

**Script Directory Version**: 2.0 (Updated for Enterprise Root CA)  
**Created**: October 8, 2025  
**Status**: Production Scripts Operational  
**PKI Deployment**: ✅ Complete

---

*"Automation transforms complexity into simplicity."* - Baker Street Labs PKI
