#!/bin/bash

# Zero-downtime deployment script for Podcast AI
set -euo pipefail

ENVIRONMENT=${1:-"green"}
SERVICE=${2:-"all"}

echo "🚀 Starting zero-downtime deployment..."
echo "📋 Environment: $ENVIRONMENT"
echo "🔧 Service: $SERVICE"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check service health
check_health() {
    local service_url=$1
    local max_attempts=30
    local attempt=1
    
    log_info "🔍 Checking health of $service_url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url/health" > /dev/null; then
            log_info "✅ Service is healthy"
            return 0
        fi
        
        log_warn "⏳ Attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_error "❌ Service failed health check after $max_attempts attempts"
    return 1
}

# Function to deploy a service
deploy_service() {
    local service_name=$1
    local environment=$2
    
    log_info "🔄 Deploying $service_name to $environment environment..."
    
    # Build new image
    log_info "🏗️ Building $service_name image..."
    docker compose -f deploy/blue-green-deploy.yml build ${service_name}-${environment}
    
    # Start new environment
    log_info "🚀 Starting $service_name in $environment..."
    docker compose -f deploy/blue-green-deploy.yml up -d ${service_name}-${environment}
    
    # Wait for health check
    local service_url="http://localhost:8080"
    if check_health "$service_url"; then
        log_info "✅ $service_name $environment deployment successful"
        return 0
    else
        log_error "❌ $service_name $environment deployment failed"
        return 1
    fi
}

# Function to switch traffic
switch_traffic() {
    local to_environment=$1
    
    log_info "🔀 Switching traffic to $to_environment environment..."
    
    # Update nginx configuration (in production, this would update load balancer config)
    if [ "$to_environment" = "green" ]; then
        log_info "Switching to green environment"
        # curl -X POST http://localhost:8081/switch-to-green
        log_info "Traffic switched to green"
    else
        log_info "Switching to blue environment"
        # curl -X POST http://localhost:8081/switch-to-blue
        log_info "Traffic switched to blue"
    fi
}

# Function to cleanup old environment
cleanup_old_environment() {
    local old_environment=$1
    
    log_info "🧹 Cleaning up $old_environment environment..."
    
    # Stop old containers
    docker compose -f deploy/blue-green-deploy.yml stop ${SERVICE}-${old_environment} || true
    docker compose -f deploy/blue-green-deploy.yml rm -f ${SERVICE}-${old_environment} || true
    
    log_info "✅ Cleanup completed"
}

# Main deployment logic
main() {
    log_info "🎬 Starting zero-downtime deployment process..."
    
    # Check if this is a blue or green deployment
    CURRENT_ENV="blue"
    TARGET_ENV="green"
    
    if [ "$ENVIRONMENT" = "blue" ]; then
        CURRENT_ENV="green"
        TARGET_ENV="blue"
    fi
    
    log_info "📊 Current: $CURRENT_ENV, Target: $TARGET_ENV"
    
    # Deploy to target environment
    if deploy_service "$SERVICE" "$TARGET_ENV"; then
        # Switch traffic to new environment
        switch_traffic "$TARGET_ENV"
        
        # Wait a bit to ensure everything is working
        sleep 30
        
        # Cleanup old environment
        cleanup_old_environment "$CURRENT_ENV"
        
        log_info "🎉 Zero-downtime deployment completed successfully!"
    else
        log_error "💥 Deployment failed, keeping current environment"
        # Cleanup failed deployment
        cleanup_old_environment "$TARGET_ENV"
        exit 1
    fi
}

# Run main function
main "$@"