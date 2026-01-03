# 🔐 Certichain - Plateforme de Gestion des Certificats Décentralisée

Une plateforme web moderne pour émettre, gérer et vérifier des certificats de manière décentralisée utilisant la blockchain Ethereum (Sepolia) et le stockage IPFS.

## 📋 Architecture

### Fonctionnalités Principales

- **Landing Page Moderne** : Page d'accueil attractive avec boutons signup/login
- **Authentification Institution** : Inscription et connexion sécurisées
- **2FA avec OTP** : Authentification à deux facteurs via email
- **Dashboard Institution** : Tableau de bord pour gérer les certificats
- **Émission de Certificats** : Créer et publier des certificats sur la blockchain
- **Vérification de Certificats** : Vérifier l'authenticité des certificats
- **Stockage IPFS** : Stockage sécurisé et immuable avec Pinata

### Stack Technologique

- **Backend** : Flask (Python)
- **Base de données** : SQLite
- **Email** : Flask-Mail (SMTP)
- **Blockchain** : Web3.py + Ethereum Sepolia
- **Stockage** : Pinata IPFS
- **Frontend** : HTML5 + CSS3 + Vanilla JavaScript

## 🚀 Installation

### Prérequis

- Python 3.8+
- pip
- Compte Pinata (pour IPFS)
- Compte Infura (pour Ethereum)
- Configuration SMTP (Gmail, Outlook, SendGrid, etc.)
- MetaMask ou portefeuille Ethereum

### 1. Cloner le projet

```bash
cd c:\Users\lenovo\Desktop\nn\Certichain
```

### 2. Créer un environnement virtuel

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet :

```env
# Configuration SMTP (exemple Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre.email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe_app  # Utilisez un mot de passe d'application
MAIL_DEFAULT_SENDER=votre.email@gmail.com

# Ou utilisez un autre service SMTP (Outlook, SendGrid, etc.)
```

### 5. Configurer les clés API dans `config.py`

Modifiez `config.py` avec vos valeurs :

```python
PINATA_API_KEY = "votre_clé_api_pinata"
PINATA_SECRET_KEY = "votre_clé_secrète_pinata"
INFURA_PROJECT_ID = "votre_project_id_infura"
CONTRACT_ADDRESS = "adresse_du_smart_contract"
ISSUER_ADDRESS = "votre_adresse_wallet"
ISSUER_PRIVATE_KEY = "votre_clé_privée"
```

## 📧 Configuration Email (SMTP)

### Option 1 : Gmail

1. Activez l'authentification à deux facteurs : https://myaccount.google.com/security
2. Créez un mot de passe d'application : https://myaccount.google.com/apppasswords
3. Sélectionnez "Mail" et "Windows Computer"
4. Copiez le mot de passe généré (16 caractères)
5. Utilisez-le dans le fichier `.env` comme `MAIL_PASSWORD`

### Option 2 : Outlook

```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre.email@outlook.com
MAIL_PASSWORD=votre_mot_de_passe
```

### Option 3 : SendGrid

```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.votre_clé_api_sendgrid
```

## 🔗 Configuration Blockchain

### Infura Setup

1. Créez un compte : https://infura.io/
2. Créez un nouveau projet
3. Sélectionnez le réseau "Sepolia"
4. Copiez l'URL HTTPS
5. Extrayez le Project ID et mettez à jour `config.py`

### Pinata Setup

1. Créez un compte : https://www.pinata.cloud/
2. Générez une clé API
3. Copiez la clé API et la clé secrète
4. Mettez à jour `config.py`

### Déploiement Smart Contract

1. Déployez `certificate.sol` sur Sepolia
2. Obtenez l'adresse du contrat
3. Mettez à jour `config.py` avec l'adresse
4. Assurez-vous que le fichier `contract_abi.json` est à jour

## ▶️ Lancement de l'application

```bash
python app.py
```

L'application sera disponible sur `http://localhost:5000`

## 📁 Structure du projet

```
Certichain/
├── app.py                      # Application principale Flask
├── models.py                   # Modèles SQLAlchemy (Institution, OTPLog)
├── config.py                   # Configuration (clés API)
├── requirements.txt            # Dépendances Python
├── .env.example               # Exemple de configuration
├── contract_abi.json          # ABI du smart contract
├── certificate.sol            # Smart contract Solidity
├── static/
│   ├── main.js               # JavaScript frontend
│   └── style.css             # Styles CSS
├── templates/
│   ├── landing.html          # Page d'accueil
│   ├── signup.html           # Page d'inscription
│   ├── login.html            # Page de connexion
│   ├── verify_otp.html       # Vérification OTP
│   ├── dashboard.html        # Dashboard institution
│   ├── create_cert.html      # Création certificat
│   ├── verify.html           # Vérification certificat
│   ├── base.html             # Template de base
│   ├── 404.html              # Erreur 404
│   └── 500.html              # Erreur 500
├── certs/
│   ├── uploads/              # Fichiers uploadés
│   └── cert_templates/       # Templates de certificats
└── smart_contracts/
    └── certificate.sol       # Smart contract
```

## 🔐 Flux d'authentification

### 1. Inscription (Signup)

```
Utilisateur → Page d'inscription → Validation email/mot de passe
→ Création compte en BDD → Redirection login
```

### 2. Connexion (Login)

```
Utilisateur → Page login → Validation email/mot de passe
→ Génération OTP → Envoi email → Redirection vérification OTP
```

### 3. Vérification 2FA (OTP)

```
Utilisateur reçoit OTP par email → Entre le code
→ Validation (6 chiffres, < 15 min, < 5 tentatives)
→ Session créée → Redirection dashboard
```

## 🛡️ Sécurité

### Mot de passe

- Minimum 8 caractères
- Au moins 1 majuscule
- Au moins 1 minuscule
- Au moins 1 chiffre
- Hash SHA256 avec Werkzeug

### OTP

- Génération aléatoire 6 chiffres
- Validité 15 minutes
- Maximum 5 tentatives
- Logs d'utilisation
- Email en HTML sécurisé

### Session

- Secret key généré aléatoirement
- Protection CSRF
- Cookies sécurisés
- Décorateur `@login_required`

## 📱 Routes API

### Routes Publiques

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Landing page |
| `/signup` | GET/POST | Inscription institution |
| `/login` | GET/POST | Connexion |
| `/verify-otp` | POST | Vérifier OTP |
| `/resend-otp` | GET | Renvoyer OTP |
| `/verify` | GET/POST | Vérifier certificat |

### Routes Protégées

| Route | Méthode | Description |
|-------|---------|-------------|
| `/dashboard` | GET | Dashboard institution |
| `/create-cert` | GET/POST | Émettre certificat |
| `/logout` | POST | Déconnexion |

## 🐛 Dépannage

### Erreur "No module named 'models'"

Assurez-vous que vous êtes dans le bon répertoire et que les fichiers `models.py` et `app.py` sont présents.

### Erreur SMTP

- Vérifiez les identifiants dans `.env`
- Pour Gmail, utilisez un mot de passe d'application
- Vérifiez que le firewall n'est pas bloqué
- Activez les "applications moins sécurisées" si nécessaire (Gmail)

### Erreur Blockchain

- Vérifiez le Project ID Infura
- Assurez-vous d'avoir des crédits Infura
- Vérifiez l'adresse du smart contract
- Vérifiez le fichier `contract_abi.json`

### Erreur Pinata

- Vérifiez les clés API Pinata
- Assurez-vous que le quota n'est pas dépassé
- Vérifiez les permissions CORS

## 📚 Ressources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Ethereum Sepolia Testnet](https://sepolia.etherscan.io/)
- [Pinata IPFS](https://www.pinata.cloud/)
- [Infura](https://infura.io/)

## 📝 Notes de développement

### Pour ajouter une nouvelle route

1. Créez la route dans `app.py`
2. Créez le template correspondant dans `templates/`
3. Testez la route localement
4. Vérifiez les permissions (publique/protégée)

### Pour ajouter une nouvelle table

1. Créez le modèle dans `models.py`
2. Exécutez `db.create_all()` dans le shell Flask
3. Testez la création

## 🤝 Support

Pour toute question ou problème, consultez la documentation ou contactez l'équipe de support.

## 📄 Licence

Ce projet est fourni à titre d'exemple éducatif.

---

**Créé en décembre 2025** | Certichain - Authentification Décentralisée
