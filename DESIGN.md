# Baker Street Integrations Design Diagrams

All design maps and diagrams for integration infrastructure, rendered in Mermaid format.

---

## Integration Architecture Overview

```mermaid
graph TB
    subgraph Components["Integration Components"]
        PKI[PKI Automation<br/>Windows AD CS]
        PANOSPKI[PANOS PKI Manager<br/>Firewall Certs]
        PANOSObj[PANOS Object Creator<br/>Config Objects]
        Torq[Torq Integration<br/>Workflows]
        GP[GlobalProtect SAML<br/>VPN Config]
    end
    
    subgraph Infrastructure["Infrastructure"]
        ADCA[Active Directory CA<br/>192.168.0.65]
        PANOSHub[PANOS Hub<br/>192.168.0.7]
        PANOSSpoke[PANOS Spoke<br/>192.168.255.200]
        TorqRunner[Torq Self-Hosted Runners]
    end
    
    subgraph External["External Services"]
        TorqCloud[Torq.io Cloud<br/>Orchestration]
        GitLab[GitLab<br/>CI/CD]
        Slack[Slack<br/>Notifications]
    end
    
    PKI --> ADCA
    PANOSPKI --> ADCA
    PANOSPKI --> PANOSHub
    PANOSPKI --> PANOSSpoke
    PANOSObj --> PANOSHub
    PANOSObj --> PANOSSpoke
    Torq --> TorqCloud
    TorqCloud --> TorqRunner
    TorqRunner --> PANOSHub
    TorqRunner --> ADCA
    GP --> PANOSHub
    Torq --> GitLab
    Torq --> Slack
```

---

## PKI Certificate Lifecycle Flow

```mermaid
sequenceDiagram
    participant Client
    participant Template as Certificate Template
    participant CA as Windows CA
    participant Enrollment as Auto-Enrollment
    participant System as Target System
    
    Client->>Template: Create Template (PowerShell)
    Template->>CA: Publish Template
    CA->>Enrollment: GPO Configuration
    Enrollment->>System: Auto-Enrollment Trigger
    System->>CA: Certificate Request
    CA->>CA: Sign Certificate
    CA->>System: Return Certificate
    System->>System: Install Certificate
    System-->>Client: Enrollment Complete
```

---

## PANOS PKI Manager Workflow

```mermaid
flowchart TD
    Start([Start PANOS PKI Manager]) --> CheckCA{Intermediate CA<br/>Exists?}
    
    CheckCA -->|No| CreateTemplate[Create NGFWIntermediate Template]
    CreateTemplate --> GenerateCSR[Generate Intermediate CA CSR]
    CheckCA -->|Yes| LoadCA[Load Intermediate CA]
    
    GenerateCSR --> SubmitCSR[Submit CSR to Root CA]
    SubmitCSR --> SignCSR[Root CA Signs CSR]
    SignCSR --> StoreCA[Store Intermediate CA]
    LoadCA --> ProcessFW[Process Firewalls]
    StoreCA --> ProcessFW
    
    ProcessFW --> ForEachFW{For Each Firewall}
    ForEachFW --> ConnectFW[Connect to Firewall API]
    ConnectFW --> BackupConfig[Backup Configuration]
    BackupConfig --> ForEachCert{For Each Certificate}
    
    ForEachCert --> CheckCert{Certificate<br/>Exists?}
    CheckCert -->|No| GenerateCSRFW[Generate CSR on Firewall]
    CheckCert -->|Yes| SkipCert[Skip Certificate]
    
    GenerateCSRFW --> RetrieveCSR[Retrieve CSR from Firewall]
    RetrieveCSR --> SubmitCSRCA[Submit CSR to CA via WinRM]
    SubmitCSRCA --> SignCSRCA[CA Signs CSR]
    SignCSRCA --> BuildChain[Build Certificate Chain]
    BuildChain --> ImportCert[Import Certificate to Firewall]
    ImportCert --> CommitFW[Commit Firewall Configuration]
    
    SkipCert --> ForEachCert
    CommitFW --> ForEachCert
    ForEachCert -->|Complete| ForEachFW
    ForEachFW -->|Complete| Complete([Complete])
```

---

## PANOS Object Creator Workflow

```mermaid
sequenceDiagram
    participant User
    participant Script as Object Creator Script
    participant SDK as pan-os-python SDK
    participant Firewall as PANOS Firewall
    participant Config as Configuration
    
    User->>Script: Run with CSV or CLI args
    Script->>Script: Parse Input
    Script->>SDK: Connect to Firewall
    SDK->>Firewall: API Authentication
    Firewall-->>SDK: Authentication Success
    
    loop For Each Object
        Script->>Script: Create Object Instance
        Script->>SDK: Add Object to Firewall
        SDK->>Firewall: Add Object (XML API)
        Firewall-->>SDK: Object Added
    end
    
    Script->>Config: Commit Configuration
    Config->>Firewall: Commit Changes
    Firewall-->>Config: Commit Success
    Config-->>Script: Configuration Committed
    Script-->>User: Success Report
```

---

## Torq Workflow Orchestration Flow

```mermaid
graph TB
    subgraph Events["Event Sources"]
        GitLabEvent[GitLab Webhook<br/>Merge Event]
        SlackCommand[Slack Command<br/>/provision-lab]
        ScheduledEvent[Scheduled Trigger<br/>Daily 00:00]
        ManualEvent[Manual Trigger<br/>On-Demand]
    end
    
    subgraph TorqCloud["Torq.io Cloud Platform"]
        Trigger[Workflow Trigger]
        Workflow[Workflow Engine]
        Step1[Step 1: HTTP Request]
        Step2[Step 2: Script Execution]
        Step3[Step 3: CLI Command]
        Step4[Step 4: Integration Call]
    end
    
    subgraph Runner["Self-Hosted Runner"]
        TaskQueue[Task Queue]
        Executor[Task Executor]
        ScriptRunner[Script Runner]
        CLIRunner[CLI Runner]
    end
    
    subgraph Targets["Target Infrastructure"]
        Kubernetes[Kubernetes Cluster]
        Ansible[Ansible Playbooks]
        Docker[Docker Containers]
        PANOS[PANOS Firewalls]
    end
    
    GitLabEvent --> Trigger
    SlackCommand --> Trigger
    ScheduledEvent --> Trigger
    ManualEvent --> Trigger
    
    Trigger --> Workflow
    Workflow --> Step1
    Step1 --> Step2
    Step2 --> Step3
    Step3 --> Step4
    
    Step2 --> TaskQueue
    Step3 --> TaskQueue
    Step4 --> TaskQueue
    
    TaskQueue --> Executor
    Executor --> ScriptRunner
    Executor --> CLIRunner
    
    ScriptRunner --> Kubernetes
    ScriptRunner --> Ansible
    CLIRunner --> Docker
    CLIRunner --> PANOS
```

---

## Certificate Auto-Enrollment Flow

```mermaid
sequenceDiagram
    participant GPO as Group Policy
    participant System as Domain Computer
    participant CA as Certificate Authority
    participant Template as Certificate Template
    
    GPO->>System: Apply Auto-Enrollment Policy
    System->>System: Check Certificate Status
    System->>System: Certificate Expiring/Missing?
    
    alt Certificate Needed
        System->>CA: Certificate Enrollment Request
        CA->>Template: Select Template
        Template->>CA: Validate Request
        CA->>CA: Sign Certificate
        CA->>System: Return Certificate
        System->>System: Install Certificate
        System->>System: Update Certificate Store
    end
    
    System-->>GPO: Enrollment Status
```

---

## PKI Cross-Platform Integration

```mermaid
graph LR
    subgraph Windows["Windows Systems"]
        ADCS[Active Directory<br/>Certificate Services]
        Templates[Certificate<br/>Templates]
        AutoEnroll[Auto-Enrollment<br/>GPO]
    end
    
    subgraph Linux["Linux Systems"]
        OpenSSL[OpenSSL<br/>CSR Generation]
        WebEnroll[Web Enrollment<br/>Interface]
        Certmonger[Certmonger<br/>Auto-Renewal]
        SSSD[SSSD<br/>Cert Auth]
    end
    
    subgraph Kubernetes["Kubernetes"]
        CertManager[cert-manager<br/>Operator]
        ClusterCA[Cluster CA<br/>Certificates]
        ServiceCerts[Service<br/>Certificates]
    end
    
    ADCS --> Templates
    Templates --> AutoEnroll
    Templates --> WebEnroll
    WebEnroll --> OpenSSL
    OpenSSL --> Certmonger
    Certmonger --> SSSD
    Templates --> CertManager
    CertManager --> ClusterCA
    CertManager --> ServiceCerts
```

---

## PANOS Certificate Chain Building

```mermaid
flowchart TD
    Start([Start Certificate Chain Building]) --> GetCert[Get Signed Certificate]
    GetCert --> GetIntermediate[Get Intermediate CA Certificate]
    GetIntermediate --> GetRoot[Get Root CA Certificate]
    GetRoot --> ValidateRoot[Validate Root CA]
    ValidateRoot --> ValidateIntermediate[Validate Intermediate CA]
    ValidateIntermediate --> ValidateEndEntity[Validate End Entity Certificate]
    ValidateEndEntity --> BuildChain[Build Certificate Chain]
    BuildChain --> FormatPEM[Format as PEM]
    FormatPEM --> ReturnChain([Return Full Chain])
```

---

## Torq Self-Hosted Runner Architecture

```mermaid
graph TB
    subgraph Cloud["Torq.io Cloud"]
        ControlPlane[Control Plane]
        WorkflowEngine[Workflow Engine]
    end
    
    subgraph Network["Private Network"]
        Runner[Self-Hosted Runner<br/>Container]
        TaskExecutor[Task Executor]
    end
    
    subgraph Infrastructure["On-Premise Infrastructure"]
        K3s[K3s Cluster]
        Ansible[Ansible Tower]
        vCenter[vCenter Server]
        PANOS[PANOS Firewalls]
    end
    
    ControlPlane -->|Outbound HTTPS| Runner
    WorkflowEngine -->|Delegates Tasks| Runner
    Runner -->|Execute Locally| TaskExecutor
    TaskExecutor --> K3s
    TaskExecutor --> Ansible
    TaskExecutor --> vCenter
    TaskExecutor --> PANOS
```

---

## GlobalProtect SAML Configuration Flow

```mermaid
sequenceDiagram
    participant Admin
    participant Script as SAML Import Script
    participant PANOS as PANOS Firewall
    participant SAMLProvider as SAML Provider
    participant Metadata as SAML Metadata
    
    Admin->>Script: Run Import Script
    Script->>SAMLProvider: Retrieve SAML Metadata
    SAMLProvider-->>Script: Return Metadata XML
    Script->>Script: Parse Metadata
    Script->>Script: Extract Certificates
    Script->>PANOS: Import SAML Provider (API)
    PANOS-->>Script: Provider Imported
    Script->>PANOS: Configure Authentication Profile
    PANOS-->>Script: Profile Configured
    Script->>PANOS: Apply to Portal/Gateway
    PANOS-->>Script: Configuration Applied
    Script-->>Admin: SAML Configuration Complete
```

---

**Last Updated**: 2026-01-08  
**Maintained By**: Baker Street Labs Infrastructure Team

