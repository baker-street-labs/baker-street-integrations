#!/usr/bin/env python3
"""
Baker Street Labs - Enhanced Route Injection Service
Automatically injects routes into master router when DNS records are created
"""

import os
import json
import logging
import requests
import xml.etree.ElementTree as ET
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
from urllib3.exceptions import InsecureRequestWarning
import warnings
import ipaddress
import hashlib
import hmac
import time

# Suppress SSL warnings for testing
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class ConfigManager:
    """Manages configuration for route injection service"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file loading fails"""
        return {
            "master_router": {
                "primary": {
                    "ip_address": "192.168.255.254",
                    "username": "admin",
                    "password": "Paloalto1!",
                    "api_port": 443,
                    "timeout": 30,
                    "virtual_router": "default",
                    "interface": "ethernet1/1",
                    "next_hop": "172.21.55.20",
                    "metric": 10
                }
            },
            "dns_api": {
                "mothership": {
                    "base_url": "http://10.43.20.75:9090",
                    "username": "admin",
                    "password": "admin",
                    "timeout": 30
                }
            },
            "route_injection": {
                "cyber_range_networks": ["10.0.0.0/8", "172.20.0.0/16", "192.168.0.0/16"],
                "auto_commit": True,
                "commit_timeout": 60
            },
            "redis": {
                "host": "localhost",
                "port": 6380,
                "db": 0,
                "timeout": 30
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

class MasterRouterManager:
    """Manages master router operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.primary_router = self.config.get('master_router.primary')
        self.backup_router = self.config.get('master_router.backup')
        self.api_keys = {}
    
    def get_api_key(self, router_config: Dict[str, Any]) -> Optional[str]:
        """Get or generate API key for router"""
        router_ip = router_config['ip_address']
        
        # Check if we have a cached API key
        if router_ip in self.api_keys:
            return self.api_keys[router_ip]
        
        try:
            logger.info(f"Generating API key for master router {router_ip}")
            
            url = f"https://{router_ip}:{router_config['api_port']}/api/"
            params = {
                "type": "keygen",
                "user": router_config['username'],
                "password": router_config['password']
            }
            
            response = requests.get(
                url, 
                params=params, 
                verify=False, 
                timeout=router_config['timeout']
            )
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                api_key = root.findtext('.//key')
                
                if api_key:
                    self.api_keys[router_ip] = api_key
                    logger.info(f"API key generated for {router_ip}")
                    return api_key
                else:
                    logger.error(f"API key not found in response from {router_ip}")
                    return None
            else:
                logger.error(f"API key generation failed for {router_ip}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating API key for {router_ip}: {str(e)}")
            return None
    
    def create_static_route(self, route_name: str, destination: str, 
                          router_config: Dict[str, Any] = None) -> bool:
        """Create static route on master router"""
        if router_config is None:
            router_config = self.primary_router
        
        try:
            api_key = self.get_api_key(router_config)
            if not api_key:
                logger.error(f"Failed to get API key for {router_config['ip_address']}")
                return False
            
            logger.info(f"Creating route {route_name} -> {destination} on {router_config['ip_address']}")
            
            # Create route XML
            route_xml = self._create_route_xml(router_config, destination)
            
            # Determine XPath
            xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='{router_config['virtual_router']}']/routing-table/ip/static-route/entry[@name='{route_name}']"
            
            url = f"https://{router_config['ip_address']}:{router_config['api_port']}/api/"
            params = {
                "type": "config",
                "action": "set",
                "xpath": xpath,
                "element": route_xml,
                "key": api_key
            }
            
            response = requests.get(url, params=params, verify=False, timeout=router_config['timeout'])
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info(f"Route {route_name} created successfully on {router_config['ip_address']}")
                    return True
                else:
                    logger.error(f"Route creation failed on {router_config['ip_address']}: {status}")
                    # Log the full response for debugging
                    logger.error(f"Response: {response.text}")
                    return False
            else:
                logger.error(f"Route creation failed on {router_config['ip_address']}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating route on {router_config['ip_address']}: {str(e)}")
            return False
    
    def delete_static_route(self, route_name: str, router_config: Dict[str, Any] = None) -> bool:
        """Delete static route from master router"""
        if router_config is None:
            router_config = self.primary_router
        
        try:
            api_key = self.get_api_key(router_config)
            if not api_key:
                logger.error(f"Failed to get API key for {router_config['ip_address']}")
                return False
            
            logger.info(f"Deleting route {route_name} from {router_config['ip_address']}")
            
            xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='{router_config['virtual_router']}']/routing-table/ip/static-route/entry[@name='{route_name}']"
            
            url = f"https://{router_config['ip_address']}:{router_config['api_port']}/api/"
            params = {
                "type": "config",
                "action": "delete",
                "xpath": xpath,
                "key": api_key
            }
            
            response = requests.get(url, params=params, verify=False, timeout=router_config['timeout'])
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info(f"Route {route_name} deleted successfully from {router_config['ip_address']}")
                    return True
                else:
                    logger.error(f"Route deletion failed on {router_config['ip_address']}: {status}")
                    return False
            else:
                logger.error(f"Route deletion failed on {router_config['ip_address']}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting route from {router_config['ip_address']}: {str(e)}")
            return False
    
    def commit_configuration(self, router_config: Dict[str, Any] = None) -> bool:
        """Commit configuration on master router"""
        if router_config is None:
            router_config = self.primary_router
        
        try:
            api_key = self.get_api_key(router_config)
            if not api_key:
                logger.error(f"Failed to get API key for {router_config['ip_address']}")
                return False
            
            logger.info(f"Committing configuration on {router_config['ip_address']}")
            
            url = f"https://{router_config['ip_address']}:{router_config['api_port']}/api/"
            params = {
                "type": "commit",
                "key": api_key,
                "cmd": "<commit></commit>"
            }
            
            response = requests.get(url, params=params, verify=False, timeout=router_config['timeout'])
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info(f"Configuration committed successfully on {router_config['ip_address']}")
                    return True
                else:
                    logger.error(f"Commit failed on {router_config['ip_address']}: {status}")
                    return False
            else:
                logger.error(f"Commit failed on {router_config['ip_address']}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error committing configuration on {router_config['ip_address']}: {str(e)}")
            return False
    
    def _create_route_xml(self, router_config: Dict[str, Any], destination: str) -> str:
        """Create XML for static route configuration"""
        route_xml = f"""<nexthop>
  <ip-address>{router_config['next_hop']}</ip-address>
</nexthop>
<bfd>
  <profile>None</profile>
</bfd>
<interface>{router_config['interface']}</interface>
<metric>{router_config['metric']}</metric>
<destination>{destination}</destination>
<route-table>
  <unicast/>
</route-table>"""
        
        return route_xml

class DNSAPIManager:
    """Manages DNS API operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.mothership_config = self.config.get('dns_api.mothership')
        self.kong_config = self.config.get('dns_api.kong')
        self.session = requests.Session()
        self.jwt_token = None
    
    def authenticate_mothership(self) -> bool:
        """Authenticate with mothership DNS tool"""
        try:
            url = f"{self.mothership_config['base_url']}/api/auth/login"
            data = {
                "username": self.mothership_config['username'],
                "password": self.mothership_config['password']
            }
            
            response = self.session.post(url, data=data, timeout=self.mothership_config['timeout'])
            
            if response.status_code == 200:
                result = response.json()
                if 'access_token' in result:
                    self.jwt_token = result['access_token']
                    self.session.headers.update({'Authorization': f'Bearer {self.jwt_token}'})
                    logger.info("Successfully authenticated with mothership DNS tool")
                    return True
                else:
                    logger.error("No access token in mothership response")
                    return False
            else:
                logger.error(f"Mothership authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with mothership: {str(e)}")
            return False
    
    def add_dns_record(self, zone: str, fqdn: str, ip_address: str, ttl: int = 60) -> Dict[str, Any]:
        """Add DNS record via mothership API"""
        try:
            if not self.jwt_token:
                if not self.authenticate_mothership():
                    return {"success": False, "error": "Authentication failed"}
            
            url = f"{self.mothership_config['base_url']}/api/dns/records"
            params = {
                "zone": zone,
                "fqdn": fqdn,
                "ip_address": ip_address,
                "ttl": ttl
            }
            
            response = self.session.post(url, params=params, timeout=self.mothership_config['timeout'])
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"DNS record added: {fqdn} -> {ip_address}")
                return {"success": True, "result": result}
            else:
                logger.error(f"DNS record addition failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error adding DNS record: {str(e)}")
            return {"success": False, "error": str(e)}

class RouteInjectionService:
    """Main route injection service"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_manager = ConfigManager(config_file)
        self.router_manager = MasterRouterManager(self.config_manager)
        self.dns_manager = DNSAPIManager(self.config_manager)
        self.redis_client = self._init_redis()
        self.cyber_range_networks = self.config_manager.get('route_injection.cyber_range_networks', [])
    
    def _init_redis(self) -> redis.Redis:
        """Initialize Redis client"""
        redis_config = self.config_manager.get('redis', {})
        return redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6380),
            db=redis_config.get('db', 0),
            decode_responses=True,
            socket_timeout=redis_config.get('timeout', 30)
        )
    
    def is_cyber_range_ip(self, ip_address: str) -> bool:
        """Check if IP address is in cyber range networks"""
        try:
            ip = ipaddress.ip_address(ip_address)
            for network_str in self.cyber_range_networks:
                network = ipaddress.ip_network(network_str, strict=False)
                if ip in network:
                    return True
            return False
        except:
            return False
    
    def generate_route_name(self, fqdn: str, ip_address: str, zone: str = None) -> str:
        """Generate route name based on configuration"""
        naming_config = self.config_manager.get('route_injection.route_naming', {})
        
        parts = [naming_config.get('prefix', 'dns')]
        
        if naming_config.get('include_zone', True) and zone:
            parts.append(zone.replace('.', '_'))
        
        # Add FQDN (sanitized)
        fqdn_clean = fqdn.replace('.', '_').replace('-', '_')
        parts.append(fqdn_clean)
        
        # Add IP (sanitized)
        ip_clean = ip_address.replace('.', '_')
        parts.append(ip_clean)
        
        if naming_config.get('include_timestamp', False):
            parts.append(str(int(time.time())))
        
        separator = naming_config.get('separator', '_')
        return separator.join(parts)
    
    def inject_route_for_dns_record(self, zone: str, fqdn: str, ip_address: str, ttl: int = 60) -> Dict[str, Any]:
        """Complete workflow: Add DNS record and inject route"""
        try:
            logger.info(f"Processing DNS record: {fqdn} -> {ip_address}")
            
            # Check if IP is in cyber range
            if not self.is_cyber_range_ip(ip_address):
                logger.info(f"IP {ip_address} is not in cyber range, skipping route injection")
                return {
                    "success": True,
                    "message": "DNS record processed, no route injection needed",
                    "route_injected": False
                }
            
            # Add DNS record
            dns_result = self.dns_manager.add_dns_record(zone, fqdn, ip_address, ttl)
            if not dns_result.get('success'):
                return {
                    "success": False,
                    "message": f"DNS record addition failed: {dns_result.get('error')}",
                    "route_injected": False
                }
            
            # Generate route name
            route_name = self.generate_route_name(fqdn, ip_address, zone)
            
            # Create route on primary router
            route_created = self.router_manager.create_static_route(route_name, ip_address)
            
            if route_created:
                # Commit configuration if auto-commit is enabled
                if self.config_manager.get('route_injection.auto_commit', True):
                    commit_success = self.router_manager.commit_configuration()
                    if not commit_success:
                        logger.warning("Route created but commit failed")
                
                # Store route info in Redis
                route_info = {
                    "route_name": route_name,
                    "fqdn": fqdn,
                    "ip_address": ip_address,
                    "zone": zone,
                    "created_at": datetime.now().isoformat(),
                    "status": "active",
                    "router": "primary"
                }
                
                self.redis_client.setex(
                    f"route:{route_name}", 
                    self.config_manager.get('redis.ttl_seconds', 86400),
                    json.dumps(route_info)
                )
                
                logger.info(f"Route injection successful: {route_name}")
                return {
                    "success": True,
                    "message": f"DNS record added and route injected: {fqdn}",
                    "route_injected": True,
                    "route_name": route_name,
                    "dns_result": dns_result
                }
            else:
                logger.error("Route injection failed")
                return {
                    "success": False,
                    "message": "Route injection failed",
                    "route_injected": False,
                    "dns_result": dns_result
                }
                
        except Exception as e:
            logger.error(f"Error in DNS record processing: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_injected": False
            }
    
    def remove_route_for_dns_record(self, zone: str, fqdn: str, ip_address: str) -> Dict[str, Any]:
        """Remove route when DNS record is deleted"""
        try:
            logger.info(f"Removing route for DNS record: {fqdn} -> {ip_address}")
            
            # Generate route name
            route_name = self.generate_route_name(fqdn, ip_address, zone)
            
            # Check if route exists in Redis
            route_info = self.redis_client.get(f"route:{route_name}")
            if not route_info:
                logger.info(f"Route {route_name} not found in cache")
                return {
                    "success": True,
                    "message": "Route not found in cache",
                    "route_removed": False
                }
            
            # Delete route from primary router
            route_deleted = self.router_manager.delete_static_route(route_name)
            
            if route_deleted:
                # Commit configuration if auto-commit is enabled
                if self.config_manager.get('route_injection.auto_commit', True):
                    commit_success = self.router_manager.commit_configuration()
                    if not commit_success:
                        logger.warning("Route deleted but commit failed")
                
                # Remove from Redis
                self.redis_client.delete(f"route:{route_name}")
                
                logger.info(f"Route removal successful: {route_name}")
                return {
                    "success": True,
                    "message": f"Route removed for {fqdn}",
                    "route_removed": True,
                    "route_name": route_name
                }
            else:
                logger.error("Route removal failed")
                return {
                    "success": False,
                    "message": "Route removal failed",
                    "route_removed": False
                }
                
        except Exception as e:
            logger.error(f"Error removing route: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_removed": False
            }

# Initialize services
config_manager = ConfigManager()
route_service = RouteInjectionService()

# Flask API endpoints
@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "enhanced-route-injection-service",
        "timestamp": datetime.now().isoformat(),
        "config_loaded": config_manager.config is not None
    })

@app.route('/api/v1/dns-record', methods=['POST'])
def add_dns_record_with_route():
    """Add DNS record and inject route"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['zone', 'fqdn', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = route_service.inject_route_for_dns_record(
            zone=data['zone'],
            fqdn=data['fqdn'],
            ip_address=data['ip_address'],
            ttl=data.get('ttl', 60)
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error in DNS record endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/dns-record', methods=['DELETE'])
def remove_dns_record_with_route():
    """Remove DNS record and delete route"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['zone', 'fqdn', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = route_service.remove_route_for_dns_record(
            zone=data['zone'],
            fqdn=data['fqdn'],
            ip_address=data['ip_address']
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error in DNS record removal endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/routes', methods=['GET'])
def get_routes():
    """Get all active routes"""
    try:
        routes = []
        for key in route_service.redis_client.scan_iter("route:*"):
            route_info = json.loads(route_service.redis_client.get(key))
            routes.append(route_info)
        
        return jsonify({
            "success": True,
            "routes": routes,
            "count": len(routes)
        })
        
    except Exception as e:
        logger.error(f"Error getting routes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/config', methods=['GET'])
def get_config():
    """Get current configuration (sanitized)"""
    try:
        # Return sanitized config (remove passwords)
        sanitized_config = config_manager.config.copy()
        
        # Remove sensitive information
        if 'master_router' in sanitized_config:
            for router in sanitized_config['master_router'].values():
                if 'password' in router:
                    router['password'] = '***REDACTED***'
        
        if 'dns_api' in sanitized_config:
            for api in sanitized_config['dns_api'].values():
                if 'password' in api:
                    api['password'] = '***REDACTED***'
        
        return jsonify({
            "success": True,
            "config": sanitized_config
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Baker Street Labs Enhanced Route Injection Service")
    app.run(host='0.0.0.0', port=5001, debug=True)
