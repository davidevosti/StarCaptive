#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ ! -f .env ]; then
    log_warn "Creating .env file from template..."
    cat > .env << 'EOF'
TWINT_MERCHANT_ID=test_merchant_id
TWINT_API_KEY=test_api_key
TWINT_API_SECRET=test_api_secret
TWINT_CALLBACK_URL=http://localhost:5000/twint/callback
SESSION_DURATION=300
LOG_LEVEL=DEBUG
EOF
    log_warn "Edit .env with your TWINT credentials for production use"
fi

log_info "Building Docker image..."
docker-compose build

log_info "Starting container..."
docker-compose up -d

log_info "Waiting for service to start..."
sleep 3

log_info "Testing health endpoint..."
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    log_info "Service is running!"
    log_info "Access the portal at: http://localhost:5000"
    log_info "View logs: docker-compose logs -f"
    log_info "Stop: docker-compose down"
else
    log_error "Service failed to start. Check logs:"
    docker-compose logs
fi
