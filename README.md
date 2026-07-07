# Raspberry Pi TWINT Captive Portal

A captive portal system for Raspberry Pi that provides WiFi access to guests for 5 minutes after TWINT payment.

## Architecture

- **WiFi Access Point**: hostapd for AP, dnsmasq for DHCP/DNS
- **Captive Portal**: Flask web application
- **Payment**: TWINT API integration
- **Access Control**: iptables/nftables with time-based rules
- **Session Management**: SQLite database for tracking sessions

## Components

```
├── setup/              # Raspberry Pi setup scripts
│   ├── install.sh      # Main installation script
│   ├── ap_config.sh    # WiFi AP configuration
│   └── firewall.sh     # Firewall rules setup
├── portal/             # Flask web application
│   ├── app.py          # Main Flask application
│   ├── twint_api.py    # TWINT payment integration
│   ├── session_mgr.py  # Session management
│   └── templates/      # HTML templates
├── config/             # Configuration files
│   ├── hostapd.conf    # WiFi AP config
│   ├── dnsmasq.conf    # DNS/DHCP config
│   └── nginx.conf      # Reverse proxy config
└── systemd/            # Systemd service files
```

## Prerequisites

- Raspberry Pi 3B+ or later (with WiFi)
- Raspberry Pi OS (Bullseye or later)
- TWINT merchant account and API credentials
- Internet connection for initial setup

## Installation

1. Flash Raspberry Pi OS and boot the device
2. Clone this repository
3. Run the installation script:
   ```bash
   sudo ./setup/install.sh
   ```
4. Configure TWINT credentials in `/etc/captive-portal/config.env`
5. Reboot the system

## Configuration

Edit `/etc/captive-portal/config.env`:
```env
TWINT_MERCHANT_ID=your_merchant_id
TWINT_API_KEY=your_api_key
TWINT_API_SECRET=your_api_secret
TWINT_CALLBACK_URL=http://your-domain/twint/callback
WIFI_SSID=GuestWiFi
WIFI_PASSWORD=
SESSION_DURATION=300
```

## How It Works

1. Guest connects to the WiFi network
2. Captive portal detection redirects to payment page
3. Guest initiates TWINT payment
4. After successful payment, guest gets 5 minutes of internet access
5. Access is automatically revoked after 5 minutes

## TWINT Integration

The system uses TWINT's App-to-App payment flow:
1. Portal creates a payment request via TWINT API
2. Guest receives payment request on their phone
3. Guest confirms payment in TWINT app
4. TWINT sends webhook confirmation
5. Portal grants internet access for 5 minutes

## Security Notes

- Change default WiFi credentials
- Use HTTPS in production (Let's Encrypt)
- Regularly update system packages
- Monitor logs for suspicious activity
- Implement rate limiting for payment requests

## License

MIT
