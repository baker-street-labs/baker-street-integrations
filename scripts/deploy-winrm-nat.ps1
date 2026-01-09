#requires -Version 5.1

<#
.SYNOPSIS
    Deploy WinRM NAT rules to Range XDR firewall

.DESCRIPTION
    Safely creates WinRM NAT rules following the established RDP pattern.
    Includes validation, dry-run capability, and risk reduction measures.

.PARAMETER ApiKey
    PAN-OS API key for authentication

.PARAMETER Hostname
    Firewall hostname (default: rangexdr.bakerstreetlabs.io)

.PARAMETER DryRun
    Show what would be created without making changes

.PARAMETER SkipCommit
    Create rules but skip commit for manual review

.EXAMPLE
    .\deploy-winrm-nat.ps1 -ApiKey "your-api-key" -DryRun

.EXAMPLE
    .\deploy-winrm-nat.ps1 -ApiKey "your-api-key" -SkipCommit
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [string]$Hostname = "rangexdr.bakerstreetlabs.io",
    
    [switch]$DryRun,
    
    [switch]$SkipCommit
)

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "Range XDR WinRM NAT Rules Deployment" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

# Load API key from .secrets if not provided
if (-not $ApiKey -and (Test-Path "..\.secrets")) {
    $secrets = Get-Content "..\.secrets" | Where-Object { $_ -match "^PANOS_API_KEY=" }
    if ($secrets) {
        $ApiKey = ($secrets -split "=", 2)[1]
        Write-Host "[INFO] Loaded API key from .secrets" -ForegroundColor DarkGray
    }
}

if (-not $ApiKey) {
    Write-Host "[ERROR] No API key provided. Use -ApiKey parameter or add PANOS_API_KEY to .secrets" -ForegroundColor Red
    exit 1
}

# Build Python command
$pythonArgs = @(
    "create-winrm-nat-rules.py"
    "--api-key", $ApiKey
    "--hostname", $Hostname
)

if ($DryRun) {
    $pythonArgs += "--dry-run"
    Write-Host "[INFO] DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

if ($SkipCommit) {
    $pythonArgs += "--skip-commit"
    Write-Host "[INFO] SKIP COMMIT MODE - Rules will be created but not committed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Executing: python $($pythonArgs -join ' ')" -ForegroundColor DarkGray
Write-Host ""

# Execute Python script
try {
    $result = & python @pythonArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "=======================================================================" -ForegroundColor Green
        Write-Host "[SUCCESS] WinRM NAT deployment completed" -ForegroundColor Green
        Write-Host "=======================================================================" -ForegroundColor Green
        
        if (-not $DryRun) {
            Write-Host ""
            Write-Host "Next Steps:" -ForegroundColor Yellow
            Write-Host "1. Test WinRM access to each system:" -ForegroundColor White
            Write-Host "   `$cred = Get-Credential ad\bakerstreet" -ForegroundColor DarkGray
            Write-Host "   Invoke-Command -ComputerName 192.168.255.250 -Port 59801 -Credential `$cred" -ForegroundColor DarkGray
            Write-Host ""
            Write-Host "2. Verify DNS forwarding on AD servers:" -ForegroundColor White
            Write-Host "   Invoke-Command -ComputerName 192.168.255.250 -Port 59801 -Credential `$cred -ScriptBlock { Get-DnsServerForwarder }" -ForegroundColor DarkGray
        }
    } else {
        Write-Host ""
        Write-Host "=======================================================================" -ForegroundColor Red
        Write-Host "[ERROR] WinRM NAT deployment failed (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "=======================================================================" -ForegroundColor Red
    }
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to execute Python script: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
