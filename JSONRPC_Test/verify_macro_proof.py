#!/usr/bin/env python3
import os, sys, json
from dotenv import load_dotenv
from web3 import Web3
load_dotenv()

RPC_URL              = os.getenv("RPC_URL")
JSONAPI_ADAPTER_ADDR = os.getenv("JSONAPI_ADAPTER_ADDRESS")  # deployed IJsonApi verifier
ABI_PATH             = "artifacts/IJsonApi.json"             # ABI with verifyJsonApi

PROOF_PATH = "macroProof.json"
if not os.path.exists(PROOF_PATH):
    sys.exit(f"❌ proof file not found: {PROOF_PATH}")

if not RPC_URL or not JSONAPI_ADAPTER_ADDR:
    sys.exit("❌ set RPC_URL and JSONAPI_ADAPTER_ADDRESS in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ cannot connect RPC")

with open(ABI_PATH) as f:
    ABI = json.load(f)["abi"]

adapter = w3.eth.contract(address=w3.to_checksum_address(JSONAPI_ADAPTER_ADDR), abi=ABI)
proof = json.load(open(PROOF_PATH))

ok = adapter.functions.verifyJsonApi(proof).call()
print("Proof valid on-chain?", ok)
