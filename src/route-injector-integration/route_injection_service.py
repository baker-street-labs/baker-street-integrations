#!/usr/bin/env python3
"""
Baker Street Labs - Route Injection Integration Service
Automatically injects routes into PAN-OS when DNS records are created
"""

import os
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import yaml
from urllib3.exceptions import InsecureRequestWarning
import warnings

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

# Redis for caching and session management
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class PANOSRouteManager:
    """Manages PAN-OS route injection operations"""
    
    def __init__(self, firewall_ip: str, username: str, password: str):
        self.firewall_ip = firewall_ip
        self.username = username
        self.password = password
        self.api_key = None
        self.base_url = f"https://{firewall_ip}/api/"
    
    def authenticate(self) -> bool:
        """Generate PAN-OS API key"""
        try:
            logger.info(f"Authenticating with PAN-OS at {self.firewall_ip}")
            
            params = {
                "type": "keygen",
                "user": self.username,
                "password": self.password
            }
            
            response = requests.get(self.base_url, params=params, verify=False, timeout=30)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                api_key = root.findtext('.//key')
                
                if api_key:
                    self.api_key = api_key
                    logger.info("PAN-OS authentication successful")
                    return True
                else:
                    logger.error("API key not found in response")
                    return False
            else:
                logger.error(f"Authentication failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def create_static_route(self, route_name: str, destination: str, nexthop_ip: str, 
                          interface: str = None, metric: int = 10) -> bool:
        """Create a static route in PAN-OS"""
        try:
            if not self.api_key:
                if not self.authenticate():
                    return False
            
            logger.info(f"Creating static route: {route_name} -> {destination} via {nexthop_ip}")
            
            # Create route XML
            route_xml = self._create_route_xml(nexthop_ip, interface, metric, destination)
            
            # Determine XPath based on route type
            if self._is_internal_route(destination):
                xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='default']/routing-table/ip/static-route/entry[@name='{route_name}']"
            else:
                xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='default']/routing-table/ip/static-route/entry[@name='{route_name}']"
            
            params = {
                "type": "config",
                "action": "set",
                "xpath": xpath,
                "element": route_xml,
                "key": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, verify=False, timeout=30)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info(f"Route {route_name} created successfully")
                    return True
                else:
                    logger.error(f"Route creation failed: {status}")
                    return False
            else:
                logger.error(f"Route creation failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating route: {str(e)}")
            return False
    
    def delete_static_route(self, route_name: str) -> bool:
        """Delete a static route from PAN-OS"""
        try:
            if not self.api_key:
                if not self.authenticate():
                    return False
            
            logger.info(f"Deleting static route: {route_name}")
            
            xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='default']/routing-table/ip/static-route/entry[@name='{route_name}']"
            
            params = {
                "type": "config",
                "action": "delete",
                "xpath": xpath,
                "key": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, verify=False, timeout=30)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info(f"Route {route_name} deleted successfully")
                    return True
                else:
                    logger.error(f"Route deletion failed: {status}")
                    return False
            else:
                logger.error(f"Route deletion failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting route: {str(e)}")
            return False
    
    def commit_configuration(self) -> bool:
        """Commit PAN-OS configuration changes"""
        try:
            if not self.api_key:
                if not self.authenticate():
                    return False
            
            logger.info("Committing PAN-OS configuration")
            
            params = {
                "type": "commit",
                "key": self.api_key,
                "cmd": "<commit></commit>"
            }
            
            response = requests.get(self.base_url, params=params, verify=False, timeout=60)
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                status = root.get('status')
                
                if status == 'success':
                    logger.info("Configuration committed successfully")
                    return True
                else:
                    logger.error(f"Commit failed: {status}")
                    return False
            else:
                logger.error(f"Commit failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error committing configuration: {str(e)}")
            return False
    
    def _create_route_xml(self, nexthop_ip: str, interface: str, metric: int, destination: str) -> str:
        """Create XML for static route configuration"""
        route_xml = f"""<nexthop>
  <ip-address>{nexthop_ip}</ip-address>
</nexthop>
<bfd>
  <profile>None</profile>
</bfd>"""
        
        if interface:
            route_xml += f"""
<interface>{interface}</interface>"""
        
        route_xml += f"""
<metric>{metric}</metric>
<destination>{destination}</destination>
<route-table>
  <unicast/>
</route-table>"""
        
        return route_xml
    
    def _is_internal_route(self, destination: str) -> bool:
        """Determine if route is for internal network"""
        internal_networks = [
            "10.0.0.0/8",
            "172.16.0.0/12", 
            "192.168.0.0/16"
        ]
        
        # Simple check for private IP ranges
        if destination.startswith(("10.", "172.", "192.168.")):
            return True
        return False

class DNSWebhookHandler:
    """Handles DNS webhook events and triggers route injection"""
    
    def __init__(self, panos_manager: PANOSRouteManager):
        self.panos_manager = panos_manager
        self.cyber_range_networks = [
            "10.0.0.0/8",
            "172.20.0.0/16",
            "192.168.0.0/16"
        ]
    
    def handle_dns_record_created(self, zone: str, fqdn: str, ip_address: str, ttl: int = 60) -> Dict[str, Any]:
        """Handle DNS record creation and trigger route injection"""
        try:
            logger.info(f"DNS record created: {fqdn} -> {ip_address}")
            
            # Check if IP is in cyber range
            if not self._is_cyber_range_ip(ip_address):
                logger.info(f"IP {ip_address} is not in cyber range, skipping route injection")
                return {
                    "success": True,
                    "message": "DNS record created, no route injection needed",
                    "route_injected": False
                }
            
            # Generate route name
            route_name = f"dns_{fqdn.replace('.', '_')}_{ip_address.replace('.', '_')}"
            
            # Create static route
            success = self.panos_manager.create_static_route(
                route_name=route_name,
                destination=ip_address,
                nexthop_ip="172.21.55.20",  # Default next hop for cyber range
                interface="ethernet1/1",     # Default interface
                metric=10
            )
            
            if success:
                # Commit configuration
                commit_success = self.panos_manager.commit_configuration()
                
                if commit_success:
                    # Store route info in Redis
                    route_info = {
                        "route_name": route_name,
                        "fqdn": fqdn,
                        "ip_address": ip_address,
                        "zone": zone,
                        "created_at": datetime.now().isoformat(),
                        "status": "active"
                    }
                    
                    redis_client.setex(f"route:{route_name}", 86400, json.dumps(route_info))
                    
                    logger.info(f"Route injection successful for {fqdn} -> {ip_address}")
                    return {
                        "success": True,
                        "message": f"DNS record created and route injected for {fqdn}",
                        "route_injected": True,
                        "route_name": route_name
                    }
                else:
                    logger.error("Route created but commit failed")
                    return {
                        "success": False,
                        "message": "Route created but commit failed",
                        "route_injected": False
                    }
            else:
                logger.error("Route injection failed")
                return {
                    "success": False,
                    "message": "Route injection failed",
                    "route_injected": False
                }
                
        except Exception as e:
            logger.error(f"Error handling DNS record creation: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_injected": False
            }
    
    def handle_dns_record_deleted(self, zone: str, fqdn: str, ip_address: str) -> Dict[str, Any]:
        """Handle DNS record deletion and remove route"""
        try:
            logger.info(f"DNS record deleted: {fqdn} -> {ip_address}")
            
            # Generate route name
            route_name = f"dns_{fqdn.replace('.', '_')}_{ip_address.replace('.', '_')}"
            
            # Check if route exists in Redis
            route_info = redis_client.get(f"route:{route_name}")
            if not route_info:
                logger.info(f"Route {route_name} not found in cache")
                return {
                    "success": True,
                    "message": "Route not found in cache",
                    "route_removed": False
                }
            
            # Delete static route
            success = self.panos_manager.delete_static_route(route_name)
            
            if success:
                # Commit configuration
                commit_success = self.panos_manager.commit_configuration()
                
                if commit_success:
                    # Remove from Redis
                    redis_client.delete(f"route:{route_name}")
                    
                    logger.info(f"Route removal successful for {fqdn} -> {ip_address}")
                    return {
                        "success": True,
                        "message": f"DNS record deleted and route removed for {fqdn}",
                        "route_removed": True,
                        "route_name": route_name
                    }
                else:
                    logger.error("Route deleted but commit failed")
                    return {
                        "success": False,
                        "message": "Route deleted but commit failed",
                        "route_removed": False
                    }
            else:
                logger.error("Route removal failed")
                return {
                    "success": False,
                    "message": "Route removal failed",
                    "route_removed": False
                }
                
        except Exception as e:
            logger.error(f"Error handling DNS record deletion: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_removed": False
            }
    
    def _is_cyber_range_ip(self, ip_address: str) -> bool:
        """Check if IP address is in cyber range networks"""
        try:
            # Simple check for private IP ranges
            if ip_address.startswith(("10.", "172.", "192.168.")):
                return True
            return False
        except:
            return False

# Initialize services
panos_manager = PANOSRouteManager(
    firewall_ip="192.168.255.254",
    username="admin", 
    password="Paloalto1!"
)

webhook_handler = DNSWebhookHandler(panos_manager)

# Flask API endpoints
@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "route-injection-service",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/webhook/dns-record-created', methods=['POST'])
def dns_record_created():
    """Webhook endpoint for DNS record creation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['zone', 'fqdn', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = webhook_handler.handle_dns_record_created(
            zone=data['zone'],
            fqdn=data['fqdn'],
            ip_address=data['ip_address'],
            ttl=data.get('ttl', 60)
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error in DNS record created webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/webhook/dns-record-deleted', methods=['POST'])
def dns_record_deleted():
    """Webhook endpoint for DNS record deletion"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['zone', 'fqdn', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = webhook_handler.handle_dns_record_deleted(
            zone=data['zone'],
            fqdn=data['fqdn'],
            ip_address=data['ip_address']
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Error in DNS record deleted webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/routes', methods=['GET'])
def get_routes():
    """Get all active routes"""
    try:
        routes = []
        for key in redis_client.scan_iter("route:*"):
            route_info = json.loads(redis_client.get(key))
            routes.append(route_info)
        
        return jsonify({
            "success": True,
            "routes": routes,
            "count": len(routes)
        })
        
    except Exception as e:
        logger.error(f"Error getting routes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/routes/<route_name>', methods=['DELETE'])
def delete_route(route_name):
    """Manually delete a route"""
    try:
        # Get route info from Redis
        route_info = redis_client.get(f"route:{route_name}")
        if not route_info:
            return jsonify({"error": "Route not found"}), 404
        
        route_data = json.loads(route_info)
        
        # Delete from PAN-OS
        success = panos_manager.delete_static_route(route_name)
        
        if success:
            # Commit configuration
            commit_success = panos_manager.commit_configuration()
            
            if commit_success:
                # Remove from Redis
                redis_client.delete(f"route:{route_name}")
                
                return jsonify({
                    "success": True,
                    "message": f"Route {route_name} deleted successfully"
                })
            else:
                return jsonify({"error": "Route deleted but commit failed"}), 500
        else:
            return jsonify({"error": "Route deletion failed"}), 500
            
    except Exception as e:
        logger.error(f"Error deleting route: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Baker Street Labs Route Injection Service")
    app.run(host='0.0.0.0', port=5001, debug=True)
