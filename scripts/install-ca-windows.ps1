#!/usr/bin/env powershell
# Install Baker Street Labs CA Chain to Windows Trusted Root Store
# This allows browsers and Windows apps to trust certificates issued by Baker Street PKI

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Baker Street Labs CA Installation for Windows" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "  Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Checking for CA certificate files..." -ForegroundColor Yellow

# Get absolute paths
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Get-Location
}

$rootCertPath = Join-Path $scriptDir "baker-street-root-ca.crt"
$intermediateCertPath = Join-Path $scriptDir "baker-street-issuing-ca.crt"

Write-Host "  Script directory: $scriptDir" -ForegroundColor Cyan
Write-Host "  Root CA path: $rootCertPath" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $rootCertPath)) {
    Write-Host "[ERROR] Root CA not found: $rootCertPath" -ForegroundColor Red
    Write-Host "  Download from: https://192.168.0.236:8443/roots.pem" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $intermediateCertPath)) {
    Write-Host "[WARNING] Intermediate CA not found: $intermediateCertPath" -ForegroundColor Yellow
    Write-Host "  Will install Root CA only" -ForegroundColor Yellow
    $intermediateCertPath = $null
}

Write-Host "  [OK] Root CA found: $rootCertPath" -ForegroundColor Green
if ($intermediateCertPath) {
    Write-Host "  [OK] Intermediate CA found: $intermediateCertPath" -ForegroundColor Green
}

# Import Root CA to Trusted Root Certification Authorities
Write-Host ""
Write-Host "[2/4] Installing Root CA to Trusted Root Certification Authorities..." -ForegroundColor Yellow

try {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($rootCertPath)
    
    Write-Host "  Certificate Details:" -ForegroundColor Cyan
    Write-Host "    Subject: $($cert.Subject)" -ForegroundColor White
    Write-Host "    Issuer: $($cert.Issuer)" -ForegroundColor White
    Write-Host "    Valid: $($cert.NotBefore) to $($cert.NotAfter)" -ForegroundColor White
    Write-Host "    Thumbprint: $($cert.Thumbprint)" -ForegroundColor White
    
    # Check if already installed
    $existingCert = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    
    if ($existingCert) {
        Write-Host "  [OK] Root CA already installed (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green
    } else {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
        $store.Open("ReadWrite")
        $store.Add($cert)
        $store.Close()
        Write-Host "  [OK] Root CA installed successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "  [ERROR] Failed to install Root CA: $_" -ForegroundColor Red
    exit 1
}

# Import Intermediate CA to Intermediate Certification Authorities
if ($intermediateCertPath) {
    Write-Host ""
    Write-Host "[3/4] Installing Intermediate CA to Intermediate Certification Authorities..." -ForegroundColor Yellow
    
    try {
        $intermediateCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($intermediateCertPath)
        
        Write-Host "  Certificate Details:" -ForegroundColor Cyan
        Write-Host "    Subject: $($intermediateCert.Subject)" -ForegroundColor White
        Write-Host "    Issuer: $($intermediateCert.Issuer)" -ForegroundColor White
        Write-Host "    Valid: $($intermediateCert.NotBefore) to $($intermediateCert.NotAfter)" -ForegroundColor White
        Write-Host "    Thumbprint: $($intermediateCert.Thumbprint)" -ForegroundColor White
        
        # Check if already installed
        $existingIntermediate = Get-ChildItem Cert:\LocalMachine\CA | Where-Object { $_.Thumbprint -eq $intermediateCert.Thumbprint }
        
        if ($existingIntermediate) {
            Write-Host "  [OK] Intermediate CA already installed" -ForegroundColor Green
        } else {
            $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("CA", "LocalMachine")
            $store.Open("ReadWrite")
            $store.Add($intermediateCert)
            $store.Close()
            Write-Host "  [OK] Intermediate CA installed successfully" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [ERROR] Failed to install Intermediate CA: $_" -ForegroundColor Red
        Write-Host "  [INFO] Continuing - Root CA is sufficient for most cases" -ForegroundColor Yellow
    }
}

# Validation
Write-Host ""
Write-Host "[4/4] Validating installation..." -ForegroundColor Yellow

$rootCerts = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*Baker Street*" }
$intermediateCerts = Get-ChildItem Cert:\LocalMachine\CA | Where-Object { $_.Subject -like "*Baker Street*" }

Write-Host "  Baker Street Labs certificates in Trusted Root:" -ForegroundColor Cyan
foreach ($cert in $rootCerts) {
    Write-Host "    - $($cert.Subject)" -ForegroundColor White
}

if ($intermediateCerts) {
    Write-Host "  Baker Street Labs certificates in Intermediate:" -ForegroundColor Cyan
    foreach ($cert in $intermediateCerts) {
        Write-Host "    - $($cert.Subject)" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "[OK] CA Installation Complete!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Close and reopen your browser" -ForegroundColor White
Write-Host "  2. Access: https://rangexdr.bakerstreetlabs.io" -ForegroundColor White
Write-Host "  3. Certificate should now be trusted (green padlock)" -ForegroundColor White
Write-Host "  4. Verify certificate details show:" -ForegroundColor White
Write-Host "     - Subject: CN=rangexdr.bakerstreetlabs.io" -ForegroundColor White
Write-Host "     - Issuer: Baker Street Labs Issuing CA" -ForegroundColor White
Write-Host ""
Write-Host "Installed Certificates:" -ForegroundColor Yellow
Write-Host "  - Baker Street Labs Root CA (Trusted Root)" -ForegroundColor Green
if ($intermediateCertPath) {
    Write-Host "  - Baker Street Labs Issuing CA (Intermediate)" -ForegroundColor Green
}
Write-Host ""

