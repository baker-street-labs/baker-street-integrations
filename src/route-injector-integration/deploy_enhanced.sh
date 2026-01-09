#!/bin/bash

echo "🚀 Deploying Baker Street Labs Enhanced Route Injection Service"
echo "==============================================================="

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

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose -f docker-compose-simple.yml down 2>/dev/null || true

# Copy enhanced service files
echo "📋 Preparing enhanced service files..."
cp enhanced_route_injection_service.py route_injection_service.py
cp config.yaml .

# Update requirements if needed
echo "📦 Checking Python dependencies..."
if ! grep -q "PyYAML" requirements.txt; then
    echo "PyYAML==6.0.1" >> requirements.txt
fi

# Build and start enhanced services
echo "🔨 Building and starting enhanced services..."
docker-compose -f docker-compose-simple.yml up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking enhanced service health..."

# Check route injection service
if curl -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    echo "✅ Enhanced Route Injection Service: Healthy"
    
    # Test configuration endpoint
    if curl -s http://localhost:5001/api/v1/config > /dev/null 2>&1; then
        echo "✅ Configuration Endpoint: Working"
    else
        echo "⚠️  Configuration Endpoint: Not responding"
    fi
else
    echo "❌ Enhanced Route Injection Service: Unhealthy"
fi

# Check Redis
if docker exec baker-street-route-injection-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Unhealthy"
fi

echo ""
echo "🎉 Enhanced deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "   Enhanced Route Injection Service: http://localhost:5001"
echo "   Health Check: http://localhost:5001/api/v1/health"
echo "   Configuration: http://localhost:5001/api/v1/config"
echo "   Routes: http://localhost:5001/api/v1/routes"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker-compose -f docker-compose-simple.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose-simple.yml down"
echo "   Restart services: docker-compose -f docker-compose-simple.yml restart"
echo ""
echo "🧪 Test the enhanced integration:"
echo "   python3 test_enhanced_integration.py"
echo ""
echo "📋 Enhanced Features:"
echo "   ✅ Master router configuration management"
echo "   ✅ DNS API integration with mothership-dns-tool"
echo "   ✅ Automatic cyber range IP detection"
echo "   ✅ Route naming conventions"
echo "   ✅ Redis caching and persistence"
echo "   ✅ Comprehensive error handling"
echo "   ✅ Configuration management"
echo ""
echo "📋 Next Steps:"
echo "   1. Test the enhanced route injection service"
echo "   2. Verify master router connectivity"
echo "   3. Test DNS record creation with route injection"
echo "   4. Monitor routes in PAN-OS"
echo "   5. Configure backup master router if needed"
