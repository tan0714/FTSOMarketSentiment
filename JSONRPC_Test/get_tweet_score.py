#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
from web3 import Web3
load_dotenv()

RPC_URL         = os.getenv("RPC_URL")
ORACLE_ADDRESS  = os.getenv("TWITTER_ORACLE_ADDRESS")    # address of deployed ITwitterFTSO
ABI_PATH        = "artifacts/MockFTSO.sol/ITwitterFTSO.json"           # ABI must expose tweetScore()

if not RPC_URL or not ORACLE_ADDRESS:
    sys.exit("❌ set RPC_URL and TWITTER_ORACLE_ADDRESS in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ cannot connect to RPC")

with open(ABI_PATH) as f:
    ABI = json.load(f)["abi"]

oracle = w3.eth.contract(address=w3.to_checksum_address(ORACLE_ADDRESS), abi=ABI)

score = oracle.functions.tweetScore().call()
print("On-chain tweetScore (0–100):", score)
