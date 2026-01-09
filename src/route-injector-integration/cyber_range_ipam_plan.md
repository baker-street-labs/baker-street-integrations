# Baker Street Labs Cyber Range IPAM Plan
## Comprehensive IP Address Management for Cortex Labs Cyber Range Infrastructure

### Executive Summary

This document outlines a comprehensive IPAM plan for the new Baker Street Labs cyber range infrastructure, designed to support 4 primary cyber ranges (SE DEMO XDR, SE DEMO XSIAM, SE DEMO Platform, SE DEMO Research) with a scalable architecture for future expansion. The plan addresses VLAN mapping, IP allocation, and master router integration with PAN-OS.

---

## Network Architecture Overview

### Master Router Configuration (PAN-OS)
- **Management IP**: VLAN 900 (DirtyNet) - `192.168.0.254`
- **Ethernet1/1**: VLAN 900 (DirtyNet) - `192.168.0.1`
- **Router VLAN**: TBD based on internal routing requirements
- **Role**: Final egress point for all cyber ranges

### Core Infrastructure VLANs
- **VLAN 900**: DirtyNet (Master egress) - `192.168.0.0/16`
- **VLAN 600**: iSCSI - `172.24.254.0/24`
- **VLAN 611**: vMotion - `172.22.254.0/24`
- **VLAN 100**: iLO - `10.55.250.0/26`
- **VLAN 105**: OOBM (formerly icarus-mgmt) - `10.55.250.64/26`

---

## Cyber Range VLAN Mapping Plan

### 1. SE DEMO XDR (1000 Series VLANs)
```
VLAN 1001: xdr-public     - 172.21.55.0/24   (Gateway: 172.21.55.20)
VLAN 1002: xdr-users      - 172.21.45.0/24   (Gateway: 172.21.45.20)
VLAN 1003: xdr-DAAS       - 172.21.35.0/24   (Gateway: 172.21.35.20)
VLAN 1004: xdr-critical   - 172.21.25.0/24   (Gateway: 172.21.25.20)
VLAN 1005: xdr-iot        - 172.21.15.0/24   (Gateway: 172.21.15.20)
VLAN 1006: xdr-transit    - 172.21.65.0/24   (Gateway: 172.21.65.20)
```

### 2. SE DEMO XSIAM (2000 Series VLANs)
```
VLAN 2001: xsiam-public   - 172.21.55.0/24   (Gateway: 172.21.55.20)
VLAN 2002: xsiam-users    - 172.21.45.0/24   (Gateway: 172.21.45.20)
VLAN 2003: xsiam-DAAS     - 172.21.35.0/24   (Gateway: 172.21.35.20)
VLAN 2004: xsiam-critical - 172.21.25.0/24   (Gateway: 172.21.25.20)
VLAN 2005: xsiam-iot      - 172.21.15.0/24   (Gateway: 172.21.15.20)
VLAN 2006: xsiam-transit  - 172.21.65.0/24   (Gateway: 172.21.65.20)
```

### 3. SE DEMO Platform (3000 Series VLANs)
```
VLAN 3001: platform-public   - 172.21.55.0/24   (Gateway: 172.21.55.20)
VLAN 3002: platform-users    - 172.21.45.0/24   (Gateway: 172.21.45.20)
VLAN 3003: platform-DAAS     - 172.21.35.0/24   (Gateway: 172.21.35.20)
VLAN 3004: platform-critical - 172.21.25.0/24   (Gateway: 172.21.25.20)
VLAN 3005: platform-iot      - 172.21.15.0/24   (Gateway: 172.21.15.20)
VLAN 3006: platform-transit  - 172.21.65.0/24   (Gateway: 172.21.65.20)
```

### 4. SE DEMO Research (4000 Series VLANs)
```
VLAN 4001: research-network-1  - 10.1.0.0/24
VLAN 4002: research-network-2  - 10.2.0.0/24
VLAN 4003: research-network-3  - 10.3.0.0/24
VLAN 4004: research-network-4  - 10.4.0.0/24
VLAN 4005: research-network-5  - 10.5.0.0/24
VLAN 4006: research-network-6  - 10.6.0.0/24
VLAN 4007: research-network-7  - 10.7.0.0/24
VLAN 4008: research-network-8  - 10.8.0.0/24
VLAN 4009: research-network-9  - 10.9.0.0/24
VLAN 4010: research-network-10 - 10.10.0.0/24
VLAN 4011: research-network-11 - 10.11.0.0/24
VLAN 4012: research-network-12 - 10.12.0.0/24
```

---

## IPAM Configuration Plan

### 1. Master Router IP Allocation
```yaml
master_router:
  management:
    vlan: 900
    ip: "192.168.0.254"
    description: "PAN-OS Management Interface"
  
  ethernet1_1:
    vlan: 900
    ip: "192.168.0.1"
    description: "Primary Data Interface"
  
  router_vlan:
    vlan: 901  # Suggested internal routing VLAN
    ip: "192.168.1.1"
    description: "Internal Router VLAN"
```

### 2. DNS Server Configuration
```yaml
dns_servers:
  primary:
    ip: "192.168.0.10"
    vlan: 900
    hostname: "ns1.bakerstreetlabs.local"
  
  secondary:
    ip: "192.168.0.11"
    vlan: 900
    hostname: "ns2.bakerstreetlabs.local"
```

### 3. Active Directory Integration
```yaml
active_directory:
  domain_controllers:
    - ip: "192.168.0.20"
      vlan: 900
      hostname: "dc1.bakerstreetlabs.local"
    - ip: "192.168.0.21"
      vlan: 900
      hostname: "dc2.bakerstreetlabs.local"
  
  domain: "bakerstreetlabs.local"
  dns_servers: ["192.168.0.10", "192.168.0.11"]
```

---

## Cyber Range IP Allocation Strategy

### 1. IP Range Allocation by Cyber Range

#### SE DEMO XDR (172.21.x.0/24 Networks)
```yaml
xdr_ranges:
  public: "172.21.55.0/24"
    gateway: "172.21.55.20"
    border: "172.21.55.254"
    available_ips: "172.21.55.21-253"
  
  users: "172.21.45.0/24"
    gateway: "172.21.45.20"
    available_ips: "172.21.45.21-254"
  
  daas: "172.21.35.0/24"
    gateway: "172.21.35.20"
    available_ips: "172.21.35.21-254"
  
  critical: "172.21.25.0/24"
    gateway: "172.21.25.20"
    available_ips: "172.21.25.21-254"
  
  iot: "172.21.15.0/24"
    gateway: "172.21.15.20"
    available_ips: "172.21.15.21-254"
  
  transit: "172.21.65.0/24"
    gateway: "172.21.65.20"
    available_ips: "172.21.65.21-254"
```

#### SE DEMO XSIAM (172.21.x.0/24 Networks)
```yaml
xsiam_ranges:
  # Same structure as XDR but with different VLAN IDs (2000 series)
  # IP ranges remain the same for consistency
```

#### SE DEMO Platform (172.21.x.0/24 Networks)
```yaml
platform_ranges:
  # Same structure as XDR but with different VLAN IDs (3000 series)
  # IP ranges remain the same for consistency
```

#### SE DEMO Research (10.x.0.0/24 Networks)
```yaml
research_ranges:
  network_1: "10.1.0.0/24"
    gateway: "10.1.0.1"
    available_ips: "10.1.0.2-254"
  
  network_2: "10.2.0.0/24"
    gateway: "10.2.0.1"
    available_ips: "10.2.0.2-254"
  
  # ... continues for all 12 research networks
```

### 2. Reserved IP Allocations

#### Infrastructure Reserved IPs
```yaml
reserved_ips:
  # Master Router
  master_router_mgmt: "192.168.0.254"
  master_router_data: "192.168.0.1"
  master_router_internal: "192.168.1.1"
  
  # DNS Servers
  dns_primary: "192.168.0.10"
  dns_secondary: "192.168.0.11"
  
  # Active Directory
  ad_dc1: "192.168.0.20"
  ad_dc2: "192.168.0.21"
  
  # Core Infrastructure
  vcenter: "10.55.250.65"
  esxi_hosts: "10.55.250.66-70"
  guacamole: "10.55.250.193"
  reverse_proxy: "10.55.250.129"
  
  # Storage
  iscsi_gateway: "172.24.254.1"
  vmotion_gateway: "172.22.254.1"
```

#### Cyber Range Reserved IPs
```yaml
cyber_range_reserved:
  # Each cyber range gets reserved IPs for:
  # - Gateway (.20 or .1)
  # - Border router (.254)
  # - DNS servers (.10, .11)
  # - Management systems (.100-110)
  # - Monitoring systems (.200-210)
```

---

## Scalability Plan for Future Cyber Ranges

### 1. VLAN ID Allocation Strategy
```yaml
vlan_allocation:
  infrastructure: "100-199"
    core_services: "100-105"
    storage: "600-699"
    management: "900-999"
  
  cyber_ranges: "1000-9999"
    xdr: "1000-1999"
    xsiam: "2000-2999"
    platform: "3000-3999"
    research: "4000-4999"
    future_range_1: "5000-5999"
    future_range_2: "6000-6999"
    future_range_3: "7000-7999"
    future_range_4: "8000-8999"
```

### 2. IP Range Allocation Strategy
```yaml
ip_range_allocation:
  infrastructure: "192.168.0.0/16, 10.55.250.0/24, 172.24.254.0/24, 172.22.254.0/24"
  
  cyber_ranges:
    xdr: "172.21.0.0/16"
    xsiam: "172.21.0.0/16"  # Shared with XDR
    platform: "172.21.0.0/16"  # Shared with XDR
    research: "10.1.0.0/16"
    future_range_1: "172.22.0.0/16"
    future_range_2: "172.23.0.0/16"
    future_range_3: "10.2.0.0/16"
    future_range_4: "10.3.0.0/16"
```

### 3. Future Cyber Range Template
```yaml
future_cyber_range_template:
  vlan_base: 5000  # Starting VLAN for new range
  ip_base: "172.22.0.0/16"  # IP range for new range
  
  standard_vlans:
    public: "{vlan_base}01"
    users: "{vlan_base}02"
    daas: "{vlan_base}03"
    critical: "{vlan_base}04"
    iot: "{vlan_base}05"
    transit: "{vlan_base}06"
  
  standard_ips:
    public: "{ip_base}/24"
    users: "{ip_base}/24"
    daas: "{ip_base}/24"
    critical: "{ip_base}/24"
    iot: "{ip_base}/24"
    transit: "{ip_base}/24"
```

---

## IPAM Database Schema Updates

### 1. Cyber Range Table
```sql
CREATE TABLE cyber_ranges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    vlan_base INTEGER NOT NULL,
    ip_base INET NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert initial cyber ranges
INSERT INTO cyber_ranges (name, description, vlan_base, ip_base) VALUES
('SE DEMO XDR', 'Cortex XDR Demonstration Environment', 1000, '172.21.0.0/16'),
('SE DEMO XSIAM', 'Cortex XSIAM Demonstration Environment', 2000, '172.21.0.0/16'),
('SE DEMO Platform', 'Cortex Platform Demonstration Environment', 3000, '172.21.0.0/16'),
('SE DEMO Research', 'Research and Development Environment', 4000, '10.1.0.0/16');
```

### 2. VLAN Template Table
```sql
CREATE TABLE vlan_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    vlan_suffix INTEGER NOT NULL,
    ip_suffix INTEGER NOT NULL,
    description TEXT,
    cyber_range_id INTEGER REFERENCES cyber_ranges(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert standard VLAN templates
INSERT INTO vlan_templates (name, vlan_suffix, ip_suffix, description) VALUES
('public', 1, 55, 'Public-facing services and DMZ'),
('users', 2, 45, 'User workstations and endpoints'),
('daas', 3, 35, 'Data Analytics and AI Services'),
('critical', 4, 25, 'Critical infrastructure and services'),
('iot', 5, 15, 'IoT devices and sensors'),
('transit', 6, 65, 'Transit and inter-zone communication');
```

### 3. Updated Subnet Table
```sql
ALTER TABLE subnets ADD COLUMN cyber_range_id INTEGER REFERENCES cyber_ranges(id);
ALTER TABLE subnets ADD COLUMN vlan_template_id INTEGER REFERENCES vlan_templates(id);
ALTER TABLE subnets ADD COLUMN is_shared BOOLEAN DEFAULT FALSE;
```

---

## Implementation Plan

### Phase 1: Core Infrastructure Setup (Week 1-2)
1. **Master Router Configuration**
   - Configure PAN-OS with management IP on VLAN 900
   - Set up Ethernet1/1 on VLAN 900
   - Configure internal router VLAN
   - Set up routing between cyber ranges

2. **DNS and AD Integration**
   - Deploy DNS servers on VLAN 900
   - Configure Active Directory domain controllers
   - Set up DNS forwarding and resolution

3. **Core VLAN Configuration**
   - Configure VLAN 900 (DirtyNet)
   - Set up VLAN 600 (iSCSI) and VLAN 611 (vMotion)
   - Configure VLAN 100 (iLO) and VLAN 105 (OOBM)

### Phase 2: Cyber Range Deployment (Week 3-4)
1. **SE DEMO XDR Setup**
   - Configure VLANs 1001-1006
   - Set up IP ranges 172.21.x.0/24
   - Deploy initial devices and services

2. **SE DEMO XSIAM Setup**
   - Configure VLANs 2001-2006
   - Set up IP ranges 172.21.x.0/24
   - Deploy initial devices and services

3. **SE DEMO Platform Setup**
   - Configure VLANs 3001-3006
   - Set up IP ranges 172.21.x.0/24
   - Deploy initial devices and services

4. **SE DEMO Research Setup**
   - Configure VLANs 4001-4012
   - Set up IP ranges 10.1.0.0/24 through 10.12.0.0/24
   - Deploy initial devices and services

### Phase 3: IPAM Integration (Week 5-6)
1. **Update IPAM Service**
   - Modify database schema for cyber ranges
   - Update IP allocation logic
   - Configure VLAN templates

2. **DNS Integration**
   - Integrate with master DNS servers
   - Set up automatic DNS record creation
   - Configure zone management

3. **Route Injection Integration**
   - Configure master router integration
   - Set up automatic route creation
   - Test end-to-end connectivity

### Phase 4: Monitoring and Optimization (Week 7-8)
1. **Monitoring Setup**
   - Configure Prometheus metrics
   - Set up Grafana dashboards
   - Implement alerting

2. **Performance Optimization**
   - Optimize IP allocation algorithms
   - Configure caching strategies
   - Test scalability

3. **Documentation and Training**
   - Create operational documentation
   - Train staff on new system
   - Establish maintenance procedures

---

## Security Considerations

### 1. Network Segmentation
- **Cyber ranges are isolated** by VLAN and IP range
- **Master router controls** all inter-range communication
- **DirtyNet (VLAN 900)** serves as the security boundary

### 2. Access Control
- **Role-based access** for different cyber ranges
- **API authentication** for all IPAM operations
- **Audit logging** for all IP allocations and changes

### 3. Compliance
- **IP address tracking** for all devices
- **Change management** for network modifications
- **Forensic capabilities** for incident response

---

## Monitoring and Alerting

### 1. Key Metrics
- **IP utilization** per cyber range and VLAN
- **Device registration** and de-registration rates
- **DNS resolution** success rates
- **Route injection** success rates
- **Master router** connectivity and performance

### 2. Alerts
- **IP conflicts** within or between cyber ranges
- **VLAN capacity** warnings
- **DNS resolution** failures
- **Route injection** failures
- **Master router** connectivity issues

### 3. Dashboards
- **Cyber range overview** with status and utilization
- **VLAN utilization** across all ranges
- **Device inventory** by cyber range
- **Network topology** visualization
- **Security events** and alerts

---

## Conclusion

This comprehensive IPAM plan provides a scalable, secure, and manageable solution for the Baker Street Labs cyber range infrastructure. The design supports the current 4 cyber ranges while providing a clear path for future expansion. The integration with PAN-OS master router, DNS services, and Active Directory ensures a cohesive and secure environment for cybersecurity training and research.

**Key Benefits:**
- **Centralized management** of all IP addresses across cyber ranges
- **Scalable architecture** for future cyber range additions
- **Secure segmentation** between different environments
- **Automated provisioning** and cleanup
- **Comprehensive monitoring** and alerting
- **Integration** with existing infrastructure

**Next Steps:**
1. Review and approve the IPAM plan
2. Begin Phase 1 implementation
3. Configure master router and core infrastructure
4. Deploy and test IPAM service
5. Implement cyber range configurations

---

*Document Version: 1.0*  
*Created: September 9, 2025*  
*Baker Street Labs Infrastructure Team*
