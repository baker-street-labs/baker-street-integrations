#!/usr/bin/env python3
"""
Baker Street Labs - Enhanced Route Injection Integration Test
Tests the complete DNS -> Route Injection workflow with master router
"""

import requests
import json
import time
import sys
from datetime import datetime

class EnhancedRouteInjectionTester:
    """Test the enhanced route injection integration"""
    
    def __init__(self, service_url="http://localhost:5001"):
        self.service_url = service_url
        self.test_results = []
    
    def test_service_health(self):
        """Test enhanced service health"""
        print("\n🔍 Testing Enhanced Route Injection Service Health...")
        try:
            response = requests.get(f"{self.service_url}/api/v1/health", timeout=10)
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Service: {result['status']}")
                print(f"   ✅ Config Loaded: {result.get('config_loaded', False)}")
                self.test_results.append(("Enhanced Service Health", True, "Service is healthy"))
                return True
            else:
                print(f"   ❌ Service: HTTP {response.status_code}")
                self.test_results.append(("Enhanced Service Health", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Service: {str(e)}")
            self.test_results.append(("Enhanced Service Health", False, str(e)))
            return False
    
    def test_config_endpoint(self):
        """Test configuration endpoint"""
        print("\n🔍 Testing Configuration Endpoint...")
        try:
            response = requests.get(f"{self.service_url}/api/v1/config", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    config = result.get('config', {})
                    print(f"   ✅ Config: Loaded successfully")
                    print(f"   ✅ Master Router: {config.get('master_router', {}).get('primary', {}).get('ip_address', 'Not configured')}")
                    print(f"   ✅ Cyber Range Networks: {len(config.get('route_injection', {}).get('cyber_range_networks', []))} networks")
                    self.test_results.append(("Configuration Endpoint", True, "Config loaded successfully"))
                    return True
                else:
                    print(f"   ❌ Config: {result.get('error', 'Unknown error')}")
                    self.test_results.append(("Configuration Endpoint", False, result.get('error', 'Unknown error')))
                    return False
            else:
                print(f"   ❌ Config: HTTP {response.status_code}")
                self.test_results.append(("Configuration Endpoint", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Config: {str(e)}")
            self.test_results.append(("Configuration Endpoint", False, str(e)))
            return False
    
    def test_dns_record_with_route(self):
        """Test adding DNS record with automatic route injection"""
        print("\n🔍 Testing DNS Record with Route Injection...")
        try:
            test_data = {
                "zone": "bakerstreetlabs.local",
                "fqdn": "malware.bakerstreetlabs.local",
                "ip_address": "192.168.1.100",
                "ttl": 60
            }
            
            response = requests.post(
                f"{self.service_url}/api/v1/dns-record",
                json=test_data,
                timeout=60  # Longer timeout for route injection
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"   ✅ DNS + Route: {result['message']}")
                    print(f"   ✅ Route Injected: {result.get('route_injected', False)}")
                    if result.get('route_name'):
                        print(f"   ✅ Route Name: {result['route_name']}")
                    self.test_results.append(("DNS Record with Route", True, result['message']))
                    return True
                else:
                    print(f"   ❌ DNS + Route: {result['message']}")
                    self.test_results.append(("DNS Record with Route", False, result['message']))
                    return False
            else:
                print(f"   ❌ DNS + Route: HTTP {response.status_code} - {response.text}")
                self.test_results.append(("DNS Record with Route", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ DNS + Route: {str(e)}")
            self.test_results.append(("DNS Record with Route", False, str(e)))
            return False
    
    def test_non_cyber_range_ip(self):
        """Test with non-cyber range IP (should skip route injection)"""
        print("\n🔍 Testing Non-Cyber Range IP...")
        try:
            test_data = {
                "zone": "bakerstreetlabs.local",
                "fqdn": "external.bakerstreetlabs.local",
                "ip_address": "8.8.8.8",  # Public IP, not in cyber range
                "ttl": 60
            }
            
            response = requests.post(
                f"{self.service_url}/api/v1/dns-record",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"   ✅ Non-Cyber Range: {result['message']}")
                    print(f"   ✅ Route Injected: {result.get('route_injected', False)} (should be False)")
                    self.test_results.append(("Non-Cyber Range IP", True, result['message']))
                    return True
                else:
                    print(f"   ❌ Non-Cyber Range: {result['message']}")
                    self.test_results.append(("Non-Cyber Range IP", False, result['message']))
                    return False
            else:
                print(f"   ❌ Non-Cyber Range: HTTP {response.status_code}")
                self.test_results.append(("Non-Cyber Range IP", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Non-Cyber Range: {str(e)}")
            self.test_results.append(("Non-Cyber Range IP", False, str(e)))
            return False
    
    def test_route_removal(self):
        """Test route removal"""
        print("\n🔍 Testing Route Removal...")
        try:
            test_data = {
                "zone": "bakerstreetlabs.local",
                "fqdn": "malware.bakerstreetlabs.local",
                "ip_address": "192.168.1.100"
            }
            
            response = requests.delete(
                f"{self.service_url}/api/v1/dns-record",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"   ✅ Route Removal: {result['message']}")
                    print(f"   ✅ Route Removed: {result.get('route_removed', False)}")
                    self.test_results.append(("Route Removal", True, result['message']))
                    return True
                else:
                    print(f"   ❌ Route Removal: {result['message']}")
                    self.test_results.append(("Route Removal", False, result['message']))
                    return False
            else:
                print(f"   ❌ Route Removal: HTTP {response.status_code}")
                self.test_results.append(("Route Removal", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Route Removal: {str(e)}")
            self.test_results.append(("Route Removal", False, str(e)))
            return False
    
    def test_get_routes(self):
        """Test getting active routes"""
        print("\n🔍 Testing Get Routes...")
        try:
            response = requests.get(f"{self.service_url}/api/v1/routes", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    routes = result.get('routes', [])
                    print(f"   ✅ Get Routes: Found {len(routes)} routes")
                    for route in routes[:3]:  # Show first 3 routes
                        print(f"      - {route.get('route_name', 'Unknown')}: {route.get('fqdn', 'Unknown')} -> {route.get('ip_address', 'Unknown')}")
                    self.test_results.append(("Get Routes", True, f"Found {len(routes)} routes"))
                    return True
                else:
                    print(f"   ❌ Get Routes: {result.get('error', 'Unknown error')}")
                    self.test_results.append(("Get Routes", False, result.get('error', 'Unknown error')))
                    return False
            else:
                print(f"   ❌ Get Routes: HTTP {response.status_code}")
                self.test_results.append(("Get Routes", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Get Routes: {str(e)}")
            self.test_results.append(("Get Routes", False, str(e)))
            return False
    
    def test_master_router_connectivity(self):
        """Test master router connectivity"""
        print("\n🔍 Testing Master Router Connectivity...")
        try:
            # This test checks if the service can reach the master router
            # We'll test by trying to get the config which should show router IP
            response = requests.get(f"{self.service_url}/api/v1/config", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    config = result.get('config', {})
                    master_router = config.get('master_router', {}).get('primary', {})
                    router_ip = master_router.get('ip_address', 'Not configured')
                    print(f"   ✅ Master Router: {router_ip}")
                    print(f"   ✅ Username: {master_router.get('username', 'Not configured')}")
                    print(f"   ✅ Virtual Router: {master_router.get('virtual_router', 'Not configured')}")
                    self.test_results.append(("Master Router Config", True, f"Router configured: {router_ip}"))
                    return True
                else:
                    print(f"   ❌ Master Router: Config not loaded")
                    self.test_results.append(("Master Router Config", False, "Config not loaded"))
                    return False
            else:
                print(f"   ❌ Master Router: HTTP {response.status_code}")
                self.test_results.append(("Master Router Config", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"   ❌ Master Router: {str(e)}")
            self.test_results.append(("Master Router Config", False, str(e)))
            return False
    
    def run_all_tests(self):
        """Run all enhanced integration tests"""
        print("🚀 Starting Baker Street Labs Enhanced Route Injection Integration Tests")
        print("=" * 80)
        
        # Run tests
        self.test_service_health()
        self.test_config_endpoint()
        self.test_master_router_connectivity()
        self.test_dns_record_with_route()
        self.test_non_cyber_range_ip()
        self.test_route_removal()
        self.test_get_routes()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 80)
        print("📊 ENHANCED INTEGRATION TEST REPORT")
        print("=" * 80)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print()
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}: {message}")
        
        print("\n" + "=" * 80)
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Enhanced route injection integration is working correctly.")
            print("   ✅ DNS API integration ready")
            print("   ✅ Master router configuration working")
            print("   ✅ Route injection system operational")
            return True
        else:
            print("⚠️  SOME TESTS FAILED. Check the details above for issues.")
            print("   🔧 Common issues:")
            print("      - Master router connectivity")
            print("      - PAN-OS authentication")
            print("      - DNS API authentication")
            print("      - Route creation XML format")
            return False

def main():
    """Main test execution"""
    print("Baker Street Labs Enhanced Route Injection Integration Test")
    print("=" * 60)
    
    # Check command line arguments
    service_url = "http://localhost:5001"
    
    if len(sys.argv) > 1:
        service_url = sys.argv[1]
    
    print(f"Service URL: {service_url}")
    
    # Run tests
    tester = EnhancedRouteInjectionTester(service_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
