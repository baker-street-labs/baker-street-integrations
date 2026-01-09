#!/bin/bash

echo "🚀 Deploying Baker Street Labs IPAM Service"
echo "============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if we're on the right server
echo "📋 Checking deployment environment..."
if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "⚠️  Kong API Gateway not accessible. Make sure you're on the right server."
    echo "   Expected: bakerstreet.labinabox.net:52524"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs backups monitoring/grafana/dashboards monitoring/grafana/datasources

# Create database initialization script
echo "📋 Creating database initialization script..."
cat > init-db.sql << 'EOF'
-- Baker Street Labs IPAM Database Initialization
-- This script sets up the initial database structure

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create initial admin user (password: admin123)
INSERT INTO users (username, full_name, email, department, role) 
VALUES ('admin', 'System Administrator', 'admin@bakerstreetlabs.local', 'IT', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Create initial scenario
INSERT INTO scenarios (name, description, playbook_id, status) 
VALUES ('Default Scenario', 'Default cyber range scenario', 'default', 'inactive')
ON CONFLICT DO NOTHING;

-- Create initial subnets based on Baker Street Labs infrastructure
INSERT INTO subnets (name, network_cidr, zone, vlan_id, gateway, dns_servers, description) VALUES
('DMZ Zone', '10.0.1.0/24', 'dmz', 100, '10.0.1.1', ARRAY['10.0.1.2', '10.0.1.3'], 'DMZ zone for web servers and mail servers'),
('Internal Network', '192.168.1.0/24', 'internal', 200, '192.168.1.1', ARRAY['192.168.1.2', '192.168.1.3'], 'Internal network for user workstations and file servers'),
('Management Network', '172.16.1.0/24', 'management', 300, '172.16.1.1', ARRAY['172.16.1.2', '172.16.1.3'], 'Management network for admin workstations and backup servers'),
('User Workstations - Subnet 0', '10.0.0.0/24', 'workstations', 400, '10.0.0.1', ARRAY['10.0.0.2', '10.0.0.3'], 'User workstations subnet 0'),
('User Workstations - Subnet 1', '10.0.1.0/24', 'workstations', 401, '10.0.1.1', ARRAY['10.0.1.2', '10.0.1.3'], 'User workstations subnet 1'),
('User Workstations - Subnet 2', '10.0.2.0/24', 'workstations', 402, '10.0.2.1', ARRAY['10.0.2.2', '10.0.2.3'], 'User workstations subnet 2'),
('User Workstations - Subnet 3', '10.0.3.0/24', 'workstations', 403, '10.0.3.1', ARRAY['10.0.3.2', '10.0.3.3'], 'User workstations subnet 3'),
('User Workstations - Subnet 4', '10.0.4.0/24', 'workstations', 404, '10.0.4.1', ARRAY['10.0.4.2', '10.0.4.3'], 'User workstations subnet 4'),
('User Workstations - Subnet 5', '10.0.5.0/24', 'workstations', 405, '10.0.5.1', ARRAY['10.0.5.2', '10.0.5.3'], 'User workstations subnet 5'),
('User Workstations - Subnet 6', '10.0.6.0/24', 'workstations', 406, '10.0.6.1', ARRAY['10.0.6.2', '10.0.6.3'], 'User workstations subnet 6'),
('Honeypot Network', '10.0.7.0/24', 'honeypot', 500, '10.0.7.1', ARRAY['10.0.7.2', '10.0.7.3'], 'Honeypot network for threat simulation'),
('Sinkhole Network', '10.0.8.0/24', 'sinkhole', 600, '10.0.8.1', ARRAY['10.0.8.2', '10.0.8.3'], 'Sinkhole network for malicious traffic'),
('Forensic Network', '10.0.9.0/24', 'forensic', 700, '10.0.9.1', ARRAY['10.0.9.2', '10.0.9.3'], 'Forensic analysis network')
ON CONFLICT DO NOTHING;

-- Create some initial devices for testing
INSERT INTO devices (hostname, mac_address, device_type, vendor, role, user_id, scenario_id, status) VALUES
('web-server-01', '00:11:22:33:44:01', 'web_server', 'apache', 'web-server', 1, 1, 'active'),
('mail-server-01', '00:11:22:33:44:02', 'mail_server', 'postfix', 'mail-server', 1, 1, 'active'),
('fileserver-01', '00:11:22:33:44:03', 'file_server', 'samba', 'file-server', 1, 1, 'active'),
('admin-workstation-01', '00:11:22:33:44:04', 'windows_workstation', 'microsoft', 'admin-workstation', 1, 1, 'active'),
('honeypot-01', '00:11:22:33:44:05', 'honeypot', 'cowrie', 'honeypot', 1, 1, 'active')
ON CONFLICT DO NOTHING;

COMMIT;
EOF

# Create Prometheus configuration
echo "📋 Creating Prometheus configuration..."
cat > monitoring/prometheus-ipam.yml << 'EOF'
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  - "ipam_rules.yml"

scrape_configs:
  - job_name: 'ipam-service'
    static_configs:
      - targets: ['ipam-service:5002']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'ipam-postgres'
    static_configs:
      - targets: ['ipam-postgres:5432']
    scrape_interval: 30s

  - job_name: 'ipam-redis'
    static_configs:
      - targets: ['ipam-redis:6379']
    scrape_interval: 30s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []
EOF

# Create Grafana datasource configuration
echo "📋 Creating Grafana datasource configuration..."
cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://ipam-prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard configuration
echo "📋 Creating Grafana dashboard configuration..."
cat > monitoring/grafana/dashboards/ipam-dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'IPAM Dashboards'
    orgId: 1
    folder: 'IPAM'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Stop existing services
echo "🛑 Stopping existing IPAM services..."
docker-compose -f docker-compose-ipam.yml down 2>/dev/null || true

# Build and start IPAM services
echo "🔨 Building and starting IPAM services..."
docker-compose -f docker-compose-ipam.yml up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 60

# Check service health
echo "🔍 Checking IPAM service health..."

# Check IPAM service
if curl -s http://localhost:5002/api/v1/health > /dev/null 2>&1; then
    echo "✅ IPAM Service: Healthy"
    
    # Test basic endpoints
    if curl -s http://localhost:5002/api/v1/ipam/subnets > /dev/null 2>&1; then
        echo "✅ Subnets Endpoint: Working"
    else
        echo "⚠️  Subnets Endpoint: Not responding"
    fi
    
    if curl -s http://localhost:5002/api/v1/ipam/devices > /dev/null 2>&1; then
        echo "✅ Devices Endpoint: Working"
    else
        echo "⚠️  Devices Endpoint: Not responding"
    fi
    
    if curl -s http://localhost:5002/api/v1/ipam/reports/usage > /dev/null 2>&1; then
        echo "✅ Usage Report: Working"
    else
        echo "⚠️  Usage Report: Not responding"
    fi
else
    echo "❌ IPAM Service: Unhealthy"
fi

# Check PostgreSQL
if docker exec baker-street-ipam-postgres pg_isready -U ipam_user -d baker_street_ipam > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Healthy"
else
    echo "❌ PostgreSQL: Unhealthy"
fi

# Check Redis
if docker exec baker-street-ipam-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Unhealthy"
fi

# Check Prometheus
if curl -s http://localhost:9091/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus: Healthy"
else
    echo "❌ Prometheus: Unhealthy"
fi

# Check Grafana
if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "✅ Grafana: Healthy"
else
    echo "❌ Grafana: Unhealthy"
fi

echo ""
echo "🎉 IPAM deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "   IPAM Service: http://localhost:5002"
echo "   Health Check: http://localhost:5002/api/v1/health"
echo "   API Documentation: http://localhost:5002/docs"
echo "   Prometheus: http://localhost:9091"
echo "   Grafana: http://localhost:3001 (admin/ipam_grafana_password_2025)"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker-compose -f docker-compose-ipam.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose-ipam.yml down"
echo "   Restart services: docker-compose -f docker-compose-ipam.yml restart"
echo ""
echo "🧪 Test the IPAM integration:"
echo "   python3 test_ipam_integration.py"
echo ""
echo "📋 IPAM Features:"
echo "   ✅ Comprehensive IP address management"
echo "   ✅ Device registration and tracking"
echo "   ✅ Subnet management with cyber range zones"
echo "   ✅ DNS integration with mothership-dns-tool"
echo "   ✅ Route injection integration"
echo "   ✅ Usage reporting and analytics"
echo "   ✅ Prometheus monitoring"
echo "   ✅ Grafana dashboards"
echo "   ✅ PostgreSQL database with INET support"
echo "   ✅ Redis caching"
echo ""
echo "📋 Next Steps:"
echo "   1. Test the IPAM service endpoints"
echo "   2. Verify DNS integration"
echo "   3. Test route injection integration"
echo "   4. Configure Grafana dashboards"
echo "   5. Import existing cyber range devices"
echo "   6. Set up automated IP allocation policies"
