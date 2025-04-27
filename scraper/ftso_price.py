import os
import json
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL         = os.getenv("COSTON2_RPC_URL")
CONSUMER_ADDR   = os.getenv("FTSO_CONSUMER_ADDRESS")
ABI_PATH        = os.getenv("FTSO_CONSUMER_ABI_PATH", "artifacts/FTSOConsumer.sol/FTSOConsumer.json")

if not all([RPC_URL, CONSUMER_ADDR]):
    raise EnvironmentError("COSTON2_RPC_URL & FTSO_CONSUMER_ADDRESS must be set")

w3_price = Web3(Web3.HTTPProvider(RPC_URL))

with open(ABI_PATH) as f:
    consumer_abi = json.load(f)["abi"]

_consumer = w3_price.eth.contract(
    address=w3_price.to_checksum_address(CONSUMER_ADDR),
    abi=consumer_abi
)

def fetch_all_feeds():
    """
    Returns dict: symbol → (price_float, iso_timestamp_str)
    where price_float is price / 1e18 and ISO timestamp is UTC.
    """
    symbols_b32, prices_raw, tss_raw = _consumer.functions.fetchAllFeeds().call()
    mapping = {}
    for b32, raw_p, raw_ts in zip(symbols_b32, prices_raw, tss_raw):
        sym = b32.decode("utf-8").rstrip("\x00")
        price = raw_p / 10**18
        iso_ts = datetime.utcfromtimestamp(int(raw_ts)).isoformat() + "Z"
        mapping[sym] = (price, iso_ts)
    return mapping

def get_price_for(symbol: str):
    """
    Fetches all feeds once, then returns (price, ts) for the given symbol.
    Raises KeyError if symbol not found.
    """
    feeds = fetch_all_feeds()
    if symbol not in feeds:
        raise KeyError(f"{symbol} not found in FTSO consumer feeds")
    return feeds[symbol]
