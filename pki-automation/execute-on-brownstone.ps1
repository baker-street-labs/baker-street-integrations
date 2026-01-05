# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

# Execute CA Web Enrollment Service Account Creation on brownstone-a
# Target: 192.168.0.65

$ComputerName = "192.168.0.65"
$AdminUser = "bakerstreetlabs\Administrator"
$AdminPassword = ConvertTo-SecureString "BakerStreet2025!" -AsPlainText -Force
$Credential = New-Object System.Management.Automation.PSCredential($AdminUser, $AdminPassword)

Write-Host "Connecting to $ComputerName..." -ForegroundColor Cyan

# Read the script content
$ScriptPath = "c:\Users\Administrator.CORTEX-UTILITY\Documents\projects\baker-street-labs\scripts\pki\create-ca-webenroll-serviceaccount.ps1"
$ScriptContent = Get-Content $ScriptPath -Raw

# Execute on remote server
try {
    Invoke-Command -ComputerName $ComputerName -Credential $Credential -ScriptBlock {
        param($Script)
        Invoke-Expression $Script
    } -ArgumentList $ScriptContent
    
    Write-Host "`nâœ… Script executed successfully on $ComputerName" -ForegroundColor Green
} catch {
    Write-Host "`nâŒ Error executing script: $($_.Exception.Message)" -ForegroundColor Red
}

