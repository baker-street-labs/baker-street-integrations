#!/usr/bin/env pwsh
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

<#
.SYNOPSIS
    Generate API keys for PAN-OS firewalls
.DESCRIPTION
    Generates API keys for Baker Street Labs PAN-OS firewalls using provided credentials
#>

Write-Host "[KEYGEN] Generating API keys for PAN-OS firewalls" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Bypass SSL certificate validation
add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@

[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

# Credentials
$username = "bakerstreet"
$password = "H4@sxXtauczXhZxWYETQ"

# Firewalls
$firewalls = @(
    @{ IP = "192.168.0.7"; Name = "rangengfw" },
    @{ IP = "192.168.0.52"; Name = "xdrngfw" }
)

$results = @{}

foreach ($fw in $firewalls) {
    Write-Host "Firewall: $($fw.Name) ($($fw.IP))" -ForegroundColor Yellow
    
    $url = "https://$($fw.IP)/api/?type=keygen&user=$username&password=$password"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -ErrorAction Stop
        
        if ($response.response.status -eq 'success') {
            $apiKey = $response.response.result.key
            Write-Host "  âœ… API Key generated successfully" -ForegroundColor Green
            Write-Host "     Key: $apiKey" -ForegroundColor Gray
            $results[$fw.IP] = $apiKey
        } else {
            Write-Host "  âŒ Failed: $($response.response.msg)" -ForegroundColor Red
            $results[$fw.IP] = $null
        }
    }
    catch {
        Write-Host "  âŒ Connection failed: $_" -ForegroundColor Red
        $results[$fw.IP] = $null
    }
    
    Write-Host ""
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "[SUMMARY]" -ForegroundColor Cyan
Write-Host ""
Write-Host "192.168.0.7:  $($results['192.168.0.7'])"
Write-Host "192.168.0.52: $($results['192.168.0.52'])"
Write-Host ""

# Return for automation
return $results

