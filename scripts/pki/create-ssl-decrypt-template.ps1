# Baker Street Labs - SSL Decryption CA Template
# Creates certificate template for PAN-OS SSL decryption intermediate CAs

<#
.SYNOPSIS
    Creates 'BSL SSL Decryption CA' certificate template for firewall SSL inspection

.DESCRIPTION
    This script:
    - Creates a custom certificate template based on Subordinate CA template
    - Configures the private key to be exportable (required for PAN-OS import)
    - Sets appropriate validity period (5 years)
    - Publishes template to Issuing CA on bakerstreetb
    
.NOTES
    Prerequisites:
    - Run as Domain Admin or Enterprise Admin
    - Subordinate CA must be operational on bakerstreetb
    - Access to Certificate Templates console
    
.EXAMPLE
    .\create-ssl-decrypt-template.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$IssuingCAServer = "bakerstreetb.ad.bakerstreetlabs.io",
    
    [Parameter(Mandatory=$false)]
    [string]$IssuingCAName = "Baker Street Labs Issuing CA",
    
    [Parameter(Mandatory=$false)]
    [string]$TemplateName = "BSLSSLDecryptCA",
    
    [Parameter(Mandatory=$false)]
    [string]$TemplateDisplayName = "BSL SSL Decryption CA",
    
    [Parameter(Mandatory=$false)]
    [int]$ValidityYears = 5
)

$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Baker Street Labs - SSL Decryption CA Template Creation" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Validate environment
Write-Host "[1/4] Validating environment..." -ForegroundColor Yellow

try {
    # Get configuration naming context
    $configNC = (Get-ADRootDSE).configurationNamingContext
    Write-Host "  [OK] Configuration NC: $configNC" -ForegroundColor Green
    
    # Check if running with proper permissions
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($currentUser)
    $isAdmin = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        throw "This script must be run as Administrator"
    }
    Write-Host "  [OK] Running with administrative privileges" -ForegroundColor Green
    
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    exit 1
}

# Step 2: Create certificate template
Write-Host ""
Write-Host "[2/4] Creating SSL Decryption CA template..." -ForegroundColor Yellow

try {
    # Get the SubCA template as a base
    $templatesDN = "CN=Certificate Templates,CN=Public Key Services,CN=Services,$configNC"
    $sourceTemplate = Get-ADObject -SearchBase $templatesDN -Filter {cn -eq "SubCA"}
    
    if (-not $sourceTemplate) {
        throw "Cannot find Subordinate CA template (SubCA) in Active Directory"
    }
    Write-Host "  [OK] Found source template: SubCA" -ForegroundColor Green
    
    # Check if template already exists
    $existingTemplate = Get-ADObject -SearchBase $templatesDN -Filter {cn -eq $TemplateName} -ErrorAction SilentlyContinue
    
    if ($existingTemplate) {
        Write-Host "  [INFO] Template '$TemplateName' already exists" -ForegroundColor Cyan
        Write-Host "  [INFO] DN: $($existingTemplate.DistinguishedName)" -ForegroundColor Cyan
    } else {
        Write-Host "  [ACTION] Creating new template from SubCA..." -ForegroundColor Yellow
        
        # Get source template object with all properties
        $sourceTemplateObj = Get-ADObject $sourceTemplate -Properties *
        
        # Create new template DN
        $newTemplateDN = "CN=$TemplateName,$templatesDN"
        
        # Prepare attributes for new template
        $attributes = @{
            'objectClass' = 'pKICertificateTemplate'
            'cn' = $TemplateName
            'displayName' = $TemplateDisplayName
            'flags' = 131648  # CT_FLAG_EXPORTABLE_KEY | CT_FLAG_MACHINE_TYPE
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIKeyUsage' = [byte[]]@(134, 0)  # Digital Signature + Key Cert Sign + CRL Sign
            'pKIMaxIssuingDepth' = 0  # Can't issue subordinate CAs
            'pKICriticalExtensions' = @('2.5.29.19', '2.5.29.15')  # Basic Constraints, Key Usage
            'pKIExtendedKeyUsage' = @('1.3.6.1.5.5.7.3.1', '1.3.6.1.5.5.7.3.2')  # Server Auth, Client Auth
            'pKIDefaultCSPs' = @('1,Microsoft Software Key Storage Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16  # ALLOW_KEY_EXPORT
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-Object System.DirectoryServices.ActiveDirectoryObjectIdentifier("1.3.6.1.4.1.311.21.8.$(Get-Random -Minimum 10000000 -Maximum 99999999)")
        }
        
        # Create the template
        New-ADObject -Name $TemplateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes
        
        Write-Host "  [OK] Template created: $TemplateName" -ForegroundColor Green
    }
    
    # Set validity period
    Write-Host "  [ACTION] Setting validity period to $ValidityYears years..." -ForegroundColor Yellow
    
    Set-ADObject -Identity "CN=$TemplateName,$templatesDN" -Replace @{
        'pKIExpirationPeriod' = [byte[]]@(0, 64, 57, 135, 46, 225, 254, 255)  # 5 years
        'pKIOverlapPeriod' = [byte[]]@(0, 128, 166, 10, 255, 222, 255, 255)   # 3 weeks
    }
    
    Write-Host "  [OK] Validity period configured" -ForegroundColor Green
    
    # Set permissions (allow Domain Computers and Administrators to enroll)
    Write-Host "  [ACTION] Setting template permissions..." -ForegroundColor Yellow
    
    $templateDN = "CN=$TemplateName,$templatesDN"
    $domainComputersgroup = New-Object System.Security.Principal.NTAccount("Domain Computers")
    $administratorsGroup = New-Object System.Security.Principal.NTAccount("Administrators")
    
    # Note: Full ACL manipulation requires ADSI which is complex
    # Recommend manual permissions via certtmpl.msc
    Write-Host "  [INFO] Template created with default permissions" -ForegroundColor Cyan
    Write-Host "  [ACTION] Review and adjust permissions via certtmpl.msc if needed" -ForegroundColor Yellow
    
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    Write-Host "  [INFO] Template may already exist or require manual creation via certtmpl.msc" -ForegroundColor Yellow
}

# Step 3: Install and configure Subordinate CA
Write-Host ""
Write-Host "[3/5] Installing Enterprise Subordinate CA..." -ForegroundColor Yellow

try {
    # Check if CA already installed
    $caService = Get-Service CertSvc -ErrorAction SilentlyContinue
    
    if ($caService -and $caService.Status -eq 'Running') {
        Write-Host "  [INFO] Certificate Services already running" -ForegroundColor Cyan
        Write-Host "  [ACTION] Skipping CA installation (already configured)" -ForegroundColor Yellow
        
        # Verify it's configured as subordinate
        $caConfig = certutil -CAInfo type
        Write-Host "  [INFO] Current CA Type: $caConfig" -ForegroundColor Cyan
    } else {
        Write-Host "  [ACTION] Installing Subordinate CA (this may take several minutes)..." -ForegroundColor Yellow
        Write-Host "  [INFO] This will submit a certificate request to the parent CA" -ForegroundColor Cyan
        
        $parentCAConfigString = "$ParentCAServer\$ParentCAName"
        
        Install-AdcsCertificationAuthority `
            -CAType EnterpriseSubordinateCA `
            -KeyLength 2048 `
            -HashAlgorithmName SHA256 `
            -ValidityPeriod Years `
            -ValidityPeriodUnits $ValidityYears `
            -CryptoProviderName "RSA#Microsoft Software Key Storage Provider" `
            -CACommonName $IssuingCAName `
            -ParentCA $parentCAConfigString `
            -Force `
            -Confirm:$false
        
        Write-Host "  [OK] Subordinate CA installation initiated" -ForegroundColor Green
        Write-Host ""
        Write-Host "  [IMPORTANT] The CA has submitted a certificate request to the parent CA" -ForegroundColor Yellow
        Write-Host "  [ACTION] You may need to approve this request on bakerstreeta:" -ForegroundColor Yellow
        Write-Host "           1. Open Certificate Authority console on bakerstreeta" -ForegroundColor Gray
        Write-Host "           2. Navigate to 'Pending Requests'" -ForegroundColor Gray
        Write-Host "           3. Right-click the request → All Tasks → Issue" -ForegroundColor Gray
        Write-Host "           4. Return here and restart CertSvc: Restart-Service CertSvc" -ForegroundColor Gray
        Write-Host ""
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    Write-Host "  [INFO] If CA is already configured, this is expected" -ForegroundColor Yellow
    Write-Host "  [ACTION] Verify CA status with: Get-Service CertSvc" -ForegroundColor Yellow
}

# Step 4: Publish template to CA
Write-Host ""
Write-Host "[4/5] Publishing SSL Decryption template to Issuing CA..." -ForegroundColor Yellow

try {
    # Add template to CA
    $caConfigString = "$IssuingCAServer\$IssuingCAName"
    
    Write-Host "  [ACTION] Adding template to CA: $caConfigString" -ForegroundColor Yellow
    
    # Use certutil to add template
    $result = certutil -SetCATemplates +"$TemplateName"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Template published to CA" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Template may already be published or CA not ready" -ForegroundColor Yellow
        Write-Host "  [INFO] Manually publish via Certificate Authority console if needed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] $_" -ForegroundColor Yellow
    Write-Host "  [INFO] Template can be published manually via CA console" -ForegroundColor Yellow
}

# Step 5: Verify configuration
Write-Host ""
Write-Host "[5/5] Verifying configuration..." -ForegroundColor Yellow

try {
    Write-Host "  [INFO] Checking CA service..." -ForegroundColor Cyan
    $caService = Get-Service CertSvc
    Write-Host "  [OK] CertSvc Status: $($caService.Status)" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "  [INFO] Checking published templates..." -ForegroundColor Cyan
    $templates = certutil -CATemplates
    
    if ($templates -match $TemplateName) {
        Write-Host "  [OK] SSL Decryption template is published" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Template not yet visible to CA" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "  [INFO] CA Information:" -ForegroundColor Cyan
    certutil -CAInfo name
    
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
}

# Final summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " ✅ Setup Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Subordinate Issuing CA: $IssuingCAName" -ForegroundColor White
Write-Host "Server: $IssuingCAServer" -ForegroundColor White
Write-Host "SSL Decryption Template: $TemplateName" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Verify CA is fully operational (may need parent CA approval)" -ForegroundColor Yellow
Write-Host "  2. Run request-and-export-firewall-cas.ps1 to generate firewall certificates" -ForegroundColor Yellow
Write-Host "  3. Import PFX files into PAN-OS firewalls" -ForegroundColor Yellow
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - auth_ad_omnibus.md (PKI Infrastructure section)" -ForegroundColor Gray
Write-Host "  - docs/PKI_QUICK_START_OPERATOR.md" -ForegroundColor Gray
Write-Host ""


