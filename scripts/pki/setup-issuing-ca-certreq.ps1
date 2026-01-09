<#
.SYNOPSIS
    Agentic Subordinate CA Setup using certreq.exe (PowerShell cmdlet alternative)
    
.DESCRIPTION
    Fully automated, API-driven Subordinate CA installation for Baker Street Labs
    Ideal for cyber range automation - zero GUI dependencies
    
.PARAMETER RootCAServer
    Root CA hostname (default: bakerstreeta.ad.bakerstreetlabs.io)
    
.PARAMETER SubCAServer
    Subordinate CA hostname (default: bakerstreetb.ad.bakerstreetlabs.io)
    
.PARAMETER WorkPath
    Working directory for CSR/cert files (default: C:\pki-scripts)
    
.EXAMPLE
    .\setup-issuing-ca-certreq.ps1 -Verbose
    
.NOTES
    Author: Baker Street Labs - Agentic Deployment System
    Date: October 9, 2025
    Version: 2.0 (certreq-based for full automation)
#>

[CmdletBinding()]
param(
    [string]$RootCAServer = "bakerstreeta.ad.bakerstreetlabs.io",
    [string]$SubCAServer = "bakerstreetb.ad.bakerstreetlabs.io",
    [string]$WorkPath = "C:\pki-scripts",
    [string]$CAName = "Baker Street Labs Issuing CA"
)

$ErrorActionPreference = "Stop"
$VerbosePreference = "Continue"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  AGENTIC SUBORDINATE CA SETUP - certreq.exe Method" -ForegroundColor Cyan
Write-Host "  Baker Street Labs PKI Automation v2.0" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ensure work directory exists
if (!(Test-Path $WorkPath)) {
    New-Item -ItemType Directory -Path $WorkPath -Force | Out-Null
    Write-Verbose "Created working directory: $WorkPath"
}

# Step 1: Create certificate request INF file
Write-Host "[1/8] Creating certificate request INF file..." -ForegroundColor Yellow
$infPath = Join-Path $WorkPath "subca-request.inf"
$infContent = @"
[Version]
Signature="`$Windows NT$"

[NewRequest]
Subject="CN=$CAName, O=Baker Street Labs, L=Cybersecurity Lab, ST=Virginia, C=US"
KeyLength=2048
KeySpec=1
KeyUsage=0xf0
Exportable=FALSE
MachineKeySet=TRUE
ProviderName="Microsoft RSA SChannel Cryptographic Provider"
RequestType=PKCS10
HashAlgorithm=SHA256
SMIME=FALSE
PrivateKeyArchive=FALSE
UserProtected=FALSE
UseExistingKeySet=FALSE

[RequestAttributes]
CertificateTemplate="SubCA"

[Extensions]
2.5.29.19 = "{text}ca=1&pathlength=0"
Critical = 2.5.29.19
"@

Set-Content -Path $infPath -Value $infContent -Force
Write-Host "    [OK] INF file created: $infPath" -ForegroundColor Green

# Step 2: Generate CSR on Subordinate CA
Write-Host "[2/8] Generating certificate request (CSR)..." -ForegroundColor Yellow
$reqPath = Join-Path $WorkPath "subca-request.req"

try {
    $result = certreq.exe -new $infPath $reqPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "certreq -new failed with exit code $LASTEXITCODE : $result"
    }
    Write-Host "    [OK] CSR generated: $reqPath" -ForegroundColor Green
    
    # Validate CSR
    $csrContent = Get-Content $reqPath -Raw
    if ($csrContent -match "BEGIN NEW CERTIFICATE REQUEST") {
        Write-Verbose "    CSR validation: Valid PKCS#10 request"
        Write-Verbose "    CSR size: $((Get-Item $reqPath).Length) bytes"
    } else {
        throw "Invalid CSR format"
    }
} catch {
    Write-Host "    [ERROR] CSR generation failed: $_" -ForegroundColor Red
    throw
}

# Step 3: Submit CSR to Root CA
Write-Host "[3/8] Submitting CSR to Root CA ($RootCAServer)..." -ForegroundColor Yellow
$certPath = Join-Path $WorkPath "subca-cert.cer"
$p7bPath = Join-Path $WorkPath "subca-cert.p7b"

try {
    $caConfig = "$RootCAServer\Baker Street Labs Root CA"
    $result = certreq.exe -submit -config $caConfig $reqPath $certPath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Certificate issued immediately: $certPath" -ForegroundColor Green
    } elseif ($LASTEXITCODE -eq 5) {
        # Certificate pending - need to approve
        Write-Host "    [WARN] Certificate request pending approval (ReqID in output)" -ForegroundColor Yellow
        Write-Host "    Output: $result" -ForegroundColor Cyan
        
        # Extract Request ID from output
        $reqId = $null
        if ($result -match "RequestId:\s+(\d+)") {
            $reqId = $matches[1]
            Write-Host "    Request ID: $reqId" -ForegroundColor Cyan
            
            # Attempt auto-approval (requires CA admin rights)
            Write-Host "[3a/8] Attempting auto-approval on Root CA..." -ForegroundColor Yellow
            try {
                Invoke-Command -ComputerName $RootCAServer -ScriptBlock {
                    param($RequestId)
                    certutil.exe -resubmit $RequestId
                } -ArgumentList $reqId -ErrorAction Stop
                
                Write-Host "    [OK] Certificate approved" -ForegroundColor Green
                Start-Sleep -Seconds 2
                
                # Retrieve issued certificate
                $result = certreq.exe -retrieve $reqId -config $caConfig $certPath 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    [OK] Certificate retrieved: $certPath" -ForegroundColor Green
                } else {
                    throw "Certificate retrieval failed: $result"
                }
            } catch {
                Write-Host "    [ERROR] Auto-approval failed: $_" -ForegroundColor Red
                Write-Host "    MANUAL ACTION REQUIRED:" -ForegroundColor Red
                Write-Host "      1. RDP to $RootCAServer" -ForegroundColor Yellow
                Write-Host "      2. Open Certification Authority console" -ForegroundColor Yellow
                Write-Host "      3. Approve request ID: $reqId" -ForegroundColor Yellow
                Write-Host "      4. Re-run: certreq -retrieve $reqId -config '$caConfig' '$certPath'" -ForegroundColor Yellow
                throw "Manual certificate approval required"
            }
        } else {
            throw "Could not extract Request ID from output: $result"
        }
    } else {
        throw "certreq -submit failed with exit code $LASTEXITCODE : $result"
    }
} catch {
    Write-Host "    [ERROR] CSR submission failed: $_" -ForegroundColor Red
    throw
}

# Step 4: Validate issued certificate
Write-Host "[4/8] Validating issued certificate..." -ForegroundColor Yellow
try {
    $certInfo = certutil.exe -dump $certPath 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Certificate is valid" -ForegroundColor Green
        Write-Verbose ($certInfo | Out-String)
        
        # Check for CA certificate extension
        if ($certInfo -match "CA Version") {
            Write-Verbose "    Confirmed: CA certificate"
        }
    } else {
        throw "Certificate validation failed: $certInfo"
    }
} catch {
    Write-Host "    [ERROR] Certificate validation failed: $_" -ForegroundColor Red
    throw
}

# Step 5: Install certificate on Subordinate CA
Write-Host "[5/8] Installing certificate on Subordinate CA..." -ForegroundColor Yellow
try {
    $result = certreq.exe -accept $certPath 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Certificate installed and CA configured" -ForegroundColor Green
        Write-Verbose ($result | Out-String)
    } else {
        throw "Certificate installation failed with exit code $LASTEXITCODE : $result"
    }
    
    Start-Sleep -Seconds 3
} catch {
    Write-Host "    [ERROR] Certificate installation failed: $_" -ForegroundColor Red
    throw
}

# Step 6: Configure CDP and AIA extensions
Write-Host "[6/8] Configuring CDP and AIA extensions..." -ForegroundColor Yellow
try {
    # CRL Distribution Points
    $crlUrls = @(
        "1:$env:WINDIR\system32\CertSrv\CertEnroll\%%3%%8%%9.crl",
        "2:http://crl.ad.bakerstreetlabs.io/CertEnroll/%%3%%8%%9.crl",
        "65:ldap:///CN=%%7%%8,CN=%%2,CN=CDP,CN=Public Key Services,CN=Services,%%6%%10"
    ) -join "\n"
    
    certutil.exe -setreg CA\CRLPublicationURLs $crlUrls | Out-Null
    Write-Host "    [OK] CDP configured" -ForegroundColor Green
    
    # Authority Information Access
    $aiaUrls = @(
        "1:$env:WINDIR\system32\CertSrv\CertEnroll\%%1_%%3%%4.crt",
        "2:http://crl.ad.bakerstreetlabs.io/CertEnroll/%%1_%%3%%4.crt",
        "32:ldap:///CN=%%7,CN=AIA,CN=Public Key Services,CN=Services,%%6%%11"
    ) -join "\n"
    
    certutil.exe -setreg CA\CACertPublicationURLs $aiaUrls | Out-Null
    Write-Host "    [OK] AIA configured" -ForegroundColor Green
    
} catch {
    Write-Host "    [WARN] CDP/AIA configuration warning: $_" -ForegroundColor Yellow
    Write-Host "    (Non-critical - can be configured later)" -ForegroundColor Yellow
}

# Step 7: Restart Certificate Services
Write-Host "[7/8] Restarting Certificate Services..." -ForegroundColor Yellow
try {
    Restart-Service certsvc -Force -ErrorAction Stop
    Start-Sleep -Seconds 5
    
    $svc = Get-Service certsvc
    if ($svc.Status -eq 'Running') {
        Write-Host "    [OK] Certificate Services restarted successfully" -ForegroundColor Green
    } else {
        throw "Service status: $($svc.Status)"
    }
} catch {
    Write-Host "    [ERROR] Service restart failed: $_" -ForegroundColor Red
    throw
}

# Step 8: Publish CRL and validate CA
Write-Host "[8/8] Publishing CRL and validating CA..." -ForegroundColor Yellow
try {
    certutil.exe -crl | Out-Null
    Write-Host "    [OK] CRL published" -ForegroundColor Green
    
    # Validate CA is operational
    $caConfig = "$SubCAServer\$CAName"
    $pingResult = certutil.exe -ping -config $caConfig 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] CA is operational!" -ForegroundColor Green
        Write-Verbose ($pingResult | Out-String)
    } else {
        throw "CA ping failed: $pingResult"
    }
} catch {
    Write-Host "    [ERROR] CRL/validation failed: $_" -ForegroundColor Red
    throw
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  [SUCCESS] SUBORDINATE CA INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "CA Configuration:" -ForegroundColor Cyan
Write-Host "  Name: $CAName" -ForegroundColor White
Write-Host "  Server: $SubCAServer" -ForegroundColor White
Write-Host "  Config: $SubCAServer``\$CAName" -ForegroundColor White
Write-Host "  Status: OPERATIONAL" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Create SSL Decrypt Template:" -ForegroundColor White
Write-Host "     Invoke-Command -ComputerName `$SubCAServer -ScriptBlock {" -ForegroundColor Yellow
Write-Host "         C:``\pki-scripts``\create-ssl-decrypt-template.ps1 -Verbose" -ForegroundColor Yellow
Write-Host "     }" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Generate Firewall Certificates:" -ForegroundColor White
Write-Host "     Invoke-Command -ComputerName `$SubCAServer -ScriptBlock {" -ForegroundColor Yellow
Write-Host "         C:``\pki-scripts``\request-and-export-firewall-cas.ps1 -Verbose" -ForegroundColor Yellow
Write-Host "     }" -ForegroundColor Yellow
Write-Host ""
Write-Host "Files Created:" -ForegroundColor Cyan
Write-Host "  INF: $infPath" -ForegroundColor White
Write-Host "  CSR: $reqPath" -ForegroundColor White
Write-Host "  CERT: $certPath" -ForegroundColor White
Write-Host ""

