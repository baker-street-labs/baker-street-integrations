# Baker Street Labs - Subordinate Issuing CA Setup
# Installs Enterprise Subordinate CA on bakerstreetb (secondary DC)
# Subordinate to existing Root CA on bakerstreeta

<#
.SYNOPSIS
    Installs Enterprise Subordinate CA on secondary domain controller

.DESCRIPTION
    This script:
    - Installs AD Certificate Services role on bakerstreetb
    - Configures as Enterprise Subordinate CA
    - Requests signing certificate from Root CA on bakerstreeta
    - Sets up web enrollment interface
    
.NOTES
    Prerequisites:
    - Run as Domain Admin on bakerstreetb.ad.bakerstreetlabs.io
    - Root CA operational on bakerstreeta.ad.bakerstreetlabs.io
    - Forest functional level 2016+
    
.EXAMPLE
    .\setup-issuing-ca-on-dc2.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ParentCAServer = "bakerstreeta.ad.bakerstreetlabs.io",
    
    [Parameter(Mandatory=$false)]
    [string]$ParentCAName = "Baker Street Labs Root CA",
    
    [Parameter(Mandatory=$false)]
    [string]$IssuingCAName = "Baker Street Labs Issuing CA",
    
    [Parameter(Mandatory=$false)]
    [int]$ValidityYears = 5
)

# Set error action
$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Baker Street Labs - Subordinate Issuing CA Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Validate environment
Write-Host "[1/5] Validating environment..." -ForegroundColor Yellow

try {
    $computerName = $env:COMPUTERNAME
    Write-Host "  [INFO] Running on: $computerName" -ForegroundColor Cyan
    
    # Check if running on bakerstreetb
    if ($computerName -notlike "bakerstreetb*") {
        Write-Host "  [WARN] This script is designed for bakerstreetb" -ForegroundColor Yellow
        Write-Host "  [INFO] Current computer: $computerName" -ForegroundColor Yellow
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne 'y') {
            Write-Host "  [INFO] Aborting..." -ForegroundColor Yellow
            exit 0
        }
    }
    
    # Check if Domain Controller
    $isDC = (Get-WmiObject -Class Win32_ComputerSystem).DomainRole -ge 4
    if (-not $isDC) {
        throw "This script must be run on a Domain Controller"
    }
    Write-Host "  [OK] Running on Domain Controller" -ForegroundColor Green
    
    # Check if parent CA is accessible
    Write-Host "  [INFO] Testing connectivity to parent CA: $ParentCAServer" -ForegroundColor Cyan
    if (Test-Connection -ComputerName $ParentCAServer -Count 2 -Quiet) {
        Write-Host "  [OK] Parent CA server is reachable" -ForegroundColor Green
    } else {
        throw "Cannot reach parent CA server: $ParentCAServer"
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    exit 1
}

# Step 2: Install AD CS roles
Write-Host ""
Write-Host "[2/5] Installing AD Certificate Services roles..." -ForegroundColor Yellow

try {
    # Check if already installed
    $adcsRole = Get-WindowsFeature -Name Adcs-Cert-Authority
    
    if ($adcsRole.Installed) {
        Write-Host "  [INFO] AD CS role already installed" -ForegroundColor Cyan
    } else {
        Write-Host "  [ACTION] Installing AD CS role (this may take several minutes)..." -ForegroundColor Yellow
        
        $installResult = Add-WindowsFeature Adcs-Cert-Authority, Adcs-Web-Enrollment -IncludeManagementTools
        
        if ($installResult.Success) {
            Write-Host "  [OK] AD CS role installed successfully" -ForegroundColor Green
            Write-Host "  [INFO] Restart Required: $($installResult.RestartNeeded)" -ForegroundColor Cyan
        } else {
            throw "Failed to install AD CS role"
        }
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    exit 1
}

# Step 3: Configure Subordinate CA
Write-Host ""
Write-Host "[3/5] Configuring Enterprise Subordinate CA..." -ForegroundColor Yellow

try {
    # Parent CA configuration string
    $parentCAConfigString = "$ParentCAServer\$ParentCAName"
    Write-Host "  [INFO] Parent CA: $parentCAConfigString" -ForegroundColor Cyan
    Write-Host "  [INFO] Subordinate CA Name: $IssuingCAName" -ForegroundColor Cyan
    Write-Host "  [INFO] Validity Period: $ValidityYears years" -ForegroundColor Cyan
    
    # Check if CA is already configured
    $existingCA = Get-Service CertSvc -ErrorAction SilentlyContinue
    
    if ($existingCA -and $existingCA.Status -eq 'Running') {
        Write-Host "  [INFO] Certificate Services already configured and running" -ForegroundColor Cyan
        Write-Host "  [INFO] Skipping CA installation..." -ForegroundColor Yellow
    } else {
        Write-Host "  [ACTION] Installing Subordinate CA..." -ForegroundColor Yellow
        
        Install-AdcsCertificationAuthority `
            -CAType EnterpriseSubordinateCA `
            -KeyLength 2048 `
            -HashAlgorithmName SHA256 `
            -ValidityPeriod Years `
            -ValidityPeriodUnits $ValidityYears `
            -CryptoProviderName "RSA#Microsoft Software Key Storage Provider" `
            -CACommonName $IssuingCAName `
            -ParentCA $parentCAConfigString `
            -Force
        
        Write-Host "  [OK] Subordinate CA configured successfully" -ForegroundColor Green
        Write-Host "  [INFO] CA request submitted to parent CA" -ForegroundColor Cyan
        Write-Host "  [INFO] Parent CA admin may need to approve the request" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    Write-Host "  [INFO] This may be due to an existing CA configuration" -ForegroundColor Yellow
    Write-Host "  [INFO] Check Certificate Authority console for details" -ForegroundColor Yellow
}

# Step 4: Install Web Enrollment
Write-Host ""
Write-Host "[4/5] Installing Certificate Services Web Enrollment..." -ForegroundColor Yellow

try {
    $webEnrollmentRole = Get-WindowsFeature -Name Adcs-Web-Enrollment
    
    if ($webEnrollmentRole.Installed) {
        # Try to configure web enrollment
        $webEnrollment = Get-AdcsWebEnrollment -ErrorAction SilentlyContinue
        
        if (-not $webEnrollment) {
            Write-Host "  [ACTION] Configuring Web Enrollment..." -ForegroundColor Yellow
            Install-AdcsWebEnrollment -Force
            Write-Host "  [OK] Web Enrollment configured" -ForegroundColor Green
        } else {
            Write-Host "  [INFO] Web Enrollment already configured" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  [WARN] Web Enrollment configuration issue: $_" -ForegroundColor Yellow
    Write-Host "  [INFO] This can be configured later via Server Manager" -ForegroundColor Yellow
}

# Step 5: Restart and verify
Write-Host ""
Write-Host "[5/5] Restarting Certificate Services and verifying..." -ForegroundColor Yellow

try {
    Restart-Service CertSvc -ErrorAction Stop
    Start-Sleep -Seconds 5
    
    $caStatus = Get-Service CertSvc
    Write-Host "  [OK] Certificate Services Status: $($caStatus.Status)" -ForegroundColor Green
    
    # Check CA configuration
    Write-Host ""
    Write-Host "  [INFO] CA Configuration:" -ForegroundColor Cyan
    certutil -CAInfo
    
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Installation Summary" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $env:COMPUTERNAME" -ForegroundColor White
Write-Host "Subordinate CA: $IssuingCAName" -ForegroundColor White
Write-Host "Parent CA: $parentCAConfigString" -ForegroundColor White
Write-Host "Validity: $ValidityYears years" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Check parent CA (bakerstreeta) for pending certificate request" -ForegroundColor Yellow
Write-Host "  2. Approve the subordinate CA certificate request if needed" -ForegroundColor Yellow
Write-Host "  3. Verify CA is operational: certutil -ping" -ForegroundColor Yellow
Write-Host "  4. Publish certificate templates to this Issuing CA" -ForegroundColor Yellow
Write-Host "  5. Test certificate enrollment from a client" -ForegroundColor Yellow
Write-Host ""
Write-Host "Web Enrollment URL:" -ForegroundColor Cyan
Write-Host "  https://bakerstreetb.ad.bakerstreetlabs.io/certsrv" -ForegroundColor Green
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""


