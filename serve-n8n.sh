#!/bin/bash

# n8n Server Management Script
# Provides robust serving with fallbacks, auto-restart, and monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_FILE="${SCRIPT_DIR}/n8n.pid"
LOG_FILE="${LOG_DIR}/n8n-server.log"
ERROR_LOG="${LOG_DIR}/n8n-error.log"
MAX_RESTARTS=5
RESTART_DELAY=10
HEALTH_CHECK_INTERVAL=30
PORT="${N8N_PORT:-5678}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Print colored output
print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Create log directory
setup_logging() {
    mkdir -p "${LOG_DIR}"
    touch "${LOG_FILE}" "${ERROR_LOG}"
}

# Check if n8n is already running
is_running() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        else
            rm -f "${PID_FILE}"
            return 1
        fi
    fi
    return 1
}

# Find the best available Node.js runtime
detect_runtime() {
    local runtimes=("bun" "npx" "npm")
    
    for runtime in "${runtimes[@]}"; do
        if command -v "${runtime}" >/dev/null 2>&1; then
            echo "${runtime}"
            return 0
        fi
    done
    
    return 1
}

# Get the appropriate start command for the runtime
get_start_command() {
    local runtime="$1"
    
    case "${runtime}" in
        bun)
            echo "bun n8n"
            ;;
        npx)
            echo "npx n8n"
            ;;
        npm)
            echo "npm run serve"
            ;;
        *)
            return 1
            ;;
    esac
}

# Health check function
health_check() {
    # n8n does not provide a /healthz endpoint by default.
    # Check the root endpoint for server health.
    if curl -f -s "http://localhost:${PORT}/" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start n8n server
start_server() {
    local runtime
    local start_command
    
    if ! runtime=$(detect_runtime); then
        print_status "${RED}" "❌ Error: No suitable Node.js runtime found (bun, npx, or npm)"
        exit 1
    fi
    
    start_command=$(get_start_command "${runtime}")
    
    print_status "${BLUE}" "🚀 Starting n8n server using ${runtime}..."
    log "INFO" "Starting n8n server with command: ${start_command}"
    
    cd "${SCRIPT_DIR}"
    
    # Start n8n in background and capture PID
    nohup ${start_command} >> "${LOG_FILE}" 2>> "${ERROR_LOG}" &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    
    # Wait a moment for startup
    sleep 5
    
    # Verify it's still running
    if ! kill -0 "${pid}" 2>/dev/null; then
        print_status "${RED}" "❌ Failed to start n8n server"
        log "ERROR" "n8n server failed to start"
        rm -f "${PID_FILE}"
        return 1
    fi
    
    print_status "${GREEN}" "✅ n8n server started successfully (PID: ${pid})"
    log "INFO" "n8n server started successfully with PID: ${pid}"
    
    # Wait for server to be ready
    local attempts=0
    local max_attempts=30
    
    print_status "${YELLOW}" "⏳ Waiting for server to be ready..."
    
    while [ ${attempts} -lt ${max_attempts} ]; do
        if health_check; then
            print_status "${GREEN}" "✅ Server is ready and responding on port ${PORT}"
            log "INFO" "Server health check passed"
            return 0
        fi
        
        sleep 2
        ((attempts++))
        
        if ! kill -0 "${pid}" 2>/dev/null; then
            print_status "${RED}" "❌ Server process died during startup"
            log "ERROR" "Server process died during startup"
            rm -f "${PID_FILE}"
            return 1
        fi
    done
    
    print_status "${YELLOW}" "⚠️  Server started but health check failed. It may still be initializing."
    log "WARNING" "Server health check failed but process is running"
    return 0
}

# Stop n8n server
stop_server() {
    if ! is_running; then
        print_status "${YELLOW}" "⚠️  n8n server is not running"
        return 0
    fi
    
    local pid=$(cat "${PID_FILE}")
    print_status "${BLUE}" "🛑 Stopping n8n server (PID: ${pid})..."
    log "INFO" "Stopping n8n server with PID: ${pid}"
    
    # Try graceful shutdown first
    if kill -TERM "${pid}" 2>/dev/null; then
        local attempts=0
        while [ ${attempts} -lt 10 ] && kill -0 "${pid}" 2>/dev/null; do
            sleep 1
            ((attempts++))
        done
        
        # Force kill if still running
        if kill -0 "${pid}" 2>/dev/null; then
            print_status "${YELLOW}" "⚠️  Graceful shutdown failed, force killing..."
            kill -KILL "${pid}" 2>/dev/null || true
        fi
    fi
    
    rm -f "${PID_FILE}"
    print_status "${GREEN}" "✅ n8n server stopped"
    log "INFO" "n8n server stopped successfully"
}

# Restart n8n server
restart_server() {
    print_status "${BLUE}" "🔄 Restarting n8n server..."
    stop_server
    sleep 2
    start_server
}

# Monitor and auto-restart functionality
monitor_server() {
    local restart_count=0
    
    print_status "${BLUE}" "👁️  Starting n8n server monitor..."
    log "INFO" "Starting server monitor with auto-restart enabled"
    
    while true; do
        if ! is_running; then
            if [ ${restart_count} -ge ${MAX_RESTARTS} ]; then
                print_status "${RED}" "❌ Maximum restart attempts (${MAX_RESTARTS}) reached. Exiting."
                log "ERROR" "Maximum restart attempts reached. Monitor exiting."
                exit 1
            fi
            
            print_status "${YELLOW}" "⚠️  Server not running. Attempting restart (${restart_count}/${MAX_RESTARTS})..."
            log "WARNING" "Server not running. Attempting restart ${restart_count}/${MAX_RESTARTS}"
            
            if start_server; then
                restart_count=0
                print_status "${GREEN}" "✅ Server restarted successfully"
                log "INFO" "Server restarted successfully"
            else
                ((restart_count++))
                print_status "${RED}" "❌ Restart failed. Waiting ${RESTART_DELAY} seconds..."
                log "ERROR" "Restart attempt failed"
                sleep ${RESTART_DELAY}
            fi
        else
            # Periodic health check
            if ! health_check; then
                print_status "${YELLOW}" "⚠️  Health check failed"
                log "WARNING" "Health check failed"
            fi
        fi
        
        sleep ${HEALTH_CHECK_INTERVAL}
    done
}

# Show server status
show_status() {
    if is_running; then
        local pid=$(cat "${PID_FILE}")
        print_status "${GREEN}" "✅ n8n server is running (PID: ${pid})"
        
        if health_check; then
            print_status "${GREEN}" "✅ Server is responding on port ${PORT}"
        else
            print_status "${YELLOW}" "⚠️  Server process is running but not responding to health checks"
        fi
        
        # Show resource usage
        if command -v ps >/dev/null 2>&1; then
            echo "Resource usage:"
            ps -p "${pid}" -o pid,ppid,pcpu,pmem,etime,cmd 2>/dev/null || true
        fi
    else
        print_status "${RED}" "❌ n8n server is not running"
    fi
}

# Show logs
show_logs() {
    local lines="${1:-50}"
    
    if [ -f "${LOG_FILE}" ]; then
        print_status "${BLUE}" "📄 Last ${lines} lines from ${LOG_FILE}:"
        tail -n "${lines}" "${LOG_FILE}"
    else
        print_status "${YELLOW}" "⚠️  Log file not found: ${LOG_FILE}"
    fi
    
    if [ -f "${ERROR_LOG}" ] && [ -s "${ERROR_LOG}" ]; then
        print_status "${RED}" "🚨 Error log (last ${lines} lines):"
        tail -n "${lines}" "${ERROR_LOG}"
    fi
}

# Cleanup function
cleanup() {
    print_status "${BLUE}" "🧹 Cleaning up..."
    stop_server
    exit 0
}

# Setup signal handlers
trap cleanup SIGINT SIGTERM

# Main script logic
main() {
    setup_logging
    
    case "${1:-start}" in
        start)
            if is_running; then
                print_status "${YELLOW}" "⚠️  n8n server is already running"
                show_status
            else
                start_server
            fi
            ;;
        stop)
            stop_server
            ;;
        restart)
            restart_server
            ;;
        status)
            show_status
            ;;
        monitor)
            if ! is_running; then
                start_server
            fi
            monitor_server
            ;;
        logs)
            show_logs "${2:-50}"
            ;;
        help|--help|-h)
            echo "Usage: $0 {start|stop|restart|status|monitor|logs [lines]|help}"
            echo ""
            echo "Commands:"
            echo "  start   - Start n8n server"
            echo "  stop    - Stop n8n server"
            echo "  restart - Restart n8n server"
            echo "  status  - Show server status"
            echo "  monitor - Start server with auto-restart monitoring"
            echo "  logs    - Show server logs (default: 50 lines)"
            echo "  help    - Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  N8N_PORT - Port for n8n server (default: 5678)"
            ;;
        *)
            print_status "${RED}" "❌ Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"