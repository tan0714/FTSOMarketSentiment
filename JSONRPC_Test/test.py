#!/usr/bin/env python3
import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
RPC_URL        = os.getenv("RPC_URL")
PRIVATE_KEY    = os.getenv("PRIVATE_KEY")
CONTRACT_ADDR  = os.getenv("COMPOSITE_CONTRACT")    # address of CompositeSentimentConsumer
CSV_PATH       = "ExampleFinalData.csv"
PROOF_PATH     = "macroProof.json"                  # must contain a valid IJsonApi.Proof

if not all([RPC_URL, PRIVATE_KEY, CONTRACT_ADDR]):
    sys.exit("Missing RPC_URL, PRIVATE_KEY or COMPOSITE_CONTRACT in .env")

# ─── Setup web3 + contract ────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(RPC_URL))
# if you are on a PoA testnet:
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

acct = w3.eth.account.from_key(PRIVATE_KEY)
CONTRACT_ADDR = w3.to_checksum_address(CONTRACT_ADDR)

# load ABI of CompositeSentimentConsumer
with open("artifacts/CompositeSentimentConsumer.json") as f:
    ABI = json.load(f)["abi"]
consumer = w3.eth.contract(address=CONTRACT_ADDR, abi=ABI)


def load_macro_proof(path:str) -> dict:
    """Load the IJsonApi.Proof struct from disk (JSON)."""
    with open(path) as f:
        proof = json.load(f)
    # web3.py wants the dict keys exactly matching the struct field names
    return proof


def pick_latest_macro_score(csv_path:str) -> int:
    df = pd.read_csv(csv_path)
    if "macroScore" not in df.columns:
        sys.exit("CSV must have a column named 'macroScore'")
    # take last non‐null
    return int(df["macroScore"].dropna().iloc[-1])


def build_tx(proof:dict) -> dict:
    """Builds the transaction dict for updateComposite(proof)."""
    # get gas estimate
    est = consumer.functions.updateComposite(proof).estimate_gas({"from": acct.address})
    gas_limit = int(est * 1.2)
    tx = consumer.functions.updateComposite(proof).build_transaction({
        "from":      acct.address,
        "gas":       gas_limit,
        "gasPrice":  w3.to_wei("20", "gwei"),
        "nonce":     w3.eth.get_transaction_count(acct.address)
    })
    return tx


def main():
    # 1) read CSV, extract macroScore
    macro_score = pick_latest_macro_score(CSV_PATH)
    print("Latest macroScore from CSV:", macro_score)

    # 2) load JSON-API proof (must have been generated for that same macroScore)
    proof = load_macro_proof(PROOF_PATH)

    # 3) sanity check – you can inspect proof["data"]["responseBody"]["abi_encoded_data"]
    print("Proof abi_encoded_data:", proof["data"]["responseBody"]["abi_encoded_data"])

    # 4) send tx
    tx = build_tx(proof)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("Submitted updateComposite tx hash:", h.hex())

    # 5) wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(h)
    print("Mined in block", receipt.blockNumber)
    # show the CompositeUpdated event
    for ev in consumer.events.CompositeUpdated().process_receipt(receipt):
        print("⏺ CompositeUpdated →",
              "tweetScore=", ev.args.tweetScore,
              "macroScore=", ev.args.macroScore,
              "composite=", ev.args.composite)


if __name__=="__main__":
    main()
