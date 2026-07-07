# Quick Start Guide

## Development Setup (Local Testing)

For local development and testing without a Raspberry Pi:

1. Install dependencies:
```bash
cd portal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a local config file:
```bash
cp config.env.example config.env
# Edit config.env with your Stripe credentials
```

3. Run the Flask app:
```bash
python app.py
```

4. Access the portal at: http://localhost:5000

## Docker Testing

For quick testing with Docker:

```bash
./test-docker.sh
```

Access the portal at: http://localhost:7070

## Production Setup (Raspberry Pi)

1. Flash Raspberry Pi OS (Bullseye or later) onto an SD card
2. Boot the Raspberry Pi and connect to the internet
3. Clone this repository:
```bash
git clone <your-repo-url>
cd wifi
```

4. Run the installation script:
```bash
sudo ./setup/install.sh
```

5. Configure Stripe credentials:
```bash
sudo nano /etc/captive-portal/config.env
```

6. Reboot:
```bash
sudo reboot
```

7. Connect to the "GuestWiFi" network from any device
8. The captive portal should appear automatically

## Testing Stripe Integration

### Test Mode

For testing without real payments, use Stripe test mode:

1. Update `config.env` with test credentials (sk_test_...)
2. Use Stripe test card numbers (e.g., 4242 4242 4242 4242)
3. Check logs: `sudo journalctl -u captive-portal -f`

### Manual Testing

Test the payment flow:
```bash
curl -X POST http://localhost:5000/payment/initiate \
  -H "Content-Type: application/json"
```

Check session status:
```bash
curl http://localhost:5000/session/check
```

## Stripe Webhook Setup

For production, configure webhooks in your Stripe Dashboard:

1. Go to Developers > Webhooks
2. Add endpoint: `https://your-domain.com/stripe/webhook`
3. Select events:
   - `checkout.session.completed`
   - `checkout.session.expired`
4. Copy the webhook signing secret to your config

## Troubleshooting

### WiFi AP not starting
```bash
sudo systemctl status hostapd
sudo journalctl -u hostapd -n 50
```

### Portal not accessible
```bash
sudo systemctl status captive-portal
sudo journalctl -u captive-portal -n 50
sudo systemctl status nginx
```

### Firewall issues
```bash
sudo iptables -L -v -n
sudo iptables -t nat -L -v -n
```

### Database issues
```bash
sqlite3 /var/lib/captive-portal/sessions.db
.tables
SELECT * FROM sessions;
```

### Stripe webhook not working
```bash
# Check webhook logs
sudo journalctl -u captive-portal -f | grep webhook

# Test webhook signature
curl -X POST http://localhost:5000/stripe/webhook \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: test_signature" \
  -d '{"type": "checkout.session.completed"}'
```

## Logs

View all logs:
```bash
sudo journalctl -u captive-portal -f
sudo journalctl -u hostapd -f
sudo journalctl -u dnsmasq -f
```

## Security Checklist

- [ ] Change default WiFi SSID
- [ ] Set strong Stripe API credentials
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Configure firewall rules
- [ ] Regular system updates
- [ ] Monitor logs for suspicious activity
- [ ] Implement rate limiting
- [ ] Backup database regularly
- [ ] Configure Stripe webhooks with signing secret
