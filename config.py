import os
import json
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY")
INFURA_PROJECT_ID = os.getenv("INFURA_PROJECT_ID")
ISSUER_ADDRESS = os.getenv("ISSUER_ADDRESS")
ISSUER_PRIVATE_KEY = os.getenv("ISSUER_PRIVATE_KEY")

# Mail configuration (Gmail / SMTP) — used only as a LOCAL DEV fallback.
# Most cloud hosts (Render, Heroku, Railway free tiers) block outbound SMTP
# ports (25/465/587), so production should use BREVO_API_KEY instead (HTTP API,
# port 443, never blocked).
MAIL_SERVER   = os.getenv("MAIL_SERVER",   "smtp.gmail.com")
MAIL_PORT     = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS  = os.getenv("MAIL_USE_TLS",  "True").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

# ─── Brevo (transactional email over HTTPS — works on Render/Heroku free tiers) ──
BREVO_API_KEY     = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Certichain Africa")

# Contract deployed on Polygon Amoy — set after deployment via Remix
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

# ─── Super admin (auto-seeded on first run if no admin row exists) ────────────
ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

try:
    with open('contract_abi.json', 'r') as f:
        CONTRACT_ABI = json.load(f)
except FileNotFoundError:
    CONTRACT_ABI = []

# ─── MTN MoMo ─────────────────────────────────────────────────────────────────
MOMO_SUBSCRIPTION_KEY = os.getenv('MOMO_SUBSCRIPTION_KEY', '')
MOMO_API_USER         = os.getenv('MOMO_API_USER', '')
MOMO_API_KEY          = os.getenv('MOMO_API_KEY', '')
MOMO_ENVIRONMENT      = os.getenv('MOMO_ENVIRONMENT', 'sandbox')
MOMO_BASE_URL         = os.getenv('MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
MOMO_CALLBACK_URL     = os.getenv('MOMO_CALLBACK_URL', '')
MOMO_CONFIGURED       = bool(MOMO_SUBSCRIPTION_KEY and MOMO_API_USER and MOMO_API_KEY)