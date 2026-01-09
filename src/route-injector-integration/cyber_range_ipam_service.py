#!/usr/bin/env python3
"""
Baker Street Labs Cyber Range IPAM Service
Comprehensive IP Address Management for Cortex Labs Cyber Range Infrastructure
"""

import os
import json
import logging
import asyncio
import ipaddress
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import uvicorn
import redis
import yaml
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import INET, MACADDR, ARRAY
import jwt
from passlib.context import CryptContext
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class CyberRange(Base):
    __tablename__ = "cyber_ranges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    vlan_base = Column(Integer, nullable=False)
    ip_base = Column(String(50), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VLANTemplate(Base):
    __tablename__ = "vlan_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    vlan_suffix = Column(Integer, nullable=False)
    ip_suffix = Column(Integer, nullable=False)
    description = Column(Text)
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Subnet(Base):
    __tablename__ = "subnets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    network_cidr = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    vlan_id = Column(Integer, nullable=False)
    gateway = Column(String(50))
    dns_servers = Column(ARRAY(String))
    description = Column(Text)
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    vlan_template_id = Column(Integer, ForeignKey("vlan_templates.id"))
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), nullable=False)
    mac_address = Column(String(17))
    device_type = Column(String(50), nullable=False)
    vendor = Column(String(100))
    role = Column(String(100))
    user_id = Column(Integer)
    scenario_id = Column(Integer)
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IPAddress(Base):
    __tablename__ = "ip_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False, unique=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    status = Column(String(20), default="available")
    allocated_at = Column(DateTime)
    expires_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(255))
    email = Column(String(255))
    department = Column(String(100))
    role = Column(String(50))
    cyber_range_access = Column(ARRAY(String))  # List of cyber ranges user can access
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    playbook_id = Column(String(100))
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    status = Column(String(20), default="inactive")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DNSRecord(Base):
    __tablename__ = "dns_records"
    
    id = Column(Integer, primary_key=True, index=True)
    fqdn = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=False)
    record_type = Column(String(10), default="A")
    ttl = Column(Integer, default=300)
    zone = Column(String(100))
    device_id = Column(Integer, ForeignKey("devices.id"))
    cyber_range_id = Column(Integer, ForeignKey("cyber_ranges.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models
class CyberRangeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    vlan_base: int
    ip_base: str
    status: str = "active"

class CyberRangeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    vlan_base: int
    ip_base: str
    status: str
    created_at: datetime
    updated_at: datetime

class SubnetCreate(BaseModel):
    name: str
    network_cidr: str
    zone: str
    vlan_id: int
    gateway: Optional[str] = None
    dns_servers: Optional[List[str]] = []
    description: Optional[str] = None
    cyber_range_id: int
    vlan_template_id: Optional[int] = None
    is_shared: bool = False

class SubnetResponse(BaseModel):
    id: int
    name: str
    network_cidr: str
    zone: str
    vlan_id: int
    gateway: Optional[str]
    dns_servers: Optional[List[str]]
    description: Optional[str]
    cyber_range_id: int
    vlan_template_id: Optional[int]
    is_shared: bool
    created_at: datetime
    updated_at: datetime

class DeviceCreate(BaseModel):
    hostname: str
    mac_address: Optional[str] = None
    device_type: str
    vendor: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None
    scenario_id: Optional[int] = None
    cyber_range_id: int

class DeviceResponse(BaseModel):
    id: int
    hostname: str
    mac_address: Optional[str]
    device_type: str
    vendor: Optional[str]
    role: Optional[str]
    user_id: Optional[int]
    scenario_id: Optional[int]
    cyber_range_id: int
    status: str
    created_at: datetime
    updated_at: datetime

class IPAllocationRequest(BaseModel):
    subnet_id: int
    device_id: Optional[int] = None
    cyber_range_id: int
    preferred_ip: Optional[str] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None

class IPAllocationResponse(BaseModel):
    id: int
    ip_address: str
    subnet_id: int
    device_id: Optional[int]
    cyber_range_id: int
    status: str
    allocated_at: Optional[datetime]
    expires_at: Optional[datetime]
    notes: Optional[str]

class CyberRangeIPAMConfig:
    """Configuration management for Cyber Range IPAM service"""
    
    def __init__(self, config_file: str = "cyber_range_ipam_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Cyber Range IPAM configuration loaded from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load cyber range IPAM config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "baker_street_cyber_range_ipam",
                "user": "ipam_user",
                "password": "ipam_password_2025"
            },
            "redis": {
                "host": "localhost",
                "port": 6380,
                "db": 2
            },
            "cyber_ranges": {},
            "master_router": {
                "management": {"ip": "192.168.0.254"},
                "ethernet1_1": {"ip": "192.168.0.1"},
                "router_vlan": {"ip": "192.168.1.1"}
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

class CyberRangeIPAMService:
    """Core Cyber Range IPAM service logic"""
    
    def __init__(self, config: CyberRangeIPAMConfig):
        self.config = config
        self.db_engine = self._init_database()
        self.redis_client = self._init_redis()
        self.dns_api = DNSAPIClient(config)
        self.route_injection = RouteInjectionClient(config)
        self.master_router = MasterRouterClient(config)
    
    def _init_database(self):
        """Initialize database connection"""
        db_config = self.config.get('database', {})
        connection_string = f"postgresql://{db_config.get('user')}:{db_config.get('password')}@{db_config.get('host')}:{db_config.get('port')}/{db_config.get('name')}"
        return create_engine(connection_string)
    
    def _init_redis(self):
        """Initialize Redis client"""
        redis_config = self.config.get('redis', {})
        return redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6380),
            db=redis_config.get('db', 2),
            decode_responses=True,
            socket_timeout=redis_config.get('timeout', 30)
        )
    
    def create_tables(self):
        """Create database tables"""
        Base.metadata.create_all(bind=self.db_engine)
        logger.info("Cyber Range IPAM database tables created successfully")
    
    def get_session(self):
        """Get database session"""
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)
        return SessionLocal()
    
    def initialize_cyber_ranges(self):
        """Initialize cyber ranges from configuration"""
        session = self.get_session()
        try:
            cyber_ranges_config = self.config.get('cyber_ranges', {})
            
            for range_name, range_config in cyber_ranges_config.items():
                # Check if cyber range already exists
                existing = session.query(CyberRange).filter(CyberRange.name == range_config['name']).first()
                if existing:
                    continue
                
                # Create cyber range
                cyber_range = CyberRange(
                    name=range_config['name'],
                    description=range_config.get('description', ''),
                    vlan_base=range_config['vlan_base'],
                    ip_base=range_config['ip_base'],
                    status=range_config.get('status', 'active')
                )
                session.add(cyber_range)
                session.flush()  # Get the ID
                
                # Create VLAN templates
                vlan_templates = range_config.get('vlans', {})
                for vlan_name, vlan_config in vlan_templates.items():
                    vlan_template = VLANTemplate(
                        name=vlan_name,
                        vlan_suffix=vlan_config['vlan_id'] % 1000,  # Extract suffix
                        ip_suffix=vlan_config['network'].split('.')[2],  # Extract IP suffix
                        description=vlan_config.get('description', ''),
                        cyber_range_id=cyber_range.id
                    )
                    session.add(vlan_template)
                    session.flush()  # Get the ID
                    
                    # Create subnet
                    subnet = Subnet(
                        name=f"{range_config['name']}-{vlan_name}",
                        network_cidr=vlan_config['network'],
                        zone=vlan_name,
                        vlan_id=vlan_config['vlan_id'],
                        gateway=vlan_config.get('gateway'),
                        dns_servers=vlan_config.get('dns_servers', []),
                        description=vlan_config.get('description', ''),
                        cyber_range_id=cyber_range.id,
                        vlan_template_id=vlan_template.id,
                        is_shared=range_config.get('is_shared', False)
                    )
                    session.add(subnet)
            
            session.commit()
            logger.info("Cyber ranges initialized successfully")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing cyber ranges: {str(e)}")
            raise
        finally:
            session.close()
    
    def allocate_ip(self, subnet_id: int, cyber_range_id: int, device_id: Optional[int] = None, 
                   preferred_ip: Optional[str] = None, notes: Optional[str] = None,
                   expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Allocate IP address from subnet within cyber range"""
        session = self.get_session()
        try:
            # Get subnet information
            subnet = session.query(Subnet).filter(
                Subnet.id == subnet_id,
                Subnet.cyber_range_id == cyber_range_id
            ).first()
            if not subnet:
                raise HTTPException(status_code=404, detail="Subnet not found in cyber range")
            
            # Parse subnet
            network = ipaddress.ip_network(subnet.network_cidr)
            
            # Check if preferred IP is valid
            if preferred_ip:
                try:
                    ip = ipaddress.ip_address(preferred_ip)
                    if ip not in network:
                        raise HTTPException(status_code=400, detail="Preferred IP not in subnet")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid preferred IP format")
            
            # Find available IP
            if preferred_ip:
                # Check if preferred IP is available
                existing = session.query(IPAddress).filter(
                    IPAddress.ip_address == preferred_ip,
                    IPAddress.status.in_(['allocated', 'reserved'])
                ).first()
                if existing:
                    raise HTTPException(status_code=409, detail="Preferred IP already allocated")
                ip_to_allocate = preferred_ip
            else:
                # Find first available IP
                allocated_ips = session.query(IPAddress).filter(
                    IPAddress.subnet_id == subnet_id,
                    IPAddress.status.in_(['allocated', 'reserved'])
                ).all()
                
                allocated_set = set(ip.ip_address for ip in allocated_ips)
                
                # Find first available IP (skip network and broadcast)
                for ip in network.hosts():
                    if str(ip) not in allocated_set:
                        ip_to_allocate = str(ip)
                        break
                else:
                    raise HTTPException(status_code=507, detail="No available IPs in subnet")
            
            # Create IP address record
            ip_record = IPAddress(
                ip_address=ip_to_allocate,
                subnet_id=subnet_id,
                device_id=device_id,
                cyber_range_id=cyber_range_id,
                status='allocated',
                allocated_at=datetime.utcnow(),
                expires_at=expires_at,
                notes=notes
            )
            
            session.add(ip_record)
            session.commit()
            
            # Create DNS record if device is specified
            if device_id:
                device = session.query(Device).filter(Device.id == device_id).first()
                if device:
                    self._create_dns_record(device.hostname, ip_to_allocate, subnet.zone, cyber_range_id)
            
            # Trigger route injection if in cyber range
            if self._is_cyber_range_ip(ip_to_allocate, cyber_range_id):
                self._trigger_route_injection(ip_to_allocate, device_id, cyber_range_id)
            
            # Cache in Redis
            self._cache_ip_allocation(ip_record)
            
            return {
                "id": ip_record.id,
                "ip_address": ip_record.ip_address,
                "subnet_id": ip_record.subnet_id,
                "device_id": ip_record.device_id,
                "cyber_range_id": ip_record.cyber_range_id,
                "status": ip_record.status,
                "allocated_at": ip_record.allocated_at,
                "expires_at": ip_record.expires_at,
                "notes": ip_record.notes
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error allocating IP: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            session.close()
    
    def _is_cyber_range_ip(self, ip_address: str, cyber_range_id: int) -> bool:
        """Check if IP is in cyber range networks"""
        session = self.get_session()
        try:
            cyber_range = session.query(CyberRange).filter(CyberRange.id == cyber_range_id).first()
            if not cyber_range:
                return False
            
            # Check if IP is in the cyber range's IP base
            ip_base = ipaddress.ip_network(cyber_range.ip_base, strict=False)
            ip = ipaddress.ip_address(ip_address)
            return ip in ip_base
        except:
            return False
        finally:
            session.close()
    
    def _create_dns_record(self, hostname: str, ip_address: str, zone: str, cyber_range_id: int):
        """Create DNS record via DNS API"""
        try:
            self.dns_api.create_record(hostname, ip_address, zone)
            logger.info(f"DNS record created: {hostname} -> {ip_address}")
        except Exception as e:
            logger.error(f"Failed to create DNS record: {str(e)}")
    
    def _trigger_route_injection(self, ip_address: str, device_id: Optional[int], cyber_range_id: int):
        """Trigger route injection for cyber range IP"""
        try:
            self.route_injection.inject_route(ip_address, device_id, cyber_range_id)
            logger.info(f"Route injection triggered for IP: {ip_address}")
        except Exception as e:
            logger.error(f"Failed to trigger route injection: {str(e)}")
    
    def _cache_ip_allocation(self, ip_record: IPAddress):
        """Cache IP allocation in Redis"""
        try:
            key = f"cyber_range_ipam:ip:{ip_record.ip_address}"
            data = {
                "id": ip_record.id,
                "ip_address": ip_record.ip_address,
                "subnet_id": ip_record.subnet_id,
                "device_id": ip_record.device_id,
                "cyber_range_id": ip_record.cyber_range_id,
                "status": ip_record.status,
                "allocated_at": ip_record.allocated_at.isoformat() if ip_record.allocated_at else None,
                "expires_at": ip_record.expires_at.isoformat() if ip_record.expires_at else None,
                "notes": ip_record.notes
            }
            self.redis_client.setex(key, 3600, json.dumps(data))  # 1 hour TTL
        except Exception as e:
            logger.error(f"Failed to cache IP allocation: {str(e)}")

class DNSAPIClient:
    """Client for DNS API integration"""
    
    def __init__(self, config: CyberRangeIPAMConfig):
        self.config = config
        self.base_url = config.get('dns_api.base_url')
        self.username = config.get('dns_api.username')
        self.password = config.get('dns_api.password')
        self.session = requests.Session()
        self.jwt_token = None
    
    def _authenticate(self):
        """Authenticate with DNS API"""
        if self.jwt_token:
            return
        
        try:
            url = f"{self.base_url}/api/auth/login"
            data = {
                "username": self.username,
                "password": self.password
            }
            
            response = self.session.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'access_token' in result:
                self.jwt_token = result['access_token']
                self.session.headers.update({'Authorization': f'Bearer {self.jwt_token}'})
                logger.info("DNS API authentication successful")
            else:
                raise Exception("No access token in response")
                
        except Exception as e:
            logger.error(f"DNS API authentication failed: {str(e)}")
            raise
    
    def create_record(self, hostname: str, ip_address: str, zone: str):
        """Create DNS record"""
        self._authenticate()
        
        url = f"{self.base_url}/api/dns/records"
        params = {
            "zone": zone,
            "fqdn": f"{hostname}.{zone}",
            "ip_address": ip_address,
            "ttl": 300
        }
        
        response = self.session.post(url, params=params, timeout=30)
        response.raise_for_status()
        
        logger.info(f"DNS record created: {hostname}.{zone} -> {ip_address}")

class RouteInjectionClient:
    """Client for route injection integration"""
    
    def __init__(self, config: CyberRangeIPAMConfig):
        self.config = config
        self.base_url = config.get('route_injection.base_url')
        self.api_key = config.get('route_injection.api_key')
    
    def inject_route(self, ip_address: str, device_id: Optional[int], cyber_range_id: int):
        """Trigger route injection"""
        try:
            url = f"{self.base_url}/api/v1/dns-record"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            data = {
                "zone": "bakerstreetlabs.local",
                "fqdn": f"device-{device_id}.bakerstreetlabs.local" if device_id else f"ip-{ip_address.replace('.', '-')}.bakerstreetlabs.local",
                "ip_address": ip_address,
                "cyber_range_id": cyber_range_id
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Route injection triggered for IP: {ip_address}")
            
        except Exception as e:
            logger.error(f"Route injection failed: {str(e)}")
            raise

class MasterRouterClient:
    """Client for master router integration"""
    
    def __init__(self, config: CyberRangeIPAMConfig):
        self.config = config
        self.mgmt_ip = config.get('master_router.management.ip')
        self.data_ip = config.get('master_router.ethernet1_1.ip')
        self.internal_ip = config.get('master_router.router_vlan.ip')
        self.username = config.get('master_router.api_credentials.username')
        self.password = config.get('master_router.api_credentials.password')
        self.api_port = config.get('master_router.api_credentials.api_port')
    
    def get_api_key(self) -> Optional[str]:
        """Get API key for master router"""
        try:
            url = f"https://{self.mgmt_ip}:{self.api_port}/api/"
            params = {
                "type": "keygen",
                "user": self.username,
                "password": self.password
            }
            
            response = requests.get(url, params=params, verify=False, timeout=30)
            response.raise_for_status()
            
            # Parse XML response for API key
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            api_key = root.findtext('.//key')
            
            if api_key:
                logger.info(f"Master router API key obtained")
                return api_key
            else:
                logger.error("API key not found in master router response")
                return None
                
        except Exception as e:
            logger.error(f"Error getting master router API key: {str(e)}")
            return None

# Initialize FastAPI app
app = FastAPI(
    title="Baker Street Labs Cyber Range IPAM Service",
    description="IP Address Management for Cortex Labs Cyber Range Infrastructure",
    version="1.0.0"
)

# Initialize services
config = CyberRangeIPAMConfig()
ipam_service = CyberRangeIPAMService(config)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            config.get('security.jwt_secret'),
            algorithms=[config.get('security.jwt_algorithm')]
        )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize database and cyber ranges on startup"""
    ipam_service.create_tables()
    ipam_service.initialize_cyber_ranges()
    logger.info("Baker Street Labs Cyber Range IPAM Service started")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "baker-street-cyber-range-ipam",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/v1/cyber-ranges", response_model=List[CyberRangeResponse])
async def list_cyber_ranges():
    """List all cyber ranges"""
    session = ipam_service.get_session()
    try:
        cyber_ranges = session.query(CyberRange).all()
        return cyber_ranges
    finally:
        session.close()

@app.get("/api/v1/cyber-ranges/{cyber_range_id}/subnets", response_model=List[SubnetResponse])
async def list_cyber_range_subnets(cyber_range_id: int):
    """List subnets for a specific cyber range"""
    session = ipam_service.get_session()
    try:
        subnets = session.query(Subnet).filter(Subnet.cyber_range_id == cyber_range_id).all()
        return subnets
    finally:
        session.close()

@app.post("/api/v1/cyber-ranges/{cyber_range_id}/ips/allocate", response_model=IPAllocationResponse)
async def allocate_ip(cyber_range_id: int, request: IPAllocationRequest):
    """Allocate IP address within cyber range"""
    result = ipam_service.allocate_ip(
        subnet_id=request.subnet_id,
        cyber_range_id=cyber_range_id,
        device_id=request.device_id,
        preferred_ip=request.preferred_ip,
        notes=request.notes,
        expires_at=request.expires_at
    )
    return result

@app.get("/api/v1/cyber-ranges/{cyber_range_id}/ips/available")
async def get_available_ips(cyber_range_id: int, subnet_id: int):
    """Get available IPs in cyber range subnet"""
    session = ipam_service.get_session()
    try:
        subnet = session.query(Subnet).filter(
            Subnet.id == subnet_id,
            Subnet.cyber_range_id == cyber_range_id
        ).first()
        if not subnet:
            raise HTTPException(status_code=404, detail="Subnet not found in cyber range")
        
        network = ipaddress.ip_network(subnet.network_cidr)
        allocated_ips = session.query(IPAddress).filter(
            IPAddress.subnet_id == subnet_id,
            IPAddress.status.in_(['allocated', 'reserved'])
        ).all()
        
        allocated_set = set(ip.ip_address for ip in allocated_ips)
        available_ips = [str(ip) for ip in network.hosts() if str(ip) not in allocated_set]
        
        return {
            "cyber_range_id": cyber_range_id,
            "subnet_id": subnet_id,
            "network_cidr": subnet.network_cidr,
            "available_ips": available_ips[:100],  # Limit to first 100
            "total_available": len(available_ips)
        }
    finally:
        session.close()

@app.get("/api/v1/cyber-ranges/{cyber_range_id}/devices", response_model=List[DeviceResponse])
async def list_cyber_range_devices(cyber_range_id: int):
    """List devices in a specific cyber range"""
    session = ipam_service.get_session()
    try:
        devices = session.query(Device).filter(Device.cyber_range_id == cyber_range_id).all()
        return devices
    finally:
        session.close()

@app.post("/api/v1/cyber-ranges/{cyber_range_id}/devices", response_model=DeviceResponse)
async def create_device(cyber_range_id: int, device: DeviceCreate):
    """Create device in cyber range"""
    session = ipam_service.get_session()
    try:
        db_device = Device(**device.dict(), cyber_range_id=cyber_range_id)
        session.add(db_device)
        session.commit()
        session.refresh(db_device)
        return db_device
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/v1/cyber-ranges/{cyber_range_id}/reports/usage")
async def get_cyber_range_usage_report(cyber_range_id: int):
    """Generate usage report for cyber range"""
    session = ipam_service.get_session()
    try:
        cyber_range = session.query(CyberRange).filter(CyberRange.id == cyber_range_id).first()
        if not cyber_range:
            raise HTTPException(status_code=404, detail="Cyber range not found")
        
        subnets = session.query(Subnet).filter(Subnet.cyber_range_id == cyber_range_id).all()
        usage_report = []
        
        for subnet in subnets:
            network = ipaddress.ip_network(subnet.network_cidr)
            total_ips = len(list(network.hosts()))
            
            allocated_count = session.query(IPAddress).filter(
                IPAddress.subnet_id == subnet.id,
                IPAddress.status == 'allocated'
            ).count()
            
            reserved_count = session.query(IPAddress).filter(
                IPAddress.subnet_id == subnet.id,
                IPAddress.status == 'reserved'
            ).count()
            
            usage_percentage = ((allocated_count + reserved_count) / total_ips) * 100 if total_ips > 0 else 0
            
            usage_report.append({
                "subnet_id": subnet.id,
                "subnet_name": subnet.name,
                "network_cidr": subnet.network_cidr,
                "vlan_id": subnet.vlan_id,
                "zone": subnet.zone,
                "total_ips": total_ips,
                "allocated": allocated_count,
                "reserved": reserved_count,
                "available": total_ips - allocated_count - reserved_count,
                "usage_percentage": round(usage_percentage, 2)
            })
        
        return {
            "cyber_range_id": cyber_range_id,
            "cyber_range_name": cyber_range.name,
            "report_timestamp": datetime.utcnow().isoformat(),
            "subnets": usage_report
        }
    finally:
        session.close()

if __name__ == "__main__":
    uvicorn.run(
        "cyber_range_ipam_service:app",
        host="0.0.0.0",
        port=5003,
        reload=True
    )
