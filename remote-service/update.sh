#!/bin/bash
#
# Update script for Remote Temperature Monitor Service
# This script updates the temperature broadcaster on Raspberry Pi
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
echo -e "${GREEN}Update Script${NC}"
echo -e "${GREEN}================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if service is installed
if [ ! -f "${SERVICE_PATH}" ]; then
    echo -e "${RED}ERROR: Service not found. Please run install.sh first.${NC}"
    exit 1
fi

# Stop the service
echo -e "${GREEN}Stopping temperature monitor service...${NC}"
systemctl stop "${SERVICE_FILE}"

# Backup current script
if [ -f "${INSTALL_DIR}/${SCRIPT_NAME}" ]; then
    echo -e "${GREEN}Backing up current script...${NC}"
    cp "${INSTALL_DIR}/${SCRIPT_NAME}" "${INSTALL_DIR}/${SCRIPT_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Copy updated Python script
echo -e "${GREEN}Installing updated broadcaster script...${NC}"
cp "${SCRIPT_NAME}" "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/${SCRIPT_NAME}"

# Update systemd service file (in case it changed)
echo -e "${GREEN}Updating systemd service file...${NC}"
cp "${SERVICE_FILE}" "${SERVICE_PATH}"

# Reload systemd
echo -e "${GREEN}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Start the service
echo -e "${GREEN}Starting temperature monitor service...${NC}"
systemctl start "${SERVICE_FILE}"

# Check status
echo
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo
echo "Service Status:"
systemctl status "${SERVICE_FILE}" --no-pager || true
echo
echo -e "${GREEN}The service has been updated and restarted.${NC}"
echo -e "${GREEN}It should now broadcast model and RAM information.${NC}"
echo
echo "To view logs in real-time:"
echo "  sudo journalctl -u ${SERVICE_FILE} -f"
echo
