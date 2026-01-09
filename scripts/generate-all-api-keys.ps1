#!/usr/bin/env pwsh
#
# Generate API Keys for All Range Firewalls
# Stores them in .secrets file for later use
#

$ErrorActionPreference = "Stop"

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "Generating API Keys for All Range Firewalls" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

$username = "bakerstreet"
$password = "H4@sxXtauczXhZxWYETQ"

$firewalls = @(
    @{name="rangeplatform"; fqdn="rangeplatform.bakerstreetlabs.io"; ip="192.168.0.62"},
    @{name="rangeagentix"; fqdn="rangeagentix.bakerstreetlabs.io"; ip="192.168.0.64"},
    @{name="rangelande"; fqdn="rangelande.bakerstreetlabs.io"; ip="192.168.0.67"},
    @{name="rangexsiam"; fqdn="rangexsiam.bakerstreetlabs.io"; ip="192.168.0.62"}
)

foreach ($fw in $firewalls) {
    Write-Host "[$($fw.name)] Generating API key..." -ForegroundColor Yellow
    
    try {
        # Try with FQDN first
        $url = "https://$($fw.fqdn)/api/?type=keygen&user=$username&password=$([uri]::EscapeDataString($password))"
        $response = Invoke-RestMethod -Uri $url -Method Post -SkipCertificateCheck -TimeoutSec 10
        
        $apiKey = ([xml]$response).response.result.key
        
        if ($apiKey) {
            Write-Host "  [OK] API Key generated for $($fw.fqdn)" -ForegroundColor Green
            Write-Host "  Key: $apiKey" -ForegroundColor Cyan
            
            # Append to .secrets file
            Add-Content -Path "..\.secrets" -Value ""
            Add-Content -Path "..\.secrets" -Value "# $($fw.name) Firewall ($($fw.fqdn))"
            Add-Content -Path "..\.secrets" -Value "$($fw.name.ToUpper())_API_KEY=$apiKey"
        } else {
            Write-Host "  [ERROR] Failed to extract API key from response" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "  [ERROR] Failed with FQDN: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  [INFO] Trying with IP address..." -ForegroundColor Yellow
        
        try {
            $url = "https://$($fw.ip)/api/?type=keygen&user=$username&password=$([uri]::EscapeDataString($password))"
            $response = Invoke-RestMethod -Uri $url -Method Post -SkipCertificateCheck -TimeoutSec 10
            
            $apiKey = ([xml]$response).response.result.key
            
            if ($apiKey) {
                Write-Host "  [OK] API Key generated for $($fw.ip)" -ForegroundColor Green
                Write-Host "  Key: $apiKey" -ForegroundColor Cyan
                
                # Append to .secrets file
                Add-Content -Path "..\.secrets" -Value ""
                Add-Content -Path "..\.secrets" -Value "# $($fw.name) Firewall ($($fw.ip))"
                Add-Content -Path "..\.secrets" -Value "$($fw.name.ToUpper())_API_KEY=$apiKey"
            } else {
                Write-Host "  [ERROR] Failed to extract API key from IP response" -ForegroundColor Red
            }
            
        } catch {
            Write-Host "  [ERROR] Failed with IP too: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "  [WARNING] $($fw.name) may be powered off or unreachable" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
}

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "[OK] API Key Generation Complete!" -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API keys have been saved to ..\.secrets"
Write-Host "Review the file to see which firewalls were successful."
Write-Host ""

