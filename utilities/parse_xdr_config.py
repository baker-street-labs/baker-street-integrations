#!/usr/bin/env python3
# EXTRACTED FROM PRODUCTION BAKER STREET MONOREPO – 2025-12-03
# Verified working in active cyber range for 18+ months
# Part of the official Tier 1 / Tier 2 crown jewels audit (Conservative Option A)
# DO NOT REFACTOR UNLESS EXPLICITLY APPROVED

"""
Parse XDR Range Firewall Configuration
Extracts key configuration elements and creates a comprehensive guide
"""

import xml.etree.ElementTree as ET
import json
from datetime import datetime
import re

class XDRConfigParser:
    def __init__(self, config_file):
        self.config_file = config_file
        self.tree = None
        self.root = None
        self.config_data = {}
        
    def parse_config(self):
        """Parse the XML configuration file"""
        try:
            self.tree = ET.parse(self.config_file)
            self.root = self.tree.getroot()
            print(f"✅ Successfully parsed {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error parsing {self.config_file}: {str(e)}")
            return False
    
    def extract_system_info(self):
        """Extract system information"""
        system_info = {}
        
        # Basic system settings
        system_settings = self.root.find('.//system/settings')
        if system_settings is not None:
            system_info['hostname'] = system_settings.findtext('hostname', 'Unknown')
            system_info['domain'] = system_settings.findtext('domain', 'Unknown')
            system_info['timezone'] = system_settings.findtext('timezone', 'Unknown')
        
        # Device info
        device_info = self.root.find('.//system/deviceconfig')
        if device_info is not None:
            system_info['device_type'] = device_info.findtext('system/type', 'Unknown')
        
        return system_info
    
    def extract_interfaces(self):
        """Extract network interfaces configuration"""
        interfaces = {}
        
        # Ethernet interfaces
        for interface in self.root.findall('.//network/interface/ethernet/entry'):
            name = interface.get('name', 'Unknown')
            interface_data = {
                'type': 'ethernet',
                'comment': interface.findtext('comment', ''),
                'vsys': interface.findtext('vsys', 'vsys1')
            }
            
            # Layer3 configuration
            layer3 = interface.find('layer3')
            if layer3 is not None:
                interface_data['layer3'] = {
                    'ip': layer3.findtext('ip/entry', ''),
                    'management_profile': layer3.findtext('management-profile', ''),
                    'mtu': layer3.findtext('mtu', '1500')
                }
            
            # Layer2 configuration
            layer2 = interface.find('layer2')
            if layer2 is not None:
                interface_data['layer2'] = {
                    'vlan': layer2.findtext('vlan', ''),
                    'netflow_profile': layer2.findtext('netflow-profile', '')
                }
            
            interfaces[name] = interface_data
        
        # Loopback interfaces
        for interface in self.root.findall('.//network/interface/loopback/entry'):
            name = interface.get('name', 'Unknown')
            interface_data = {
                'type': 'loopback',
                'comment': interface.findtext('comment', ''),
                'vsys': interface.findtext('vsys', 'vsys1')
            }
            
            layer3 = interface.find('layer3')
            if layer3 is not None:
                interface_data['layer3'] = {
                    'ip': layer3.findtext('ip', ''),
                    'management_profile': layer3.findtext('management-profile', '')
                }
            
            interfaces[name] = interface_data
        
        return interfaces
    
    def extract_zones(self):
        """Extract security zones configuration"""
        zones = {}
        
        for zone in self.root.findall('.//vsys/entry/zone/entry'):
            name = zone.get('name', 'Unknown')
            zone_data = {
                'network': zone.findtext('network/layer3', ''),
                'zone_profile': zone.findtext('zone-profile', ''),
                'log_setting': zone.findtext('log-setting', ''),
                'enable_user_identification': zone.findtext('enable-user-identification', 'no')
            }
            zones[name] = zone_data
        
        return zones
    
    def extract_address_objects(self):
        """Extract address objects"""
        addresses = {}
        
        for addr in self.root.findall('.//vsys/entry/address/entry'):
            name = addr.get('name', 'Unknown')
            addr_data = {
                'description': addr.findtext('description', ''),
                'ip_netmask': addr.findtext('ip-netmask', ''),
                'fqdn': addr.findtext('fqdn', ''),
                'ip_range': addr.findtext('ip-range', ''),
                'tag': [tag.text for tag in addr.findall('tag/member')]
            }
            addresses[name] = addr_data
        
        return addresses
    
    def extract_address_groups(self):
        """Extract address groups"""
        groups = {}
        
        for group in self.root.findall('.//vsys/entry/address-group/entry'):
            name = group.get('name', 'Unknown')
            group_data = {
                'description': group.findtext('description', ''),
                'static_members': [member.text for member in group.findall('static/member')],
                'dynamic_members': [member.text for member in group.findall('dynamic/member')],
                'tag': [tag.text for tag in group.findall('tag/member')]
            }
            groups[name] = group_data
        
        return groups
    
    def extract_services(self):
        """Extract service objects"""
        services = {}
        
        for service in self.root.findall('.//vsys/entry/service/entry'):
            name = service.get('name', 'Unknown')
            service_data = {
                'description': service.findtext('description', ''),
                'protocol': service.findtext('protocol', ''),
                'port': service.findtext('port', ''),
                'source_port': service.findtext('source-port', ''),
                'tag': [tag.text for tag in service.findall('tag/member')]
            }
            services[name] = service_data
        
        return services
    
    def extract_security_rules(self):
        """Extract security policy rules"""
        rules = {}
        
        for rule in self.root.findall('.//vsys/entry/rulebase/security/rules/entry'):
            name = rule.get('name', 'Unknown')
            rule_data = {
                'description': rule.findtext('description', ''),
                'from_zones': [zone.text for zone in rule.findall('from/member')],
                'to_zones': [zone.text for zone in rule.findall('to/member')],
                'source_addresses': [addr.text for addr in rule.findall('source/member')],
                'destination_addresses': [addr.text for addr in rule.findall('destination/member')],
                'applications': [app.text for app in rule.findall('application/member')],
                'services': [svc.text for svc in rule.findall('service/member')],
                'action': rule.findtext('action', 'deny'),
                'log_setting': rule.findtext('log-setting', ''),
                'disabled': rule.findtext('disabled', 'no')
            }
            rules[name] = rule_data
        
        return rules
    
    def extract_nat_rules(self):
        """Extract NAT rules"""
        nat_rules = {}
        
        for rule in self.root.findall('.//vsys/entry/rulebase/nat/rules/entry'):
            name = rule.get('name', 'Unknown')
            rule_data = {
                'description': rule.findtext('description', ''),
                'from_zones': [zone.text for zone in rule.findall('from/member')],
                'to_zones': [zone.text for zone in rule.findall('to/member')],
                'source_addresses': [addr.text for addr in rule.findall('source/member')],
                'destination_addresses': [addr.text for addr in rule.findall('destination/member')],
                'service': rule.findtext('service', ''),
                'nat_type': rule.findtext('nat-type', ''),
                'source_translation': rule.findtext('source-translation', ''),
                'destination_translation': rule.findtext('destination-translation', ''),
                'disabled': rule.findtext('disabled', 'no')
            }
            nat_rules[name] = rule_data
        
        return nat_rules
    
    def extract_routing(self):
        """Extract routing configuration"""
        routing = {
            'virtual_routers': {},
            'static_routes': {},
            'ospf': {},
            'bgp': {}
        }
        
        # Virtual routers
        for vr in self.root.findall('.//network/virtual-router/entry'):
            name = vr.get('name', 'Unknown')
            vr_data = {
                'interface': [iface.text for iface in vr.findall('interface/member')],
                'routing_table': [table.text for table in vr.findall('routing-table/member')],
                'protocol': [proto.text for proto in vr.findall('protocol/member')]
            }
            routing['virtual_routers'][name] = vr_data
        
        # Static routes
        for route in self.root.findall('.//network/virtual-router/entry/routing-table/ip/static-route/entry'):
            name = route.get('name', 'Unknown')
            route_data = {
                'destination': route.findtext('destination', ''),
                'nexthop': route.findtext('nexthop/ip-address', ''),
                'interface': route.findtext('interface', ''),
                'metric': route.findtext('metric', '10'),
                'route_table': route.findtext('route-table/unicast', '')
            }
            routing['static_routes'][name] = route_data
        
        return routing
    
    def extract_profiles(self):
        """Extract security profiles"""
        profiles = {
            'vulnerability_protection': {},
            'antivirus': {},
            'spyware': {},
            'file_blocking': {},
            'data_filtering': {},
            'wildfire_analysis': {},
            'url_filtering': {}
        }
        
        # Vulnerability Protection Profiles
        for profile in self.root.findall('.//vsys/entry/profiles/vulnerability-protection/entry'):
            name = profile.get('name', 'Unknown')
            profile_data = {
                'description': profile.findtext('description', ''),
                'rules': []
            }
            
            for rule in profile.findall('rules/entry'):
                rule_data = {
                    'threat_name': rule.findtext('threat-name', ''),
                    'action': rule.findtext('action', ''),
                    'packet_capture': rule.findtext('packet-capture', '')
                }
                profile_data['rules'].append(rule_data)
            
            profiles['vulnerability_protection'][name] = profile_data
        
        return profiles
    
    def generate_config_guide(self):
        """Generate comprehensive configuration guide"""
        if not self.parse_config():
            return False
        
        print("📊 Extracting configuration data...")
        
        # Extract all configuration elements
        self.config_data = {
            'system_info': self.extract_system_info(),
            'interfaces': self.extract_interfaces(),
            'zones': self.extract_zones(),
            'address_objects': self.extract_address_objects(),
            'address_groups': self.extract_address_groups(),
            'services': self.extract_services(),
            'security_rules': self.extract_security_rules(),
            'nat_rules': self.extract_nat_rules(),
            'routing': self.extract_routing(),
            'profiles': self.extract_profiles()
        }
        
        # Generate markdown guide
        self.create_markdown_guide()
        
        return True
    
    def create_markdown_guide(self):
        """Create comprehensive markdown configuration guide"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        guide_content = f"""# XDR Range Firewall Configuration Guide

**Generated:** {timestamp}  
**Source:** xdr_range.xml  
**Firewall:** cortex-labs-border-xdr (192.168.255.201)

---

## Table of Contents

1. [System Information](#system-information)
2. [Network Interfaces](#network-interfaces)
3. [Security Zones](#security-zones)
4. [Address Objects](#address-objects)
5. [Address Groups](#address-groups)
6. [Service Objects](#service-objects)
7. [Security Policy Rules](#security-policy-rules)
8. [NAT Rules](#nat-rules)
9. [Routing Configuration](#routing-configuration)
10. [Security Profiles](#security-profiles)

---

## System Information

"""
        
        # System Information
        system = self.config_data['system_info']
        guide_content += f"""
- **Hostname:** {system.get('hostname', 'Unknown')}
- **Domain:** {system.get('domain', 'Unknown')}
- **Timezone:** {system.get('timezone', 'Unknown')}
- **Device Type:** {system.get('device_type', 'Unknown')}

---

## Network Interfaces

"""
        
        # Interfaces
        interfaces = self.config_data['interfaces']
        for name, data in interfaces.items():
            guide_content += f"""
### {name} ({data['type'].upper()})
- **Comment:** {data.get('comment', 'None')}
- **VSYS:** {data.get('vsys', 'vsys1')}
"""
            if 'layer3' in data:
                layer3 = data['layer3']
                guide_content += f"""
- **IP Address:** {layer3.get('ip', 'None')}
- **Management Profile:** {layer3.get('management_profile', 'None')}
- **MTU:** {layer3.get('mtu', '1500')}
"""
            if 'layer2' in data:
                layer2 = data['layer2']
                guide_content += f"""
- **VLAN:** {layer2.get('vlan', 'None')}
- **NetFlow Profile:** {layer2.get('netflow_profile', 'None')}
"""
            guide_content += "\n"
        
        # Security Zones
        guide_content += "## Security Zones\n\n"
        zones = self.config_data['zones']
        for name, data in zones.items():
            guide_content += f"""
### {name}
- **Network:** {data.get('network', 'None')}
- **Zone Profile:** {data.get('zone_profile', 'None')}
- **Log Setting:** {data.get('log_setting', 'None')}
- **User Identification:** {data.get('enable_user_identification', 'no')}

"""
        
        # Address Objects
        guide_content += "## Address Objects\n\n"
        addresses = self.config_data['address_objects']
        for name, data in addresses.items():
            guide_content += f"""
### {name}
- **Description:** {data.get('description', 'None')}
- **IP Netmask:** {data.get('ip_netmask', 'None')}
- **FQDN:** {data.get('fqdn', 'None')}
- **IP Range:** {data.get('ip_range', 'None')}
- **Tags:** {', '.join(data.get('tag', [])) if data.get('tag') else 'None'}

"""
        
        # Address Groups
        guide_content += "## Address Groups\n\n"
        groups = self.config_data['address_groups']
        for name, data in groups.items():
            guide_content += f"""
### {name}
- **Description:** {data.get('description', 'None')}
- **Static Members:** {', '.join(data.get('static_members', [])) if data.get('static_members') else 'None'}
- **Dynamic Members:** {', '.join(data.get('dynamic_members', [])) if data.get('dynamic_members') else 'None'}
- **Tags:** {', '.join(data.get('tag', [])) if data.get('tag') else 'None'}

"""
        
        # Service Objects
        guide_content += "## Service Objects\n\n"
        services = self.config_data['services']
        for name, data in services.items():
            guide_content += f"""
### {name}
- **Description:** {data.get('description', 'None')}
- **Protocol:** {data.get('protocol', 'None')}
- **Port:** {data.get('port', 'None')}
- **Source Port:** {data.get('source_port', 'None')}
- **Tags:** {', '.join(data.get('tag', [])) if data.get('tag') else 'None'}

"""
        
        # Security Rules
        guide_content += "## Security Policy Rules\n\n"
        rules = self.config_data['security_rules']
        for name, data in rules.items():
            guide_content += f"""
### {name}
- **Description:** {data.get('description', 'None')}
- **From Zones:** {', '.join(data.get('from_zones', [])) if data.get('from_zones') else 'None'}
- **To Zones:** {', '.join(data.get('to_zones', [])) if data.get('to_zones') else 'None'}
- **Source Addresses:** {', '.join(data.get('source_addresses', [])) if data.get('source_addresses') else 'None'}
- **Destination Addresses:** {', '.join(data.get('destination_addresses', [])) if data.get('destination_addresses') else 'None'}
- **Applications:** {', '.join(data.get('applications', [])) if data.get('applications') else 'None'}
- **Services:** {', '.join(data.get('services', [])) if data.get('services') else 'None'}
- **Action:** {data.get('action', 'deny')}
- **Log Setting:** {data.get('log_setting', 'None')}
- **Disabled:** {data.get('disabled', 'no')}

"""
        
        # NAT Rules
        guide_content += "## NAT Rules\n\n"
        nat_rules = self.config_data['nat_rules']
        for name, data in nat_rules.items():
            guide_content += f"""
### {name}
- **Description:** {data.get('description', 'None')}
- **From Zones:** {', '.join(data.get('from_zones', [])) if data.get('from_zones') else 'None'}
- **To Zones:** {', '.join(data.get('to_zones', [])) if data.get('to_zones') else 'None'}
- **Source Addresses:** {', '.join(data.get('source_addresses', [])) if data.get('source_addresses') else 'None'}
- **Destination Addresses:** {', '.join(data.get('destination_addresses', [])) if data.get('destination_addresses') else 'None'}
- **Service:** {data.get('service', 'None')}
- **NAT Type:** {data.get('nat_type', 'None')}
- **Source Translation:** {data.get('source_translation', 'None')}
- **Destination Translation:** {data.get('destination_translation', 'None')}
- **Disabled:** {data.get('disabled', 'no')}

"""
        
        # Routing
        guide_content += "## Routing Configuration\n\n"
        routing = self.config_data['routing']
        
        # Virtual Routers
        guide_content += "### Virtual Routers\n\n"
        for name, data in routing['virtual_routers'].items():
            guide_content += f"""
#### {name}
- **Interfaces:** {', '.join(data.get('interface', [])) if data.get('interface') else 'None'}
- **Routing Tables:** {', '.join(data.get('routing_table', [])) if data.get('routing_table') else 'None'}
- **Protocols:** {', '.join(data.get('protocol', [])) if data.get('protocol') else 'None'}

"""
        
        # Static Routes
        guide_content += "### Static Routes\n\n"
        for name, data in routing['static_routes'].items():
            guide_content += f"""
#### {name}
- **Destination:** {data.get('destination', 'None')}
- **Next Hop:** {data.get('nexthop', 'None')}
- **Interface:** {data.get('interface', 'None')}
- **Metric:** {data.get('metric', '10')}
- **Route Table:** {data.get('route_table', 'None')}

"""
        
        # Security Profiles
        guide_content += "## Security Profiles\n\n"
        profiles = self.config_data['profiles']
        
        # Vulnerability Protection Profiles
        guide_content += "### Vulnerability Protection Profiles\n\n"
        for name, data in profiles['vulnerability_protection'].items():
            guide_content += f"""
#### {name}
- **Description:** {data.get('description', 'None')}
- **Rules Count:** {len(data.get('rules', []))}

"""
        
        # Summary
        guide_content += f"""
---

## Configuration Summary

- **Total Interfaces:** {len(interfaces)}
- **Total Zones:** {len(zones)}
- **Total Address Objects:** {len(addresses)}
- **Total Address Groups:** {len(groups)}
- **Total Service Objects:** {len(services)}
- **Total Security Rules:** {len(rules)}
- **Total NAT Rules:** {len(nat_rules)}
- **Total Static Routes:** {len(routing['static_routes'])}

---

*This configuration guide was automatically generated from the XDR Range firewall configuration.*
"""
        
        # Write the guide to file
        with open('Config_Guide.md', 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print("✅ Configuration guide created: Config_Guide.md")
        
        # Also save the parsed data as JSON for reference
        with open('xdr_config_parsed.json', 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, default=str)
        
        print("✅ Parsed configuration data saved: xdr_config_parsed.json")

def main():
    """Main execution"""
    print("🔍 XDR Range Configuration Parser")
    print("=" * 50)
    
    parser = XDRConfigParser('xdr_range.xml')
    
    if parser.generate_config_guide():
        print("\n🎉 Configuration parsing and guide generation completed!")
        print("📄 Files created:")
        print("   - Config_Guide.md (Comprehensive configuration guide)")
        print("   - xdr_config_parsed.json (Raw parsed data)")
    else:
        print("\n❌ Failed to parse configuration or generate guide")

if __name__ == "__main__":
    main()
