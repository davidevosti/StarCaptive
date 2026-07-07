#!/usr/bin/env python3
import os
import sys
from session_mgr import SessionManager

def main():
    db_path = os.getenv('DATABASE_PATH', '/var/lib/captive-portal/sessions.db')
    
    try:
        session_mgr = SessionManager(db_path)
        cleaned = session_mgr.cleanup_expired_sessions()
        
        if cleaned > 0:
            print(f"Cleaned up {cleaned} expired session(s)")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
