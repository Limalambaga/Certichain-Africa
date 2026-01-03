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

# Fixed Configuration
CONTRACT_ADDRESS = "0x6DAfb87Edc9F4D218B9489D4741555fd80678a33"

try:
    with open('contract_abi.json', 'r') as f:
        CONTRACT_ABI = json.load(f)
except FileNotFoundError:
    CONTRACT_ABI = []