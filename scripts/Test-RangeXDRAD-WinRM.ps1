#requires -Version 5.1

<#
.SYNOPSIS
    Test WinRM access to RangeXDR AD servers via NAT

.DESCRIPTION
    100% non-interactive script to test WinRM NAT access to AD01 and AD02.
    Loads credentials from .secrets file automatically.

.PARAMETER SecretsPath
    Path to .secrets file (default: parent directory)

.EXAMPLE
    .\Test-RangeXDRAD-WinRM.ps1
#>

param(
    [string]$SecretsPath = "..\.secrets"
)

# Suppress all interactive prompts
$ErrorActionPreference = "Continue"
$ConfirmPreference = "None"

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "RangeXDR AD WinRM NAT Test - Non-Interactive" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

# Load credentials from .secrets
Write-Host "[1/4] Loading credentials from .secrets..." -ForegroundColor Yellow

if (-not (Test-Path $SecretsPath)) {
    Write-Host "[ERROR] .secrets file not found at: $SecretsPath" -ForegroundColor Red
    exit 1
}

$secretsContent = Get-Content $SecretsPath -Raw
$winrmUser = if ($secretsContent -match 'WINRM_USERNAME=(.+)') { $matches[1].Trim() } else { $null }
$winrmPass = if ($secretsContent -match 'WINRM_PASSWORD=(.+)') { $matches[1].Trim() } else { $null }

if (-not $winrmUser -or -not $winrmPass) {
    Write-Host "[ERROR] WINRM_USERNAME or WINRM_PASSWORD not found in .secrets" -ForegroundColor Red
    exit 1
}

Write-Host "  Username: $winrmUser" -ForegroundColor Green
Write-Host "  Password: [LOADED]" -ForegroundColor Green

# Create PSCredential object (non-interactive)
$securePassword = ConvertTo-SecureString -String $winrmPass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($winrmUser, $securePassword)

# Session options for self-signed certs
$sessionOpt = New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck

Write-Host ""
Write-Host "[2/4] Testing WinRM NAT to AD01..." -ForegroundColor Yellow
Write-Host "  Target: 192.168.255.250:59801" -ForegroundColor White
Write-Host "  Expected: RangeXDR AD01 (172.29.4.65)" -ForegroundColor White
Write-Host ""

try {
    $ad01Result = Invoke-Command -ComputerName 192.168.255.250 -Port 59801 -UseSSL `
        -SessionOption $sessionOpt -Credential $credential -ErrorAction Stop -ScriptBlock {
        [PSCustomObject]@{
            Hostname = $env:COMPUTERNAME
            Domain = $env:USERDNSDOMAIN
            IP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '172.29.*' }).IPAddress | Select-Object -First 1
            TimeSource = (w32tm /query /source 2>$null)
            Stratum = ((w32tm /query /status 2>$null) -match 'Stratum:' | Out-String).Trim()
        }
    }
    
    Write-Host "[SUCCESS] Connected to AD01!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Hostname: $($ad01Result.Hostname)" -ForegroundColor Cyan
    Write-Host "  Domain: $($ad01Result.Domain)" -ForegroundColor Cyan
    Write-Host "  IP: $($ad01Result.IP)" -ForegroundColor Cyan
    Write-Host "  Time Source: $($ad01Result.TimeSource)" -ForegroundColor Cyan
    Write-Host "  Stratum: $($ad01Result.Stratum)" -ForegroundColor Cyan
    
} catch {
    Write-Host "[FAILED] Could not connect to AD01" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[3/4] Testing WinRM NAT to AD02..." -ForegroundColor Yellow
Write-Host "  Target: 192.168.255.250:59802" -ForegroundColor White
Write-Host "  Expected: RangeXDR AD02 (172.29.4.66)" -ForegroundColor White
Write-Host ""

try {
    $ad02Result = Invoke-Command -ComputerName 192.168.255.250 -Port 59802 -UseSSL `
        -SessionOption $sessionOpt -Credential $credential -ErrorAction Stop -ScriptBlock {
        $env:COMPUTERNAME
    }
    
    Write-Host "[SUCCESS] Connected to AD02: $ad02Result" -ForegroundColor Green
    
} catch {
    Write-Host "[EXPECTED FAILURE] AD02 not accessible" -ForegroundColor Yellow
    Write-Host "  Reason: NAT rule may not be configured" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[4/4] Getting DNS Forwarder Configuration from AD01..." -ForegroundColor Yellow

try {
    $forwarders = Invoke-Command -ComputerName 192.168.255.250 -Port 59801 -UseSSL `
        -SessionOption $sessionOpt -Credential $credential -ErrorAction Stop -ScriptBlock {
        Get-DnsServerForwarder | Select-Object IPAddress, EnableReordering
    }
    
    Write-Host "[OK] DNS Forwarders:" -ForegroundColor Green
    $forwarders | Format-Table -AutoSize
    
} catch {
    Write-Host "[FAILED] Could not get DNS forwarders: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "Test Complete - No credential prompts should have appeared" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""




