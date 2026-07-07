import requests
import hmac
import hashlib
import time
import json
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class TwintAPI:
    def __init__(self, merchant_id, api_key, api_secret, callback_url):
        self.merchant_id = merchant_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.callback_url = callback_url
        self.base_url = 'https://api.twint.com'
        
    def _generate_signature(self, method, path, timestamp, body=''):
        message = f"{method}\n{path}\n{timestamp}\n{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, method, endpoint, data=None):
        path = f"/v1/{endpoint}"
        timestamp = str(int(time.time()))
        
        body = json.dumps(data) if data else ''
        signature = self._generate_signature(method, path, timestamp, body)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Merchant-ID': self.merchant_id,
            'X-API-Key': self.api_key,
            'X-Timestamp': timestamp,
            'X-Signature': signature
        }
        
        url = f"{self.base_url}{path}"
        
        try:
            if method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TWINT API request failed: {e}")
            raise Exception(f"TWINT API request failed: {str(e)}")
    
    def create_payment_request(self, amount, currency='CHF', reference=None):
        data = {
            'amount': amount,
            'currency': currency,
            'reference': reference or f"payment-{int(time.time())}",
            'callback_url': self.callback_url,
            'description': 'WiFi Access - 5 minutes',
            'merchant_id': self.merchant_id
        }
        
        try:
            result = self._make_request('POST', 'payments', data)
            
            payment_id = result.get('payment_id')
            payment_url = result.get('payment_url')
            qr_code = result.get('qr_code')
            
            logger.info(f"Payment request created: {payment_id}")
            
            return {
                'payment_id': payment_id,
                'payment_url': payment_url,
                'qr_code': qr_code
            }
            
        except Exception as e:
            logger.error(f"Failed to create payment request: {e}")
            raise
    
    def check_payment_status(self, payment_id):
        try:
            result = self._make_request('GET', f'payments/{payment_id}')
            return result.get('status')
        except Exception as e:
            logger.error(f"Failed to check payment status: {e}")
            raise
    
    def verify_webhook(self, payload, signature_header):
        expected_signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature_header)
