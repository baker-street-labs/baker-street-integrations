# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO - 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

# Verify and Publish PKI Certificate Templates
# Baker Street Labs - Template Management Script
# Run this after creating templates via certtmpl.msc

<#
.SYNOPSIS
    Verifies PKI certificate templates and ensures they're published to the CA.

.DESCRIPTION
    This script checks for the presence of custom BSL certificate templates,
    verifies their configuration, and publishes them to the Certificate Authority.
    
.PARAMETER TemplateNames
    Array of template names to verify and publish. Defaults to all BSL templates.

.PARAMETER CreateGroups
    Switch to create required AD security groups for template permissions.

.EXAMPLE
    .\verify_and_publish_templates.ps1
    Verifies all BSL templates

.EXAMPLE
    .\verify_and_publish_templates.ps1 -TemplateNames "BSLMachineAuth","BSLUserAuth"
    Verifies specific templates

.EXAMPLE
    .\verify_and_publish_templates.ps1 -CreateGroups
    Verifies templates and creates AD security groups
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string[]]$TemplateNames = @(
        "BSLMachineAuth",
        "BSLUserAuth",
        "BSLWebServer",
        "BSLK8sSigner",
        "BSLK8sService",
        "BSLLinuxAuth",
        "BSLCodeSigning",
        "BSLVPNAuth",
        "BSLRedTeam",
        "BSLShortLived"
    ),
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateGroups
)

# Requires running on CA server or with remote CA access
$ErrorActionPreference = "Stop"

Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Baker Street Labs - PKI Template Verification" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Check if running on CA server
$caService = Get-Service -Name CertSvc -ErrorAction SilentlyContinue
if (-not $caService) {
    Write-Host "âš ï¸  Warning: Not running on CA server" -ForegroundColor Yellow
    Write-Host "   This script should be run on bakerstreeta.ad.bakerstreetlabs.io" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit 1
    }
}

# Function to check if template exists in AD
function Test-CertificateTemplate {
    param([string]$TemplateName)
    
    try {
        $null = certutil -v -template $TemplateName 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Function to check if template is published to CA
function Test-TemplatePublished {
    param([string]$TemplateName)
    
    $published = certutil -CATemplates 2>&1 | Select-String $TemplateName
    return ($null -ne $published)
}

# Function to publish template to CA
function Publish-CertificateTemplate {
    param([string]$TemplateName)
    
    try {
        certutil -SetCATemplates +$TemplateName | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Check and publish templates
Write-Host "Checking templates..." -ForegroundColor Yellow
Write-Host ""

$results = @()

foreach ($templateName in $TemplateNames) {
    $exists = Test-CertificateTemplate -TemplateName $templateName
    $published = Test-TemplatePublished -TemplateName $templateName
    
    $result = [PSCustomObject]@{
        Template = $templateName
        Exists = $exists
        Published = $published
        Status = ""
    }
    
    if ($exists -and $published) {
        $result.Status = "âœ… Ready"
        Write-Host "âœ… $templateName - Exists and Published" -ForegroundColor Green
    } elseif ($exists -and -not $published) {
        Write-Host "âš ï¸  $templateName - Exists but NOT published, publishing..." -ForegroundColor Yellow
        $publishResult = Publish-CertificateTemplate -TemplateName $templateName
        if ($publishResult) {
            $result.Status = "âœ… Published"
            $result.Published = $true
            Write-Host "   âœ… Successfully published" -ForegroundColor Green
        } else {
            $result.Status = "âŒ Publish Failed"
            Write-Host "   âŒ Failed to publish" -ForegroundColor Red
        }
    } else {
        $result.Status = "âŒ Not Found"
        Write-Host "âŒ $templateName - NOT FOUND (needs to be created)" -ForegroundColor Red
    }
    
    $results += $result
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

$results | Format-Table -AutoSize

$totalTemplates = $results.Count
$existingTemplates = ($results | Where-Object { $_.Exists }).Count
$publishedTemplates = ($results | Where-Object { $_.Published }).Count

Write-Host "Total Templates: $totalTemplates" -ForegroundColor White
Write-Host "Templates Existing: $existingTemplates" -ForegroundColor White
Write-Host "Templates Published: $publishedTemplates" -ForegroundColor White
Write-Host ""

if ($existingTemplates -eq $totalTemplates) {
    Write-Host "âœ… All templates created!" -ForegroundColor Green
} else {
    Write-Host "âš ï¸  Some templates missing. Create them using:" -ForegroundColor Yellow
    Write-Host "   certtmpl.msc on bakerstreeta.ad.bakerstreetlabs.io" -ForegroundColor Yellow
    Write-Host "   See: docs/instructions/pki_template_creation_guide.md" -ForegroundColor Yellow
}

if ($publishedTemplates -eq $totalTemplates) {
    Write-Host "âœ… All templates published to CA!" -ForegroundColor Green
} else {
    Write-Host "âš ï¸  Some templates not published" -ForegroundColor Yellow
}

Write-Host ""

# Create AD Security Groups if requested
if ($CreateGroups) {
    Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
    Write-Host "  Creating AD Security Groups" -ForegroundColor Cyan
    Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
    Write-Host ""
    
    Import-Module ActiveDirectory -ErrorAction Stop
    
    $domainDN = (Get-ADDomain).DistinguishedName
    $groupsOU = "OU=PKI,OU=Groups,$domainDN"
    
    # Create OU if it doesn't exist
    if (-not (Get-ADOrganizationalUnit -Filter "DistinguishedName -eq '$groupsOU'" -ErrorAction SilentlyContinue)) {
        try {
            New-ADOrganizationalUnit -Name "PKI" -Path "OU=Groups,$domainDN" -ErrorAction Stop
            Write-Host "âœ… Created OU: PKI" -ForegroundColor Green
        } catch {
            Write-Host "âš ï¸  Could not create PKI OU: $_" -ForegroundColor Yellow
            $groupsOU = "CN=Users,$domainDN"  # Fallback to Users container
        }
    }
    
    # Define groups
    $groups = @(
        @{ Name = "BSL-WebServer-Admins"; Description = "Can request web server certificates" },
        @{ Name = "BSL-K8S-Admins"; Description = "Can request Kubernetes certificates" },
        @{ Name = "BSL-Linux-Admins"; Description = "Can manage Linux system certificates" },
        @{ Name = "BSL-CodeSigning-Admins"; Description = "Can request code signing certificates" },
        @{ Name = "BSL-VPN-Users"; Description = "Auto-enroll VPN certificates" },
        @{ Name = "BSL-RedTeam"; Description = "Can request red team certificates" },
        @{ Name = "BSL-Training-Admins"; Description = "Can request training certificates" }
    )
    
    foreach ($group in $groups) {
        if (-not (Get-ADGroup -Filter "Name -eq '$($group.Name)'" -ErrorAction SilentlyContinue)) {
            try {
                New-ADGroup -Name $group.Name `
                    -GroupScope Global `
                    -GroupCategory Security `
                    -Path $groupsOU `
                    -Description $group.Description `
                    -ErrorAction Stop
                Write-Host "âœ… Created group: $($group.Name)" -ForegroundColor Green
            } catch {
                Write-Host "âŒ Failed to create group $($group.Name): $_" -ForegroundColor Red
            }
        } else {
            Write-Host "âš ï¸  Group already exists: $($group.Name)" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "âœ… Security groups creation complete" -ForegroundColor Green
}

Write-Host ""
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

if ($existingTemplates -lt $totalTemplates) {
    Write-Host "1. Create missing templates using certtmpl.msc" -ForegroundColor Yellow
    Write-Host "   Guide: docs/instructions/pki_template_creation_guide.md" -ForegroundColor Gray
    Write-Host ""
}

if ($publishedTemplates -eq $totalTemplates) {
    Write-Host "1. Test auto-enrollment:" -ForegroundColor Yellow
    Write-Host "   gpupdate /force && certutil -pulse" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Verify certificates issued:" -ForegroundColor Yellow
    Write-Host "   Get-ChildItem Cert:\LocalMachine\My | Where-Object { `$_.Issuer -like '*Baker Street Labs*' }" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Test manual enrollment:" -ForegroundColor Yellow
    Write-Host "   https://bakerstreeta.ad.bakerstreetlabs.io/certsrv" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" -ForegroundColor Cyan
Write-Host ""

# Return results for pipeline usage
return $results

