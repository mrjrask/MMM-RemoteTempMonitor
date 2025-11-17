#!/bin/bash
#
# Installation script for Remote Temperature Monitor Service
# This script installs and configures the temperature broadcaster on Raspberry Pi
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/remote-temp-monitor"
SERVICE_FILE="temp-monitor.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE}"
SCRIPT_NAME="temp_broadcaster.py"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Remote Temperature Monitor${NC}"
echo -e "${GREEN}Installation Script${NC}"
echo -e "${GREEN}================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if running on Raspberry Pi (optional warning)
if [ ! -f "/sys/class/thermal/thermal_zone0/temp" ]; then
    echo -e "${YELLOW}WARNING: Temperature sensor not found at /sys/class/thermal/thermal_zone0/temp${NC}"
    echo -e "${YELLOW}This script is designed for Raspberry Pi. Continue anyway? (y/n)${NC}"
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# Create installation directory
echo -e "${GREEN}Creating installation directory...${NC}"
mkdir -p "${INSTALL_DIR}"

# Copy Python script
echo -e "${GREEN}Installing temperature broadcaster script...${NC}"
cp "${SCRIPT_NAME}" "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/${SCRIPT_NAME}"

# Copy and enable systemd service
echo -e "${GREEN}Installing systemd service...${NC}"
cp "${SERVICE_FILE}" "${SERVICE_PATH}"

# Reload systemd
echo -e "${GREEN}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable service to start on boot
echo -e "${GREEN}Enabling service to start on boot...${NC}"
systemctl enable "${SERVICE_FILE}"

# Start the service
echo -e "${GREEN}Starting temperature monitor service...${NC}"
systemctl start "${SERVICE_FILE}"

# Check status
echo
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo
echo "Service Status:"
systemctl status "${SERVICE_FILE}" --no-pager || true
echo
echo -e "${GREEN}Useful commands:${NC}"
echo "  - View status:  sudo systemctl status ${SERVICE_FILE}"
echo "  - View logs:    sudo journalctl -u ${SERVICE_FILE} -f"
echo "  - Stop service: sudo systemctl stop ${SERVICE_FILE}"
echo "  - Start service: sudo systemctl start ${SERVICE_FILE}"
echo "  - Restart service: sudo systemctl restart ${SERVICE_FILE}"
echo
echo -e "${GREEN}The service is now broadcasting temperature data on UDP port 9876${NC}"
