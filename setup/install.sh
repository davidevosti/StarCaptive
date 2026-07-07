#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="/etc/captive-portal"

log_info "Starting captive portal installation..."

log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

log_info "Installing required packages..."
apt-get install -y \
    hostapd \
    dnsmasq \
    iptables \
    iptables-persistent \
    nginx \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3 \
    curl \
    wget \
    git

log_info "Creating configuration directory..."
mkdir -p "$CONFIG_DIR"
chmod 755 "$CONFIG_DIR"

log_info "Setting up Python virtual environment..."
python3 -m venv "$CONFIG_DIR/venv"
source "$CONFIG_DIR/venv/bin/activate"

log_info "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r "$PROJECT_DIR/portal/requirements.txt"

log_info "Configuring WiFi access point..."
bash "$SCRIPT_DIR/ap_config.sh"

log_info "Setting up firewall rules..."
bash "$SCRIPT_DIR/firewall.sh"

log_info "Creating default configuration..."
if [ ! -f "$CONFIG_DIR/config.env" ]; then
    cat > "$CONFIG_DIR/config.env" << 'EOF'
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_SUCCESS_URL=http://192.168.4.1/payment/success?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=http://192.168.4.1/payment/cancel
WIFI_SSID=GuestWiFi
WIFI_PASSWORD=
SESSION_DURATION=300
PORTAL_HOST=0.0.0.0
PORTAL_PORT=5000
DATABASE_PATH=/var/lib/captive-portal/sessions.db
LOG_LEVEL=INFO
EOF
    chmod 600 "$CONFIG_DIR/config.env"
    log_warn "Please edit $CONFIG_DIR/config.env with your Stripe credentials"
fi

log_info "Creating data directory..."
mkdir -p /var/lib/captive-portal
chmod 755 /var/lib/captive-portal

log_info "Installing systemd services..."
cp "$PROJECT_DIR/systemd/captive-portal.service" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/session-cleaner.service" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/session-cleaner.timer" /etc/systemd/system/

systemctl daemon-reload

log_info "Configuring nginx..."
cp "$PROJECT_DIR/config/nginx.conf" /etc/nginx/sites-available/captive-portal
ln -sf /etc/nginx/sites-available/captive-portal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

log_info "Enabling and starting services..."
systemctl enable hostapd
systemctl enable dnsmasq
systemctl enable nginx
systemctl enable captive-portal
systemctl enable session-cleaner.timer

log_info "Setting up IP forwarding..."
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99_captive_portal.conf
sysctl -p /etc/sysctl.d/99_captive_portal.conf

log_info "Saving firewall rules..."
netfilter-persistent save

log_info "Installation complete!"
log_warn "Next steps:"
echo "  1. Edit $CONFIG_DIR/config.env with your Stripe credentials"
echo "  2. Configure webhook endpoint in Stripe Dashboard"
echo "  3. Reboot the system: sudo reboot"
echo "  4. Connect to WiFi network 'GuestWiFi'"
echo "  5. Test the captive portal"
