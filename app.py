import os
import hashlib
import requests
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from web3 import Web3

from models import db, Institution

from config import (
    PINATA_API_KEY, 
    PINATA_SECRET_KEY, 
    CONTRACT_ADDRESS, 
    CONTRACT_ABI,
    INFURA_PROJECT_ID,
    ISSUER_ADDRESS,
    ISSUER_PRIVATE_KEY
)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certichain.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Initialize extensions
db.init_app(app)

# Web3 Setup
infura_url = f"https://sepolia.infura.io/v3/{INFURA_PROJECT_ID}"
w3 = Web3(Web3.HTTPProvider(infura_url))

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

if CHECKED_CONTRACT and CHECKED_ISSUER:
    contract = w3.eth.contract(address=CHECKED_CONTRACT, abi=CONTRACT_ABI)
else:
    contract = None

os.makedirs("certs/uploads", exist_ok=True)

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
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"pinata_api_key": PINATA_API_KEY, "pinata_secret_api_key": PINATA_SECRET_KEY}
    with open(file_path, "rb") as f:
        response = requests.post(url, files={"file": f}, headers=headers)
    if response.status_code == 200:
        return response.json()["IpfsHash"]
    raise Exception(f"IPFS Error: {response.text}")

# ==================== Routes ====================

@app.route('/')
def index():
    return render_template('landing.html')

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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        institution = Institution.query.filter_by(email=email).first()
        
        if not institution or not institution.check_password(password):
            return render_template('login.html', error='Email ou mot de passe incorrect')
        
        # Créer une session
        session['institution_id'] = institution.id
        session['institution_email'] = institution.email
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"Erreur login: {e}")
        return render_template('login.html', error='Une erreur est survenue. Veuillez réessayer.')

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
            return jsonify({
                "verified": True,
                "recipient": cert.recipient_name,
                "issueDate": int(cert.created_at.timestamp()),
                "ipfs": cert.ipfs_hash,
                "certificate_type": cert.certificate_type,
                "domain": cert.domain,
                "message": "Certificat authentique trouvé dans la base de données"
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

        # Rechercher le certificat par hash blockchain dans la DB
        cert = Certificate.query.filter_by(blockchain_hash=blockchain_hash).first()

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
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf
    from flask import send_file
    
    pdf_map = {
        'diplome': create_diploma_pdf,
        'certification': create_certification_pdf,
        'badge': create_badge_pdf
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
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf
    from flask import send_file
    
    pdf_map = {
        'diplome': create_diploma_pdf,
        'certification': create_certification_pdf,
        'badge': create_badge_pdf
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
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf

    data = request.json or {}
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
        pdf_payload['blockchain_hash'] = 'En cours...'  # Placeholder temporaire

        pdf_map = {
            'diplome': create_diploma_pdf,
            'certification': create_certification_pdf,
            'badge': create_badge_pdf
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

        # Calculer le hash du fichier
        file_hash = generate_file_hash(file_path)
        cert.file_hash = file_hash

        # Uploader sur IPFS
        try:
            ipfs_hash = upload_to_ipfs(file_path)
            cert.ipfs_hash = ipfs_hash
        except Exception as e:
            cert.ipfs_hash = None
            print(f"IPFS upload failed: {e}")

        # Enregistrer sur la blockchain si possible
        blockchain_hash = None
        if contract and CHECKED_ISSUER and ISSUER_PRIVATE_KEY:
            try:
                cert_id = w3.solidity_keccak(['string'], [file_hash])
                nonce = w3.eth.get_transaction_count(CHECKED_ISSUER)
                tx = contract.functions.issueCertificate(cert_id, cert.ipfs_hash or '', cert.recipient_name).build_transaction({
                    'chainId': 11155111,
                    'gas': 500000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                })
                signed = w3.eth.account.sign_transaction(tx, private_key=ISSUER_PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                w3.eth.wait_for_transaction_receipt(tx_hash)
                blockchain_hash = w3.to_hex(tx_hash)
                cert.blockchain_hash = blockchain_hash
                cert.status = 'issued'
            except Exception as e:
                print(f"Blockchain issue failed: {e}")

        # Régénérer le PDF avec le vrai hash blockchain si disponible
        if blockchain_hash:
            pdf_payload['blockchain_hash'] = blockchain_hash[:20] + '...'  # Tronquer pour l'affichage
            pdf_buffer_final = pdf_func(pdf_payload)
            pdf_buffer_final.seek(0)
            with open(file_path, 'wb') as f:
                f.write(pdf_buffer_final.read())

        db.session.commit()

        return jsonify({
            'message': 'Certificat créé et enregistré (local/ipfs/blockchain si disponible)',
            'certificate_id': cert.id,
            'certificate': cert.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 400

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
    """Télécharger un certificat comme PDF"""
    from models import Certificate, Institution
    from pdf_generator import create_diploma_pdf, create_certification_pdf, create_badge_pdf
    from flask import send_file

    institution_id = session.get('institution_id')
    cert = Certificate.query.filter_by(id=cert_id, institution_id=institution_id).first()

    if not cert:
        return render_template('404.html'), 404

    # Préparer les données pour le PDF
    institution = Institution.query.get(institution_id)
    data = cert.data or {}
    pdf_payload = dict(data)
    pdf_payload['institution_name'] = institution.name if institution else pdf_payload.get('institution_name', 'Institution')
    pdf_payload['recipient_name'] = cert.recipient_name
    pdf_payload['graduation_date'] = data.get('graduation_date', datetime.now().strftime('%d/%m/%Y'))
    pdf_payload['cert_number'] = f'CERT-{datetime.now().year}-{cert.id:05d}'
    pdf_payload['duration'] = data.get('duration', 'N/A')
    pdf_payload['blockchain_hash'] = (cert.blockchain_hash[:20] + '...' if cert.blockchain_hash else 'Non disponible')

    pdf_map = {
        'diplome': create_diploma_pdf,
        'certification': create_certification_pdf,
        'badge': create_badge_pdf
    }

    try:
        pdf_func = pdf_map.get(cert.certificate_type)
        if pdf_func:
            pdf_buffer = pdf_func(pdf_payload)
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{cert.certificate_type}_{cert.recipient_name}_{cert.id}.pdf'
            )
        else:
            return jsonify({'error': 'Type de certificat inconnu'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

# ==================== Initialization ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)