#!/usr/bin/env python3
# Usage examples:
#   python working_governor_propose.py propose TestExample

import os
import sys
import json
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import Web3RPCError

load_dotenv()

RPC_URL            = os.getenv("RPC_URL")
PRIVATE_KEY        = os.getenv("PRIVATE_KEY")
GOVERNOR_ADDRESS   = os.getenv("GOVERNOR_ADDRESS")    # deployed TruthAnchorGovernor
TOKEN_ADDRESS      = os.getenv("TOKEN_ADDRESS")       # deployed TruthToken
TIMELOCK_ADDRESS   = os.getenv("TIMELOCK_ADDRESS")    # deployed MyTimelockController
GOV_ABI_PATH       = "artifacts/Governor.sol/TruthAnchorGovernor.json"
TOKEN_ABI_PATH     = "artifacts/Governance_token.sol/TruthToken.json"

if not all([RPC_URL, PRIVATE_KEY, GOVERNOR_ADDRESS, TOKEN_ADDRESS, TIMELOCK_ADDRESS]):
    sys.exit("❌ Missing one of RPC_URL, PRIVATE_KEY, GOVERNOR_ADDRESS, TOKEN_ADDRESS, TIMELOCK_ADDRESS in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ Cannot connect to RPC")

acct = w3.eth.account.from_key(PRIVATE_KEY)
GOVERNOR_ADDRESS = w3.to_checksum_address(GOVERNOR_ADDRESS)
TOKEN_ADDRESS    = w3.to_checksum_address(TOKEN_ADDRESS)
TIMELOCK_ADDRESS = w3.to_checksum_address(TIMELOCK_ADDRESS)

with open(GOV_ABI_PATH)  as f: GOV_ABI  = json.load(f)["abi"]
with open(TOKEN_ABI_PATH) as f: TOKEN_ABI = json.load(f)["abi"]

gov    = w3.eth.contract(address=GOVERNOR_ADDRESS, abi=GOV_ABI)
token  = w3.eth.contract(address=TOKEN_ADDRESS,    abi=TOKEN_ABI)


def send_tx(tx):
    """
    Sign and send a transaction; if a pending tx with the same nonce is in the mempool,
    bump the gasPrice by 10% and retry as a replace-by-fee.
    Returns the transaction hash.
    """
    nonce = w3.eth.get_transaction_count(acct.address)
    tx["nonce"] = nonce
    signed = acct.sign_transaction(tx)
    try:
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        print("✅ tx hash:", h.hex())
        return h
    except Web3RPCError as e:
        err = str(e)
        if "already in mpool" in err or "replacement transaction underpriced" in err:
            old_price = tx.get("gasPrice", w3.to_wei("20", "gwei"))
            new_price = int(old_price * 1.10)
            print(f"🔧 Pending tx found (nonce {nonce}), bumping gasPrice from {old_price} to {new_price}")
            tx["gasPrice"] = new_price
            signed = acct.sign_transaction(tx)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            print("✅ tx hash (replacement):", h.hex())
            return h
        raise


def propose(handle: str):
    est = gov.functions.proposeTwitterHandle(handle).estimate_gas({"from": acct.address})
    gas = int(est * 1.2)
    print(f"🔧 proposeTwitterHandle(): est {est}, gas {gas}")
    tx = gov.functions.proposeTwitterHandle(handle).build_transaction({
        "from":     acct.address,
        "gas":      gas,
        "gasPrice": w3.to_wei("20", "gwei"),
    })

    try:
        txh = send_tx(tx)
    except Web3RPCError as e:
        print("❌ Propose failed:", e)
        print("   You need at least 5 TAT delegated to your address")
        print("   Delegate now with:")
        print("     python working_governor_propose.py delegate <your_address>")
        return

    # wait for mining and extract proposalId
    receipt = w3.eth.wait_for_transaction_receipt(txh)
    print("⏱️  mined in block", receipt.blockNumber)
    evs = gov.events.ProposalCreated().process_receipt(receipt)
    if not evs:
        print("⚠️ no ProposalCreated event found!")
    else:
        pid = evs[0]["args"]["proposalId"]
        print(f"🎉 ProposalCreated → ID = {pid}")


def help_msg():
    print("""
Usage: python working_governor_propose.py <cmd> [args...]

Commands:
  propose <twitterHandle>         → propose a new Twitter handle
""")    


if __name__=="__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "propose":
        help_msg()
        sys.exit(1)
    propose(sys.argv[2])
