import stripe
import logging
import os

logger = logging.getLogger(__name__)


class StripeAPI:
    def __init__(self, api_key, webhook_secret, success_url, cancel_url):
        stripe.api_key = api_key
        self.webhook_secret = webhook_secret
        self.success_url = success_url
        self.cancel_url = cancel_url
        
    def create_checkout_session(self, amount, currency='chf', client_ip=None, metadata=None):
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': 'WiFi Access - 5 minutes',
                            'description': 'Internet access for 5 minutes',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                metadata=metadata or {},
                client_reference_id=client_ip,
            )
            
            logger.info(f"Checkout session created: {session.id} for {client_ip}")
            
            return {
                'session_id': session.id,
                'checkout_url': session.url
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise Exception(f"Payment initiation failed: {str(e)}")
    
    def verify_webhook(self, payload, sig_header):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Webhook payload error: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature error: {e}")
            raise
    
    def get_session(self, session_id):
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve session: {e}")
            raise
