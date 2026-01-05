# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

# Create All BSL Certificate Templates
# Baker Street Labs - Automated Template Creation
# Run this on bakerstreeta.ad.bakerstreetlabs.io or via WinRM

<#
.SYNOPSIS
    Creates all Baker Street Labs custom certificate templates programmatically.

.DESCRIPTION
    This script creates 10 custom certificate templates in Active Directory
    for the Baker Street Labs PKI infrastructure. Templates are created by
    duplicating base templates and modifying attributes programmatically.

.EXAMPLE
    .\create_all_templates.ps1
    Creates all BSL templates

.EXAMPLE
    Invoke-Command -ComputerName bakerstreeta.ad.bakerstreetlabs.io -FilePath .\create_all_templates.ps1
    Creates templates via WinRM
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Baker Street Labs - Certificate Template Creation" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Import Active Directory module
try {
    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Host "âœ… Active Directory module loaded" -ForegroundColor Green
} catch {
    Write-Host "âŒ Failed to load Active Directory module: $_" -ForegroundColor Red
    exit 1
}

# Get configuration context
$configNC = (Get-ADRootDSE).configurationNamingContext
$templatesDN = "CN=Certificate Templates,CN=Public Key Services,CN=Services,$configNC"
$domainSID = (Get-ADDomain).DomainSID

Write-Host "Configuration Context: $configNC" -ForegroundColor Gray
Write-Host "Templates DN: $templatesDN" -ForegroundColor Gray
Write-Host ""

# Helper function to create OID
function New-TemplateOID {
    return "1.3.6.1.4.1.311.21.8." + (Get-Random -Minimum 10000000 -Maximum 99999999) + "." + (Get-Random -Minimum 1000000 -Maximum 9999999)
}

# Helper function to set template permissions
function Set-TemplatePermissions {
    param(
        [string]$TemplateDN,
        [string[]]$Groups
    )
    
    $acl = Get-Acl -Path "AD:$TemplateDN"
    
    foreach ($groupName in $Groups) {
        try {
            if ($groupName -eq "Domain Computers") {
                $sid = New-Object System.Security.Principal.SecurityIdentifier("$domainSID-515")
            } elseif ($groupName -eq "Domain Users") {
                $sid = New-Object System.Security.Principal.SecurityIdentifier("$domainSID-513")
            } elseif ($groupName -eq "Domain Controllers") {
                $sid = New-Object System.Security.Principal.SecurityIdentifier("$domainSID-516")
            } else {
                $group = Get-ADGroup -Filter "Name -eq '$groupName'" -ErrorAction SilentlyContinue
                if ($group) {
                    $sid = New-Object System.Security.Principal.SecurityIdentifier($group.SID)
                } else {
                    Write-Host "   âš ï¸  Group $groupName not found, skipping..." -ForegroundColor Yellow
                    continue
                }
            }
            
            # Grant Read, Enroll, Autoenroll
            $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
                $sid,
                'ReadProperty,WriteProperty,ExtendedRight',
                'Allow',
                [guid]'00000000-0000-0000-0000-000000000000'
            )
            $acl.AddAccessRule($ace)
        } catch {
            Write-Host "   âš ï¸  Failed to set permissions for $groupName : $_" -ForegroundColor Yellow
        }
    }
    
    Set-Acl -Path "AD:$TemplateDN" -AclObject $acl
}

# Template creation counters
$created = 0
$skipped = 0
$failed = 0

Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Phase 1: Essential Templates" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Template 1: BSLMachineAuth
Write-Host "[1/10] Creating BSLMachineAuth..." -ForegroundColor Yellow
$templateName = "BSLMachineAuth"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Machine Authentication"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131680  # Auto-enrollment enabled
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,64,57,135,46,225,254,255)  # 2 years
            'pKIOverlapPeriod' = [byte[]](0,128,166,10,255,222,255,255)  # 6 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider','2,Microsoft DH SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 41  # Auto-enrollment
            'msPKI-Private-Key-Flag' = 16842752  # Exportable = No
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.2','1.3.6.1.5.5.7.3.1')  # Client + Server Auth
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Set-TemplatePermissions -TemplateDN $templateDN -Groups @("Domain Computers", "Domain Controllers")
        Write-Host "   âœ… Created BSLMachineAuth" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 2: BSLUserAuth
Write-Host "[2/10] Creating BSLUserAuth..." -ForegroundColor Yellow
$templateName = "BSLUserAuth"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs User Authentication"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131680  # Auto-enrollment enabled
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,128,114,111,213,233,255,255)  # 1 year
            'pKIOverlapPeriod' = [byte[]](0,128,166,10,255,222,255,255)  # 6 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 41  # Auto-enrollment
            'msPKI-Private-Key-Flag' = 16842768  # Exportable = Yes, Archival = Yes
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.2','1.3.6.1.5.5.7.3.4')  # Client Auth + Secure Email
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Set-TemplatePermissions -TemplateDN $templateDN -Groups @("Domain Users")
        Write-Host "   âœ… Created BSLUserAuth" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 3: BSLWebServer
Write-Host "[3/10] Creating BSLWebServer..." -ForegroundColor Yellow
$templateName = "BSLWebServer"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Web Server"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584  # No auto-enrollment
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,128,114,111,213,233,255,255)  # 1 year
            'pKIOverlapPeriod' = [byte[]](0,128,166,10,255,222,255,255)  # 6 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0  # Manual enrollment
            'msPKI-Private-Key-Flag' = 16842768  # Exportable = Yes
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.1')  # Server Auth only
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Set-TemplatePermissions -TemplateDN $templateDN -Groups @("Domain Computers")
        Write-Host "   âœ… Created BSLWebServer" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Phase 2: Infrastructure Templates" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Template 4: BSLK8sSigner
Write-Host "[4/10] Creating BSLK8sSigner..." -ForegroundColor Yellow
$templateName = "BSLK8sSigner"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Kubernetes Signer"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584  # No auto-enrollment
            'revision' = 100
            'pKIDefaultKeySpec' = 2  # Key exchange
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,192,171,182,130,185,250,255)  # 5 years
            'pKIOverlapPeriod' = [byte[]](0,64,57,135,46,225,254,255)  # 26 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842752  # Not exportable (CA key)
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 4096
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLK8sSigner (note: set as CA template in GUI if needed)" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 5: BSLK8sService
Write-Host "[5/10] Creating BSLK8sService..." -ForegroundColor Yellow
$templateName = "BSLK8sService"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Kubernetes Service"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,192,254,255,163,246,255,255)  # 90 days
            'pKIOverlapPeriod' = [byte[]](0,128,28,6,126,251,255,255)  # 2 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842752
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.1','1.3.6.1.5.5.7.3.2')
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLK8sService" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 6: BSLLinuxAuth
Write-Host "[6/10] Creating BSLLinuxAuth..." -ForegroundColor Yellow
$templateName = "BSLLinuxAuth"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Linux Authentication"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131680
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,64,57,135,46,225,254,255)  # 2 years
            'pKIOverlapPeriod' = [byte[]](0,128,166,10,255,222,255,255)
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 41
            'msPKI-Private-Key-Flag' = 16842752
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.2','1.3.6.1.5.5.7.3.1')
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Set-TemplatePermissions -TemplateDN $templateDN -Groups @("Domain Computers")
        Write-Host "   âœ… Created BSLLinuxAuth" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Phase 3: Specialized Templates" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Template 7: BSLCodeSigning
Write-Host "[7/10] Creating BSLCodeSigning..." -ForegroundColor Yellow
$templateName = "BSLCodeSigning"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Code Signing"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584
            'revision' = 100
            'pKIDefaultKeySpec' = 2
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,128,214,58,124,219,253,255)  # 3 years
            'pKIOverlapPeriod' = [byte[]](0,64,57,135,46,225,254,255)
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842768  # Exportable
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 3072
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.3')  # Code Signing
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLCodeSigning" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 8: BSLVPNAuth
Write-Host "[8/10] Creating BSLVPNAuth..." -ForegroundColor Yellow
$templateName = "BSLVPNAuth"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs VPN Authentication"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131680
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,128,114,111,213,233,255,255)  # 1 year
            'pKIOverlapPeriod' = [byte[]](0,128,166,10,255,222,255,255)
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 41
            'msPKI-Private-Key-Flag' = 16842752
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.2','1.3.6.1.5.5.8.2.2')  # Client Auth + IPSec IKE
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLVPNAuth" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 9: BSLRedTeam
Write-Host "[9/10] Creating BSLRedTeam..." -ForegroundColor Yellow
$templateName = "BSLRedTeam"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Red Team Certificate"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,64,89,55,234,236,255,255)  # 6 months
            'pKIOverlapPeriod' = [byte[]](0,192,171,182,130,251,255,255)  # 4 weeks
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842768  # Exportable
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.1','1.3.6.1.5.5.7.3.2')
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLRedTeam" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

# Template 10: BSLShortLived
Write-Host "[10/10] Creating BSLShortLived..." -ForegroundColor Yellow
$templateName = "BSLShortLived"
$templateDN = "CN=$templateName,$templatesDN"

if (Get-ADObject -Filter "cn -eq '$templateName'" -SearchBase $templatesDN -ErrorAction SilentlyContinue) {
    Write-Host "   âš ï¸  Template already exists, skipping" -ForegroundColor Yellow
    $skipped++
} else {
    try {
        $attributes = @{
            'cn' = $templateName
            'displayName' = "Baker Street Labs Short-Lived Certificate"
            'objectClass' = 'pKICertificateTemplate'
            'flags' = 131584
            'revision' = 100
            'pKIDefaultKeySpec' = 1
            'pKIMaxIssuingDepth' = 0
            'pKIExpirationPeriod' = [byte[]](0,128,198,117,123,254,255,255)  # 7 days
            'pKIOverlapPeriod' = [byte[]](0,0,228,11,253,255,255,255)  # 1 day
            'pKIDefaultCSPs' = @('1,Microsoft RSA SChannel Cryptographic Provider')
            'msPKI-RA-Signature' = 0
            'msPKI-Enrollment-Flag' = 0
            'msPKI-Private-Key-Flag' = 16842752
            'msPKI-Certificate-Name-Flag' = 1
            'msPKI-Minimal-Key-Size' = 2048
            'msPKI-Template-Schema-Version' = 4
            'msPKI-Template-Minor-Revision' = 0
            'msPKI-Cert-Template-OID' = New-TemplateOID
            'msPKI-Certificate-Application-Policy' = @('1.3.6.1.5.5.7.3.1','1.3.6.1.5.5.7.3.2')
        }
        
        New-ADObject -Name $templateName -Type pKICertificateTemplate -Path $templatesDN -OtherAttributes $attributes -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Host "   âœ… Created BSLShortLived" -ForegroundColor Green
        $created++
    } catch {
        Write-Host "   âŒ Failed: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""
Write-Host "Templates Created: $created" -ForegroundColor Green
Write-Host "Templates Skipped: $skipped" -ForegroundColor Yellow
Write-Host "Templates Failed: $failed" -ForegroundColor Red
Write-Host ""

if ($created -gt 0) {
    Write-Host "âœ… Template creation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Publish templates to CA: .\verify_and_publish_templates.ps1" -ForegroundColor Gray
    Write-Host "2. Test auto-enrollment: gpupdate /force && certutil -pulse" -ForegroundColor Gray
    Write-Host "3. Verify certificates issued" -ForegroundColor Gray
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan






