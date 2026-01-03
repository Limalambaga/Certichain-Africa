from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Institution(db.Model):
    __tablename__ = 'institutions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    wallet_address = db.Column(db.String(255))
    
    # Relation avec les certificats
    certificates = db.relationship('Certificate', back_populates='institution', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat(),
            'wallet_address': self.wallet_address
        }


class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    certificate_type = db.Column(db.String(50), nullable=False)  # diplome, certification, badge
    recipient_name = db.Column(db.String(255), nullable=False)
    recipient_email = db.Column(db.String(255))
    domain = db.Column(db.String(255))
    mention = db.Column(db.String(100))
    data = db.Column(db.JSON)  # Données JSON pour flexibilité
    file_hash = db.Column(db.String(255))
    ipfs_hash = db.Column(db.String(255))
    blockchain_hash = db.Column(db.String(255))
    status = db.Column(db.String(50), default='created')  # created, issued, verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation inversée
    institution = db.relationship('Institution', back_populates='certificates')
    
    def to_dict(self):
        return {
            'id': self.id,
            'certificate_type': self.certificate_type,
            'recipient_name': self.recipient_name,
            'recipient_email': self.recipient_email,
            'domain': self.domain,
            'mention': self.mention,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'file_hash': self.file_hash,
            'ipfs_hash': self.ipfs_hash,
            'blockchain_hash': self.blockchain_hash,
            'data': self.data
        }

