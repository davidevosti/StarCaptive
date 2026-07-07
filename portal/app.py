import os
import logging
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from dotenv import load_dotenv

from twint_api import TwintAPI
from session_mgr import SessionManager

load_dotenv('/etc/captive-portal/config.env')

app = Flask(__name__)
app.secret_key = os.urandom(24)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

twint_api = TwintAPI(
    merchant_id=os.getenv('TWINT_MERCHANT_ID'),
    api_key=os.getenv('TWINT_API_KEY'),
    api_secret=os.getenv('TWINT_API_SECRET'),
    callback_url=os.getenv('TWINT_CALLBACK_URL')
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
        payment_request = twint_api.create_payment_request(
            amount=1.00,
            currency='CHF',
            reference=f'wifi-{client_ip}-{int(os.times()[0])}'
        )
        
        session['payment_id'] = payment_request['payment_id']
        session['client_ip'] = client_ip
        
        return jsonify({
            'payment_url': payment_request['payment_url'],
            'qr_code': payment_request.get('qr_code'),
            'payment_id': payment_request['payment_id']
        })
        
    except Exception as e:
        logger.error(f"Payment initiation failed: {e}")
        return jsonify({'error': 'Payment initiation failed'}), 500


@app.route('/twint/callback', methods=['POST'])
def twint_callback():
    try:
        data = request.get_json()
        logger.info(f"TWINT callback received: {data}")
        
        payment_id = data.get('payment_id')
        status = data.get('status')
        
        if not payment_id or not status:
            return jsonify({'error': 'Invalid callback data'}), 400
        
        if status == 'approved':
            client_ip = session.get('client_ip')
            if not client_ip:
                stored_payment = session_mgr.get_payment(payment_id)
                if stored_payment:
                    client_ip = stored_payment['client_ip']
            
            if client_ip:
                session_mgr.create_session(client_ip, payment_id)
                session_mgr.update_payment_status(payment_id, 'completed')
                logger.info(f"Session created for {client_ip} after payment {payment_id}")
                return jsonify({'status': 'success', 'message': 'Payment approved'})
            else:
                logger.error(f"No client IP found for payment {payment_id}")
                return jsonify({'error': 'No client IP found'}), 400
        else:
            session_mgr.update_payment_status(payment_id, status)
            logger.warning(f"Payment {payment_id} status: {status}")
            return jsonify({'status': 'received', 'message': f'Payment {status}'})
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return jsonify({'error': 'Callback processing failed'}), 500


@app.route('/payment/status/<payment_id>')
def payment_status(payment_id):
    payment = session_mgr.get_payment(payment_id)
    if payment:
        return jsonify({
            'status': payment['status'],
            'client_ip': payment['client_ip']
        })
    return jsonify({'error': 'Payment not found'}), 404


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
