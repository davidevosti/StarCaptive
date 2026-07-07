# Raspberry Pi Stripe Captive Portal

A captive portal system for Raspberry Pi that provides WiFi access to guests for 5 minutes after Stripe payment.

## Architecture

- **WiFi Access Point**: hostapd for AP, dnsmasq for DHCP/DNS
- **Captive Portal**: Flask web application
- **Payment**: Stripe Checkout integration
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
│   ├── stripe_api.py   # Stripe payment integration
│   ├── session_mgr.py  # Session management
│   └── templates/      # HTML templates
├── config/             # Configuration files
│   ├── hostapd.conf    # WiFi AP config
│   ├── dnsmasq.conf    # DNS/DHCP config
│   └── nginx.conf      # Reverse proxy config
└── systemd/            # Systemd service files
```

## Docker Testing

Test the application locally using Docker (no Raspberry Pi required):

```bash
# Quick start
./test-docker.sh

# Or manually
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access the portal at http://localhost:7070

Configure Stripe credentials in `.env` file (created automatically on first run).

## Prerequisites

- Raspberry Pi 3B+ or later (with WiFi)
- Raspberry Pi OS (Bullseye or later)
- Stripe account and API credentials
- Internet connection for initial setup

**For Docker testing:**
- Docker and Docker Compose
- No Raspberry Pi required

## Installation

1. Flash Raspberry Pi OS and boot the device
2. Clone this repository
3. Run the installation script:
   ```bash
   sudo ./setup/install.sh
   ```
4. Configure Stripe credentials in `/etc/captive-portal/config.env`
5. Reboot the system

## Configuration

Edit `/etc/captive-portal/config.env`:
```env
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_SUCCESS_URL=http://your-domain/payment/success?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=http://your-domain/payment/cancel
SESSION_DURATION=300
```

## How It Works

1. Guest connects to the WiFi network
2. Captive portal detection redirects to payment page
3. Guest initiates Stripe payment
4. Guest completes payment on Stripe Checkout page
5. Stripe sends webhook confirmation
6. Portal grants 5 minutes of internet access
7. Access is automatically revoked after 5 minutes

## Stripe Integration

The system uses Stripe Checkout for secure payments:
1. Portal creates a Checkout Session via Stripe API
2. Guest is redirected to Stripe-hosted payment page
3. Guest enters payment details (card, Apple Pay, Google Pay, etc.)
4. Stripe processes payment and sends webhook
5. Portal grants internet access for 5 minutes

## Webhook Configuration

Configure the webhook endpoint in your Stripe Dashboard:
- URL: `http://your-domain/stripe/webhook`
- Events: `checkout.session.completed`, `checkout.session.expired`

## Security Notes

- Change default WiFi credentials
- Use HTTPS in production (Let's Encrypt)
- Regularly update system packages
- Monitor logs for suspicious activity
- Implement rate limiting for payment requests
- Keep Stripe API keys secure

## License

MIT
