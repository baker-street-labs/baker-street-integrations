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
    
    Write-Host "`n✅ Script executed successfully on $ComputerName" -ForegroundColor Green
} catch {
    Write-Host "`n❌ Error executing script: $($_.Exception.Message)" -ForegroundColor Red
}

