#!/bin/bash

# n8n Service Installation Script
# Installs n8n as a systemd service for lightweight server deployment

set -euo pipefail

# Configuration
INSTALL_DIR="/opt/n8n"
SERVICE_USER="n8n"
SERVICE_GROUP="n8n"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_status "${RED}" "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Create service user
create_user() {
    if ! id "${SERVICE_USER}" &>/dev/null; then
        print_status "${BLUE}" "👤 Creating service user: ${SERVICE_USER}"
        useradd --system --create-home --home-dir "${INSTALL_DIR}" \
                --shell /bin/bash --comment "n8n Service User" "${SERVICE_USER}"
        usermod -aG "${SERVICE_GROUP}" "${SERVICE_USER}" 2>/dev/null || true
    else
        print_status "${YELLOW}" "User ${SERVICE_USER} already exists"
    fi
}

# Install files
install_files() {
    print_status "${BLUE}" "Installing files to ${INSTALL_DIR}"

		if [ ! -e "$INSTALL_DIR" ]; then
				ln -s "$SCRIPT_DIR" "$INSTALL_DIR"
				mkdir -p "$INSTALL_DIR/.n8n"
		fi

    # Set ownership and permissions
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}"
    chmod +x "${INSTALL_DIR}/scripts/serve-n8n.mjs"
    chmod 755 "${INSTALL_DIR}"
    chmod 750 "${INSTALL_DIR}/logs" "${INSTALL_DIR}/.n8n"
}

# Install systemd service
install_service() {
    print_status "${BLUE}" "Installing systemd service"

    # Update service file paths
    sed -i "s|/opt/n8n|${INSTALL_DIR}|g" "${INSTALL_DIR}/n8n.service"
    sed -i "s|User=n8n|User=${SERVICE_USER}|g" "${INSTALL_DIR}/n8n.service"
    sed -i "s|Group=n8n|Group=${SERVICE_GROUP}|g" "${INSTALL_DIR}/n8n.service"

    # Install service file
    cp "${INSTALL_DIR}/n8n.service" /etc/systemd/system/
    systemctl daemon-reload

    print_status "${GREEN}" "Service installed successfully"
}

# Install dependencies
install_dependencies() {
    print_status "${BLUE}" "Checking dependencies"

    # Check for Node.js runtime
    local has_runtime=false

    if command -v "node" >/dev/null 2>&1; then
					has_runtime=true
					break
		fi

    if [ "${has_runtime}" = false ]; then
        print_status "${YELLOW}" "No Node.js runtime found. Installing Node.js..."

        # Install Node.js using NodeSource repository
        curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
        apt-get install -y nodejs

        print_status "${GREEN}" "Node.js installed"
    fi

    # Check for curl (needed for health checks)
    if ! command -v curl >/dev/null 2>&1; then
        print_status "${BLUE}" "Installing curl..."
        apt-get update
        apt-get install -y curl
    fi
}

# Main installation function
main() {
    print_status "${BLUE}" "Installing n8n service..."

    check_root
    install_dependencies
    create_user
    install_files
    install_service

    print_status "${GREEN}" "Installation completed successfully!"
    echo
    print_status "${BLUE}" "Next steps:"
    echo "  1. Enable the service: sudo systemctl enable n8n"
    echo "  2. Start the service: sudo systemctl start n8n"
    echo "  3. Check status: sudo systemctl status n8n"
    echo "  4. View logs: sudo journalctl -u n8n -f"
    echo
    print_status "${BLUE}" "Access n8n at: http://localhost:5678"
    echo
    print_status "${YELLOW}" "Remember to configure firewall rules if needed"
}

# Show help
show_help() {
    echo "n8n Service Installation Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --install-dir DIR    Installation directory (default: /opt/n8n)"
    echo "  --user USER          Service user (default: n8n)"
    echo "  --group GROUP        Service group (default: n8n)"
    echo "  --help, -h           Show this help message"
    echo
    echo "This script will:"
    echo "  - Create a service user"
    echo "  - Install n8n files to the specified directory"
    echo "  - Create a systemd service"
    echo "  - Install required dependencies"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --user)
            SERVICE_USER="$2"
            shift 2
            ;;
        --group)
            SERVICE_GROUP="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_status "${RED}" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

main