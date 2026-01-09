# Torq.io Integration for Baker Street Labs

## Overview

This directory contains the complete Torq.io integration for Baker Street Labs, enabling event-driven automation and orchestration of the cyber range infrastructure. The integration transforms the platform from imperative scripting to intelligent, event-driven workflows.

## Architecture

### Current State → Target State
```
BEFORE: Imperative Script-Based
├── GitLab CI/CD Pipeline
├── Single Ubuntu Runner (SPOF)
├── Ansible Playbooks (Monolithic)
├── Manual Process Management
└── Limited Automation

AFTER: Event-Driven Automation
├── Torq.io Control Plane
├── Self-Hosted Runners (Scalable)
├── Native Workflows (Modular)
├── Automated Governance
└── Intelligent Orchestration
```

## Directory Structure

```
torq-integration/
├── README.md                    # This file
├── config/                      # Configuration files
│   └── torq-config.yaml        # Main Torq.io configuration
├── workflows/                   # Torq.io workflow definitions
│   ├── dns-management.yaml     # DNS management workflow
│   ├── traffic-generation.yaml # Traffic generation workflow
│   ├── mythic-deployment.yaml  # Mythic C2 deployment workflow
│   ├── lab-provisioning.yaml   # Self-service lab provisioning
│   └── cost-management.yaml    # Automated cost optimization
├── runners/                     # Self-hosted runner configurations
│   ├── k3s-runner.yaml         # K3s cluster runner
│   ├── cloud-runner.yaml       # Cloud infrastructure runner
│   └── runner-secrets.yaml     # Runner authentication secrets
├── integrations/                # Integration configurations
│   ├── gitlab-webhook.yaml     # GitLab webhook setup
│   ├── slack-integration.yaml  # Slack integration config
│   └── monitoring-webhook.yaml # Monitoring integration
└── scripts/                     # Deployment and management scripts
    ├── deploy-torq-integration.sh # Main deployment script
    ├── test-workflows.sh        # Workflow testing script
    └── migrate-legacy.sh        # Legacy system migration
```

## Quick Start

### Prerequisites

1. **Torq.io Account**: Sign up at [torq.io](https://torq.io)
2. **K3s Cluster**: Running Baker Street Labs infrastructure
3. **Environment Variables**: Set required configuration

### Required Environment Variables

```bash
export TORQ_WORKSPACE_ID="your-workspace-id"
export TORQ_API_TOKEN="your-api-token"
export GITLAB_WEBHOOK_SECRET="your-webhook-secret"
export GITLAB_PROJECT_ID="your-project-id"
export GITLAB_API_TOKEN="your-gitlab-token"
export SLACK_BOT_TOKEN="your-slack-token"
export SLACK_APP_TOKEN="your-slack-app-token"
```

### Deployment

```bash
# Deploy complete Torq.io integration
./scripts/deploy-torq-integration.sh

# Verify deployment
kubectl get pods -n torq-automation
kubectl get secrets -n torq-automation
```

## Workflows

### 1. DNS Management Workflow

**Trigger**: GitLab push to `dns/*` branch  
**Purpose**: Manages DNS zones and records for cyber range infrastructure  
**Features**:
- Automated DNS zone deployment
- CoreDNS configuration updates
- DNS resolution verification
- GitLab status updates
- Slack notifications

### 2. Traffic Generation Workflow

**Trigger**: Scheduled (every 6 hours)  
**Purpose**: Generates realistic network traffic for testing  
**Features**:
- Multi-vendor traffic generation
- Realistic syslog simulation
- Performance monitoring
- Automated cleanup

### 3. Mythic C2 Deployment Workflow

**Trigger**: On-demand with parameters  
**Purpose**: Deploys and manages Mythic C2 infrastructure  
**Features**:
- Environment-specific deployments
- Scalable replica management
- Health checks and monitoring
- Configuration management

### 4. Lab Provisioning Workflow

**Trigger**: Slack command `/lab-create`  
**Purpose**: Self-service lab environment provisioning  
**Features**:
- Template-based provisioning
- User permission validation
- Automated cleanup scheduling
- Resource monitoring

### 5. Cost Management Workflow

**Trigger**: Scheduled (daily at midnight)  
**Purpose**: Automated cost optimization and resource cleanup  
**Features**:
- Idle resource detection
- User notification system
- Automated termination
- Cost reporting

## Self-Hosted Runners

### K3s Runner

**Purpose**: Execute workflows within the K3s cluster  
**Capabilities**:
- Kubernetes API access
- Ansible playbook execution
- Docker container management
- Bash/Python scripting

**Configuration**:
```yaml
name: "baker-street-k3s"
labels: ["k3s", "ansible", "docker", "kubectl", "baker-street"]
max_concurrent: 5
timeout: 3600
```

### Cloud Runner

**Purpose**: Manage cloud infrastructure resources  
**Capabilities**:
- Terraform execution
- Cloud provider APIs
- Multi-cloud deployments
- Infrastructure automation

## Integrations

### GitLab Integration

**Webhook URL**: `https://app.torq.io/webhook/gitlab-baker-street`  
**Events**: Push, Merge Request, Pipeline  
**Features**:
- Automatic workflow triggering
- Commit status updates
- Branch-based deployments
- Project-specific configurations

### Slack Integration

**Bot Token**: Configured via secrets  
**Channels**: `#baker-street-ops`  
**Features**:
- Workflow notifications
- Interactive commands
- Status updates
- Error alerts

### Monitoring Integration

**Prometheus**: Metrics collection and alerting  
**Grafana**: Dashboard visualization  
**Elasticsearch**: Log aggregation and analysis  
**Features**:
- Real-time monitoring
- Performance metrics
- Alert management
- Historical analysis

## Configuration

### Torq.io Configuration

The main configuration file `config/torq-config.yaml` contains:

- **Workspace Settings**: API tokens and endpoints
- **Runner Configuration**: Labels, limits, and capabilities
- **Integration Settings**: GitLab, Slack, and monitoring
- **Workflow Parameters**: Timeouts, concurrency, and scheduling
- **Security Settings**: RBAC, secrets management, and audit logging

### Environment-Specific Overrides

```yaml
environments:
  development:
    runners:
      k3s_runner:
        max_concurrent: 2
    workflows:
      dns_management:
        timeout: 300
  
  production:
    runners:
      k3s_runner:
        max_concurrent: 5
    monitoring:
      alerting:
        enabled: true
```

## Security

### RBAC Configuration

The Torq runner has comprehensive Kubernetes RBAC permissions:

- **Cluster-wide Access**: Pods, services, configmaps, secrets
- **Application Management**: Deployments, replicasets, statefulsets
- **Network Management**: Ingresses, network policies
- **Batch Operations**: Jobs, cronjobs
- **Custom Resources**: Baker Street Labs specific resources

### Secrets Management

All sensitive data is stored in Kubernetes secrets:

- **Torq Runner Token**: API authentication
- **GitLab Integration**: Webhook secrets and API tokens
- **Slack Integration**: Bot and app tokens
- **Kubeconfig**: Cluster access credentials

### Network Security

- **Namespace Isolation**: All resources in `torq-automation` namespace
- **Service Account**: Dedicated service account for runner
- **Network Policies**: Traffic control and filtering
- **TLS Encryption**: All API communications encrypted

## Monitoring and Alerting

### Health Checks

- **Runner Health**: HTTP health endpoints
- **Workflow Status**: Success/failure monitoring
- **Resource Usage**: CPU, memory, and storage monitoring
- **Integration Status**: External service connectivity

### Alerting Channels

- **Slack**: Real-time notifications
- **Email**: Critical alerts and reports
- **PagerDuty**: Production incident management
- **Webhooks**: Custom integrations

### Metrics

- **Workflow Execution**: Success rates, duration, and frequency
- **Runner Performance**: Resource utilization and availability
- **Integration Health**: API response times and error rates
- **Cost Optimization**: Resource usage and savings

## Troubleshooting

### Common Issues

1. **Runner Not Starting**
   ```bash
   kubectl get pods -n torq-automation
   kubectl logs -n torq-automation deployment/torq-runner
   ```

2. **Workflow Failures**
   ```bash
   # Check Torq.io dashboard for workflow logs
   # Verify runner connectivity and permissions
   kubectl describe pod -n torq-automation -l app=torq-runner
   ```

3. **Integration Issues**
   ```bash
   # Test GitLab webhook
   curl -X POST "https://app.torq.io/webhook/gitlab-baker-street" \
        -H "Content-Type: application/json" \
        -d '{"test": "webhook"}'
   
   # Test Slack integration
   curl -X POST "https://slack.com/api/auth.test" \
        -H "Authorization: Bearer $SLACK_BOT_TOKEN"
   ```

### Debug Commands

```bash
# Check runner status
kubectl get pods -n torq-automation -l app=torq-runner

# View runner logs
kubectl logs -n torq-automation -l app=torq-runner -f

# Check secrets
kubectl get secrets -n torq-automation

# Verify RBAC
kubectl auth can-i create pods --as=system:serviceaccount:torq-automation:torq-runner

# Test workflow execution
./scripts/test-workflows.sh
```

## Migration from Legacy System

### Phase 1: Wrapper Implementation
- Deploy Torq.io integration
- Create wrapper workflows for existing Ansible playbooks
- Test end-to-end functionality
- Decommission legacy Ubuntu runner

### Phase 2: Native Migration
- Migrate DNS management to native workflows
- Migrate traffic generation to native workflows
- Migrate Mythic C2 deployment to native workflows
- Implement monitoring and alerting

### Phase 3: Advanced Features
- Implement self-service lab provisioning
- Implement automated cost management
- Implement policy enforcement
- Implement ChatOps integration

## Support and Documentation

### Resources

- **Torq.io Documentation**: [docs.torq.io](https://docs.torq.io)
- **Baker Street Labs Docs**: [docs.baker-street.com](https://docs.baker-street.com)
- **Implementation Plan**: `docs/plans/Torq_Migration_Implementation_Plan.md`

### Support Channels

- **Torq.io Support**: [support.torq.io](https://support.torq.io)
- **Baker Street Labs**: ops@baker-street.com
- **Slack Channel**: #baker-street-ops

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request
5. Update documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Torq.io Integration for Baker Street Labs** - Transforming cyber range automation through event-driven orchestration.

*"The automation of our trade is as important as the tools that execute it. In Baker Street Labs, we provide both."* - Sherlock Holmes
