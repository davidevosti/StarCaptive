import sqlite3
import time
import logging
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, db_path, duration=300):
        self.db_path = db_path
        self.duration = duration
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_ip TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                started_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT UNIQUE NOT NULL,
                client_ip TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def create_session(self, client_ip, payment_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = int(time.time())
        expires_at = now + self.duration
        
        cursor.execute('''
            INSERT INTO sessions (client_ip, payment_id, started_at, expires_at, active)
            VALUES (?, ?, ?, ?, 1)
        ''', (client_ip, payment_id, now, expires_at))
        
        conn.commit()
        conn.close()
        
        self._allow_client(client_ip)
        
        logger.info(f"Session created for {client_ip}, expires at {expires_at}")
        return {
            'client_ip': client_ip,
            'started_at': now,
            'expires_at': expires_at
        }
    
    def get_active_session(self, client_ip):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = int(time.time())
        
        cursor.execute('''
            SELECT client_ip, started_at, expires_at, active
            FROM sessions
            WHERE client_ip = ? AND active = 1 AND expires_at > ?
            ORDER BY expires_at DESC
            LIMIT 1
        ''', (client_ip, now))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'client_ip': row[0],
                'started_at': row[1],
                'expires_at': row[2],
                'remaining_seconds': row[2] - now
            }
        return None
    
    def update_payment_status(self, payment_id, status):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payments SET status = ? WHERE payment_id = ?
        ''', (status, payment_id))
        
        conn.commit()
        conn.close()
    
    def get_payment(self, payment_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT payment_id, client_ip, amount, currency, status, created_at
            FROM payments
            WHERE payment_id = ?
        ''', (payment_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'payment_id': row[0],
                'client_ip': row[1],
                'amount': row[2],
                'currency': row[3],
                'status': row[4],
                'created_at': row[5]
            }
        return None
    
    def store_payment(self, payment_id, client_ip, amount, currency):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = int(time.time())
        
        cursor.execute('''
            INSERT INTO payments (payment_id, client_ip, amount, currency, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (payment_id, client_ip, amount, currency, now))
        
        conn.commit()
        conn.close()
    
    def cleanup_expired_sessions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = int(time.time())
        
        cursor.execute('''
            SELECT client_ip FROM sessions
            WHERE active = 1 AND expires_at <= ?
        ''', (now,))
        
        expired = cursor.fetchall()
        
        for row in expired:
            client_ip = row[0]
            cursor.execute('''
                UPDATE sessions SET active = 0
                WHERE client_ip = ? AND active = 1 AND expires_at <= ?
            ''', (client_ip, now))
            
            self._deny_client(client_ip)
            logger.info(f"Session expired for {client_ip}")
        
        conn.commit()
        conn.close()
        
        return len(expired)
    
    def _allow_client(self, client_ip):
        try:
            subprocess.run(
                ['/usr/local/bin/captive-portal-allow.sh', client_ip, 'add'],
                check=True,
                capture_output=True
            )
            logger.info(f"Firewall rule added for {client_ip}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add firewall rule for {client_ip}: {e}")
    
    def _deny_client(self, client_ip):
        try:
            subprocess.run(
                ['/usr/local/bin/captive-portal-allow.sh', client_ip, 'remove'],
                check=True,
                capture_output=True
            )
            logger.info(f"Firewall rule removed for {client_ip}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove firewall rule for {client_ip}: {e}")
