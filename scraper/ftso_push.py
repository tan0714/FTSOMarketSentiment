import os
import json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL          = os.getenv("FLARE_RPC_URL")
PRIVATE_KEY      = os.getenv("FLARE_PRIVATE_KEY")
TWITTER_FTSO     = os.getenv("TWITTER_FTSO_ADDR")
ABI_PATH         = os.getenv("TWITTER_FTSO_ABI_PATH", "artifacts/MockFTSO.sol/MockTwitterFTSO.json")

if not all([RPC_URL, PRIVATE_KEY, TWITTER_FTSO]):
    raise EnvironmentError("FLARE_RPC_URL, FLARE_PRIVATE_KEY & TWITTER_FTSO_ADDR must be set")

# Web3 setup
w3_push = Web3(Web3.HTTPProvider(RPC_URL))
_account = w3_push.eth.account.from_key(PRIVATE_KEY)

with open(ABI_PATH) as f:
    _ftso_abi = json.load(f)["abi"]

_ftso = w3_push.eth.contract(
    address=w3_push.to_checksum_address(TWITTER_FTSO),
    abi=_ftso_abi
)

def push_aggregated_score(score: int) -> str:
    """
    Push an integer score (0–100) to your Twitter FTSO contract.
    Returns the tx hash.
    """
    tx = _ftso.functions.setTweetScore(score).build_transaction({
        "from":     _account.address,
        "gas":      200_000,
        "gasPrice": w3_push.to_wei(30, "gwei"),
        "nonce":    w3_push.eth.get_transaction_count(_account.address),
        "chainId":  w3_push.eth.chain_id,
    })
    signed = _account.sign_transaction(tx)
    txh = w3_push.eth.send_raw_transaction(signed.raw_transaction)
    return txh.hex()
