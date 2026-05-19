import os
import hashlib
import requests
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail, Message
from web3 import Web3

from models import db, Institution, Payment

import momo as momo_api

from config import (
    PINATA_API_KEY,
    PINATA_SECRET_KEY,
    CONTRACT_ADDRESS,
    CONTRACT_ABI,
    INFURA_PROJECT_ID,
    ISSUER_ADDRESS,
    ISSUER_PRIVATE_KEY,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER,
    MOMO_CONFIGURED,
)

app = Flask(__name__)
CORS(app)

# Configuration
_db_url = os.getenv('DATABASE_URL') or 'sqlite:///certichain.db'
# Fix Heroku/Railway-style postgres:// URIs
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Mail configuration
app.config['MAIL_SERVER']         = MAIL_SERVER
app.config['MAIL_PORT']           = MAIL_PORT
app.config['MAIL_USE_TLS']        = MAIL_USE_TLS
app.config['MAIL_USERNAME']       = MAIL_USERNAME
app.config['MAIL_PASSWORD']       = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

# Initialize extensions
db.init_app(app)
mail = Mail(app)

# OTP is only enforced when SMTP credentials are configured
MAIL_CONFIGURED = bool(MAIL_USERNAME and MAIL_PASSWORD)

# Web3 Setup — Polygon Amoy testnet (free gas via faucet.polygon.technology)
POLYGON_RPC = os.getenv('POLYGON_RPC', 'https://polygon-rpc.com')
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

try:
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except ImportError:
    from web3.middleware import geth_poa_middleware
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

def get_safe_address(addr):
    try:
        return w3.to_checksum_address(addr)
    except:
        return None

CHECKED_CONTRACT = get_safe_address(CONTRACT_ADDRESS)
CHECKED_ISSUER = get_safe_address(ISSUER_ADDRESS)

BLOCKCHAIN_CONFIGURED = bool(
    ISSUER_ADDRESS and ISSUER_PRIVATE_KEY
    and CHECKED_CONTRACT and CHECKED_ISSUER
)

if BLOCKCHAIN_CONFIGURED:
    contract = w3.eth.contract(address=CHECKED_CONTRACT, abi=CONTRACT_ABI)
else:
    contract = None
    missing = []
    if not INFURA_PROJECT_ID:  missing.append('INFURA_PROJECT_ID')
    if not ISSUER_ADDRESS:     missing.append('ISSUER_ADDRESS')
    if not ISSUER_PRIVATE_KEY: missing.append('ISSUER_PRIVATE_KEY')
    if missing:
        print(f"[BLOCKCHAIN] Désactivé — variables manquantes dans .env : {', '.join(missing)}")
        print("[BLOCKCHAIN] Les certificats seront signés par hash SHA-256 local.")

os.makedirs("certs/uploads", exist_ok=True)

# ── Inject current institution into every template ────────────────────
@app.context_processor
def inject_current_institution():
    inst = None
    if session.get('institution_id'):
        inst = Institution.query.get(session['institution_id'])
    return {'current_institution': inst}

# ==================== OTP Rate-Limiter (in-memory) ====================
# Maps email -> list of Unix timestamps of OTP-send events
_otp_rate_limit: dict = {}

OTP_MAX_SEND_PER_HOUR = 5       # max OTP requests per email per hour
OTP_RESEND_COOLDOWN   = 60      # seconds before a resend is allowed
OTP_MAX_ATTEMPTS      = 5       # wrong guesses before the session is invalidated
OTP_EXPIRY_MINUTES    = 10

def _otp_allowed(email: str) -> bool:
    """Return True if this email may receive a new OTP (rate-limit check)."""
    now = datetime.now().timestamp()
    ts  = _otp_rate_limit.get(email, [])
    ts  = [t for t in ts if now - t < 3600]          # keep last hour only
    if len(ts) >= OTP_MAX_SEND_PER_HOUR:
        _otp_rate_limit[email] = ts
        return False
    ts.append(now)
    _otp_rate_limit[email] = ts
    return True

def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def _generate_otp() -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def _store_otp(email: str, institution_id: int, code: str) -> None:
    now = datetime.now().timestamp()
    session['otp_pending_id']    = institution_id
    session['otp_pending_email'] = email
    session['otp_hash']          = _hash_otp(code)
    session['otp_expiry']        = now + OTP_EXPIRY_MINUTES * 60
    session['otp_attempts']      = 0
    session['otp_last_sent']     = now

def _clear_otp_session() -> None:
    for k in ('otp_pending_id', 'otp_pending_email', 'otp_hash',
              'otp_expiry', 'otp_attempts', 'otp_last_sent'):
        session.pop(k, None)

# ==================== Utilities ====================

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une minuscule"
    if not re.search(r'[0-9]', password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    return True, "Mot de passe valide"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'institution_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'message': 'Session expirée. Veuillez vous reconnecter.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def upload_to_ipfs(file_path):
    """Upload to Pinata IPFS. Returns IpfsHash string or raises."""
    if not (PINATA_API_KEY and PINATA_SECRET_KEY):
        raise Exception("Pinata non configuré — clés manquantes dans .env")
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"pinata_api_key": PINATA_API_KEY, "pinata_secret_api_key": PINATA_SECRET_KEY}
    with open(file_path, "rb") as f:
        response = requests.post(url, files={"file": f}, headers=headers)
    if response.status_code == 200:
        return response.json()["IpfsHash"]
    raise Exception(f"IPFS Error: {response.text}")

def send_otp_email(to_email, otp_code, institution_name=''):
    """Send a branded OTP email via Flask-Mail."""
    html_body = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Inter',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
<tr><td align="center">
  <table width="520" cellpadding="0" cellspacing="0" style="background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(10,30,82,0.10);">
    <!-- Header -->
    <tr><td style="background:#0A1E52;padding:28px 36px;text-align:center;">
      <span style="font-size:1.3rem;font-weight:800;color:white;letter-spacing:-0.02em;">Certichain Africa</span>
      <div style="font-size:0.78rem;color:rgba(255,255,255,0.5);margin-top:4px;">Blockchain · IPFS · Sécurité</div>
    </td></tr>
    <!-- Body -->
    <tr><td style="padding:36px 36px 28px;">
      <h2 style="font-size:1.25rem;font-weight:700;color:#0A1E52;margin:0 0 8px;">Votre code de connexion</h2>
      <p style="font-size:0.9rem;color:#64748B;margin:0 0 28px;line-height:1.6;">
        Utilisez le code ci-dessous pour accéder à votre espace institution Certichain.
        Ce code expire dans <strong>10 minutes</strong>.
      </p>
      <!-- OTP Box -->
      <div style="background:#F8FAFC;border:2px solid #E2E8F0;border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
        <span style="font-size:2.8rem;font-weight:800;color:#0A1E52;letter-spacing:0.35em;font-family:monospace;">{otp_code}</span>
      </div>
      <p style="font-size:0.82rem;color:#94A3B8;margin:0;line-height:1.6;">
        Si vous n'avez pas demandé ce code, ignorez cet email. Ne partagez jamais votre code OTP.
      </p>
    </td></tr>
    <!-- Footer -->
    <tr><td style="padding:20px 36px;border-top:1px solid #E2E8F0;background:#F8FAFC;text-align:center;">
      <span style="font-size:0.75rem;color:#94A3B8;">© 2025 Certichain Africa. Tous droits réservés.</span>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""
    msg = Message(
        subject='Votre code de connexion Certichain — ' + otp_code,
        recipients=[to_email],
        html=html_body,
    )
    mail.send(msg)

# ==================== Routes ====================

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not name:
            return render_template('signup.html', error='Le nom de l\'institution est requis')
        
        if not validate_email(email):
            return render_template('signup.html', error='Adresse email invalide')
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            return render_template('signup.html', error=msg)
        
        if password != confirm_password:
            return render_template('signup.html', error='Les mots de passe ne correspondent pas')
        
        existing = Institution.query.filter_by(email=email).first()
        if existing:
            return render_template('signup.html', error='Cet email est déjà utilisé')
        
        institution = Institution(name=name, email=email, is_verified=True)
        institution.set_password(password)
        db.session.add(institution)
        db.session.commit()
        
        return render_template('login.html', info='Inscription réussie ! Vous pouvez maintenant vous connecter.')
        
    except Exception as e:
        print(f"Erreur signup: {e}")
        return render_template('signup.html', error='Une erreur est survenue. Veuillez réessayer.')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    try:
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        institution = Institution.query.filter_by(email=email).first()

        if not institution or not institution.check_password(password):
            return render_template('login.html', error='Email ou mot de passe incorrect')

        if MAIL_CONFIGURED:
            if not _otp_allowed(email):
                return render_template('login.html',
                                       error='Trop de demandes OTP. Réessayez dans une heure.')
            otp_code = _generate_otp()
            _store_otp(email, institution.id, otp_code)
            try:
                send_otp_email(email, otp_code, institution.name)
                return redirect(url_for('verify_otp'))
            except Exception as mail_err:
                print(f"Mail OTP error: {mail_err}")
                _clear_otp_session()
                return render_template('login.html',
                                       error="Échec d'envoi de l'OTP. Vérifiez la configuration SMTP.")
        else:
            # SMTP not configured — log in directly (no OTP)
            session['institution_id']    = institution.id
            session['institution_email'] = institution.email
            return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Erreur login: {e}")
        return render_template('login.html', error='Une erreur est survenue. Veuillez réessayer.')


@app.route('/login/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp_hash' not in session:
        return redirect(url_for('login'))

    email        = session.get('otp_pending_email', '')
    attempts     = session.get('otp_attempts', 0)
    attempts_left = OTP_MAX_ATTEMPTS - attempts
    last_sent    = session.get('otp_last_sent', 0)
    resend_wait  = max(0, int(OTP_RESEND_COOLDOWN - (datetime.now().timestamp() - last_sent)))

    if request.method == 'GET':
        return render_template('login_otp.html', email=email,
                               attempts_left=attempts_left, resend_wait=resend_wait)

    entered = request.form.get('otp', '').strip()

    # Expiry check
    if datetime.now().timestamp() > session.get('otp_expiry', 0):
        _clear_otp_session()
        return render_template('login_otp.html', email=email, attempts_left=0, resend_wait=0,
                               error='Code expiré. Reconnectez-vous pour en recevoir un nouveau.')

    # Attempt-limit check (before comparing so attackers can't keep guessing)
    if attempts >= OTP_MAX_ATTEMPTS:
        _clear_otp_session()
        return render_template('login.html',
                               error='Trop de tentatives incorrectes. Veuillez vous reconnecter.')

    # Verify hashed code
    if _hash_otp(entered) != session.get('otp_hash', ''):
        session['otp_attempts'] = attempts + 1
        remaining = OTP_MAX_ATTEMPTS - session['otp_attempts']
        if remaining <= 0:
            _clear_otp_session()
            return render_template('login.html',
                                   error='Trop de tentatives incorrectes. Veuillez vous reconnecter.')
        return render_template('login_otp.html', email=email,
                               attempts_left=remaining, resend_wait=resend_wait,
                               error=f'Code incorrect. Il vous reste {remaining} tentative{"s" if remaining > 1 else ""}.')

    # ✓ OTP valid — create real session
    institution_id = session.get('otp_pending_id')
    _clear_otp_session()

    institution = Institution.query.get(institution_id)
    session['institution_id']    = institution_id
    session['institution_email'] = institution.email if institution else ''

    return redirect(url_for('dashboard'))


@app.route('/login/resend-otp', methods=['POST'])
def resend_otp():
    if 'otp_pending_email' not in session:
        return redirect(url_for('login'))

    email     = session['otp_pending_email']
    last_sent = session.get('otp_last_sent', 0)
    now       = datetime.now().timestamp()
    wait      = int(OTP_RESEND_COOLDOWN - (now - last_sent))

    if wait > 0:
        return render_template('login_otp.html', email=email,
                               attempts_left=OTP_MAX_ATTEMPTS - session.get('otp_attempts', 0),
                               resend_wait=wait,
                               error=f'Veuillez attendre {wait}s avant de renvoyer un code.')

    if not _otp_allowed(email):
        return render_template('login_otp.html', email=email,
                               attempts_left=OTP_MAX_ATTEMPTS - session.get('otp_attempts', 0),
                               resend_wait=OTP_RESEND_COOLDOWN,
                               error='Trop de demandes OTP. Réessayez dans une heure.')

    otp_code = _generate_otp()
    inst_id  = session.get('otp_pending_id')
    _store_otp(email, inst_id, otp_code)

    try:
        send_otp_email(email, otp_code, '')
        return render_template('login_otp.html', email=email,
                               attempts_left=OTP_MAX_ATTEMPTS, resend_wait=OTP_RESEND_COOLDOWN,
                               info='Un nouveau code a été envoyé à votre adresse Gmail.')
    except Exception as e:
        print(f"Resend OTP error: {e}")
        return render_template('login_otp.html', email=email,
                               attempts_left=OTP_MAX_ATTEMPTS - session.get('otp_attempts', 0),
                               resend_wait=0,
                               error='Échec de renvoi. Vérifiez la configuration SMTP.')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip().lower()
    if not validate_email(email):
        return render_template('forgot_password.html',
                               error='Adresse email invalide.')

    institution = Institution.query.filter_by(email=email).first()
    # Always show success message to avoid email enumeration
    success_msg = 'Si cette adresse est enregistrée, vous recevrez un lien de réinitialisation.'

    if institution and MAIL_CONFIGURED:
        token  = secrets.token_urlsafe(48)
        expiry = datetime.now() + timedelta(hours=1)
        institution.reset_token        = token
        institution.reset_token_expiry = expiry
        db.session.commit()

        base = os.getenv('APP_BASE_URL', request.host_url.rstrip('/'))
        reset_url = f"{base}/reset-password/{token}"
        html_body = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Inter',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
<tr><td align="center">
  <table width="520" cellpadding="0" cellspacing="0" style="background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(10,30,82,0.10);">
    <tr><td style="background:#0A1E52;padding:28px 36px;text-align:center;">
      <span style="font-size:1.3rem;font-weight:800;color:white;letter-spacing:-0.02em;">Certichain Africa</span>
      <div style="font-size:0.78rem;color:rgba(255,255,255,0.5);margin-top:4px;">Réinitialisation du mot de passe</div>
    </td></tr>
    <tr><td style="padding:36px 36px 28px;">
      <h2 style="font-size:1.25rem;font-weight:700;color:#0A1E52;margin:0 0 8px;">Réinitialiser votre mot de passe</h2>
      <p style="font-size:0.9rem;color:#64748B;margin:0 0 28px;line-height:1.6;">
        Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe.
        Ce lien est valable <strong>1 heure</strong>.
      </p>
      <div style="text-align:center;margin-bottom:28px;">
        <a href="{reset_url}" style="display:inline-block;background:#0A1E52;color:white;font-weight:700;font-size:0.95rem;padding:14px 32px;border-radius:10px;text-decoration:none;letter-spacing:-0.01em;">
          Réinitialiser le mot de passe
        </a>
      </div>
      <p style="font-size:0.82rem;color:#94A3B8;margin:0;line-height:1.6;">
        Si vous n'avez pas demandé cette réinitialisation, ignorez cet email. Votre mot de passe ne sera pas modifié.
      </p>
    </td></tr>
    <tr><td style="padding:20px 36px;border-top:1px solid #E2E8F0;background:#F8FAFC;text-align:center;">
      <span style="font-size:0.75rem;color:#94A3B8;">© 2025 Certichain Africa. Tous droits réservés.</span>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>"""
        try:
            msg = Message(
                subject='Réinitialisation de votre mot de passe Certichain',
                recipients=[email],
                html=html_body,
            )
            mail.send(msg)
        except Exception as e:
            print(f"Reset password mail error: {e}")

    return render_template('forgot_password.html', info=success_msg)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    institution = Institution.query.filter_by(reset_token=token).first()

    if not institution or not institution.reset_token_expiry \
            or datetime.now() > institution.reset_token_expiry:
        return render_template('forgot_password.html',
                               error='Ce lien est invalide ou expiré. Veuillez recommencer.')

    if request.method == 'GET':
        return render_template('reset_password.html', token=token)

    password = request.form.get('password', '')
    confirm  = request.form.get('confirm_password', '')

    is_valid, msg = validate_password(password)
    if not is_valid:
        return render_template('reset_password.html', token=token, error=msg)

    if password != confirm:
        return render_template('reset_password.html', token=token,
                               error='Les mots de passe ne correspondent pas.')

    institution.set_password(password)
    institution.reset_token        = None
    institution.reset_token_expiry = None
    db.session.commit()

    return render_template('login.html',
                           info='Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.')


@app.route('/dashboard')
@login_required
def dashboard():
    institution = Institution.query.get(session['institution_id'])
    return render_template('dashboard.html', institution=institution)

@app.route('/create-cert', methods=['GET', 'POST'])
@login_required
def create_cert():
    institution = Institution.query.get(session['institution_id'])
    
    if request.method == 'GET':
        return render_template('create_cert.html', institution=institution)
    
    if not contract or not CHECKED_ISSUER:
        return render_template('create_cert.html', error='Smart contract non configuré')
    
    try:
        name = request.form.get('name', '')
        uploaded_file = request.files.get('file')
        
        if not uploaded_file or not name:
            return render_template('create_cert.html', error='Nom et fichier requis')
        
        file_path = os.path.join("certs/uploads", uploaded_file.filename)
        uploaded_file.save(file_path)
        
        file_hash = generate_file_hash(file_path)
        cert_id = w3.solidity_keccak(['string'], [file_hash])
        
        ipfs_hash = upload_to_ipfs(file_path)
        
        nonce = w3.eth.get_transaction_count(CHECKED_ISSUER)
        tx = contract.functions.issueCertificate(cert_id, ipfs_hash, name).build_transaction({
            'chainId': 11155111,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed = w3.eth.account.sign_transaction(tx, private_key=ISSUER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return render_template('create_cert.html', 
                             success=True,
                             tx_hash=w3.to_hex(tx_hash),
                             cert_id=w3.to_hex(cert_id),
                             ipfs_hash=ipfs_hash)
        
    except Exception as e:
        return render_template('create_cert.html', error=f'Erreur: {str(e)}')

@app.route('/certificates')
@login_required
def certificates():
    institution = Institution.query.get(session['institution_id'])
    return render_template('certificates.html', institution=institution)

@app.route('/settings')
@login_required
def settings():
    institution = Institution.query.get(session['institution_id'])
    return render_template('settings.html', institution=institution)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    institution = Institution.query.get(session['institution_id'])
    name = request.form.get('name', '').strip()
    if not name:
        flash('Le nom ne peut pas être vide.', 'error')
        return redirect(url_for('settings'))
    institution.name = name
    db.session.commit()
    flash('Profil mis à jour avec succès.', 'success')
    return redirect(url_for('settings'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    institution = Institution.query.get(session['institution_id'])
    current = request.form.get('current_password', '')
    new_pw  = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if not institution.check_password(current):
        flash('Mot de passe actuel incorrect.', 'error')
        return redirect(url_for('settings'))
    if new_pw != confirm:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'error')
        return redirect(url_for('settings'))
    valid, msg = validate_password(new_pw)
    if not valid:
        flash(msg, 'error')
        return redirect(url_for('settings'))
    institution.set_password(new_pw)
    db.session.commit()
    flash('Mot de passe modifié avec succès.', 'success')
    return redirect(url_for('settings'))

@app.route('/update-wallet', methods=['POST'])
@login_required
def update_wallet():
    institution = Institution.query.get(session['institution_id'])
    wallet = request.form.get('wallet', '').strip()
    if wallet and not re.match(r'^0x[0-9a-fA-F]{40}$', wallet):
        flash("Adresse de portefeuille invalide. Format attendu : 0x suivi de 40 caractères hexadécimaux.", 'error')
        return redirect(url_for('settings'))
    institution.wallet_address = wallet or None
    db.session.commit()
    flash('Adresse blockchain mise à jour.', 'success')
    return redirect(url_for('settings'))

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'GET':
        return render_template('verify.html')

    try:
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({"verified": False, "error": "Fichier requis"})

        file_path = os.path.join("certs/uploads", uploaded_file.filename)
        uploaded_file.save(file_path)

        file_hash = generate_file_hash(file_path)

        # D'abord vérifier dans la base de données
        from models import Certificate
        cert = Certificate.query.filter_by(file_hash=file_hash).first()

        if cert:
            on_chain = cert.blockchain_hash and cert.blockchain_hash.startswith('0x')
            return jsonify({
                "verified": True,
                "cert_id": cert.id,
                "recipient": cert.recipient_name,
                "issueDate": int(cert.created_at.timestamp()),
                "ipfs": cert.ipfs_hash,
                "blockchain_hash": cert.blockchain_hash,
                "certificate_type": cert.certificate_type,
                "domain": cert.domain,
                "mention": cert.mention,
                "on_chain": on_chain,
                "message": "Certificat authentique — ancré sur blockchain Polygon" if on_chain else "Certificat authentique — empreinte SHA-256 locale"
            })

        # Si pas trouvé en DB, vérifier sur la blockchain
        if contract:
            cert_id = w3.solidity_keccak(['string'], [file_hash])
            exists = contract.functions.verifyCertificate(cert_id).call()

            if exists:
                data = contract.functions.getCertificate(cert_id).call()
                return jsonify({
                    "verified": True,
                    "recipient": data[1],
                    "issueDate": data[2],
                    "ipfs": data[0],
                    "message": "Certificat authentique trouvé sur la blockchain"
                })

        return jsonify({"verified": False, "message": "Certificat non trouvé ou modifié"})

    except Exception as e:
        return jsonify({"verified": False, "error": str(e)})

@app.route('/api/certificates/public/<int:cert_id>')
def get_public_certificate(cert_id):
    """Récupérer les informations publiques d'un certificat par ID"""
    from models import Certificate

    cert = Certificate.query.get(cert_id)
    if not cert:
        return jsonify({'certificate': None, 'message': 'Certificat non trouvé'}), 404

    return jsonify({'certificate': cert.to_dict()}), 200

@app.route('/verify-hash', methods=['POST'])
def verify_by_hash():
    """Vérifier un certificat par son hash blockchain"""
    from models import Certificate

    try:
        data = request.json or {}
        blockchain_hash = data.get('blockchain_hash', '').strip()

        if not blockchain_hash:
            return jsonify({"verified": False, "message": "Hash blockchain requis"})

        # Chercher exactement, puis avec préfixe sha256: si non trouvé
        cert = Certificate.query.filter_by(blockchain_hash=blockchain_hash).first()
        if not cert and not blockchain_hash.startswith('sha256:') and not blockchain_hash.startswith('0x'):
            cert = Certificate.query.filter_by(blockchain_hash='sha256:' + blockchain_hash).first()

        if cert:
            return jsonify({
                "verified": True,
                "recipient": cert.recipient_name,
                "issueDate": int(cert.created_at.timestamp()),  # Timestamp Unix
                "ipfs": cert.ipfs_hash,
                "certificate_type": cert.certificate_type,
                "domain": cert.domain
            })
        else:
            return jsonify({"verified": False, "message": "Certificat non trouvé avec ce hash blockchain"})

    except Exception as e:
        return jsonify({"verified": False, "error": str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== Templates Routes ====================

@app.route('/templates')
def templates_library():
    """Page de bibliothèque de modèles"""
    return render_template('templates_library.html')

@app.route('/templates/preview/<template_type>')
def template_preview(template_type):
    """Aperçu du modèle PDF"""
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf, create_cyber_diploma_pdf
    from flask import send_file
    
    pdf_map = {
        'diplome': create_diploma_pdf,
        'certification': create_certification_pdf,
        'badge': create_badge_pdf,
        'cyber': create_cyber_diploma_pdf
    }
    
    if template_type not in pdf_map:
        return render_template('404.html'), 404
    
    try:
        pdf_buffer = pdf_map[template_type]()
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'apercu_{template_type}.pdf'
        )
    except Exception as e:
        print(f"Erreur aperçu: {e}")
        return render_template('500.html'), 500

@app.route('/templates/download/<template_type>')
def template_download(template_type):
    """Télécharger le modèle PDF éditable"""
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf, create_cyber_diploma_pdf
    from flask import send_file
    
    pdf_map = {
        'diplome': create_diploma_pdf,
        'certification': create_certification_pdf,
        'badge': create_badge_pdf,
        'cyber': create_cyber_diploma_pdf
    }
    
    if template_type not in pdf_map:
        return jsonify({"error": "Template not found"}), 404
    
    try:
        pdf_buffer = pdf_map[template_type]()
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'modele_{template_type}.pdf'
        )
    except Exception as e:
        print(f"Erreur téléchargement: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== Certificate Routes ====================

@app.route('/create-certificate')
@login_required
def create_certificate_page():
    """Page de création de certificat"""
    return render_template('create_certificate.html')

@app.route('/my-certificates')
@login_required
def my_certificates():
    """Page de gestion des certificats de l'institution"""
    return render_template('my_certificates.html')

@app.route('/api/certificates/create', methods=['POST'])
@login_required
def create_certificate():
    """API pour créer un certificat"""
    from models import Certificate, Institution
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf, create_cyber_diploma_pdf

    data = request.get_json(force=True, silent=True) or {}
    institution_id = session.get('institution_id')

    if not institution_id:
        return jsonify({'message': 'Institution non authentifiée'}), 401

    try:
        cert = Certificate(
            institution_id=institution_id,
            certificate_type=data.get('certificate_type'),
            recipient_name=data.get('recipient_name'),
            recipient_email=data.get('recipient_email'),
            domain=data.get('domain'),
            mention=data.get('mention'),
            data=data,
            status='created'
        )
        db.session.add(cert)
        db.session.commit()

        # Préparer les données pour le PDF
        institution = Institution.query.get(institution_id)
        pdf_payload = dict(data)
        pdf_payload['institution_name'] = institution.name if institution else pdf_payload.get('institution_name')
        pdf_payload['recipient_name'] = cert.recipient_name
        # Ajouter les champs manquants pour le PDF
        pdf_payload['graduation_date'] = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
        pdf_payload['cert_number'] = f'CERT-{datetime.now().year}-{cert.id:05d}'
        pdf_payload['duration'] = data.get('duration', 'N/A')
        pdf_payload['blockchain_hash'] = 'En cours...'
        pdf_payload['verify_url'] = request.host_url.rstrip('/') + f'/verify/{cert.id}'

        pdf_map = {
            'diplome': create_diploma_pdf,
            'certification': create_certification_pdf,
            'badge': create_badge_pdf,
        'cyber': create_cyber_diploma_pdf
        }

        pdf_func = pdf_map.get(cert.certificate_type)
        if pdf_func is None:
            return jsonify({'message': 'Type de certificat inconnu'}), 400

        # Générer le PDF initial
        pdf_buffer = pdf_func(pdf_payload)

        # Sauvegarder le PDF localement
        os.makedirs(os.path.join('certs', 'uploads'), exist_ok=True)
        filename = f'cert_{cert.id}.pdf'
        file_path = os.path.join('certs', 'uploads', filename)
        pdf_buffer.seek(0)
        with open(file_path, 'wb') as f:
            f.write(pdf_buffer.read())

        # Hash of the draft PDF — used as the on-chain certificate identifier
        file_hash = generate_file_hash(file_path)

        # ── Blockchain ou hash local ──────────────────────────────────────
        blockchain_hash = None

        if BLOCKCHAIN_CONFIGURED:
            try:
                cert_id_bytes = w3.solidity_keccak(['string'], [file_hash])
                nonce = w3.eth.get_transaction_count(CHECKED_ISSUER)
                tx = contract.functions.issueCertificate(
                    cert_id_bytes, '', cert.recipient_name
                ).build_transaction({
                    'chainId': 137,  # Polygon mainnet
                    'gas': 500000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                })
                signed  = w3.eth.account.sign_transaction(tx, private_key=ISSUER_PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                w3.eth.wait_for_transaction_receipt(tx_hash)
                blockchain_hash      = w3.to_hex(tx_hash)
                cert.blockchain_hash = blockchain_hash
                cert.status          = 'issued'
                print(f"[BLOCKCHAIN] Certificat {cert.id} enregistré → {blockchain_hash}")
            except Exception as e:
                print(f"[BLOCKCHAIN] Echec transaction cert {cert.id}: {e}")
                err_data = cert.data or {}
                err_data['blockchain_error'] = str(e)
                cert.data = err_data
                blockchain_hash = None

        if not blockchain_hash:
            # Fingerprint SHA-256 — vérifiable localement, sans frais de gas
            blockchain_hash      = 'sha256:' + file_hash
            cert.blockchain_hash = blockchain_hash
            cert.status          = 'issued'
            print(f"[BLOCKCHAIN] Cert {cert.id} signe localement (sha256)")

        # Régénérer le PDF avec le hash COMPLET inscrit dessus (sans troncature)
        pdf_payload['blockchain_hash'] = blockchain_hash
        pdf_buffer_final = pdf_func(pdf_payload)
        pdf_buffer_final.seek(0)
        with open(file_path, 'wb') as f:
            f.write(pdf_buffer_final.read())

        # Recompute hash from the FINAL PDF (the one the user will download)
        cert.file_hash = generate_file_hash(file_path)

        # Upload IPFS du PDF FINAL (après que le hash soit imprimé dessus)
        try:
            ipfs_hash = upload_to_ipfs(file_path)
            cert.ipfs_hash = ipfs_hash
            # Mettre à jour la tx blockchain avec le CID si possible
            print(f"[IPFS] Certificat {cert.id} uploade → {ipfs_hash}")
        except Exception as e:
            cert.ipfs_hash = f"local:{cert.id}"
            print(f"[IPFS] Fallback local pour cert {cert.id} — {e}")

        db.session.commit()

        on_chain = cert.blockchain_hash and cert.blockchain_hash.startswith('0x')
        return jsonify({
            'message': 'Certificat ancré sur blockchain Polygon' if on_chain else 'Certificat signé (hash SHA-256 local)',
            'certificate_id': cert.id,
            'on_chain': on_chain,
            'blockchain_hash': cert.blockchain_hash,
            'certificate': cert.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

@app.route('/verify/<int:cert_id>')
def verify_cert_public(cert_id):
    """Page publique de vérification — appelée depuis le QR code dans le PDF."""
    from models import Certificate
    cert = Certificate.query.get(cert_id)
    if not cert:
        return render_template('verify_public.html', cert=None)
    on_chain = bool(cert.blockchain_hash and cert.blockchain_hash.startswith('0x'))
    institution = Institution.query.get(cert.institution_id)
    return render_template('verify_public.html', cert=cert, on_chain=on_chain, institution=institution)

@app.route('/certs/<int:cert_id>/pdf')
def serve_cert_pdf(cert_id):
    """Servir le fichier PDF d'un certificat (public)."""
    from models import Certificate
    cert = Certificate.query.get_or_404(cert_id)
    file_path = os.path.join('certs', 'uploads', f'cert_{cert_id}.pdf')
    if not os.path.exists(file_path):
        abort(404)
    safe_name = re.sub(r'[^\w\s-]', '', cert.recipient_name or 'certificat').strip().replace(' ', '_')
    return send_file(
        file_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'Certichain_{safe_name}_{cert_id}.pdf'
    )

@app.route('/api/blockchain/status')
def blockchain_status():
    """Diagnostic public de l'état blockchain/IPFS."""
    status = {
        'blockchain_configured': BLOCKCHAIN_CONFIGURED,
        'ipfs_configured': bool(PINATA_API_KEY and PINATA_SECRET_KEY),
        'polygon_rpc': POLYGON_RPC,
    }
    if BLOCKCHAIN_CONFIGURED:
        try:
            status['block_number'] = w3.eth.block_number
            bal = w3.eth.get_balance(CHECKED_ISSUER)
            status['wallet_matic'] = float(w3.from_wei(bal, 'ether'))
            status['contract'] = CHECKED_CONTRACT
        except Exception as e:
            status['rpc_error'] = str(e)
    return jsonify(status)

@app.route('/api/certificates')
@login_required
def get_certificates():
    """Récupérer tous les certificats de l'institution"""
    from models import Certificate
    
    institution_id = session.get('institution_id')
    certificates = Certificate.query.filter_by(institution_id=institution_id).all()
    
    return jsonify({
        'certificates': [cert.to_dict() for cert in certificates]
    }), 200

@app.route('/api/certificates/<int:cert_id>', methods=['DELETE'])
@login_required
def delete_certificate(cert_id):
    """Supprimer un certificat"""
    from models import Certificate
    
    institution_id = session.get('institution_id')
    cert = Certificate.query.filter_by(id=cert_id, institution_id=institution_id).first()
    
    if not cert:
        return jsonify({'message': 'Certificat non trouvé'}), 404
    
    try:
        db.session.delete(cert)
        db.session.commit()
        return jsonify({'message': 'Certificat supprimé'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

@app.route('/certificate/<int:cert_id>')
@login_required
def view_certificate(cert_id):
    """Voir les détails d'un certificat"""
    from models import Certificate
    
    institution_id = session.get('institution_id')
    cert = Certificate.query.filter_by(id=cert_id, institution_id=institution_id).first()
    
    if not cert:
        return render_template('404.html'), 404
    
    return jsonify(cert.to_dict()), 200

@app.route('/certificate/<int:cert_id>/download')
@login_required
def download_certificate_file(cert_id):
    """Serve the saved PDF — never regenerate, so file_hash stays consistent."""
    from models import Certificate, Institution
    from flask import send_file

    institution_id = session.get('institution_id')
    cert = Certificate.query.filter_by(id=cert_id, institution_id=institution_id).first()
    if not cert:
        return render_template('404.html'), 404

    saved_path = os.path.join('certs', 'uploads', f'cert_{cert.id}.pdf')

    if os.path.exists(saved_path):
        return send_file(
            saved_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{cert.certificate_type}_{cert.recipient_name}_{cert.id}.pdf'
        )

    # File missing (old cert) — regenerate, save, and update stored hash
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf, create_cyber_diploma_pdf
    institution = Institution.query.get(institution_id)
    data = cert.data or {}
    pdf_payload = dict(data)
    pdf_payload['institution_name'] = institution.name if institution else 'Institution'
    pdf_payload['recipient_name']   = cert.recipient_name
    pdf_payload['graduation_date']  = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
    pdf_payload['cert_number']      = f'CERT-{datetime.now().year}-{cert.id:05d}'
    pdf_payload['duration']         = data.get('duration', 'N/A')
    pdf_payload['blockchain_hash']  = cert.blockchain_hash or 'N/A'
    pdf_payload['verify_url']       = request.host_url.rstrip('/') + f'/verify/{cert.id}'

    pdf_map = {'diplome': create_diploma_pdf, 'certification': create_certification_pdf, 'badge': create_badge_pdf, 'cyber': create_cyber_diploma_pdf}
    pdf_func = pdf_map.get(cert.certificate_type)
    if not pdf_func:
        return jsonify({'error': 'Type de certificat inconnu'}), 400

    try:
        os.makedirs(os.path.join('certs', 'uploads'), exist_ok=True)
        buf = pdf_func(pdf_payload)
        buf.seek(0)
        with open(saved_path, 'wb') as f:
            f.write(buf.read())
        cert.file_hash = generate_file_hash(saved_path)
        db.session.commit()
        return send_file(
            saved_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{cert.certificate_type}_{cert.recipient_name}_{cert.id}.pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Plan pricing table (XAF) ─────────────────────────────────────────────────
PLAN_PRICES = {
    'starter':    {'monthly': 19900,  'annual': 190800},   # 15900 * 12
    'academique': {'monthly': 49900,  'annual': 478800},   # 39900 * 12
}
PLAN_QUOTA = {'free': 5, 'starter': 50, 'academique': 300, 'enterprise': 999999}


@app.route('/api/payment/initiate', methods=['POST'])
@login_required
def payment_initiate():
    """Initiate a MoMo payment request."""
    if not MOMO_CONFIGURED:
        return jsonify({'error': 'Paiement MoMo non configuré sur ce serveur.'}), 503

    data  = request.get_json() or {}
    plan  = data.get('plan', '').lower()
    billing = data.get('billing', 'monthly').lower()
    phone = (data.get('phone') or '').strip().replace(' ', '').replace('-', '')

    if plan not in PLAN_PRICES:
        return jsonify({'error': 'Plan invalide.'}), 400
    if billing not in ('monthly', 'annual'):
        return jsonify({'error': 'Période invalide.'}), 400
    if not phone or len(phone) < 9:
        return jsonify({'error': 'Numéro de téléphone invalide.'}), 400

    # Normalise Cameroon numbers: 6XXXXXXXX → 2376XXXXXXXX
    if len(phone) == 9 and phone[0] in ('6', '2'):
        phone = '237' + phone

    amount    = PLAN_PRICES[plan][billing]
    ref_id    = str(__import__('uuid').uuid4())
    label     = f"Certichain {plan.capitalize()} {'mensuel' if billing == 'monthly' else 'annuel'}"

    try:
        ok = momo_api.request_to_pay(phone, amount, 'XAF', ref_id, label)
    except Exception as e:
        return jsonify({'error': f'Erreur MoMo: {str(e)}'}), 502

    if not ok:
        return jsonify({'error': 'La requête MoMo a été rejetée.'}), 502

    payment = Payment(
        institution_id=session['institution_id'],
        reference_id=ref_id,
        plan=plan,
        billing=billing,
        amount=amount,
        phone=phone,
        status='pending',
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({'reference_id': ref_id, 'amount': amount, 'currency': 'XAF'}), 202


@app.route('/api/payment/status/<reference_id>')
@login_required
def payment_status(reference_id):
    """Poll MoMo payment status and upgrade plan on success."""
    payment = Payment.query.filter_by(
        reference_id=reference_id,
        institution_id=session['institution_id'],
    ).first_or_404()

    if payment.status == 'pending':
        try:
            result = momo_api.get_status(reference_id)
            momo_status = result.get('status', 'PENDING').upper()
        except Exception as e:
            return jsonify({'status': 'pending', 'error': str(e)}), 200

        if momo_status == 'SUCCESSFUL':
            payment.status = 'successful'
            institution = Institution.query.get(session['institution_id'])
            institution.plan = payment.plan
            days = 365 if payment.billing == 'annual' else 30
            institution.plan_expires_at = datetime.utcnow() + timedelta(days=days)
            db.session.commit()

        elif momo_status == 'FAILED':
            payment.status = 'failed'
            db.session.commit()

    return jsonify({
        'status':   payment.status,
        'plan':     payment.plan,
        'billing':  payment.billing,
        'amount':   payment.amount,
    })


@app.route('/api/payment/callback', methods=['POST'])
def payment_callback():
    """MoMo push notification webhook (optional — polling is the primary mechanism)."""
    data = request.get_json(silent=True) or {}
    ref_id = data.get('externalId') or data.get('referenceId', '')
    status = data.get('status', '').upper()

    if ref_id and status in ('SUCCESSFUL', 'FAILED'):
        payment = Payment.query.filter_by(reference_id=ref_id).first()
        if payment and payment.status == 'pending':
            payment.status = status.lower()
            if status == 'SUCCESSFUL':
                institution = Institution.query.get(payment.institution_id)
                if institution:
                    institution.plan = payment.plan
                    days = 365 if payment.billing == 'annual' else 30
                    institution.plan_expires_at = datetime.utcnow() + timedelta(days=days)
            db.session.commit()

    return '', 204


@app.route('/api/me')
@login_required
def api_me():
    institution = Institution.query.get(session['institution_id'])
    if not institution:
        return jsonify({'message': 'Institution introuvable'}), 404
    return jsonify({'id': institution.id, 'name': institution.name, 'email': institution.email}), 200

@app.route('/logout', methods=['GET', 'POST'])
def logout_get():
    session.clear()
    return redirect(url_for('login'))

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'message': 'Route introuvable.'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'message': f'Erreur serveur : {str(error)}'}), 500
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(error):
    if request.path.startswith('/api/'):
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Erreur : {str(error)}'}), 500
    raise error

# ==================== Initialization ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)