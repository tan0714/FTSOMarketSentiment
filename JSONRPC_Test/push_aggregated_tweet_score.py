#!/usr/bin/env python3
# JSONRPC_test/push_aggregated_tweet_score.py
# TO ADD TO END OF PYTHON TWITTER FLOW

import os, sys, json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL           = os.getenv("FLARE_RPC_URL")
PRIVATE_KEY       = os.getenv("FLARE_PRIVATE_KEY")
TWITTER_FTSO_ADDR = os.getenv("TWITTER_FTSO_ADDR")
ABI_PATH          = "artifacts/MockFTSO.sol/MockTwitterFTSO.json"

if not all([RPC_URL, PRIVATE_KEY, TWITTER_FTSO_ADDR]):
    sys.exit("❌ set FLARE_RPC_URL, FLARE_PRIVATE_KEY, TWITTER_FTSO_ADDR in .env")

w3   = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

with open(ABI_PATH) as f:
    abi = json.load(f)["abi"]

ftso = w3.eth.contract(
    address=w3.to_checksum_address(TWITTER_FTSO_ADDR),
    abi=abi
)

def push_dummy_score(score=50):
    print(f"Pushing dummy tweetScore = {score}")
    tx = ftso.functions.setTweetScore(score).build_transaction({
        "from":     acct.address,
        "gas":      200_000,
        "gasPrice": w3.to_wei(30, "gwei"),
        "nonce":    w3.eth.get_transaction_count(acct.address),
        "chainId":  w3.eth.chain_id,
    })
    signed = acct.sign_transaction(tx)
    txh = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("→ tx hash:", txh.hex())
    r = w3.eth.wait_for_transaction_receipt(txh)
    print("→ mined in block", r.blockNumber)

def read_score():
    s = ftso.functions.tweetScore().call()
    print("On-chain tweetScore() →", s)

if __name__=="__main__":
    push_dummy_score(50)
    read_score()
