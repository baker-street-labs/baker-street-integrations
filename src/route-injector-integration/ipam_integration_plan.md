# Baker Street Labs IPAM Integration Plan
## Cyber Range IP Address Management System

### Executive Summary

Based on analysis of the existing Baker Street Labs cyber range infrastructure, this document outlines a comprehensive IPAM (IP Address Management) system integration with the DNS system. The current infrastructure shows a sophisticated cyber range with multiple network zones, user workstations, and automated traffic generation capabilities.

---

## Current Infrastructure Analysis

### Existing Network Topology
From the analysis of `enhanced-corporate-network-playbook.yaml` and `users_ssh.csv`, the current cyber range includes:

#### Network Zones
- **DMZ Zone**: `10.0.1.0/24` (Web servers, mail servers)
- **Internal Network**: `192.168.1.0/24` (User workstations, file servers)
- **Management Network**: `172.16.1.0/24` (Admin workstations, backup servers)
- **User Workstations**: `10.0.0.0/8` (392+ user devices across multiple subnets)

#### Device Distribution
- **392 User Workstations** across subnets:
  - `10.0.0.0/24` - 50+ devices
  - `10.0.1.0/24` - 50+ devices  
  - `10.0.2.0/24` - 50+ devices
  - `10.0.3.0/24` - 50+ devices
  - `10.0.4.0/24` - 50+ devices
  - `10.0.5.0/24` - 50+ devices
  - `10.0.6.0/24` - 50+ devices

#### Current Services
- **DNS Service**: mothership-dns-tool (port 9090)
- **Route Injection**: Enhanced service (port 5001)
- **API Gateway**: Kong (port 8000)
- **Ollama**: AI service (port 11434)

---

## IPAM System Requirements

### 1. Core IPAM Features

#### IP Address Management
- **Subnet Management**: Track all cyber range subnets
- **IP Allocation**: Automatic and manual IP assignment
- **Reservation System**: Reserve IPs for specific devices/services
- **Conflict Detection**: Prevent duplicate IP assignments
- **Range Validation**: Ensure IPs are within valid subnets

#### Device Management
- **Device Registration**: Track all cyber range devices
- **MAC Address Binding**: Link IPs to MAC addresses
- **Device Categorization**: Classify by type (workstation, server, IoT, etc.)
- **Vendor Integration**: Track security vendor assignments
- **User Association**: Link devices to users

#### Network Topology
- **Zone Management**: DMZ, Internal, Management zones
- **VLAN Tracking**: Associate subnets with VLANs
- **Gateway Management**: Track default gateways per subnet
- **Service Discovery**: Map services to IP addresses

### 2. Cyber Range Specific Features

#### Scenario Management
- **Playbook Integration**: Link IPs to traffic playbooks
- **Scenario Isolation**: Separate IP ranges for different scenarios
- **Dynamic Allocation**: Assign IPs based on scenario requirements
- **Cleanup Automation**: Release IPs when scenarios end

#### Security Integration
- **Threat Actor IPs**: Track malicious IP addresses
- **Sinkhole Management**: Manage sinkhole IP assignments
- **Honeypot Networks**: Dedicated IP ranges for honeypots
- **Forensic Tracking**: Maintain IP history for investigations

#### Training Environment
- **Student Workstations**: Dedicated IP ranges for training
- **Lab Networks**: Isolated networks for specific exercises
- **Red Team Infrastructure**: Separate IP ranges for attack simulation
- **Blue Team Tools**: IP ranges for defensive tools

---

## Recommended IPAM Architecture

### 1. Database Schema

```sql
-- Subnets table
CREATE TABLE subnets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    network_cidr INET NOT NULL,
    zone VARCHAR(50) NOT NULL,
    vlan_id INTEGER,
    gateway INET,
    dns_servers INET[],
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- IP addresses table
CREATE TABLE ip_addresses (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL UNIQUE,
    subnet_id INTEGER REFERENCES subnets(id),
    device_id INTEGER REFERENCES devices(id),
    status VARCHAR(20) DEFAULT 'available', -- available, allocated, reserved, conflict
    allocated_at TIMESTAMP,
    expires_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Devices table
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    mac_address MACADDR,
    device_type VARCHAR(50) NOT NULL, -- workstation, server, router, switch, etc.
    vendor VARCHAR(100),
    role VARCHAR(100),
    user_id INTEGER REFERENCES users(id),
    scenario_id INTEGER REFERENCES scenarios(id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    email VARCHAR(255),
    department VARCHAR(100),
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scenarios table
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    playbook_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'inactive',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- DNS records table (integration with existing DNS)
CREATE TABLE dns_records (
    id SERIAL PRIMARY KEY,
    fqdn VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    record_type VARCHAR(10) DEFAULT 'A',
    ttl INTEGER DEFAULT 300,
    zone VARCHAR(100),
    device_id INTEGER REFERENCES devices(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. API Endpoints

#### Subnet Management
```
GET    /api/v1/ipam/subnets              # List all subnets
POST   /api/v1/ipam/subnets              # Create new subnet
GET    /api/v1/ipam/subnets/{id}         # Get subnet details
PUT    /api/v1/ipam/subnets/{id}         # Update subnet
DELETE /api/v1/ipam/subnets/{id}         # Delete subnet
```

#### IP Address Management
```
GET    /api/v1/ipam/ips                  # List IP addresses
POST   /api/v1/ipam/ips/allocate         # Allocate IP address
POST   /api/v1/ipam/ips/reserve          # Reserve IP address
PUT    /api/v1/ipam/ips/{id}/release     # Release IP address
GET    /api/v1/ipam/ips/available        # Get available IPs
GET    /api/v1/ipam/ips/conflicts        # Get IP conflicts
```

#### Device Management
```
GET    /api/v1/ipam/devices              # List devices
POST   /api/v1/ipam/devices              # Register device
GET    /api/v1/ipam/devices/{id}         # Get device details
PUT    /api/v1/ipam/devices/{id}         # Update device
DELETE /api/v1/ipam/devices/{id}         # Remove device
```

#### Integration Endpoints
```
POST   /api/v1/ipam/dns/sync             # Sync with DNS system
POST   /api/v1/ipam/route/inject         # Trigger route injection
GET    /api/v1/ipam/reports/usage        # Generate usage reports
GET    /api/v1/ipam/reports/conflicts    # Generate conflict reports
```

### 3. Integration Points

#### DNS System Integration
- **Automatic DNS Record Creation**: When IP is allocated, create DNS record
- **DNS Record Cleanup**: When IP is released, remove DNS record
- **Reverse DNS**: Automatically create PTR records
- **Zone Management**: Sync with existing DNS zones

#### Route Injection Integration
- **Automatic Route Creation**: When IP is allocated in cyber range, inject route
- **Route Cleanup**: When IP is released, remove route
- **Subnet Monitoring**: Monitor subnet usage for route optimization
- **Gateway Management**: Update routes when gateways change

#### API Gateway Integration
- **Service Discovery**: Register services with IPAM
- **Load Balancing**: Use IPAM for load balancer configuration
- **Health Monitoring**: Track service health by IP
- **Traffic Management**: Route traffic based on IPAM data

---

## Implementation Plan

### Phase 1: Core IPAM Service (Week 1-2)
1. **Database Setup**
   - Create IPAM database schema
   - Set up PostgreSQL with IPAM tables
   - Create database migration scripts

2. **Basic API Service**
   - Implement core IPAM API endpoints
   - Add authentication and authorization
   - Create basic web interface

3. **Subnet Management**
   - Import existing cyber range subnets
   - Implement subnet validation
   - Add subnet monitoring

### Phase 2: Device Integration (Week 3-4)
1. **Device Registration**
   - Import existing devices from CSV
   - Implement device discovery
   - Add device categorization

2. **IP Allocation System**
   - Implement automatic IP allocation
   - Add IP reservation system
   - Create conflict detection

3. **User Management**
   - Import users from existing data
   - Implement user-device associations
   - Add role-based access control

### Phase 3: DNS Integration (Week 5-6)
1. **DNS Sync Service**
   - Create DNS synchronization service
   - Implement automatic DNS record creation
   - Add reverse DNS support

2. **Zone Management**
   - Integrate with existing DNS zones
   - Implement zone-based IP allocation
   - Add zone monitoring

3. **DNS API Integration**
   - Integrate with mothership-dns-tool
   - Add DNS record validation
   - Implement DNS conflict resolution

### Phase 4: Route Injection Integration (Week 7-8)
1. **Route Management**
   - Integrate with enhanced route injection service
   - Implement automatic route creation
   - Add route cleanup automation

2. **Network Monitoring**
   - Add subnet usage monitoring
   - Implement network health checks
   - Create network topology visualization

3. **Automation**
   - Implement scenario-based IP allocation
   - Add automated cleanup processes
   - Create network provisioning workflows

### Phase 5: Advanced Features (Week 9-10)
1. **Reporting and Analytics**
   - Create IP usage reports
   - Implement network analytics
   - Add capacity planning tools

2. **Integration Enhancements**
   - Add API Gateway integration
   - Implement service discovery
   - Create monitoring dashboards

3. **Security Features**
   - Add threat actor IP tracking
   - Implement sinkhole management
   - Create forensic IP tracking

---

## Technical Specifications

### 1. Technology Stack
- **Backend**: Python FastAPI
- **Database**: PostgreSQL with INET extension
- **Frontend**: React with Material-UI
- **Authentication**: JWT with RBAC
- **API Gateway**: Kong integration
- **Monitoring**: Prometheus + Grafana

### 2. Database Requirements
- **PostgreSQL 15+** with INET extension
- **Minimum 10GB** storage for IPAM data
- **Backup strategy** with daily snapshots
- **High availability** with replication

### 3. Network Requirements
- **Dedicated VLAN** for IPAM service
- **Firewall rules** for API access
- **Load balancer** for high availability
- **SSL/TLS** for secure communication

### 4. Integration Requirements
- **DNS API**: mothership-dns-tool integration
- **Route Injection**: Enhanced route injection service
- **API Gateway**: Kong service registration
- **Monitoring**: Prometheus metrics export

---

## Cyber Range Specific Features

### 1. Scenario Management
```yaml
scenarios:
  red_team_exercise:
    name: "Red Team Penetration Test"
    subnets: ["10.100.0.0/16"]
    devices: 50
    duration: "4 hours"
    cleanup: "automatic"
    
  blue_team_training:
    name: "Blue Team Incident Response"
    subnets: ["10.200.0.0/16"]
    devices: 30
    duration: "8 hours"
    cleanup: "manual"
    
  malware_analysis:
    name: "Malware Analysis Lab"
    subnets: ["10.300.0.0/24"]
    devices: 10
    duration: "2 hours"
    cleanup: "automatic"
```

### 2. Device Categories
```yaml
device_categories:
  workstations:
    - windows_workstation
    - linux_workstation
    - mac_workstation
    
  servers:
    - web_server
    - mail_server
    - file_server
    - database_server
    
  network_devices:
    - router
    - switch
    - firewall
    - load_balancer
    
  security_tools:
    - honeypot
    - sinkhole
    - monitoring_station
    - forensic_workstation
```

### 3. IP Allocation Policies
```yaml
allocation_policies:
  automatic:
    - workstation_ips: "10.0.{1-6}.{100-200}"
    - server_ips: "10.0.{1-6}.{10-99}"
    - network_ips: "10.0.{1-6}.{1-9}"
    
  reserved:
    - gateway_ips: "10.0.{1-6}.1"
    - dns_ips: "10.0.{1-6}.{2-3}"
    - monitoring_ips: "10.0.{1-6}.{4-5}"
    
  special:
    - honeypot_ips: "10.0.7.0/24"
    - sinkhole_ips: "10.0.8.0/24"
    - forensic_ips: "10.0.9.0/24"
```

---

## Security Considerations

### 1. Access Control
- **Role-based access** for different user types
- **API key authentication** for service integration
- **Audit logging** for all IPAM operations
- **IP whitelisting** for API access

### 2. Data Protection
- **Encryption at rest** for sensitive data
- **Encryption in transit** for API communication
- **Data retention policies** for IP history
- **Secure backup** procedures

### 3. Network Security
- **VLAN isolation** for IPAM service
- **Firewall rules** for API access
- **DDoS protection** for public endpoints
- **Rate limiting** for API calls

---

## Monitoring and Alerting

### 1. Key Metrics
- **IP utilization** per subnet
- **Device registration** rates
- **DNS sync** success rates
- **Route injection** success rates
- **API response** times

### 2. Alerts
- **IP conflicts** detected
- **Subnet capacity** warnings
- **DNS sync** failures
- **Route injection** failures
- **API errors** exceeding thresholds

### 3. Dashboards
- **Network overview** with subnet status
- **Device inventory** with status
- **IP allocation** trends
- **Integration status** with other services
- **Security events** and alerts

---

## Conclusion

The proposed IPAM integration will provide comprehensive IP address management for the Baker Street Labs cyber range, enabling:

1. **Centralized IP Management**: Single source of truth for all IP addresses
2. **Automated Provisioning**: Automatic IP allocation and DNS record creation
3. **Network Integration**: Seamless integration with DNS and route injection systems
4. **Scenario Management**: Support for cyber range training scenarios
5. **Security Enhancement**: Better tracking and management of network resources

This system will significantly improve the efficiency and reliability of the cyber range infrastructure while providing the foundation for advanced network automation and security features.

---

*Document Version: 1.0*  
*Created: September 9, 2025*  
*Baker Street Labs Infrastructure Team*
