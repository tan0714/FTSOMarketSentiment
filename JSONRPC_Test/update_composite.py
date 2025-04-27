#!/usr/bin/env python3
# update_composite.py
#
# Reads macro_proof.json, packs it into the exact IJsonApi.Proof tuple, calls
# CompositeSentimentConsumer.updateComposite(...), then reads back lastComposite.

import os, sys, json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL             = os.getenv("FLARE_RPC_URL")
PRIVATE_KEY         = os.getenv("FLARE_PRIVATE_KEY")
COMPOSITE_ADDR      = os.getenv("COMPOSITE_ADDR")
COMPOSITE_ABI_PATH  = "artifacts/CompositeSentimentConsumer.sol/CompositeSentimentConsumer.json"
MOCK_FTSO_ABI_PATH  = "artifacts/MockFTSO.sol/MockTwitterFTSO.json"
MACRO_PROOF_JSON    = "macro_proof.json"

if not all([RPC_URL, PRIVATE_KEY, COMPOSITE_ADDR]):
    sys.exit("❌ set FLARE_RPC_URL, FLARE_PRIVATE_KEY and COMPOSITE_ADDR in .env")

w3   = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

# --- load ABIs & init contracts ---
with open(COMPOSITE_ABI_PATH) as f:
    comp_abi = json.load(f)["abi"]
comp = w3.eth.contract(address=w3.to_checksum_address(COMPOSITE_ADDR), abi=comp_abi)

with open(MOCK_FTSO_ABI_PATH) as f:
    ftso_abi = json.load(f)["abi"]

# 1) DEBUG: which oracle is your composite pointing at?
oracle_addr = comp.functions.twitterOracle().call()
print("Composite.twitterOracle() →", oracle_addr)

# if that matches your MockTwitterFTSO address, load it and read its score:
try:
    ftso = w3.eth.contract(address=oracle_addr, abi=ftso_abi)
    print("Oracle tweetScore() →", ftso.functions.tweetScore().call())
except Exception as e:
    print("⚠️ Could not read tweetScore() from oracle:", e)

print("---")

def send_raw_tx(to, data, gas=300_000, gas_price_gwei=25):
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = {
        "to":       to,
        "value":    0,
        "data":     data,
        "gas":      gas,
        "gasPrice": w3.to_wei(gas_price_gwei, "gwei"),
        "nonce":    nonce,
        "chainId":  w3.eth.chain_id,
    }
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("→ tx hash:", h.hex())
    r = w3.eth.wait_for_transaction_receipt(h)
    print("→ mined in block", r.blockNumber)
    return r

def update_composite():
    # 2) load the proof JSON
    proof = json.load(open(MACRO_PROOF_JSON))

    # 3) extract our single ABI-encoded uint256 and decode it
    hex_data      = proof["data"]["responseBody"]["abi_encoded_data"]
    encoded_bytes = bytes.fromhex(hex_data[2:])
    macro_score   = int.from_bytes(encoded_bytes, "big")
    print("Decoded macro score  →", macro_score)

    # 4) build the IJsonApi.Proof tuple
    merkle_proof   = []
    att_type       = b"\x00" * 32
    source_id      = b"\x00" * 32
    voting_round   = 0
    lowest_ts      = 0
    request_body   = ("", "", "")
    response_body  = (encoded_bytes,)

    data_struct = (
        att_type,
        source_id,
        voting_round,
        lowest_ts,
        request_body,
        response_body
    )
    proof_arg = (merkle_proof, data_struct)

    print("Calling updateComposite with proof_arg =", proof_arg)

    # 5) ABI-encode the call (web3.py v6+)
    call_data = comp.encode_abi("updateComposite", [proof_arg])

    # 6) send it on-chain
    send_raw_tx(comp.address, call_data)

    # 7) read back the on-chain composite
    last = comp.functions.lastComposite().call()
    print("→ lastComposite (1e18 scale) =", last)

if __name__ == "__main__":
    update_composite()
