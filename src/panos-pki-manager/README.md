# PAN-OS PKI Manager
## Automated Certificate Management for Palo Alto Networks Firewalls
### Baker Street Labs Certificate Infrastructure Integration

**Version**: 1.0  
**Created**: October 8, 2025  
**Status**: Production-Ready  
**Python**: 3.10+

---

## 🎯 Overview

This tool provides automated PKI certificate lifecycle management for Palo Alto Networks Next-Generation Firewalls (PAN-OS NGFW) using the Baker Street Labs PKI infrastructure. It creates an intermediate CA specifically for NGFW certificates and automates the complete certificate provisioning workflow.

### Key Features

- ✅ **Automated Intermediate CA Creation** - Creates NGFW-specific intermediate CA
- ✅ **Certificate Template Management** - Programmatically creates AD CS templates
- ✅ **CSR Generation on Firewalls** - Uses PAN-OS XML API
- ✅ **Automated Signing** - Submits CSRs to Windows CA via WinRM
- ✅ **Certificate Import** - Imports signed certificates back to firewalls
- ✅ **Full Chain Support** - Builds and validates certificate chains
- ✅ **Multi-Firewall Support** - Processes multiple firewalls in batch
- ✅ **Dry Run Mode** - Test without making changes
- ✅ **Comprehensive Logging** - Detailed operation logging
- ✅ **Error Handling** - Robust error handling and recovery

---

## 🏗️ Architecture

```
Baker Street Labs PKI
├── Root CA (bakerstreeta.ad.bakerstreetlabs.io)
│   └── "Baker Street Labs Root CA"
│       └── Intermediate CA (NGFW)
│           └── "Baker Street Labs NGFW Intermediate CA"
│               ├── Hub Firewall Certificate (192.168.0.7)
│               ├── Spoke Firewall Certificate (192.168.255.200)
│               └── Additional NGFW Certificates
```

### Integration Points

1. **Windows Active Directory Certificate Services**
   - Enterprise Root CA: bakerstreeta.ad.bakerstreetlabs.io
   - Domain: ad.bakerstreetlabs.io
   - Access: WinRM with Kerberos authentication

2. **Palo Alto Networks Firewalls**
   - Hub: 192.168.0.7
   - Spoke: 192.168.255.200
   - Access: XML API with API key or username/password

3. **Certificate Templates**
   - NGFWIntermediate: 5-year CA certificate
   - BSLWebServer or NGFWServer: 1-year firewall certificates

---

## 📋 Prerequisites

### System Requirements
- Python 3.10 or later
- Network access to:
  - bakerstreeta.ad.bakerstreetlabs.io (WinRM port 5985)
  - Palo Alto firewalls (HTTPS port 443)
- Domain credentials with Domain Admin privileges
- Firewall API access (API key or admin credentials)

### Software Dependencies
- Windows CA: Active Directory Certificate Services operational
- PAN-OS: Version 11.0 or later recommended
- Network: Kerberos/WinRM configured for domain

### Knowledge Requirements
- Basic PKI concepts (CA, CSR, certificates)
- PAN-OS certificate management
- Windows Active Directory familiarity
- Python development basics

---

## 🚀 Installation

### Step 1: Clone or Download

```bash
cd /e/projects/baker-street-labs/tools
# Already in panos-pki-manager directory
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Kerberos (for WinRM)

**On Windows**:
- Ensure machine is domain-joined to ad.bakerstreetlabs.io
- Login as domain user with admin privileges
- Kerberos authentication automatic

**On Linux**:
```bash
# Install Kerberos client
sudo apt-get install krb5-user  # Debian/Ubuntu
sudo dnf install krb5-workstation  # RHEL/Rocky

# Configure /etc/krb5.conf
[libdefaults]
    default_realm = AD.BAKERSTREETLABS.IO
    
[realms]
    AD.BAKERSTREETLABS.IO = {
        kdc = bakerstreeta.ad.bakerstreetlabs.io
        admin_server = bakerstreeta.ad.bakerstreetlabs.io
    }

# Get Kerberos ticket
kinit richard@AD.BAKERSTREETLABS.IO
```

### Step 4: Configure Application

```bash
# Copy example configuration
cp config.yaml.example config.yaml

# Edit configuration
nano config.yaml  # or your preferred editor
```

**Required Configuration**:
- Certificate Authority FQDN and name
- Firewall IP addresses and hostnames
- Certificate specifications (CN, SANs, templates)

### Step 5: Set Environment Variables

Create `.env` file or set in shell:

```bash
# WinRM Credentials (Windows CA access)
export WINRM_USER="richard@BAKERSTREETLABS"  # or BAKERSTREETLABS\richard
export WINRM_PASS="your_domain_password"

# Firewall API Keys (preferred) or Passwords
export PAN_HUB_API_KEY="your_hub_api_key"
export PAN_SPOKE_API_KEY="your_spoke_api_key"

# Alternative: Use passwords
export PAN_HUB_USERNAME="admin"
export PAN_HUB_PASSWORD="your_hub_password"
export PAN_SPOKE_USERNAME="admin"
export PAN_SPOKE_PASSWORD="your_spoke_password"
```

**Security Note**: Never commit `.env` file to git. It's in `.gitignore`.

---

## 💻 Usage

### Basic Usage

```bash
# Process all configured firewalls
python main.py

# Process specific firewalls
python main.py --firewalls hub spoke

# Dry run (no changes made)
python main.py --dry-run

# Verbose output
python main.py --verbose

# Custom configuration file
python main.py --config custom_config.yaml
```

### Setup Intermediate CA Only

```bash
# Create intermediate CA without processing firewalls
python main.py --setup-ca-only
```

### Common Workflows

**Initial Setup**:
```bash
# 1. Setup intermediate CA
python main.py --setup-ca-only

# 2. Process all firewalls
python main.py
```

**Update Single Firewall**:
```bash
# Process only hub firewall
python main.py --firewalls hub
```

**Testing Changes**:
```bash
# Dry run to see what would happen
python main.py --dry-run --verbose
```

---

## 🔧 Configuration Reference

### Certificate Authority Section

```yaml
certificate_authority:
  fqdn: "bakerstreeta.ad.bakerstreetlabs.io"  # REQUIRED: CA server FQDN
  ip_address: "192.168.0.65"                   # Optional: CA IP address
  domain: "ad.bakerstreetlabs.io"              # REQUIRED: AD domain
  ca_name: "Baker Street Labs Root CA"         # REQUIRED: CA name
  
  winrm:
    port: 5985                                  # WinRM HTTP port
    transport: "kerberos"                       # kerberos, ntlm, or basic
```

### Intermediate CA Section

```yaml
intermediate_ca:
  create_if_missing: true                      # Auto-create if doesn't exist
  template_name: "NGFWIntermediate"            # AD template name
  display_name: "Baker Street Labs NGFW Intermediate CA"
  
  subject:
    common_name: "Baker Street Labs NGFW Intermediate CA"
    organization: "Baker Street Labs"
    organizational_unit: "NGFW"
    country: "US"
    
  key_config:
    algorithm: "RSA"
    key_size: 4096                             # 4096 for CA certificates
    hash_algorithm: "SHA256"
    
  validity:
    years: 5                                   # Long-lived for stability
    renewal_weeks: 26
```

### Firewall Section

```yaml
firewalls:
  - name: "hub"                                # REQUIRED: Unique name
    hostname: "hub-fw.ad.bakerstreetlabs.io"   # REQUIRED: FQDN
    ip_address: "192.168.0.7"                  # REQUIRED: Management IP
    role: "hub"                                # Optional: Metadata
    
    certificates:
      - name: "management-interface"           # REQUIRED: Cert name on firewall
        common_name: "hub-fw.ad.bakerstreetlabs.io"  # REQUIRED: Certificate CN
        sans:                                  # Optional but recommended
          - "hub-fw.ad.bakerstreetlabs.io"
          - "192.168.0.7"
          - "hub-firewall"
        template: "BSLWebServer"               # CA template to use
        key_size: 2048                         # RSA key size
        validity_years: 1                      # Certificate validity
```

---

## 📂 Project Structure

```
panos-pki-manager/
├── main.py                      # Main entry point
├── config_manager.py            # Configuration management
├── pki_intermediate.py          # Intermediate CA operations
├── firewall_api.py              # PAN-OS API interactions
├── csr_signing.py               # CSR signing with Windows CA
├── utils.py                     # Utility functions
├── test_pki_manager.py          # Unit tests
├── requirements.txt             # Python dependencies
├── config.yaml.example          # Example configuration
├── config.yaml                  # Your configuration (not in git)
├── .env                         # Environment variables (not in git)
└── README.md                    # This file

Output directories (created automatically):
├── certificates/                # Signed certificates
├── csrs/                        # Certificate signing requests
├── backups/                     # Firewall configuration backups
└── panos_pki_manager.log        # Application log file
```

---

## 🔐 Security Considerations

### Credential Management

**DO**:
- ✅ Use environment variables for credentials
- ✅ Use API keys instead of passwords when possible
- ✅ Use Kerberos for WinRM authentication
- ✅ Restrict file permissions on config files
- ✅ Use `.env` file (not committed to git)

**DON'T**:
- ❌ Hardcode credentials in configuration files
- ❌ Commit `.env` or `config.yaml` with secrets to git
- ❌ Use Basic auth for WinRM (use Kerberos)
- ❌ Store private keys in insecure locations

### Key Management

**Intermediate CA Private Key**:
- Saved to `intermediate_ca_key.pem` on first creation
- **CRITICAL**: Protect this file (consider HSM or key vault in production)
- Backup securely and store offline
- Restrict file permissions: `chmod 600 intermediate_ca_key.pem`

**Firewall Private Keys**:
- Generated on firewall, never exported
- Remain on firewall device
- More secure than external generation + import

### Network Security

- WinRM traffic: Use Kerberos (encrypted by default)
- PAN-OS API: HTTPS (encrypted)
- Firewall management: Restrict to management network
- CA server: Restrict WinRM access to authorized systems

---

## 🔄 Workflow Details

### Complete Certificate Provisioning Workflow

```
1. Check/Create Intermediate CA
   ├── Check if NGFWIntermediate template exists in AD
   ├── Create template if missing (via PowerShell/WinRM)
   ├── Check if intermediate CA certificate exists
   ├── Generate CSR for intermediate CA (4096-bit RSA)
   ├── Submit CSR to Root CA for signing
   └── Store intermediate CA certificate and key

2. For Each Firewall:
   ├── Connect to firewall via API
   ├── Backup current configuration
   ├── For each configured certificate:
   │   ├── Check if certificate already exists
   │   ├── Generate CSR on firewall (2048-bit RSA)
   │   ├── Retrieve CSR from firewall
   │   ├── Submit CSR to Windows CA (via WinRM)
   │   ├── CA signs CSR using specified template
   │   ├── Retrieve signed certificate
   │   ├── Build certificate chain (cert + intermediate + root)
   │   ├── Validate certificate chain
   │   ├── Import certificate chain to firewall
   │   └── Save certificate to output directory
   └── Commit firewall configuration changes

3. Summary and Reporting
   ├── Log all operations
   ├── Report success/failure for each firewall
   └── Save certificates and CSRs for audit trail
```

### Error Handling

The tool handles various error scenarios:

- **WinRM Connection Failures**: Retries, clear error messages
- **CSR Generation Failures**: Validates CSR before submission
- **CA Signing Failures**: Detailed error logging
- **Certificate Import Failures**: Rollback available (via backup)
- **API Timeouts**: Configurable timeouts and retries

---

## 📊 Operational Examples

### Example 1: Initial Certificate Deployment

```bash
# 1. Setup (first time only)
python main.py --setup-ca-only --verbose

# Expected output:
# ✅ Template NGFWIntermediate created
# ✅ Intermediate CA CSR generated
# ✅ Intermediate CA certificate signed by Root CA
# ✅ Intermediate CA ready

# 2. Deploy certificates to all firewalls
python main.py --verbose

# Expected output:
# ✅ Connected to hub firewall
# ✅ Generated CSR for management-interface
# ✅ CSR signed by CA using BSLWebServer template
# ✅ Certificate imported to hub
# ✅ Committed changes to hub
# ✅ Connected to spoke firewall
# ... (repeat for spoke)
```

### Example 2: Update Certificate for Single Firewall

```bash
# Process only the hub firewall
python main.py --firewalls hub

# Expected output:
# ✅ Intermediate CA exists
# ✅ Processing firewall: hub
# ✅ Certificate management-interface already exists
# ℹ️  1/1 certificates processed for hub
```

### Example 3: Dry Run Before Production

```bash
# Test what would happen without making changes
python main.py --dry-run --verbose

# Expected output:
# ⚠️  DRY RUN MODE - No changes will be made
# ℹ️  [DRY RUN] Would generate CSR for management-interface
# ℹ️  [DRY RUN] Would commit changes to firewall
```

---

## 🔍 Troubleshooting

### Common Issues

#### Issue 1: WinRM Connection Failures

**Symptoms**:
```
ERROR - Failed to create WinRM session: ...
```

**Solutions**:
1. **Verify FQDN**: Must use `bakerstreeta.ad.bakerstreetlabs.io` (not IP)
2. **Check Credentials**: Ensure WINRM_USER and WINRM_PASS are set
3. **Test WinRM**:
   ```powershell
   Test-WSMan -ComputerName bakerstreeta.ad.bakerstreetlabs.io
   ```
4. **Verify Kerberos**: Ensure domain authentication working
5. **Check Network**: Firewall rules allow WinRM port 5985

#### Issue 2: Firewall API Connection Failures

**Symptoms**:
```
ERROR - Failed to connect to firewall hub: ...
```

**Solutions**:
1. **Verify IP Address**: Ping 192.168.0.7
2. **Check API Access**: Test in browser https://192.168.0.7
3. **Verify Credentials**: Check API key or password
4. **Generate API Key** (if needed):
   ```xml
   <request><password-hash><password>your_password</password></password-hash></request>
   ```
   Or via Web UI: Device → Administrators → Generate API Key

#### Issue 3: CSR Generation Fails

**Symptoms**:
```
ERROR - Failed to generate CSR for management-interface
```

**Solutions**:
1. **Check Certificate Name**: Must be unique on firewall
2. **Verify Permissions**: API user needs certificate management rights
3. **Check Existing**: May need to delete existing CSR/cert
4. **Review Firewall Logs**: Check system logs on PAN-OS

#### Issue 4: Certificate Signing Fails

**Symptoms**:
```
ERROR - CSR signing failed: ...
```

**Solutions**:
1. **Verify Template**: Ensure BSLWebServer template published to CA
   ```powershell
   certutil -CATemplates | Select-String "BSLWebServer"
   ```
2. **Check CA Service**: `Get-Service CertSvc` should be Running
3. **Verify Permissions**: User needs Enroll rights on template
4. **Review CA Logs**: Check Application event log on CA server

#### Issue 5: Certificate Import Fails

**Symptoms**:
```
ERROR - Failed to import certificate management-interface-signed
```

**Solutions**:
1. **Check Certificate Format**: Must be valid PEM
2. **Verify Chain**: Certificate chain must be complete
3. **Check Firewall Space**: Ensure sufficient storage
4. **Review XML API Response**: Check for specific error codes

### Debug Mode

Enable verbose logging:

```bash
python main.py --verbose

# Or set in config.yaml:
logging:
  level: "DEBUG"
```

### Testing Individual Components

```python
# Test configuration
python -c "from config_manager import ConfigManager; c = ConfigManager(); print(c.get_ca_config())"

# Test WinRM connection
python -c "import winrm; s = winrm.Session('http://bakerstreeta.ad.bakerstreetlabs.io:5985/wsman', auth=('user', 'pass')); print(s.run_ps('hostname'))"

# Test firewall connection
python -c "from panos import firewall; fw = firewall.Firewall('192.168.0.7', api_username='admin', api_password='pass'); print(fw.op('show system info'))"
```

---

## 📚 Integration with Baker Street Labs PKI

### Leveraging Existing Templates

**BSLWebServer Template** (Recommended for NGFW):
- 1-year validity
- Server Authentication EKU
- Manual issuance
- SAN support
- Exportable private key

**NGFWServer Template** (Optional - Create if needed):
- NGFW-specific template
- Same configuration as BSLWebServer
- Easier to identify NGFW certificates
- Separate permissions if desired

### Certificate Lifecycle

**Initial Provisioning** (This Tool):
1. Generate CSR on firewall
2. Sign with Windows CA
3. Import to firewall

**Renewal** (Future Enhancement):
- Monitor certificate expiration
- Auto-renew before expiration
- Seamless certificate rotation

**Revocation** (Manual):
1. Identify certificate by serial number
2. Revoke via CA console or certutil
3. CRL/OCSP will distribute revocation status

---

## 🎓 Advanced Usage

### Custom Certificate Templates

Create NGFW-specific template:

```yaml
# In config.yaml
ngfw_template:
  create_if_missing: true
  name: "NGFWServer"
  display_name: "Baker Street Labs NGFW Server"
  validity_years: 1
  key_size: 2048
  extended_key_usage:
    - "1.3.6.1.5.5.7.3.1"  # Server Authentication
```

The tool will create this template automatically if `create_if_missing: true`.

### Multiple Certificates Per Firewall

```yaml
firewalls:
  - name: "hub"
    ip_address: "192.168.0.7"
    certificates:
      - name: "management-interface"
        common_name: "hub-fw.ad.bakerstreetlabs.io"
        template: "BSLWebServer"
        
      - name: "ssl-decryption"
        common_name: "hub-fw-decrypt.ad.bakerstreetlabs.io"
        template: "NGFWDecryption"
        
      - name: "vpn-gateway"
        common_name: "vpn.bakerstreetlabs.io"
        template: "BSLWebServer"
```

### Batch Processing

```bash
# Process all hub firewalls (if you have multiple)
python main.py --firewalls hub-dc1 hub-dc2 hub-dr

# Process all spoke firewalls
python main.py --firewalls spoke-1 spoke-2 spoke-3
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest test_pki_manager.py -v

# Run with coverage
pytest test_pki_manager.py --cov=. --cov-report=html

# Run specific test
pytest test_pki_manager.py::TestConfigManager::test_config_loading -v
```

### Integration Testing

```bash
# Set environment variable to enable integration tests
export INTEGRATION_TESTS=1

# Requires real infrastructure access
pytest test_pki_manager.py -v -m integration
```

### Manual Testing Checklist

- [ ] Configuration loads without errors
- [ ] WinRM connection to CA server successful
- [ ] Intermediate CA template created
- [ ] Intermediate CA certificate signed
- [ ] Firewall API connection successful
- [ ] CSR generated on firewall
- [ ] CSR signed by CA
- [ ] Certificate imported to firewall
- [ ] Firewall commit successful
- [ ] Certificate visible on firewall
- [ ] HTTPS works with new certificate

---

## 📖 API Documentation

### ConfigManager

```python
from config_manager import ConfigManager

config = ConfigManager('config.yaml')

# Get configurations
ca_config = config.get_ca_config()
firewalls = config.get_firewalls()
settings = config.get_settings()

# Check dry run mode
if config.is_dry_run():
    print("Running in dry-run mode")
```

### PKIIntermediateCA

```python
from pki_intermediate import PKIIntermediateCA

pki = PKIIntermediateCA(ca_config, intermediate_config)

# Check if template exists
exists = pki.check_template_exists('NGFWIntermediate')

# Create intermediate CA
pki.ensure_intermediate_ca()

# Get Root CA certificate
root_cert = pki.get_root_ca_certificate()
```

### FirewallAPI

```python
from firewall_api import FirewallAPI

fw = FirewallAPI(firewall_config)

# Generate CSR
csr = fw.generate_certificate_csr(cert_config)

# Import certificate
fw.import_certificate('cert-name', cert_chain_pem)

# Commit changes
fw.commit_changes()
```

### CSRSigner

```python
from csr_signing import CSRSigner

signer = CSRSigner(ca_config)

# Sign CSR
cert_pem = signer.sign_csr(csr_pem, 'BSLWebServer')

# Build full chain
chain = signer.get_certificate_chain(cert_pem)
```

---

## 🔄 Certificate Renewal Process

**Manual Renewal** (Current):
1. Delete old certificate on firewall
2. Run script to generate new CSR and import certificate
3. Update SSL/TLS profiles to use new certificate

**Automated Renewal** (Future Enhancement):
1. Monitor certificate expiration (60-day threshold)
2. Auto-generate new CSR
3. Submit to CA for signing
4. Import and activate new certificate
5. Remove old certificate after grace period

**Renewal Command** (Future):
```bash
python main.py --renew --threshold 60  # Renew certs expiring in 60 days
```

---

## 📊 Monitoring and Maintenance

### Check Certificate Status

```python
from firewall_api import FirewallAPI

fw = FirewallAPI(firewall_config)
certs = fw.list_certificates()

for cert in certs:
    print(f"Name: {cert['name']}")
    print(f"Subject: {cert['subject']}")
    print(f"Expiry: {cert['expiry']}")
```

### Monitor CA Health

```bash
# Via WinRM
Invoke-Command -ComputerName bakerstreeta.ad.bakerstreetlabs.io -ScriptBlock {
    Get-Service CertSvc
    certutil -ping
}
```

### Check Issued Certificates

```bash
# On CA server
certutil -view -restrict "CertificateTemplate=BSLWebServer" -out "CommonName,NotAfter" csv
```

---

## 🚀 Future Enhancements

### Planned Features
- [ ] Automated certificate renewal monitoring
- [ ] Certificate expiration alerting
- [ ] Multi-domain support
- [ ] Certificate revocation automation
- [ ] Integration with monitoring systems (Prometheus, Grafana)
- [ ] Web UI for certificate management
- [ ] REST API for programmatic access
- [ ] Support for additional firewall types

### Integration Opportunities
- **Ansible Playbook**: Wrap this tool in Ansible for infrastructure-as-code
- **Terraform Provider**: Use as provisioner in Terraform
- **CI/CD Pipeline**: Automated certificate deployment
- **Monitoring**: Export metrics for Prometheus
- **Alerting**: Integrate with alerting systems

---

## 📞 Support and Contribution

### Documentation
- **PKI Documentation**: `docs/PKI_DOCUMENTATION_INDEX.md`
- **Template Specs**: `docs/plans/pki_custom_template_recommendations.md`
- **WinRM Guide**: `docs/instructions/winrm_authentication_guide.md`
- **AI Context**: `docs/ai_context/grok_api_guide.md`

### Getting Help
1. Check this README
2. Review logs in `panos_pki_manager.log`
3. Run with `--verbose` for detailed output
4. Check Baker Street Labs documentation
5. Review test cases for usage examples

### Contributing
1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Test with `--dry-run` before production
5. Commit with descriptive messages

---

## 📋 Quick Reference

### Environment Variables
```bash
# WinRM (required)
WINRM_USER="richard@BAKERSTREETLABS"
WINRM_PASS="your_password"

# PAN-OS API (required for each firewall)
PAN_HUB_API_KEY="hub_api_key"
PAN_SPOKE_API_KEY="spoke_api_key"

# Optional overrides
LOG_LEVEL="DEBUG"
DRY_RUN="true"
```

### Quick Commands
```bash
# Full deployment
python main.py

# Dry run
python main.py --dry-run --verbose

# Single firewall
python main.py --firewalls hub

# Setup CA only
python main.py --setup-ca-only

# Run tests
pytest -v
```

### Important Files
- Configuration: `config.yaml`
- Credentials: `.env`
- Logs: `panos_pki_manager.log`
- Certificates: `certificates/`
- CSRs: `csrs/`
- Backups: `backups/`

---

## ⚠️ Important Notes

### Domain Name
**CRITICAL**: Always use `ad.bakerstreetlabs.io`
- ❌ NOT `bakerstreetlabs.local`
- ❌ NOT `bakerstreet.local`
- ✅ USE `ad.bakerstreetlabs.io`

### Server Names
- ✅ `bakerstreeta.ad.bakerstreetlabs.io` (CA server)
- ✅ `bakerstreetb.ad.bakerstreetlabs.io` (Secondary DC)
- ❌ NOT `brownstone-a` or `brownstone-b`

### Template Names
- Use `BSLWebServer` for general web server certificates
- Use `NGFWIntermediate` for the intermediate CA
- Custom templates: Follow BSL* naming convention

---

## 📜 License and Attribution

**Project**: Baker Street Labs  
**Component**: PAN-OS PKI Manager  
**Created**: October 8, 2025  
**Maintained By**: Baker Street Labs Team

This tool integrates with:
- Microsoft Active Directory Certificate Services
- Palo Alto Networks PAN-OS
- Baker Street Labs PKI infrastructure

---

## 🎯 Success Criteria

### Deployment Success
- ✅ Intermediate CA created and operational
- ✅ Certificates generated and signed
- ✅ Certificates imported to firewalls
- ✅ HTTPS/SSL services working with PKI certificates
- ✅ Certificate chain validates correctly

### Operational Success
- ✅ Automated certificate provisioning
- ✅ Reduced manual certificate management
- ✅ Audit trail of all operations
- ✅ Integration with existing PKI infrastructure

---

**README Version**: 1.0  
**Last Updated**: October 8, 2025  
**Status**: Production-Ready  
**Next Review**: After first deployment

---

*"Automation transforms complexity into simplicity—certificates managed with the precision of Sherlock Holmes himself."* - Baker Street Labs PKI Philosophy






