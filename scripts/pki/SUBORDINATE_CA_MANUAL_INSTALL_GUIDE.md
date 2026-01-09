# Subordinate CA Manual Installation Guide
## Baker Street Labs - bakerstreetb (DC2) Configuration

**Date**: October 9, 2025  
**Server**: bakerstreetb.ad.bakerstreetlabs.io (192.168.0.66)  
**Issue**: Automated installation encountering parameter conflict error  
**Solution**: Manual installation via Server Manager GUI

---

## Issue Encountered

**Error**: `ERROR_CLUSTER_PARAMETER_MISMATCH (0x80071709)`  
**Message**: "Property cannot be modified in current state of object"

**Diagnosis**:
- AD CS role installed successfully ✅
- CA configuration failing with PowerShell cmdlet
- No existing CA database or registry configuration found
- Parent CA (bakerstreeta) is operational and reachable

**Root Cause**: Likely a PowerShell cmdlet limitation or environment-specific configuration issue

---

## Manual Installation Steps (Server Manager)

### Step 1: Open Server Manager on bakerstreetb

1. RDP to bakerstreetb.ad.bakerstreetlabs.io (192.168.0.66)
2. Open Server Manager
3. Click **Manage** → **Add Roles and Features**

---

### Step 2: Configure AD Certificate Services

**Role Services to Install** (if not already):
- [x] Certification Authority
- [x] Certification Authority Web Enrollment

Click **Next** through the wizard until you reach **AD CS** configuration.

---

### Step 3: Configure Certification Authority

1. In Server Manager, click the notification flag → **Configure Active Directory Certificate Services**

2. **Credentials**: Use Domain Admin account

3. **Role Services**: Select:
   - [x] Certification Authority
   - [x] Certification Authority Web Enrollment

4. **Setup Type**: **Enterprise CA**

5. **CA Type**: **Subordinate CA** ← IMPORTANT

6. **Private Key**: 
   - ○ Create a new private key
   - Key Length: **2048**
   - Hash Algorithm: **SHA256**
   - Key Storage Provider: **Microsoft Software Key Storage Provider**

7. **CA Name**:
   - Common Name: **Baker Street Labs Issuing CA**
   - Distinguished Name: (auto-generated)

8. **Certificate Request**:
   - ○ **Send a certificate request to a parent CA**
   - Parent CA: **bakerstreeta.ad.bakerstreetlabs.io\Baker Street Labs Root CA**
   
   **OR** (if automatic fails):
   
   - ○ **Save a certificate request to file on the target machine**
   - File location: **C:\bakerstreetb-ca-request.req**

9. **Validity Period**: 5 years

10. Click **Configure**

---

### Step 4: Approve Request on Parent CA (if using file method)

If you saved the request to a file:

1. **Copy request file** from bakerstreetb:
   ```powershell
   Copy-Item \\bakerstreetb\C$\bakerstreetb-ca-request.req C:\Temp\
   ```

2. **RDP to bakerstreeta** (192.168.0.65)

3. **Open Certificate Authority console**

4. **Submit request**:
   - Right-click CA name → All Tasks → Submit new request
   - Browse to `C:\Temp\bakerstreetb-ca-request.req`
   - Click OK

5. **Issue certificate**:
   - Navigate to "Pending Requests"
   - Right-click the request → All Tasks → Issue

6. **Export issued certificate**:
   - Navigate to "Issued Certificates"
   - Double-click the newest certificate
   - Details tab → Copy to File
   - Export as .cer file
   - Save as `C:\bakerstreetb-ca-cert.cer`

---

### Step 5: Install Certificate on bakerstreetb

1. **Copy certificate back** to bakerstreetb:
   ```powershell
   Copy-Item C:\bakerstreetb-ca-cert.cer \\bakerstreetb\C$\
   ```

2. **On bakerstreetb**, open **Certificate Authority console**

3. **Install CA certificate**:
   - Right-click CA name → All Tasks → Install CA Certificate
   - Browse to `C:\bakerstreetb-ca-cert.cer`
   - Click Open

4. **Start the service**:
   ```powershell
   Start-Service CertSvc
   ```

---

### Step 6: Verify Installation

```powershell
# Check service status
Get-Service CertSvc

# Ping CA
certutil -ping

# Get CA info
certutil -CAInfo

# List templates
certutil -CATemplates
```

**Expected Output**:
- CertSvc: Running
- certutil -ping: Success
- CA Type: Subordinate CA
- Parent: Baker Street Labs Root CA

---

## Alternative: PowerShell with Manual Request File

If Server Manager also fails, use this pure PowerShell approach:

### Generate Request File

```powershell
# On bakerstreetb
$infFile = @"
[Version]
Signature="`$Windows NT`$"

[NewRequest]
Subject = "CN=Baker Street Labs Issuing CA,OU=PKI,O=Baker Street Labs,C=US"
KeySpec = 1
KeyLength = 2048
Exportable = FALSE
MachineKeySet = TRUE
RequestType = PKCS10
KeyUsage = 0x86

[Extensions]
2.5.29.19 = "{text}ca=1&pathlength=1"
2.5.29.15 = "{text}Digital Signature, Key Cert Sign, CRL Sign"
"@

$infFile | Out-File C:\issuing-ca.inf -Encoding ASCII

# Generate request
certreq -new C:\issuing-ca.inf C:\issuing-ca.req
```

### Submit to Parent CA

```powershell
# On bakerstreeta or from any machine
certreq -submit -config "bakerstreeta.ad.bakerstreetlabs.io\Baker Street Labs Root CA" C:\issuing-ca.req C:\issuing-ca.cer
```

### Install Certificate

```powershell
# On bakerstreetb
certreq -accept C:\issuing-ca.cer

# Configure the CA service to use this certificate
# This may require additional configuration via Server Manager
```

---

## Troubleshooting

### Error: Cannot start CertSvc

**Check**: CA certificate installed?
```powershell
Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -match "Issuing CA" }
```

**If not found**: Install the CA certificate first (Step 5)

### Error: Parameter Mismatch

**Solutions**:
1. Uninstall and reinstall AD CS role:
   ```powershell
   Uninstall-AdcsCertificationAuthority -Force
   Remove-WindowsFeature Adcs-Cert-Authority
   # Then reinstall and reconfigure
   ```

2. Use Server Manager GUI instead of PowerShell

3. Check event logs:
   ```powershell
   Get-EventLog -LogName Application -Source "CertificationAuthority" -Newest 20
   ```

---

## Post-Installation Tasks

Once CA is operational:

1. **Publish templates**:
   ```powershell
   certutil -SetCATemplates +BSLSSLDecryptCA
   ```

2. **Configure CRL distribution**:
   - Server Manager → AD CS → Configure
   - Set CRL and AIA URLs

3. **Test enrollment**:
   ```powershell
   certreq -new test.inf test.req
   certreq -submit test.req test.cer
   ```

---

## Next Steps After CA is Operational

1. ✅ Run `create-ssl-decrypt-template.ps1`
2. ✅ Run `request-and-export-firewall-cas.ps1`
3. ✅ Import PFX files into PAN-OS firewalls

---

## Support

**Documentation**:
- `auth_ad_omnibus.md` - Complete PKI reference
- `docs/PKI_QUICK_START_OPERATOR.md` - PKI operations
- `docs/PKI_DOCUMENTATION_INDEX.md` - All PKI docs

**Scripts**:
- `setup-issuing-ca-on-dc2.ps1` - Automated (if working)
- This guide - Manual fallback

**Server**:  bakerstreetb.ad.bakerstreetlabs.io (192.168.0.66)  
**Parent CA**: bakerstreeta.ad.bakerstreetlabs.io (192.168.0.65)

---

**Status**: Manual installation recommended due to PowerShell cmdlet issues  
**Est. Time**: 15-20 minutes via Server Manager GUI  
**Complexity**: Low (standard Windows Server procedure)

