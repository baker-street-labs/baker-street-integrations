# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

# Baker Street Labs - Firewall SSL Decryption CA Generation
# Requests and exports intermediate CA certificates for PAN-OS firewalls

<#
.SYNOPSIS
    Requests and exports SSL decryption CA certificates for PAN-OS firewalls

.DESCRIPTION
    This script:
    - Requests intermediate CA certificates using BSLSSLDecryptCA template
    - Installs certificates in local machine store
    - Exports certificates with private keys as PFX files
    - Prepares certificates for import into PAN-OS firewalls
    
.NOTES
    Prerequisites:
    - Run on bakerstreetb.ad.bakerstreetlabs.io (where Issuing CA is installed)
    - BSLSSLDecryptCA template must be published to CA
    - Run as Domain Admin
    
.PARAMETER ExportPath
    Directory to export PFX files (default: C:\pki-exports)
    
.PARAMETER PfxPassword
    Secure password for PFX files (will prompt if not provided)
    
.EXAMPLE
    .\request-and-export-firewall-cas.ps1 -Verbose
    
.EXAMPLE
    .\request-and-export-firewall-cas.ps1 -ExportPath "D:\firewall-certs"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$IssuingCAServer = "bakerstreetb.ad.bakerstreetlabs.io",
    
    [Parameter(Mandatory=$false)]
    [string]$IssuingCAName = "Baker Street Labs Issuing CA",
    
    [Parameter(Mandatory=$false)]
    [string]$TemplateName = "BSLSSLDecryptCA",
    
    [Parameter(Mandatory=$false)]
    [string]$ExportPath = "C:\pki-exports",
    
    [Parameter(Mandatory=$false)]
    [SecureString]$PfxPassword
)

$ErrorActionPreference = "Stop"

Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host " Baker Street Labs - Firewall CA Certificate Generation" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Prompt for password if not provided
if (-not $PfxPassword) {
    $PfxPassword = Read-Host -Prompt "Enter a secure password for the PFX files" -AsSecureString
    $PfxPasswordConfirm = Read-Host -Prompt "Confirm password" -AsSecureString
    
    # Convert to plain text for comparison
    $pwd1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($PfxPassword))
    $pwd2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($PfxPasswordConfirm))
    
    if ($pwd1 -ne $pwd2) {
        Write-Host "[ERROR] Passwords do not match" -ForegroundColor Red
        exit 1
    }
}

# Create export directory
if (-not (Test-Path $ExportPath)) {
    New-Item -Path $ExportPath -ItemType Directory | Out-Null
    Write-Host "[OK] Created export directory: $ExportPath" -ForegroundColor Green
} else {
    Write-Host "[INFO] Using existing directory: $ExportPath" -ForegroundColor Cyan
}

# Define firewalls
$firewalls = @(
    @{
        Name = "rangengfw"
        CommonName = "rangengfw-SSL-Decrypt-CA"
        Description = "Range NGFW SSL Decryption CA (192.168.0.7)"
    },
    @{
        Name = "xdrngfw"
        CommonName = "xdrngfw-SSL-Decrypt-CA"
        Description = "XDR NGFW SSL Decryption CA (192.168.255.200)"
    }
)

Write-Host ""
Write-Host "Processing $($firewalls.Count) firewall certificates..." -ForegroundColor Cyan
Write-Host ""

# Function to process each firewall
function New-FirewallDecryptCA {
    param(
        [Parameter(Mandatory=$true)]
        [hashtable]$Firewall,
        
        [Parameter(Mandatory=$true)]
        [string]$CAConfig,
        
        [Parameter(Mandatory=$true)]
        [string]$Template,
        
        [Parameter(Mandatory=$true)]
        [string]$Path,
        
        [Parameter(Mandatory=$true)]
        [SecureString]$Password
    )
    
    $firewallName = $Firewall.Name
    $commonName = $Firewall.CommonName
    
    Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
    Write-Host " Processing: $firewallName" -ForegroundColor Cyan
    Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Common Name: $commonName" -ForegroundColor Gray
    Write-Host "  Description: $($Firewall.Description)" -ForegroundColor Gray
    Write-Host ""
    
    # Define file paths
    $infPath = Join-Path $Path "$firewallName.inf"
    $reqPath = Join-Path $Path "$firewallName.req"
    $certPath = Join-Path $Path "$firewallName.cer"
    $pfxPath = Join-Path $Path "$firewallName.pfx"
    
    # Step 1: Create INF file
    Write-Host "  [1/5] Creating certificate request configuration..." -ForegroundColor Yellow
    
    $infContent = @"
[Version]
Signature="`$Windows NT`$"

[NewRequest]
Subject = "CN=$commonName,OU=Infrastructure,O=Baker Street Labs,L=Seattle,S=WA,C=US"
KeySpec = 1
KeyLength = 2048
Exportable = TRUE
MachineKeySet = TRUE
SMIME = FALSE
PrivateKeyArchive = FALSE
UserProtected = FALSE
UseExistingKeySet = FALSE
ProviderName = "Microsoft Software Key Storage Provider"
ProviderType = 12
RequestType = PKCS10
KeyUsage = 0x86  ; Digital Signature, Key Cert Sign, CRL Sign

[Extensions]
2.5.29.19 = "{text}ca=1&pathlength=0"  ; Basic Constraints (CA:TRUE, PathLen:0)
2.5.29.15 = "{text}"  ; Key Usage
_continue_ = "Digital Signature, Key Cert Sign, CRL Sign"

[RequestAttributes]
CertificateTemplate = "$Template"
"@
    
    $infContent | Out-File -FilePath $infPath -Encoding ASCII
    Write-Host "  [OK] Configuration file created: $infPath" -ForegroundColor Green
    
    # Step 2: Generate certificate request
    Write-Host "  [2/5] Generating certificate request..." -ForegroundColor Yellow
    
    $result = certreq.exe -new $infPath $reqPath 2>&1
    
    if (Test-Path $reqPath) {
        Write-Host "  [OK] Certificate request generated: $reqPath" -ForegroundColor Green
    } else {
        throw "Failed to generate certificate request"
    }
    
    # Step 3: Submit to CA
    Write-Host "  [3/5] Submitting request to Issuing CA: $CAConfig" -ForegroundColor Yellow
    
    $submitResult = certreq.exe -submit -config $CAConfig -attrib "CertificateTemplate:$Template" $reqPath $certPath 2>&1
    
    if (Test-Path $certPath) {
        Write-Host "  [OK] Certificate issued: $certPath" -ForegroundColor Green
        
        # Extract request ID from output
        $requestId = ($submitResult | Select-String -Pattern "RequestId:\s+(\d+)").Matches.Groups[1].Value
        if ($requestId) {
            Write-Host "  [INFO] Request ID: $requestId" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  [WARN] Certificate may need manual approval" -ForegroundColor Yellow
        Write-Host "  [ACTION] Check Certificate Authority console on $IssuingCAServer" -ForegroundColor Yellow
        Write-Host "  [ACTION] Look for pending requests and approve if necessary" -ForegroundColor Yellow
        return $false
    }
    
    # Step 4: Install certificate
    Write-Host "  [4/5] Installing certificate to local machine store..." -ForegroundColor Yellow
    
    $acceptResult = certreq.exe -accept -machine $certPath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Certificate installed in local machine store" -ForegroundColor Green
    } else {
        throw "Failed to install certificate"
    }
    
    # Step 5: Export as PFX with private key
    Write-Host "  [5/5] Exporting certificate with private key..." -ForegroundColor Yellow
    
    # Find the installed certificate
    $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { 
        $_.Subject -match $commonName 
    } | Select-Object -First 1
    
    if ($cert) {
        Write-Host "  [INFO] Found certificate:" -ForegroundColor Cyan
        Write-Host "        Subject: $($cert.Subject)" -ForegroundColor Gray
        Write-Host "        Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
        Write-Host "        NotAfter: $($cert.NotAfter)" -ForegroundColor Gray
        
        # Export to PFX
        Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $Password | Out-Null
        
        if (Test-Path $pfxPath) {
            $pfxSize = (Get-Item $pfxPath).Length
            Write-Host "  [OK] PFX exported: $pfxPath ($pfxSize bytes)" -ForegroundColor Green
        } else {
            throw "Failed to export PFX"
        }
    } else {
        throw "Could not find installed certificate for $commonName"
    }
    
    Write-Host ""
    Write-Host "  âœ… SUCCESS: $firewallName certificate ready for import" -ForegroundColor Green
    Write-Host ""
    
    return $true
}

# Process all firewalls
$caConfigString = "$IssuingCAServer\$IssuingCAName"
$successCount = 0

foreach ($fw in $firewalls) {
    try {
        $success = New-FirewallDecryptCA `
            -Firewall $fw `
            -CAConfig $caConfigString `
            -Template $TemplateName `
            -Path $ExportPath `
            -Password $PfxPassword
        
        if ($success) {
            $successCount++
        }
    } catch {
        Write-Host ""
        Write-Host "  [ERROR] Failed to process $($fw.Name): $_" -ForegroundColor Red
        Write-Host ""
    }
}

# Final summary
Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host " âœ… Certificate Generation Complete!" -ForegroundColor Green
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""
Write-Host "Certificates Processed: $successCount / $($firewalls.Count)" -ForegroundColor White
Write-Host "Export Location: $ExportPath" -ForegroundColor White
Write-Host ""
Write-Host "PFX Files Ready for PAN-OS Import:" -ForegroundColor Cyan
Get-ChildItem -Path $ExportPath -Filter "*.pfx" | ForEach-Object {
    Write-Host "  - $($_.Name) ($($_.Length) bytes)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Copy PFX files to your workstation" -ForegroundColor Yellow
Write-Host "  2. Log into each PAN-OS firewall web interface" -ForegroundColor Yellow
Write-Host "  3. Navigate to: Device â†’ Certificate Management â†’ Certificates" -ForegroundColor Yellow
Write-Host "  4. Import each PFX file with the password you specified" -ForegroundColor Yellow
Write-Host "  5. Configure SSL decryption policies to use these CA certificates" -ForegroundColor Yellow
Write-Host ""
Write-Host "Documentation: auth_ad_omnibus.md (PKI Infrastructure section)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""


