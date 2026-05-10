"""MTN Mobile Money (MoMo) Collection API client."""
import os, uuid, base64, requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL      = os.getenv('MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
SUB_KEY       = os.getenv('MOMO_SUBSCRIPTION_KEY', '')
API_USER      = os.getenv('MOMO_API_USER', '')
API_KEY       = os.getenv('MOMO_API_KEY', '')
ENVIRONMENT   = os.getenv('MOMO_ENVIRONMENT', 'sandbox')
CALLBACK_URL  = os.getenv('MOMO_CALLBACK_URL', '')


def _token() -> str:
    credentials = base64.b64encode(f"{API_USER}:{API_KEY}".encode()).decode()
    r = requests.post(
        f"{BASE_URL}/collection/token/",
        headers={
            "Authorization": f"Basic {credentials}",
            "Ocp-Apim-Subscription-Key": SUB_KEY,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()['access_token']


def _headers(token: str, ref_id: str | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "X-Target-Environment": ENVIRONMENT,
        "Ocp-Apim-Subscription-Key": SUB_KEY,
        "Content-Type": "application/json",
    }
    if ref_id:
        h["X-Reference-Id"] = ref_id
    if CALLBACK_URL:
        h["X-Callback-Url"] = CALLBACK_URL
    return h


def request_to_pay(phone: str, amount: int, currency: str,
                   reference_id: str, note: str) -> bool:
    """Initiate a payment request. Returns True on 202 Accepted."""
    token = _token()
    r = requests.post(
        f"{BASE_URL}/collection/v1_0/requesttopay",
        json={
            "amount": str(amount),
            "currency": currency,
            "externalId": reference_id,
            "payer": {"partyIdType": "MSISDN", "partyId": phone},
            "payerMessage": note,
            "payeeNote": note,
        },
        headers=_headers(token, reference_id),
        timeout=20,
    )
    return r.status_code == 202


def get_status(reference_id: str) -> dict:
    """Return MoMo status dict. Key 'status': PENDING | SUCCESSFUL | FAILED."""
    token = _token()
    r = requests.get(
        f"{BASE_URL}/collection/v1_0/requesttopay/{reference_id}",
        headers=_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_balance() -> dict:
    """Return account balance (diagnostic)."""
    token = _token()
    r = requests.get(
        f"{BASE_URL}/collection/v1_0/account/balance",
        headers=_headers(token),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()
