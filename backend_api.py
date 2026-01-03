from flask import Flask, request, jsonify, send_file, render_template  # ← ADD render_template here
from flask_cors import CORS
import socket
import json
import uuid
import time
import os
import threading
from pathlib import Path
import hashlib

app = Flask(__name__)
CORS(app)

# Configuration
NETWORK_HOST = 'localhost'
NETWORK_PORT = 9000
UPLOAD_FOLDER = Path('./uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Simple user database (in production, use a real database)
users_db = {
    'demo@example.com': {
        'password': hashlib.sha256('demo123'.encode()).hexdigest(),
        'user_id': 'user_demo',
        'name': 'Demo User',
        'storage_quota': 5 * 1024 * 1024 * 1024,  # 5GB
        'used_storage': 0
    }
}

# Active transfers tracking
active_transfers = {}

def communicate_with_network(message: dict) -> dict:
    """Send message to network server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((NETWORK_HOST, NETWORK_PORT))
        sock.send(json.dumps(message).encode('utf-8'))
        response = json.loads(sock.recv(8192).decode('utf-8'))
        sock.close()
        return response
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# ← ADD THIS NEW ROUTE HERE (after the helper function, before other routes)
@app.route('/')
def index():
    """Serve the web interface"""
    return render_template('index.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if email in users_db:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        if users_db[email]['password'] == hashed_pw:
            user = users_db[email].copy()
            user.pop('password')
            return jsonify({'status': 'success', 'user': user})
    
    return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

# ... rest of your code stays the same ...

@app.route('/api/storage/expand', methods=['POST'])
def expand_storage():
    """Expand user storage (simulates adding a new node)"""
    data = request.json
    user_id = data.get('user_id')
    additional_gb = data.get('additional_gb', 5)
    
    # Find user
    user = None
    for u in users_db.values():
        if u['user_id'] == user_id:
            user = u
            break
    
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    # Increase quota
    additional_bytes = additional_gb * 1024 * 1024 * 1024
    user['storage_quota'] += additional_bytes
    
    return jsonify({
        'status': 'success',
        'new_quota': user['storage_quota'],
        'message': f'Storage expanded by {additional_gb}GB'
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Backend API Server Starting")
    print("="*60)
    print(f"API URL: http://localhost:5000")
    print(f"Network Server: {NETWORK_HOST}:{NETWORK_PORT}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    
# ← REMOVE THIS PART - it's in the wrong place and will never execute