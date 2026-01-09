#!/usr/bin/env python3
"""
Baker Street Labs - DNS Webhook Integration
Enhances DNS API to trigger route injection webhooks
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DNSWebhookTrigger:
    """Triggers webhooks when DNS records are created or deleted"""
    
    def __init__(self, route_injection_service_url: str = "http://localhost:5001"):
        self.route_injection_service_url = route_injection_service_url
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    def trigger_route_injection(self, zone: str, fqdn: str, ip_address: str, ttl: int = 60) -> Dict[str, Any]:
        """Trigger route injection when DNS record is created"""
        try:
            logger.info(f"Triggering route injection for {fqdn} -> {ip_address}")
            
            webhook_data = {
                "zone": zone,
                "fqdn": fqdn,
                "ip_address": ip_address,
                "ttl": ttl,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send webhook to route injection service
            response = requests.post(
                f"{self.route_injection_service_url}/api/v1/webhook/dns-record-created",
                json=webhook_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Route injection webhook successful: {result}")
                return result
            else:
                logger.error(f"Route injection webhook failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Webhook failed: {response.status_code}",
                    "route_injected": False
                }
                
        except Exception as e:
            logger.error(f"Error triggering route injection: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_injected": False
            }
    
    def trigger_route_removal(self, zone: str, fqdn: str, ip_address: str) -> Dict[str, Any]:
        """Trigger route removal when DNS record is deleted"""
        try:
            logger.info(f"Triggering route removal for {fqdn} -> {ip_address}")
            
            webhook_data = {
                "zone": zone,
                "fqdn": fqdn,
                "ip_address": ip_address,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send webhook to route injection service
            response = requests.post(
                f"{self.route_injection_service_url}/api/v1/webhook/dns-record-deleted",
                json=webhook_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Route removal webhook successful: {result}")
                return result
            else:
                logger.error(f"Route removal webhook failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Webhook failed: {response.status_code}",
                    "route_removed": False
                }
                
        except Exception as e:
            logger.error(f"Error triggering route removal: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "route_removed": False
            }
    
    def is_cyber_range_ip(self, ip_address: str) -> bool:
        """Check if IP address is in cyber range networks"""
        try:
            # Check for private IP ranges
            if ip_address.startswith(("10.", "172.", "192.168.")):
                return True
            return False
        except:
            return False

def enhance_dns_api_with_webhooks(dns_api_file_path: str):
    """Enhance existing DNS API with webhook triggers"""
    
    # Read the existing DNS API file
    with open(dns_api_file_path, 'r') as f:
        dns_api_content = f.read()
    
    # Add webhook trigger import
    webhook_import = """
# Route injection webhook integration
from dns_webhook_integration import DNSWebhookTrigger
webhook_trigger = DNSWebhookTrigger()
"""
    
    # Add webhook trigger to add_record method
    webhook_enhancement = """
            # NEW: Trigger route injection webhook
            if webhook_trigger.is_cyber_range_ip(ip_address):
                webhook_result = webhook_trigger.trigger_route_injection(
                    zone=zone_name,
                    fqdn=f"{record_name}.{zone_name}",
                    ip_address=ip_address,
                    ttl=60
                )
                logger.info(f"Route injection webhook result: {webhook_result}")
            else:
                logger.info(f"IP {ip_address} is not in cyber range, skipping route injection")
"""
    
    # Add webhook trigger to delete_record method
    webhook_removal_enhancement = """
            # NEW: Trigger route removal webhook
            if webhook_trigger.is_cyber_range_ip(ip_address):
                webhook_result = webhook_trigger.trigger_route_removal(
                    zone=zone_name,
                    fqdn=f"{record_name}.{zone_name}",
                    ip_address=ip_address
                )
                logger.info(f"Route removal webhook result: {webhook_result}")
            else:
                logger.info(f"IP {ip_address} is not in cyber range, skipping route removal")
"""
    
    # Insert webhook import after other imports
    if "from dns_webhook_integration import DNSWebhookTrigger" not in dns_api_content:
        dns_api_content = dns_api_content.replace(
            "import dns.update",
            "import dns.update" + webhook_import
        )
    
    # Add webhook trigger to add_record method
    if "webhook_trigger.trigger_route_injection" not in dns_api_content:
        dns_api_content = dns_api_content.replace(
            "return {\n                \"success\": True,\n                \"record\": {\n                    \"name\": record_name,\n                    \"type\": \"A\",\n                    \"value\": ip_address,\n                    \"zone\": zone_name\n                },\n                \"message\": f\"Record {record_name}.{zone_name} added successfully\"\n            }",
            "return {\n                \"success\": True,\n                \"record\": {\n                    \"name\": record_name,\n                    \"type\": \"A\",\n                    \"value\": ip_address,\n                    \"zone\": zone_name\n                },\n                \"message\": f\"Record {record_name}.{zone_name} added successfully\"\n            }" + webhook_enhancement
        )
    
    # Add webhook trigger to delete_record method
    if "webhook_trigger.trigger_route_removal" not in dns_api_content:
        dns_api_content = dns_api_content.replace(
            "return {\n                \"success\": True,\n                \"message\": f\"Record {record_name}.{zone_name} deleted successfully\"\n            }",
            "return {\n                \"success\": True,\n                \"message\": f\"Record {record_name}.{zone_name} deleted successfully\"\n            }" + webhook_removal_enhancement
        )
    
    # Write enhanced DNS API
    enhanced_file_path = dns_api_file_path.replace('.py', '_enhanced.py')
    with open(enhanced_file_path, 'w') as f:
        f.write(dns_api_content)
    
    logger.info(f"Enhanced DNS API saved to: {enhanced_file_path}")
    return enhanced_file_path

if __name__ == '__main__':
    # Example usage
    webhook_trigger = DNSWebhookTrigger()
    
    # Test route injection
    result = webhook_trigger.trigger_route_injection(
        zone="bakerstreetlabs.local",
        fqdn="test.bakerstreetlabs.local",
        ip_address="192.168.1.100"
    )
    
    print(f"Route injection result: {result}")
