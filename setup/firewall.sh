#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

WIFI_INTERFACE="wlan0"
INTERNET_INTERFACE="eth0"
PORTAL_IP="192.168.4.1"

log_info "Setting up firewall rules..."

log_info "Flushing existing rules..."
iptables -F
iptables -t nat -F
iptables -X

log_info "Setting default policies..."
iptables -P INPUT ACCEPT
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

log_info "Allowing loopback..."
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

log_info "Allowing established connections..."
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

log_info "Configuring NAT..."
iptables -t nat -A POSTROUTING -o $INTERNET_INTERFACE -j MASQUERADE

log_info "Creating captive portal chains..."
iptables -N CAPTIVE_CHECK
iptables -N ALLOWED_CLIENTS

log_info "Setting up captive portal redirect..."
iptables -A FORWARD -i $WIFI_INTERFACE -j CAPTIVE_CHECK

iptables -A CAPTIVE_CHECK -j ALLOWED_CLIENTS
iptables -A CAPTIVE_CHECK -d $PORTAL_IP -p tcp --dport 80 -j ACCEPT
iptables -A CAPTIVE_CHECK -d $PORTAL_IP -p tcp --dport 443 -j ACCEPT

iptables -A CAPTIVE_CHECK -p tcp --dport 53 -j ACCEPT
iptables -A CAPTIVE_CHECK -p udp --dport 53 -j ACCEPT

iptables -A CAPTIVE_CHECK -p icmp -j ACCEPT

iptables -A CAPTIVE_CHECK -j REJECT --reject-with tcp-reset

log_info "Creating session cleaner script..."
cat > /usr/local/bin/captive-portal-allow.sh << 'EOF'
#!/bin/bash
CLIENT_IP=$1
ACTION=$2

if [ -z "$CLIENT_IP" ] || [ -z "$ACTION" ]; then
    echo "Usage: $0 <client_ip> <add|remove>"
    exit 1
fi

if [ "$ACTION" = "add" ]; then
    iptables -I ALLOWED_CLIENTS -s $CLIENT_IP -j ACCEPT
    echo "Added $CLIENT_IP to allowed clients"
elif [ "$ACTION" = "remove" ]; then
    iptables -D ALLOWED_CLIENTS -s $CLIENT_IP -j ACCEPT 2>/dev/null || true
    echo "Removed $CLIENT_IP from allowed clients"
else
    echo "Invalid action: $ACTION"
    exit 1
fi
EOF

chmod +x /usr/local/bin/captive-portal-allow.sh

log_info "Firewall configuration complete!"
