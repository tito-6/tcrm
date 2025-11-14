#!/bin/bash
# Quick Setup Script for CRM Lead Integration System (Linux/macOS)
# Run this script after cloning the repository for easy setup

echo "🚀 CRM Lead Integration System - Quick Setup"
echo "============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env file from template..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your API keys before starting!"
        echo "   Required: META_APP_ID, META_APP_SECRET, WHATSAPP_ACCESS_TOKEN, etc."
    else
        echo "❌ .env.example file not found!"
        exit 1
    fi
else
    echo "✅ .env file exists"
fi

# Start Docker containers
echo "🐳 Starting Docker containers..."
if docker-compose up -d; then
    echo "✅ Docker containers started successfully!"
else
    echo "❌ Failed to start Docker containers"
    exit 1
fi

# Wait a moment for services to start
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check if Odoo is accessible
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8069 | grep -q "200\|302"; then
    echo "✅ Odoo is accessible at http://localhost:8069"
else
    echo "⚠️  Odoo might still be starting up. Please wait a few more minutes."
    echo "   Check status with: docker-compose ps"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo "Next steps:"
echo "1. Access Odoo at: http://localhost:8069"
echo "2. Login with: admin / admin"
echo "3. Go to Apps and install:"
echo "   - Custom CRM Integration"
echo "   - WhatsApp Business Integration"
echo "4. Configure your API keys in the .env file"
echo ""
echo "📚 For detailed setup instructions, see README.md"

# Show container status
echo ""
echo "📊 Container Status:"
docker-compose ps