import os
import logging
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from dotenv import load_dotenv

from stripe_api import StripeAPI
from session_mgr import SessionManager

load_dotenv('/etc/captive-portal/config.env')

app = Flask(__name__)
app.secret_key = os.urandom(24)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

stripe_api = StripeAPI(
    api_key=os.getenv('STRIPE_SECRET_KEY'),
    webhook_secret=os.getenv('STRIPE_WEBHOOK_SECRET'),
    success_url=os.getenv('STRIPE_SUCCESS_URL', 'http://192.168.4.1/payment/success?session_id={CHECKOUT_SESSION_ID}'),
    cancel_url=os.getenv('STRIPE_CANCEL_URL', 'http://192.168.4.1/payment/cancel')
)

session_mgr = SessionManager(
    db_path=os.getenv('DATABASE_PATH', '/var/lib/captive-portal/sessions.db'),
    duration=int(os.getenv('SESSION_DURATION', 300))
)


@app.before_request
def log_request():
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")


@app.route('/')
def index():
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    logger.info(f"Portal access from {client_ip}")
    
    active_session = session_mgr.get_active_session(client_ip)
    if active_session:
        return render_template('active.html', 
                             expires_at=active_session['expires_at'],
                             client_ip=client_ip)
    
    return render_template('index.html', client_ip=client_ip)


@app.route('/captive/check')
def captive_check():
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    active_session = session_mgr.get_active_session(client_ip)
    
    if active_session:
        return '', 204
    else:
        return redirect(url_for('index'))


@app.route('/generate_204')
def generate_204():
    return redirect(url_for('captive_check'))


@app.route('/hotspot-detect.html')
def hotspot_detect():
    return redirect(url_for('index'))


@app.route('/connecttest.txt')
def connect_test():
    return redirect(url_for('index'))


@app.route('/ncsi.txt')
def ncsi_test():
    return redirect(url_for('index'))


@app.route('/payment/initiate', methods=['POST'])
def initiate_payment():
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    
    active_session = session_mgr.get_active_session(client_ip)
    if active_session:
        return jsonify({'error': 'Already has active session'}), 400
    
    try:
        checkout_session = stripe_api.create_checkout_session(
            amount=1.00,
            currency='chf',
            client_ip=client_ip,
            metadata={'client_ip': client_ip}
        )
        
        session['checkout_session_id'] = checkout_session['session_id']
        session['client_ip'] = client_ip
        
        return jsonify({
            'checkout_url': checkout_session['checkout_url'],
            'session_id': checkout_session['session_id']
        })
        
    except Exception as e:
        logger.error(f"Payment initiation failed: {e}")
        return jsonify({'error': 'Payment initiation failed'}), 500


@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe_api.verify_webhook(payload, sig_header)
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    if event['type'] == 'checkout.session.completed':
        checkout_session = event['data']['object']
        client_ip = checkout_session.get('client_reference_id')
        session_id = checkout_session.get('id')
        
        if not client_ip:
            metadata = checkout_session.get('metadata', {})
            client_ip = metadata.get('client_ip')
        
        if client_ip:
            session_mgr.create_session(client_ip, session_id)
            logger.info(f"Session created for {client_ip} after payment {session_id}")
        else:
            logger.error(f"No client IP found for session {session_id}")
    
    elif event['type'] == 'checkout.session.expired':
        checkout_session = event['data']['object']
        session_id = checkout_session.get('id')
        logger.warning(f"Checkout session expired: {session_id}")
    
    return jsonify({'status': 'success'}), 200


@app.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    
    if session_id:
        try:
            checkout_session = stripe_api.get_session(session_id)
            if checkout_session.payment_status == 'paid':
                active_session = session_mgr.get_active_session(client_ip)
                if active_session:
                    return render_template('active.html',
                                         expires_at=active_session['expires_at'],
                                         client_ip=client_ip)
        except Exception as e:
            logger.error(f"Failed to verify payment: {e}")
    
    return render_template('success.html', client_ip=client_ip)


@app.route('/payment/cancel')
def payment_cancel():
    return render_template('cancel.html')


@app.route('/session/check')
def check_session():
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    active_session = session_mgr.get_active_session(client_ip)
    
    if active_session:
        return jsonify({
            'active': True,
            'expires_at': active_session['expires_at'],
            'remaining_seconds': active_session['remaining_seconds']
        })
    return jsonify({'active': False}), 200


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(
        host=os.getenv('PORTAL_HOST', '0.0.0.0'),
        port=int(os.getenv('PORTAL_PORT', 5000)),
        debug=False
    )
