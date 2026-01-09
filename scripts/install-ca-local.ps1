#!/usr/bin/env pwsh
#
# Install Baker Street Labs CA Certificates to Windows Trust Store
# Installs Root CA and Issuing CA for local machine
#
# Author: Baker Street Labs
# Date: October 22, 2025
#

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "Baker Street Labs CA Certificate Installation" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$rootCertPath = Join-Path $scriptDir "baker-street-root-ca.crt"
$issuingCertPath = Join-Path $scriptDir "baker-street-issuing-ca.crt"

# Check if files exist
Write-Host "[1/4] Checking for CA certificate files..." -ForegroundColor Yellow
if (Test-Path $rootCertPath) {
    Write-Host "  [OK] Root CA found: $rootCertPath" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Root CA not found at: $rootCertPath" -ForegroundColor Red
    exit 1
}

if (Test-Path $issuingCertPath) {
    Write-Host "  [OK] Issuing CA found: $issuingCertPath" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Issuing CA not found at: $issuingCertPath" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install Root CA
Write-Host "[2/4] Installing Root CA to Trusted Root Certification Authorities..." -ForegroundColor Yellow
try {
    $rootCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($rootCertPath)
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $rootStore.Open("ReadWrite")
    
    # Check if already installed
    $existing = $rootStore.Certificates | Where-Object { $_.Thumbprint -eq $rootCert.Thumbprint }
    if ($existing) {
        Write-Host "  [INFO] Root CA already installed (Thumbprint: $($rootCert.Thumbprint))" -ForegroundColor Cyan
    } else {
        $rootStore.Add($rootCert)
        Write-Host "  [OK] Root CA installed successfully" -ForegroundColor Green
        Write-Host "    Subject: $($rootCert.Subject)" -ForegroundColor White
        Write-Host "    Issuer: $($rootCert.Issuer)" -ForegroundColor White
        Write-Host "    Thumbprint: $($rootCert.Thumbprint)" -ForegroundColor White
        Write-Host "    Valid: $($rootCert.NotBefore) to $($rootCert.NotAfter)" -ForegroundColor White
    }
    
    $rootStore.Close()
} catch {
    Write-Host "  [ERROR] Failed to install Root CA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install Issuing CA
Write-Host "[3/4] Installing Issuing CA to Intermediate Certification Authorities..." -ForegroundColor Yellow
try {
    $issuingCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($issuingCertPath)
    $caStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("CA", "LocalMachine")
    $caStore.Open("ReadWrite")
    
    # Check if already installed
    $existing = $caStore.Certificates | Where-Object { $_.Thumbprint -eq $issuingCert.Thumbprint }
    if ($existing) {
        Write-Host "  [INFO] Issuing CA already installed (Thumbprint: $($issuingCert.Thumbprint))" -ForegroundColor Cyan
    } else {
        $caStore.Add($issuingCert)
        Write-Host "  [OK] Issuing CA installed successfully" -ForegroundColor Green
        Write-Host "    Subject: $($issuingCert.Subject)" -ForegroundColor White
        Write-Host "    Issuer: $($issuingCert.Issuer)" -ForegroundColor White
        Write-Host "    Thumbprint: $($issuingCert.Thumbprint)" -ForegroundColor White
        Write-Host "    Valid: $($issuingCert.NotBefore) to $($issuingCert.NotAfter)" -ForegroundColor White
    }
    
    $caStore.Close()
} catch {
    Write-Host "  [ERROR] Failed to install Issuing CA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verify installation
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow

$rootInstalled = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $rootCert.Thumbprint }
$issuingInstalled = Get-ChildItem -Path Cert:\LocalMachine\CA | Where-Object { $_.Thumbprint -eq $issuingCert.Thumbprint }

if ($rootInstalled -and $issuingInstalled) {
    Write-Host "  [OK] Both certificates verified in Windows trust store" -ForegroundColor Green
    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host "[SUCCESS] Baker Street Labs CA Installation Complete!" -ForegroundColor Green
    Write-Host "=======================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your browser and Windows applications will now trust:" -ForegroundColor White
    Write-Host "  - rangexdr.bakerstreetlabs.io" -ForegroundColor Cyan
    Write-Host "  - rangeplatform.bakerstreetlabs.io" -ForegroundColor Cyan
    Write-Host "  - rangeagentix.bakerstreetlabs.io" -ForegroundColor Cyan
    Write-Host "  - rangelande.bakerstreetlabs.io" -ForegroundColor Cyan
    Write-Host "  - rangexsiam.bakerstreetlabs.io" -ForegroundColor Cyan
    Write-Host "  - Any other certificates signed by Baker Street Labs Issuing CA" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "  [ERROR] Verification failed - certificates not found in store" -ForegroundColor Red
    exit 1
}

