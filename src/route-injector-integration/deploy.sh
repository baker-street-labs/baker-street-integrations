#!/bin/bash

echo "🚀 Deploying Baker Street Labs Route Injection Integration"
echo "=========================================================="

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

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check route injection service
if curl -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    echo "✅ Route Injection Service: Healthy"
else
    echo "❌ Route Injection Service: Unhealthy"
fi

# Check Redis
if docker exec baker-street-route-injection-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Unhealthy"
fi

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus: Healthy"
else
    echo "❌ Prometheus: Unhealthy"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Grafana: Healthy"
else
    echo "❌ Grafana: Unhealthy"
fi

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "   Route Injection Service: http://localhost:5001"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3000"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo ""
echo "🧪 Test the integration:"
echo "   curl -X POST http://localhost:5001/api/v1/webhook/dns-record-created \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"zone\":\"bakerstreetlabs.local\",\"fqdn\":\"test.bakerstreetlabs.local\",\"ip_address\":\"192.168.1.100\"}'"
echo ""
echo "📋 Next Steps:"
echo "   1. Test the route injection service"
echo "   2. Integrate with mothership-dns-tool"
echo "   3. Test end-to-end DNS -> Route injection workflow"
echo "   4. Monitor routes in PAN-OS"
