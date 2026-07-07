#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info "Configuring WiFi access point..."

WIFI_INTERFACE="wlan0"

log_info "Stopping services..."
systemctl stop hostapd || true
systemctl stop dnsmasq || true

log_info "Configuring wlan0 interface..."
cat > /etc/dhcpcd.conf << 'EOF'
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

log_info "Configuring hostapd..."
cp "$PROJECT_DIR/config/hostapd.conf" /etc/hostapd/hostapd.conf

log_info "Setting hostapd defaults..."
cat > /etc/default/hostapd << 'EOF'
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

log_info "Configuring dnsmasq..."
cp "$PROJECT_DIR/config/dnsmasq.conf" /etc/dnsmasq.conf

log_info "Blocking hostapd/dnsmasq updates..."
cat > /etc/apt/preferences.d/hostapd << 'EOF'
Package: hostapd
Pin: release *
Pin-Priority: -10
EOF

cat > /etc/apt/preferences.d/dnsmasq << 'EOF'
Package: dnsmasq
Pin: release *
Pin-Priority: -10
EOF

log_info "Unmasking services..."
systemctl unmask hostapd
systemctl unmask dnsmasq

log_info "WiFi AP configuration complete!"
