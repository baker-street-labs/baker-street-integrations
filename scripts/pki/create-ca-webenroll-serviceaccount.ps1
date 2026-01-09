<#
.SYNOPSIS
    Creates CA Web Enrollment Service Account for Baker Street Labs
.DESCRIPTION
    Creates the svc-ca-webenroll service account in Active Directory with proper permissions
    for Certificate Services Web Enrollment.
.NOTES
    Server: brownstone-a.bakerstreetlabs.local (192.168.0.65)
    Domain: bakerstreetlabs.local
    OU: OU=CA-Service,OU=ServiceAccounts
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$DomainName = "bakerstreetlabs.local",
    
    [Parameter(Mandatory=$false)]
    [string]$AccountName = "svc-ca-webenroll",
    
    [Parameter(Mandatory=$false)]
    [string]$DisplayName = "Certificate Authority Web Enrollment Service",
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "Service account for Active Directory Certificate Services Web Enrollment"
)

# Import required modules
Import-Module ActiveDirectory -ErrorAction Stop

# Define variables
$DomainDN = "DC=bakerstreetlabs,DC=local"
$ServiceAccountOU = "OU=CA-Service,OU=ServiceAccounts,$DomainDN"
$UPN = "$AccountName@$DomainName"
$Password = ConvertTo-SecureString "ServiceAccount2025!" -AsPlainText -Force

Write-Host "`n=== Baker Street Labs CA Web Enrollment Service Account Creation ===" -ForegroundColor Cyan
Write-Host "Domain: $DomainName" -ForegroundColor Yellow
Write-Host "Account: $AccountName" -ForegroundColor Yellow
Write-Host "OU: $ServiceAccountOU" -ForegroundColor Yellow

try {
    # Check if OU exists, create if not
    Write-Host "`n📁 Checking Organizational Units..." -ForegroundColor Cyan
    
    $ServiceAccountsOU = "OU=ServiceAccounts,$DomainDN"
    $CAServiceOU = $ServiceAccountOU
    
    # Check/Create ServiceAccounts OU
    if (-not (Get-ADOrganizationalUnit -Filter "DistinguishedName -eq '$ServiceAccountsOU'" -ErrorAction SilentlyContinue)) {
        Write-Host "📋 Creating ServiceAccounts OU..." -ForegroundColor Yellow
        New-ADOrganizationalUnit -Name "ServiceAccounts" -Path $DomainDN -ProtectedFromAccidentalDeletion $true
        Write-Host "✅ ServiceAccounts OU created" -ForegroundColor Green
    } else {
        Write-Host "✅ ServiceAccounts OU exists" -ForegroundColor Green
    }
    
    # Check/Create CA-Service OU
    if (-not (Get-ADOrganizationalUnit -Filter "DistinguishedName -eq '$CAServiceOU'" -ErrorAction SilentlyContinue)) {
        Write-Host "📋 Creating CA-Service OU..." -ForegroundColor Yellow
        New-ADOrganizationalUnit -Name "CA-Service" -Path $ServiceAccountsOU -ProtectedFromAccidentalDeletion $true
        Write-Host "✅ CA-Service OU created" -ForegroundColor Green
    } else {
        Write-Host "✅ CA-Service OU exists" -ForegroundColor Green
    }
    
    # Check if service account already exists
    Write-Host "`n🔍 Checking for existing service account..." -ForegroundColor Cyan
    $ExistingAccount = Get-ADUser -Filter "SamAccountName -eq '$AccountName'" -ErrorAction SilentlyContinue
    
    if ($ExistingAccount) {
        Write-Host "⚠️  Service account '$AccountName' already exists" -ForegroundColor Yellow
        Write-Host "Distinguished Name: $($ExistingAccount.DistinguishedName)" -ForegroundColor Yellow
        Write-Host "Enabled: $($ExistingAccount.Enabled)" -ForegroundColor Yellow
        
        # Update existing account
        Write-Host "`n🔄 Updating existing account..." -ForegroundColor Cyan
        Set-ADUser -Identity $AccountName `
            -DisplayName $DisplayName `
            -Description $Description `
            -PasswordNeverExpires $true `
            -CannotChangePassword $true `
            -Enabled $true
        
        Write-Host "✅ Service account updated" -ForegroundColor Green
    } else {
        # Create new service account
        Write-Host "`n➕ Creating new service account..." -ForegroundColor Cyan
        
        New-ADUser -Name $AccountName `
            -SamAccountName $AccountName `
            -UserPrincipalName $UPN `
            -DisplayName $DisplayName `
            -Description $Description `
            -AccountPassword $Password `
            -Path $ServiceAccountOU `
            -Enabled $true `
            -PasswordNeverExpires $true `
            -CannotChangePassword $true `
            -ErrorAction Stop
        
        Write-Host "✅ Service account created successfully" -ForegroundColor Green
    }
    
    # Check/Create Service-Accounts security group
    Write-Host "`n👥 Configuring Security Groups..." -ForegroundColor Cyan
    
    $ServiceAccountsGroup = "Service-Accounts"
    if (-not (Get-ADGroup -Filter "Name -eq '$ServiceAccountsGroup'" -ErrorAction SilentlyContinue)) {
        Write-Host "📋 Creating $ServiceAccountsGroup group..." -ForegroundColor Yellow
        New-ADGroup -Name $ServiceAccountsGroup `
            -GroupScope Global `
            -GroupCategory Security `
            -Path "OU=Groups,$DomainDN" `
            -Description "Service Accounts group"
        Write-Host "✅ $ServiceAccountsGroup group created" -ForegroundColor Green
    } else {
        Write-Host "✅ $ServiceAccountsGroup group exists" -ForegroundColor Green
    }
    
    # Add to Service-Accounts group
    $GroupMembers = Get-ADGroupMember -Identity $ServiceAccountsGroup -ErrorAction SilentlyContinue | Select-Object -ExpandProperty SamAccountName
    if ($GroupMembers -notcontains $AccountName) {
        Add-ADGroupMember -Identity $ServiceAccountsGroup -Members $AccountName -ErrorAction Stop
        Write-Host "✅ Added $AccountName to $ServiceAccountsGroup" -ForegroundColor Green
    } else {
        Write-Host "✅ $AccountName is already a member of $ServiceAccountsGroup" -ForegroundColor Green
    }
    
    # Check/Create IIS_IUSRS group membership (for web enrollment)
    Write-Host "`n🌐 Configuring Web Enrollment Permissions..." -ForegroundColor Cyan
    
    # Note: IIS_IUSRS is a built-in local group, not AD group
    # We'll need to add this on the server itself
    Write-Host "ℹ️  IIS_IUSRS membership must be configured on the CA server" -ForegroundColor Yellow
    Write-Host "   Run: net localgroup IIS_IUSRS $DomainName\$AccountName /add" -ForegroundColor Yellow
    
    # Verify account creation
    Write-Host "`n✅ Verifying Service Account..." -ForegroundColor Cyan
    $CreatedAccount = Get-ADUser -Identity $AccountName -Properties *
    
    Write-Host "`n=== Service Account Details ===" -ForegroundColor Green
    Write-Host "Name:                  $($CreatedAccount.Name)" -ForegroundColor White
    Write-Host "SamAccountName:        $($CreatedAccount.SamAccountName)" -ForegroundColor White
    Write-Host "UserPrincipalName:     $($CreatedAccount.UserPrincipalName)" -ForegroundColor White
    Write-Host "DisplayName:           $($CreatedAccount.DisplayName)" -ForegroundColor White
    Write-Host "Description:           $($CreatedAccount.Description)" -ForegroundColor White
    Write-Host "DistinguishedName:     $($CreatedAccount.DistinguishedName)" -ForegroundColor White
    Write-Host "Enabled:               $($CreatedAccount.Enabled)" -ForegroundColor White
    Write-Host "PasswordNeverExpires:  $($CreatedAccount.PasswordNeverExpires)" -ForegroundColor White
    Write-Host "Created:               $($CreatedAccount.Created)" -ForegroundColor White
    
    # Get group memberships
    $Groups = Get-ADPrincipalGroupMembership -Identity $AccountName | Select-Object -ExpandProperty Name
    Write-Host "Group Memberships:     $($Groups -join ', ')" -ForegroundColor White
    
    # Additional configuration instructions
    Write-Host "`n=== Post-Creation Steps ===" -ForegroundColor Cyan
    Write-Host "1. Add to IIS_IUSRS on CA server:" -ForegroundColor Yellow
    Write-Host "   net localgroup IIS_IUSRS $DomainName\$AccountName /add" -ForegroundColor White
    Write-Host "`n2. Grant Certificate Request permissions:" -ForegroundColor Yellow
    Write-Host "   Configure in Certificate Templates (certtmpl.msc)" -ForegroundColor White
    Write-Host "`n3. Configure Web Enrollment to use this account:" -ForegroundColor Yellow
    Write-Host "   IIS Manager > CertSrv > Application Pool > Identity" -ForegroundColor White
    Write-Host "`n4. Test account authentication:" -ForegroundColor Yellow
    Write-Host "   runas /user:$DomainName\$AccountName cmd" -ForegroundColor White
    
    Write-Host "`n=== Service Account Password ===" -ForegroundColor Cyan
    Write-Host "Password: ServiceAccount2025!" -ForegroundColor Yellow
    Write-Host "⚠️  Store securely and change after initial configuration" -ForegroundColor Yellow
    
    Write-Host "`n✅ Service Account Creation Complete!" -ForegroundColor Green
    
} catch {
    Write-Host "`n❌ Error creating service account: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack Trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}

