# Quick Setup Script for CRM Lead Integration System
# Run this script after cloning the repository for easy setup

Write-Host "🚀 CRM Lead Integration System - Quick Setup" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker is available" -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Please edit .env file with your API keys before starting!" -ForegroundColor Yellow
        Write-Host "   Required: META_APP_ID, META_APP_SECRET, WHATSAPP_ACCESS_TOKEN, etc." -ForegroundColor Yellow
    } else {
        Write-Host "❌ .env.example file not found!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}

# Start Docker containers
Write-Host "🐳 Starting Docker containers..." -ForegroundColor Yellow
try {
    docker-compose up -d
    Write-Host "✅ Docker containers started successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start Docker containers: $_" -ForegroundColor Red
    exit 1
}

# Wait a moment for services to start
Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if Odoo is accessible
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8069" -TimeoutSec 30 -ErrorAction Stop
    Write-Host "✅ Odoo is accessible at http://localhost:8069" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Odoo might still be starting up. Please wait a few more minutes." -ForegroundColor Yellow
    Write-Host "   Check status with: docker-compose ps" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Access Odoo at: http://localhost:8069" -ForegroundColor White
Write-Host "2. Login with: admin / admin" -ForegroundColor White
Write-Host "3. Go to Apps and install:" -ForegroundColor White
Write-Host "   - Custom CRM Integration" -ForegroundColor Cyan
Write-Host "   - WhatsApp Business Integration" -ForegroundColor Cyan
Write-Host "4. Configure your API keys in the .env file" -ForegroundColor White
Write-Host ""
Write-Host "📚 For detailed setup instructions, see README.md" -ForegroundColor Yellow

# Show container status
Write-Host ""
Write-Host "📊 Container Status:" -ForegroundColor Yellow
docker-compose ps