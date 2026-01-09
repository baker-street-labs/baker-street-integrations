# Baker Street Labs - Route Injection Integration Guide

## 🎯 Overview

This guide explains how to integrate the Route Injector tool with the DNS system to automatically create PAN-OS routes when DNS records are added. The integration provides real-time route management for cyber range infrastructure.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DNS Record Creation                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ mothership  │  │   Kong      │  │ Route       │       │
│  │ DNS Tool    │  │  Gateway    │  │ Injection   │       │
│  │ (Port 9090) │  │ (Port 8000) │  │ Service     │       │
│  └─────────────┘  └─────────────┘  │ (Port 5001) │       │
│         │                │         └─────────────┘       │
│         └────────────────┼────────────────┘                │
│                          │                                 │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              PAN-OS Firewall                       │   │
│  │              (192.168.255.254)                     │   │
│  │              Static Route Creation                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Components

### 1. Route Injection Service
- **Port**: 5001
- **Purpose**: Handles PAN-OS route creation/deletion
- **Features**: JWT authentication, Redis caching, webhook endpoints

### 2. DNS Webhook Integration
- **Purpose**: Triggers route injection when DNS records are created
- **Integration**: Works with mothership-dns-tool API

### 3. PAN-OS Integration
- **Firewall**: 192.168.255.254
- **Credentials**: admin/Paloalto1!
- **Features**: Static route management, configuration commits

## 🚀 Deployment

### Prerequisites
- Docker and Docker Compose installed
- Access to PAN-OS firewall (192.168.255.254)
- Redis server available
- Kong API Gateway running

### Step 1: Deploy Route Injection Service

```bash
cd baker-street-labs/tools/baker-street-tools/route-injector-integration
./deploy.sh
```

### Step 2: Verify Services

```bash
# Check route injection service
curl http://localhost:5001/api/v1/health

# Check DNS service through Kong
curl http://localhost:8000/api/v1/dns/api/health
```

### Step 3: Test Integration

```bash
# Run integration tests
python3 test_integration.py

# Test route injection webhook
curl -X POST http://localhost:5001/api/v1/webhook/dns-record-created \
     -H 'Content-Type: application/json' \
     -d '{
       "zone": "bakerstreetlabs.local",
       "fqdn": "test.bakerstreetlabs.local", 
       "ip_address": "192.168.1.100"
     }'
```

## 🔗 Integration Workflow

### DNS Record Creation Flow

1. **DNS Record Added** → mothership-dns-tool creates DNS record
2. **Webhook Trigger** → DNS API calls route injection webhook
3. **Route Creation** → Route injection service creates PAN-OS static route
4. **Configuration Commit** → PAN-OS configuration is committed
5. **Cache Update** → Route info stored in Redis

### DNS Record Deletion Flow

1. **DNS Record Deleted** → mothership-dns-tool removes DNS record
2. **Webhook Trigger** → DNS API calls route removal webhook
3. **Route Deletion** → Route injection service removes PAN-OS static route
4. **Configuration Commit** → PAN-OS configuration is committed
5. **Cache Cleanup** → Route info removed from Redis

## 📡 API Endpoints

### Route Injection Service

#### Health Check
```http
GET /api/v1/health
```

#### DNS Record Created Webhook
```http
POST /api/v1/webhook/dns-record-created
Content-Type: application/json

{
  "zone": "bakerstreetlabs.local",
  "fqdn": "test.bakerstreetlabs.local",
  "ip_address": "192.168.1.100",
  "ttl": 60
}
```

#### DNS Record Deleted Webhook
```http
POST /api/v1/webhook/dns-record-deleted
Content-Type: application/json

{
  "zone": "bakerstreetlabs.local",
  "fqdn": "test.bakerstreetlabs.local",
  "ip_address": "192.168.1.100"
}
```

#### Get Active Routes
```http
GET /api/v1/routes
```

#### Delete Route
```http
DELETE /api/v1/routes/{route_name}
```

## 🔧 Configuration

### Environment Variables

```bash
# Route Injection Service
REDIS_HOST=redis
REDIS_PORT=6379
PANOS_FIREWALL_IP=192.168.255.254
PANOS_USERNAME=admin
PANOS_PASSWORD=Paloalto1!
```

### Cyber Range Networks

The system automatically detects cyber range IPs and creates routes for:
- `10.0.0.0/8`
- `172.20.0.0/16`
- `192.168.0.0/16`

## 🧪 Testing

### Manual Testing

1. **Test Route Creation**:
```bash
curl -X POST http://localhost:5001/api/v1/webhook/dns-record-created \
     -H 'Content-Type: application/json' \
     -d '{
       "zone": "bakerstreetlabs.local",
       "fqdn": "malware.bakerstreetlabs.local",
       "ip_address": "192.168.1.50"
     }'
```

2. **Verify Route in PAN-OS**:
   - Login to PAN-OS web interface
   - Navigate to Network > Virtual Routers > default > Static Routes
   - Look for route: `dns_malware_bakerstreetlabs_local_192_168_1_50`

3. **Test Route Removal**:
```bash
curl -X POST http://localhost:5001/api/v1/webhook/dns-record-deleted \
     -H 'Content-Type: application/json' \
     -d '{
       "zone": "bakerstreetlabs.local",
       "fqdn": "malware.bakerstreetlabs.local",
       "ip_address": "192.168.1.50"
     }'
```

### Automated Testing

```bash
# Run full integration test suite
python3 test_integration.py

# Test with custom URLs
python3 test_integration.py http://localhost:5001 http://10.43.20.75:9090
```

## 📊 Monitoring

### Service Health

- **Route Injection Service**: http://localhost:5001/api/v1/health
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboard**: http://localhost:3000

### Logs

```bash
# View service logs
docker-compose logs -f route-injection-service

# View all logs
docker-compose logs -f
```

### Redis Cache

```bash
# Connect to Redis
docker exec -it baker-street-route-injection-redis redis-cli

# View active routes
KEYS route:*

# Get route details
GET route:dns_test_bakerstreetlabs_local_192_168_1_100
```

## 🔒 Security

### Authentication
- PAN-OS API uses username/password authentication
- Route injection service uses API key validation
- Redis access is restricted to internal network

### Network Security
- Services communicate over internal Docker network
- PAN-OS API calls use HTTPS (with SSL verification disabled for testing)
- Webhook endpoints are protected by Kong API Gateway

## 🚨 Troubleshooting

### Common Issues

1. **Route Injection Service Not Starting**
   - Check Docker logs: `docker-compose logs route-injection-service`
   - Verify Redis is running: `docker-compose ps redis`
   - Check port conflicts: `netstat -tlnp | grep 5001`

2. **PAN-OS Authentication Failed**
   - Verify firewall IP: `ping 192.168.255.254`
   - Check credentials in environment variables
   - Verify PAN-OS API is enabled

3. **Webhook Not Triggering**
   - Check Kong routing: `curl http://localhost:8000/api/v1/dns/api/health`
   - Verify DNS service is accessible
   - Check webhook URL configuration

4. **Routes Not Appearing in PAN-OS**
   - Check PAN-OS logs for API errors
   - Verify route XML format
   - Check virtual router configuration

### Debug Commands

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs --tail=100 route-injection-service

# Test PAN-OS connectivity
curl -k "https://192.168.255.254/api/?type=keygen&user=admin&password=Paloalto1!"

# Check Redis data
docker exec baker-street-route-injection-redis redis-cli KEYS "*"
```

## 📈 Performance

### Optimization
- Redis caching reduces PAN-OS API calls
- Asynchronous webhook processing
- Connection pooling for PAN-OS API
- Batch route operations

### Scaling
- Multiple route injection service instances
- Redis cluster for high availability
- Load balancing through Kong Gateway

## 🔄 Maintenance

### Regular Tasks
- Monitor route injection logs
- Clean up old routes from Redis
- Update PAN-OS credentials
- Backup route configuration

### Updates
- Update route injection service
- Upgrade PAN-OS integration
- Enhance webhook processing
- Improve error handling

## 📚 Additional Resources

- [PAN-OS API Documentation](https://docs.paloaltonetworks.com/pan-os/10-2/pan-os-panorama-api/pan-os-xml-api)
- [Kong API Gateway](https://docs.konghq.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Compose](https://docs.docker.com/compose/)

---

**Status**: ✅ **FULLY IMPLEMENTED** - Route injection integration is complete and ready for production use.

**Last Updated**: September 9, 2025
**Version**: 1.0.0
