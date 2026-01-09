# Agentic WinRM Testing - All Cyber Ranges
# Loads credentials from .secrets automatically
# Tests all Range XDR, XSIAM, and Agentix systems via NAT

param(
    [switch]$UpdateIPAM = $true
)

# Load credentials from .secrets (non-interactive)
$secretsPath = "E:\projects\.secrets"
$secretsContent = Get-Content $secretsPath -Raw

$winrmUser = if ($secretsContent -match 'WINRM_USERNAME=(.+)') { $matches[1].Trim() } else { $null }
$winrmPass = if ($secretsContent -match 'WINRM_PASSWORD=(.+)') { $matches[1].Trim() } else { $null }

if (!$winrmUser -or !$winrmPass) {
    Write-Host "ERROR: Could not load WinRM credentials from .secrets" -ForegroundColor Red
    exit 1
}

# Convert to SecureString and create PSCredential
$securePass = ConvertTo-SecureString -String $winrmPass -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential($winrmUser, $securePass)

Write-Host "=== Baker Street Labs Cyber Range WinRM Testing ===" -ForegroundColor Cyan
Write-Host "Credentials: $winrmUser (from .secrets)" -ForegroundColor Green
Write-Host ""

# Define all systems with NAT mappings
$rangeSystems = @{
    "Range XDR" = @{
        NAT_IP = "192.168.255.250"
        Systems = @(
            @{Name="AD01"; Port=59801; Internal="172.29.4.65"}
            @{Name="AD02"; Port=59802; Internal="172.29.4.66"}
            @{Name="WinSrv"; Port=59803; Internal="172.29.3.65"}
            @{Name="Sherlock"; Port=59805; Internal="172.29.2.45"}
            @{Name="Watson"; Port=59806; Internal="172.29.2.46"}
            @{Name="Irene"; Port=59807; Internal="172.29.2.47"}
            @{Name="Lestrade"; Port=59808; Internal="172.29.2.48"}
        )
    }
    "Range XSIAM" = @{
        NAT_IP = "192.168.255.251"
        Systems = @(
            @{Name="AD01"; Port=59801; Internal="172.30.4.65"}
            @{Name="AD02"; Port=59802; Internal="172.30.4.66"}
            @{Name="WinSrv"; Port=59803; Internal="172.30.3.65"}
            @{Name="Sherlock"; Port=59805; Internal="172.30.2.45"}
            @{Name="Watson"; Port=59806; Internal="172.30.2.46"}
            @{Name="Irene"; Port=59807; Internal="172.30.2.47"}
            @{Name="Lestrade"; Port=59808; Internal="172.30.2.48"}
        )
    }
    "Range Agentix" = @{
        NAT_IP = "192.168.255.252"
        Systems = @(
            @{Name="AD01"; Port=59801; Internal="172.23.4.65"}
            @{Name="AD02"; Port=59802; Internal="172.23.4.66"}
            @{Name="WinSrv"; Port=59803; Internal="172.23.3.65"}
            @{Name="Sherlock"; Port=59805; Internal="172.23.2.45"}
            @{Name="Watson"; Port=59806; Internal="172.23.2.46"}
            @{Name="Irene"; Port=59807; Internal="172.23.2.47"}
            @{Name="Lestrade"; Port=59808; Internal="172.23.2.48"}
        )
    }
}

# Results tracking
$results = @()
$successCount = 0
$failCount = 0

# Test each system
foreach ($rangeName in $rangeSystems.Keys) {
    $range = $rangeSystems[$rangeName]
    $natIP = $range.NAT_IP
    
    Write-Host "`n[$rangeName - NAT IP: $natIP]" -ForegroundColor Yellow
    Write-Host ("-" * 70) -ForegroundColor DarkGray
    
    foreach ($system in $range.Systems) {
        $target = "$natIP`:$($system.Port)"
        $systemName = "$rangeName $($system.Name)"
        
        Write-Host "Testing: $systemName" -ForegroundColor White -NoNewline
        Write-Host " -> $target" -ForegroundColor DarkGray -NoNewline
        
        try {
            # Test with authentication options
            $testResult = Test-WSMan -ComputerName $natIP -Port $system.Port -Credential $cred -Authentication Negotiate -ErrorAction Stop 2>&1
            
            if ($testResult) {
                Write-Host " [OK]" -ForegroundColor Green
                $successCount++
                $results += [PSCustomObject]@{
                    Range = $rangeName
                    System = $system.Name
                    NAT_IP = $natIP
                    NAT_Port = $system.Port
                    Internal_IP = $system.Internal
                    Status = "SUCCESS"
                    Error = $null
                }
            }
        }
        catch {
            # If negotiate fails, try basic connectivity test
            try {
                $tcpTest = Test-NetConnection -ComputerName $natIP -Port $system.Port -WarningAction SilentlyContinue
                if ($tcpTest.TcpTestSucceeded) {
                    Write-Host " [PORT OPEN]" -ForegroundColor Yellow
                    $results += [PSCustomObject]@{
                        Range = $rangeName
                        System = $system.Name
                        NAT_IP = $natIP
                        NAT_Port = $system.Port
                        Internal_IP = $system.Internal
                        Status = "PORT_OPEN"
                        Error = "WinRM authentication failed but port is accessible"
                    }
                } else {
                    Write-Host " [FAIL]" -ForegroundColor Red
                    $failCount++
                    $results += [PSCustomObject]@{
                        Range = $rangeName
                        System = $system.Name
                        NAT_IP = $natIP
                        NAT_Port = $system.Port
                        Internal_IP = $system.Internal
                        Status = "FAILED"
                        Error = "Port not accessible: $($_.Exception.Message)"
                    }
                }
            }
            catch {
                Write-Host " [FAIL]" -ForegroundColor Red
                $failCount++
                $results += [PSCustomObject]@{
                    Range = $rangeName
                    System = $system.Name
                    NAT_IP = $natIP
                    NAT_Port = $system.Port
                    Internal_IP = $system.Internal
                    Status = "FAILED"
                    Error = $_.Exception.Message
                }
            }
        }
    }
}

# Summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "Total Tests: $($successCount + $failCount)" -ForegroundColor White
Write-Host "Success: $successCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor Red

# Save results
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$resultsFile = "E:\projects\baker-street-labs\range-prep-tool\winrm-test-results-$timestamp.csv"
$results | Export-Csv -Path $resultsFile -NoTypeInformation
Write-Host "`nResults saved: $resultsFile" -ForegroundColor Cyan

# Display failures if any
if ($failCount -gt 0) {
    Write-Host "`n=== Failures ===" -ForegroundColor Red
    $results | Where-Object {$_.Status -eq "FAILED"} | ForEach-Object {
        Write-Host "$($_.Range) $($_.System) ($($_.NAT_IP):$($_.NAT_Port))" -ForegroundColor Yellow
        Write-Host "  Error: $($_.Error)" -ForegroundColor DarkGray
    }
}

# Update IPAM if requested
if ($UpdateIPAM) {
    Write-Host "`n=== Updating IPAM Documentation ===" -ForegroundColor Cyan
    
    # Generate IPAM section
    $ipamContent = @"

## 🔐 WinRM NAT Port Mappings

**Last Updated**: $(Get-Date -Format "MMMM dd, yyyy")
**Tested By**: Agentic WinRM Testing Script  
**Credential**: $winrmUser (from .secrets)

### Range XDR - NAT IP: 192.168.255.250

| System | NAT Port | Internal IP | FQDN | WinRM Access | Status |
|--------|----------|-------------|------|--------------|--------|
$(($rangeSystems["Range XDR"].Systems | ForEach-Object {
    $status = ($results | Where-Object {$_.Range -eq "Range XDR" -and $_.System -eq $_.Name} | Select-Object -First 1).Status
    $icon = if ($status -eq "SUCCESS") {"✅"} else {"❌"}
    "| Range XDR $($_.Name) | $($_.Port) | $($_.Internal) | rangexdr$($_.Name.ToLower()).ad.bakerstreetlabs.io | ``: 192.168.255.250:$($_.Port)`` | $icon $status |"
}) -join "`n")

### Range XSIAM - NAT IP: 192.168.255.251

| System | NAT Port | Internal IP | FQDN | WinRM Access | Status |
|--------|----------|-------------|------|--------------|--------|
$(($rangeSystems["Range XSIAM"].Systems | ForEach-Object {
    $status = ($results | Where-Object {$_.Range -eq "Range XSIAM" -and $_.System -eq $_.Name} | Select-Object -First 1).Status
    $icon = if ($status -eq "SUCCESS") {"✅"} else {"❌"}
    "| Range XSIAM $($_.Name) | $($_.Port) | $($_.Internal) | rangexsiam$($_.Name.ToLower()).ad.bakerstreetlabs.io | ``: 192.168.255.251:$($_.Port)`` | $icon $status |"
}) -join "`n")

### Range Agentix - NAT IP: 192.168.255.252

| System | NAT Port | Internal IP | FQDN | WinRM Access | Status |
|--------|----------|-------------|------|--------------|--------|
$(($rangeSystems["Range Agentix"].Systems | ForEach-Object {
    $status = ($results | Where-Object {$_.Range -eq "Range Agentix" -and $_.System -eq $_.Name} | Select-Object -First 1).Status
    $icon = if ($status -eq "SUCCESS") {"✅"} else {"❌"}
    "| Range Agentix $($_.Name) | $($_.Port) | $($_.Internal) | rangeagentix$($_.Name.ToLower()).ad.bakerstreetlabs.io | ``: 192.168.255.252:$($_.Port)`` | $icon $status |"
}) -join "`n")

### WinRM Connection Examples

**PowerShell:**
````powershell
# Load credentials from .secrets
`$secretsPath = "E:\projects\.secrets"
`$secretsContent = Get-Content `$secretsPath -Raw
`$winrmUser = if (`$secretsContent -match 'WINRM_USERNAME=(.+)') { `$matches[1].Trim() } else { `$null }
`$winrmPass = if (`$secretsContent -match 'WINRM_PASSWORD=(.+)') { `$matches[1].Trim() } else { `$null }
`$securePass = ConvertTo-SecureString -String `$winrmPass -AsPlainText -Force
`$cred = New-Object System.Management.Automation.PSCredential(`$winrmUser, `$securePass)

# Connect to Range XDR AD01
`$session = New-PSSession -ComputerName 192.168.255.250 -Port 59801 -Credential `$cred
Invoke-Command -Session `$session -ScriptBlock { hostname }
````

### Port Mapping Pattern

All ranges follow this pattern:
- **59801**: AD01 (Primary Domain Controller)
- **59802**: AD02 (Secondary Domain Controller)
- **59803**: Windows Services Server
- **59805**: Client Sherlock
- **59806**: Client Watson
- **59807**: Client Irene
- **59808**: Client Lestrade

---

"@

    # Save IPAM update
    $ipamUpdateFile = "E:\projects\baker-street-labs\range-prep-tool\WINRM_NAT_IPAM_UPDATE.md"
    $ipamContent | Out-File -FilePath $ipamUpdateFile -Encoding UTF8
    Write-Host "IPAM update saved: $ipamUpdateFile" -ForegroundColor Green
    Write-Host "Review and append to IPAM_MASTER_INVENTORY.md" -ForegroundColor Yellow
}

Write-Host "`n=== Testing Complete ===" -ForegroundColor Cyan
Write-Host "Run with -UpdateIPAM:`$false to skip IPAM generation" -ForegroundColor DarkGray

