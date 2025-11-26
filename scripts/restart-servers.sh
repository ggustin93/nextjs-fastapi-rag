#!/bin/bash

#===============================================================================
# restart-servers.sh
# Production-quality script to restart development servers for nextjs-fastapi-rag
#
# Usage: ./scripts/restart-servers.sh
# Run from project root: /Users/pwablo/Documents/Gitlab/nextjs-fastapi-rag/
#
# Services:
#   - Backend:  FastAPI (Python 3.9) on port 8000
#   - Frontend: Next.js on port 3000
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# Configuration
#-------------------------------------------------------------------------------
PROJECT_ROOT="/Users/pwablo/Documents/Gitlab/nextjs-fastapi-rag"
BACKEND_DIR="${PROJECT_ROOT}/services/api"
FRONTEND_DIR="${PROJECT_ROOT}/services/web"
LOGS_DIR="${PROJECT_ROOT}/logs"

BACKEND_PORT=8000
FRONTEND_PORT=3000

BACKEND_HEALTH_URL="http://localhost:${BACKEND_PORT}/health"
FRONTEND_HEALTH_URL="http://localhost:${FRONTEND_PORT}/"

HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=2

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKEND_LOG="${LOGS_DIR}/backend_${TIMESTAMP}.log"
FRONTEND_LOG="${LOGS_DIR}/frontend_${TIMESTAMP}.log"

#-------------------------------------------------------------------------------
# Color definitions
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}${BOLD}==> $1${NC}"
}

#-------------------------------------------------------------------------------
# Kill processes on a specific port
#-------------------------------------------------------------------------------
kill_port() {
    local port=$1
    local pids

    pids=$(lsof -ti :"${port}" 2>/dev/null || true)

    if [[ -n "${pids}" ]]; then
        log_info "Killing processes on port ${port}: ${pids}"
        echo "${pids}" | xargs kill -9 2>/dev/null || true
        sleep 1

        # Verify processes are killed
        if lsof -ti :"${port}" >/dev/null 2>&1; then
            log_error "Failed to kill all processes on port ${port}"
            return 1
        fi
        log_success "Port ${port} is now free"
    else
        log_info "Port ${port} is already free"
    fi
}

#-------------------------------------------------------------------------------
# Health check with retry logic
#-------------------------------------------------------------------------------
wait_for_health() {
    local url=$1
    local service_name=$2
    local timeout=$3
    local interval=$4
    local elapsed=0

    log_info "Waiting for ${service_name} to become healthy..."

    while [[ ${elapsed} -lt ${timeout} ]]; do
        if curl -s -f -o /dev/null "${url}" 2>/dev/null; then
            log_success "${service_name} is healthy!"
            return 0
        fi

        sleep "${interval}"
        elapsed=$((elapsed + interval))
        echo -ne "\r${YELLOW}[WAIT]${NC} ${service_name}: ${elapsed}s / ${timeout}s"
    done

    echo ""
    log_error "${service_name} failed to respond within ${timeout} seconds"
    return 1
}

#-------------------------------------------------------------------------------
# Start backend service
#-------------------------------------------------------------------------------
start_backend() {
    log_step "Starting Backend (FastAPI on port ${BACKEND_PORT})"

    if [[ ! -d "${BACKEND_DIR}" ]]; then
        log_error "Backend directory not found: ${BACKEND_DIR}"
        return 1
    fi

    # Check for .venv in backend dir or project root
    if [[ ! -d "${BACKEND_DIR}/.venv" ]] && [[ ! -d "${PROJECT_ROOT}/.venv" ]]; then
        log_error "Virtual environment not found in ${BACKEND_DIR}/.venv or ${PROJECT_ROOT}/.venv"
        return 1
    fi

    cd "${BACKEND_DIR}"

    # Determine which venv to use
    local VENV_DIR
    if [[ -d "${BACKEND_DIR}/.venv" ]]; then
        VENV_DIR="${BACKEND_DIR}/.venv"
    elif [[ -d "${PROJECT_ROOT}/.venv" ]]; then
        VENV_DIR="${PROJECT_ROOT}/.venv"
    else
        log_error "No virtual environment found"
        return 1
    fi

    # Start uvicorn using venv's Python directly (more reliable than sourcing activate)
    PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}" \
    "${VENV_DIR}/bin/python" -m uvicorn app.main:app \
        --reload --host 0.0.0.0 --port "${BACKEND_PORT}" \
        >> "${BACKEND_LOG}" 2>&1 &

    BACKEND_PID=$!

    # Small delay to check if process started
    sleep 2

    if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
        log_error "Backend failed to start. Check logs: ${BACKEND_LOG}"
        return 1
    fi

    log_info "Backend started with PID: ${BACKEND_PID}"
    log_info "Logs: ${BACKEND_LOG}"

    echo "${BACKEND_PID}" > "${LOGS_DIR}/backend.pid"
}

#-------------------------------------------------------------------------------
# Start frontend service
#-------------------------------------------------------------------------------
start_frontend() {
    log_step "Starting Frontend (Next.js on port ${FRONTEND_PORT})"

    if [[ ! -d "${FRONTEND_DIR}" ]]; then
        log_error "Frontend directory not found: ${FRONTEND_DIR}"
        return 1
    fi

    if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
        log_error "package.json not found: ${FRONTEND_DIR}/package.json"
        return 1
    fi

    cd "${FRONTEND_DIR}"

    # Start Next.js dev server in background
    npm run dev >> "${FRONTEND_LOG}" 2>&1 &

    FRONTEND_PID=$!

    # Small delay to check if process started
    sleep 2

    if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        log_error "Frontend failed to start. Check logs: ${FRONTEND_LOG}"
        return 1
    fi

    log_info "Frontend started with PID: ${FRONTEND_PID}"
    log_info "Logs: ${FRONTEND_LOG}"

    echo "${FRONTEND_PID}" > "${LOGS_DIR}/frontend.pid"
}

#-------------------------------------------------------------------------------
# Cleanup function for script exit
#-------------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Script failed with exit code: ${exit_code}"
        log_info "Check logs in: ${LOGS_DIR}/"
    fi
    cd "${PROJECT_ROOT}"
}

trap cleanup EXIT

#-------------------------------------------------------------------------------
# Main execution
#-------------------------------------------------------------------------------
main() {
    echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║          nextjs-fastapi-rag - Server Restart                 ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"

    log_info "Timestamp: ${TIMESTAMP}"
    log_info "Project root: ${PROJECT_ROOT}"

    # Ensure logs directory exists
    mkdir -p "${LOGS_DIR}"

    # Step 1: Clean shutdown of existing processes
    log_step "Cleaning up existing processes"
    kill_port "${BACKEND_PORT}"
    kill_port "${FRONTEND_PORT}"

    # Step 2: Start backend
    start_backend

    # Step 3: Start frontend
    start_frontend

    # Step 4: Health checks
    log_step "Running health checks"

    backend_healthy=false
    frontend_healthy=false

    if wait_for_health "${BACKEND_HEALTH_URL}" "Backend" "${HEALTH_CHECK_TIMEOUT}" "${HEALTH_CHECK_INTERVAL}"; then
        backend_healthy=true
    fi

    if wait_for_health "${FRONTEND_HEALTH_URL}" "Frontend" "${HEALTH_CHECK_TIMEOUT}" "${HEALTH_CHECK_INTERVAL}"; then
        frontend_healthy=true
    fi

    # Step 5: Final status report
    log_step "Status Report"

    echo -e "\n${BOLD}Service Status:${NC}"
    echo "─────────────────────────────────────────────────────────────"

    if [[ "${backend_healthy}" == true ]]; then
        echo -e "  Backend:  ${GREEN}RUNNING${NC} - PID: $(cat "${LOGS_DIR}/backend.pid" 2>/dev/null || echo 'N/A')"
        echo -e "            URL: http://localhost:${BACKEND_PORT}"
        echo -e "            Health: ${BACKEND_HEALTH_URL}"
    else
        echo -e "  Backend:  ${RED}FAILED${NC}"
    fi

    if [[ "${frontend_healthy}" == true ]]; then
        echo -e "  Frontend: ${GREEN}RUNNING${NC} - PID: $(cat "${LOGS_DIR}/frontend.pid" 2>/dev/null || echo 'N/A')"
        echo -e "            URL: http://localhost:${FRONTEND_PORT}"
    else
        echo -e "  Frontend: ${RED}FAILED${NC}"
    fi

    echo "─────────────────────────────────────────────────────────────"

    echo -e "\n${BOLD}Log Files:${NC}"
    echo "  Backend:  ${BACKEND_LOG}"
    echo "  Frontend: ${FRONTEND_LOG}"

    echo -e "\n${BOLD}Commands:${NC}"
    echo "  View backend logs:  tail -f ${BACKEND_LOG}"
    echo "  View frontend logs: tail -f ${FRONTEND_LOG}"
    echo "  Stop services:      kill \$(cat ${LOGS_DIR}/backend.pid) \$(cat ${LOGS_DIR}/frontend.pid)"

    # Exit with appropriate code
    if [[ "${backend_healthy}" == true ]] && [[ "${frontend_healthy}" == true ]]; then
        echo -e "\n${GREEN}${BOLD}All services started successfully!${NC}\n"
        exit 0
    else
        echo -e "\n${RED}${BOLD}Some services failed to start. Check logs for details.${NC}\n"
        exit 1
    fi
}

# Run main function
main "$@"
