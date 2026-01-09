#!/usr/bin/env python3
"""
Baker Street Labs IPAM Service
Comprehensive IP Address Management for Cyber Range Infrastructure
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

class Subnet(Base):
    __tablename__ = "subnets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    network_cidr = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    vlan_id = Column(Integer)
    gateway = Column(String(50))
    dns_servers = Column(ARRAY(String))
    description = Column(Text)
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
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IPAddress(Base):
    __tablename__ = "ip_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False, unique=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    playbook_id = Column(String(100))
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models
class SubnetCreate(BaseModel):
    name: str
    network_cidr: str
    zone: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    dns_servers: Optional[List[str]] = []
    description: Optional[str] = None

class SubnetResponse(BaseModel):
    id: int
    name: str
    network_cidr: str
    zone: str
    vlan_id: Optional[int]
    gateway: Optional[str]
    dns_servers: Optional[List[str]]
    description: Optional[str]
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

class DeviceResponse(BaseModel):
    id: int
    hostname: str
    mac_address: Optional[str]
    device_type: str
    vendor: Optional[str]
    role: Optional[str]
    user_id: Optional[int]
    scenario_id: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

class IPAllocationRequest(BaseModel):
    subnet_id: int
    device_id: Optional[int] = None
    preferred_ip: Optional[str] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None

class IPAllocationResponse(BaseModel):
    id: int
    ip_address: str
    subnet_id: int
    device_id: Optional[int]
    status: str
    allocated_at: Optional[datetime]
    expires_at: Optional[datetime]
    notes: Optional[str]

class DNSRecordCreate(BaseModel):
    fqdn: str
    ip_address: str
    record_type: str = "A"
    ttl: int = 300
    zone: str
    device_id: Optional[int] = None

class DNSRecordResponse(BaseModel):
    id: int
    fqdn: str
    ip_address: str
    record_type: str
    ttl: int
    zone: str
    device_id: Optional[int]
    created_at: datetime
    updated_at: datetime

class IPAMConfig:
    """Configuration management for IPAM service"""
    
    def __init__(self, config_file: str = "ipam_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"IPAM configuration loaded from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load IPAM config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "baker_street_ipam",
                "user": "ipam_user",
                "password": "ipam_password"
            },
            "redis": {
                "host": "localhost",
                "port": 6380,
                "db": 1
            },
            "dns_api": {
                "base_url": "http://10.43.20.75:9090",
                "username": "admin",
                "password": "admin"
            },
            "route_injection": {
                "base_url": "http://localhost:5001",
                "api_key": "baker_street_route_injection_key"
            },
            "security": {
                "jwt_secret": "baker_street_ipam_jwt_secret_2025",
                "jwt_algorithm": "HS256",
                "jwt_expire_minutes": 60
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

class IPAMService:
    """Core IPAM service logic"""
    
    def __init__(self, config: IPAMConfig):
        self.config = config
        self.db_engine = self._init_database()
        self.redis_client = self._init_redis()
        self.dns_api = DNSAPIClient(config)
        self.route_injection = RouteInjectionClient(config)
    
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
            db=redis_config.get('db', 1),
            decode_responses=True
        )
    
    def create_tables(self):
        """Create database tables"""
        Base.metadata.create_all(bind=self.db_engine)
        logger.info("Database tables created successfully")
    
    def get_session(self):
        """Get database session"""
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)
        return SessionLocal()
    
    def allocate_ip(self, subnet_id: int, device_id: Optional[int] = None, 
                   preferred_ip: Optional[str] = None, notes: Optional[str] = None,
                   expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Allocate IP address from subnet"""
        session = self.get_session()
        try:
            # Get subnet information
            subnet = session.query(Subnet).filter(Subnet.id == subnet_id).first()
            if not subnet:
                raise HTTPException(status_code=404, detail="Subnet not found")
            
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
                    self._create_dns_record(device.hostname, ip_to_allocate, subnet.zone)
            
            # Trigger route injection if in cyber range
            if self._is_cyber_range_ip(ip_to_allocate):
                self._trigger_route_injection(ip_to_allocate, device_id)
            
            # Cache in Redis
            self._cache_ip_allocation(ip_record)
            
            return {
                "id": ip_record.id,
                "ip_address": ip_record.ip_address,
                "subnet_id": ip_record.subnet_id,
                "device_id": ip_record.device_id,
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
    
    def release_ip(self, ip_address: str) -> Dict[str, Any]:
        """Release IP address"""
        session = self.get_session()
        try:
            # Find IP record
            ip_record = session.query(IPAddress).filter(
                IPAddress.ip_address == ip_address,
                IPAddress.status == 'allocated'
            ).first()
            
            if not ip_record:
                raise HTTPException(status_code=404, detail="IP address not found or not allocated")
            
            # Update status
            ip_record.status = 'available'
            ip_record.allocated_at = None
            ip_record.expires_at = None
            ip_record.device_id = None
            
            session.commit()
            
            # Remove DNS record
            self._remove_dns_record(ip_address)
            
            # Remove route if in cyber range
            if self._is_cyber_range_ip(ip_address):
                self._remove_route_injection(ip_address)
            
            # Update cache
            self._cache_ip_allocation(ip_record)
            
            return {"message": f"IP address {ip_address} released successfully"}
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error releasing IP: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            session.close()
    
    def _is_cyber_range_ip(self, ip_address: str) -> bool:
        """Check if IP is in cyber range networks"""
        cyber_range_networks = [
            "10.0.0.0/8",
            "172.20.0.0/16",
            "172.21.0.0/16",
            "192.168.0.0/16"
        ]
        
        try:
            ip = ipaddress.ip_address(ip_address)
            for network_str in cyber_range_networks:
                network = ipaddress.ip_network(network_str, strict=False)
                if ip in network:
                    return True
            return False
        except:
            return False
    
    def _create_dns_record(self, hostname: str, ip_address: str, zone: str):
        """Create DNS record via DNS API"""
        try:
            self.dns_api.create_record(hostname, ip_address, zone)
            logger.info(f"DNS record created: {hostname} -> {ip_address}")
        except Exception as e:
            logger.error(f"Failed to create DNS record: {str(e)}")
    
    def _remove_dns_record(self, ip_address: str):
        """Remove DNS record via DNS API"""
        try:
            self.dns_api.remove_record_by_ip(ip_address)
            logger.info(f"DNS record removed for IP: {ip_address}")
        except Exception as e:
            logger.error(f"Failed to remove DNS record: {str(e)}")
    
    def _trigger_route_injection(self, ip_address: str, device_id: Optional[int]):
        """Trigger route injection for cyber range IP"""
        try:
            self.route_injection.inject_route(ip_address, device_id)
            logger.info(f"Route injection triggered for IP: {ip_address}")
        except Exception as e:
            logger.error(f"Failed to trigger route injection: {str(e)}")
    
    def _remove_route_injection(self, ip_address: str):
        """Remove route injection for cyber range IP"""
        try:
            self.route_injection.remove_route(ip_address)
            logger.info(f"Route injection removed for IP: {ip_address}")
        except Exception as e:
            logger.error(f"Failed to remove route injection: {str(e)}")
    
    def _cache_ip_allocation(self, ip_record: IPAddress):
        """Cache IP allocation in Redis"""
        try:
            key = f"ipam:ip:{ip_record.ip_address}"
            data = {
                "id": ip_record.id,
                "ip_address": ip_record.ip_address,
                "subnet_id": ip_record.subnet_id,
                "device_id": ip_record.device_id,
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
    
    def __init__(self, config: IPAMConfig):
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
    
    def remove_record_by_ip(self, ip_address: str):
        """Remove DNS record by IP address"""
        # This would need to be implemented in the DNS API
        # For now, we'll just log the request
        logger.info(f"DNS record removal requested for IP: {ip_address}")

class RouteInjectionClient:
    """Client for route injection integration"""
    
    def __init__(self, config: IPAMConfig):
        self.config = config
        self.base_url = config.get('route_injection.base_url')
        self.api_key = config.get('route_injection.api_key')
    
    def inject_route(self, ip_address: str, device_id: Optional[int]):
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
                "ip_address": ip_address
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Route injection triggered for IP: {ip_address}")
            
        except Exception as e:
            logger.error(f"Route injection failed: {str(e)}")
            raise
    
    def remove_route(self, ip_address: str):
        """Remove route injection"""
        try:
            url = f"{self.base_url}/api/v1/dns-record"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            data = {
                "zone": "bakerstreetlabs.local",
                "fqdn": f"ip-{ip_address.replace('.', '-')}.bakerstreetlabs.local",
                "ip_address": ip_address
            }
            
            response = requests.delete(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Route injection removed for IP: {ip_address}")
            
        except Exception as e:
            logger.error(f"Route injection removal failed: {str(e)}")
            raise

# Initialize FastAPI app
app = FastAPI(
    title="Baker Street Labs IPAM Service",
    description="IP Address Management for Cyber Range Infrastructure",
    version="1.0.0"
)

# Initialize services
config = IPAMConfig()
ipam_service = IPAMService(config)

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
    """Initialize database on startup"""
    ipam_service.create_tables()
    logger.info("Baker Street Labs IPAM Service started")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "baker-street-ipam",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/v1/ipam/subnets", response_model=List[SubnetResponse])
async def list_subnets():
    """List all subnets"""
    session = ipam_service.get_session()
    try:
        subnets = session.query(Subnet).all()
        return subnets
    finally:
        session.close()

@app.post("/api/v1/ipam/subnets", response_model=SubnetResponse)
async def create_subnet(subnet: SubnetCreate):
    """Create new subnet"""
    session = ipam_service.get_session()
    try:
        db_subnet = Subnet(**subnet.dict())
        session.add(db_subnet)
        session.commit()
        session.refresh(db_subnet)
        return db_subnet
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/v1/ipam/ips/allocate", response_model=IPAllocationResponse)
async def allocate_ip(request: IPAllocationRequest):
    """Allocate IP address"""
    result = ipam_service.allocate_ip(
        subnet_id=request.subnet_id,
        device_id=request.device_id,
        preferred_ip=request.preferred_ip,
        notes=request.notes,
        expires_at=request.expires_at
    )
    return result

@app.post("/api/v1/ipam/ips/release")
async def release_ip(ip_address: str):
    """Release IP address"""
    result = ipam_service.release_ip(ip_address)
    return result

@app.get("/api/v1/ipam/ips/available")
async def get_available_ips(subnet_id: int):
    """Get available IPs in subnet"""
    session = ipam_service.get_session()
    try:
        subnet = session.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            raise HTTPException(status_code=404, detail="Subnet not found")
        
        network = ipaddress.ip_network(subnet.network_cidr)
        allocated_ips = session.query(IPAddress).filter(
            IPAddress.subnet_id == subnet_id,
            IPAddress.status.in_(['allocated', 'reserved'])
        ).all()
        
        allocated_set = set(ip.ip_address for ip in allocated_ips)
        available_ips = [str(ip) for ip in network.hosts() if str(ip) not in allocated_set]
        
        return {
            "subnet_id": subnet_id,
            "network_cidr": subnet.network_cidr,
            "available_ips": available_ips[:100],  # Limit to first 100
            "total_available": len(available_ips)
        }
    finally:
        session.close()

@app.get("/api/v1/ipam/devices", response_model=List[DeviceResponse])
async def list_devices():
    """List all devices"""
    session = ipam_service.get_session()
    try:
        devices = session.query(Device).all()
        return devices
    finally:
        session.close()

@app.post("/api/v1/ipam/devices", response_model=DeviceResponse)
async def create_device(device: DeviceCreate):
    """Create new device"""
    session = ipam_service.get_session()
    try:
        db_device = Device(**device.dict())
        session.add(db_device)
        session.commit()
        session.refresh(db_device)
        return db_device
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/v1/ipam/reports/usage")
async def get_usage_report():
    """Generate IP usage report"""
    session = ipam_service.get_session()
    try:
        # Get subnet usage statistics
        subnets = session.query(Subnet).all()
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
                "zone": subnet.zone,
                "total_ips": total_ips,
                "allocated": allocated_count,
                "reserved": reserved_count,
                "available": total_ips - allocated_count - reserved_count,
                "usage_percentage": round(usage_percentage, 2)
            })
        
        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "subnets": usage_report
        }
    finally:
        session.close()

if __name__ == "__main__":
    uvicorn.run(
        "baker_street_ipam_service:app",
        host="0.0.0.0",
        port=5002,
        reload=True
    )
