#!/bin/bash

#===============================================================================
# test-docker-build.sh
# Script to test the Docker backend build and verify the import fix
#
# Usage: ./scripts/test-docker-build.sh
# Run from project root
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# Configuration
#-------------------------------------------------------------------------------
PROJECT_ROOT="/Users/pwablo/Documents/Gitlab/nextjs-fastapi-rag"
IMAGE_NAME="rag-backend"
IMAGE_TAG="test"
CONTAINER_NAME="rag-backend-test"
DOCKERFILE="deploy/backend.Dockerfile"

#-------------------------------------------------------------------------------
# Color definitions
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

#-------------------------------------------------------------------------------
# Utility functions
#-------------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}${BOLD}==> $1${NC}"
}

#-------------------------------------------------------------------------------
# Cleanup function
#-------------------------------------------------------------------------------
cleanup() {
    log_step "Cleaning up test container"
    docker stop "${CONTAINER_NAME}" 2>/dev/null || true
    docker rm "${CONTAINER_NAME}" 2>/dev/null || true
    log_info "Cleanup complete"
}

trap cleanup EXIT

#-------------------------------------------------------------------------------
# Main execution
#-------------------------------------------------------------------------------
main() {
    echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║          Docker Backend Build Test                           ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"

    cd "${PROJECT_ROOT}"

    # Step 1: Build Docker image
    log_step "Building Docker image"
    if docker build -f "${DOCKERFILE}" -t "${IMAGE_NAME}:${IMAGE_TAG}" .; then
        log_success "Docker image built successfully"
    else
        log_error "Docker build failed"
        exit 1
    fi

    # Step 2: Check if .env exists for environment variables
    if [[ ! -f ".env" ]]; then
        log_error ".env file not found. Creating minimal .env for testing..."
        cat > .env.docker-test <<EOF
# Minimal environment for Docker testing
SUPABASE_URL=https://placeholder.supabase.co
SUPABASE_SERVICE_KEY=placeholder_key
OPENAI_API_KEY=placeholder_key
EOF
        log_info "Created .env.docker-test - Update with real credentials for full testing"
        ENV_FILE=".env.docker-test"
    else
        ENV_FILE=".env"
    fi

    # Step 3: Run container with import verification
    log_step "Testing Python imports in container"

    if docker run --rm \
        --env-file "${ENV_FILE}" \
        "${IMAGE_NAME}:${IMAGE_TAG}" \
        python -c "
import sys
print('Python path:', sys.path)
print('---')
print('Testing imports...')
try:
    from app.api import chat, documents, health, system
    print('✓ app.api imports successful')
except Exception as e:
    print('✗ app.api import failed:', e)
    sys.exit(1)

try:
    from packages.config import settings
    print('✓ packages.config import successful')
except Exception as e:
    print('✗ packages.config import failed:', e)
    sys.exit(1)

print('---')
print('All imports successful!')
"; then
        log_success "Python imports verified successfully"
    else
        log_error "Import verification failed"
        exit 1
    fi

    # Step 4: Test container startup
    log_step "Testing container startup"

    docker run -d \
        --name "${CONTAINER_NAME}" \
        -p 8001:8000 \
        --env-file "${ENV_FILE}" \
        "${IMAGE_NAME}:${IMAGE_TAG}"

    log_info "Container started, waiting for health check..."

    # Wait for health check (max 30 seconds)
    for i in {1..15}; do
        if curl -sf http://localhost:8001/health >/dev/null 2>&1; then
            log_success "Health check passed!"
            break
        fi

        if [[ $i -eq 15 ]]; then
            log_error "Health check timeout"
            log_info "Container logs:"
            docker logs "${CONTAINER_NAME}"
            exit 1
        fi

        sleep 2
        echo -ne "\r${YELLOW}[WAIT]${NC} Waiting for health check: ${i}/15"
    done

    echo ""  # New line after progress

    # Step 5: Check container logs for errors
    log_step "Checking container logs"

    if docker logs "${CONTAINER_NAME}" 2>&1 | grep -i "error\|exception\|failed" | grep -v "HEALTHCHECK"; then
        log_error "Found errors in container logs (see above)"
        exit 1
    else
        log_success "No errors found in container logs"
    fi

    # Final report
    log_step "Test Summary"
    echo -e "\n${GREEN}${BOLD}All tests passed!${NC}\n"
    echo "Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "Test container: http://localhost:8001"
    echo ""
    echo "To test the API manually:"
    echo "  curl http://localhost:8001/health"
    echo "  curl http://localhost:8001/docs"
    echo ""
    echo "To view logs:"
    echo "  docker logs ${CONTAINER_NAME}"
    echo ""
    echo "Container will be cleaned up on exit."
    echo "Press Ctrl+C to stop and cleanup."
    echo ""

    # Keep container running for manual testing
    read -p "Press Enter to cleanup and exit..."
}

# Run main function
main "$@"
