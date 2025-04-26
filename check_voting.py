#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL          = os.getenv("RPC_URL")
GOVERNOR_ADDRESS = os.getenv("GOVERNOR_ADDRESS")    # TruthAnchorGovernor
ABI_PATH         = "artifacts/Governor.sol/TruthAnchorGovernor.json"

if not RPC_URL or not GOVERNOR_ADDRESS:
    sys.exit("❌ Please set RPC_URL and GOVERNOR_ADDRESS in your .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ Cannot connect to RPC")

GOVERNOR_ADDRESS = w3.to_checksum_address(GOVERNOR_ADDRESS)
with open(ABI_PATH) as f:
    ABI = __import__("json").load(f)["abi"]
gov = w3.eth.contract(address=GOVERNOR_ADDRESS, abi=ABI)

def human_timestamp(block_number):
    try:
        blk = w3.eth.get_block(block_number)
        return f"{blk.timestamp} (unix) → { __import__('time').strftime('%Y-%m-%d %H:%M:%S', __import__('time').gmtime(blk.timestamp)) } UTC"
    except Exception:
        return "N/A"

def main(proposal_id):
    prop = int(proposal_id)
    snap = gov.functions.proposalSnapshot(prop).call()
    dl   = gov.functions.proposalDeadline(prop).call()
    current = w3.eth.block_number

    print(f"Proposal #{prop}")
    print(f"  Snapshot (voting starts) block: {snap}   → {human_timestamp(snap)}")
    print(f"  Deadline (voting ends) block:  {dl}   → {human_timestamp(dl)}")
    print(f"  Current block: {current}   → {human_timestamp(current)}\n")

    if current < snap:
        print("🔒 Voting has not yet opened.")
    elif snap <= current <= dl:
        print("✅ Voting is currently OPEN.")
    else:
        print("⛔ Voting has CLOSED.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <proposalId>")
        sys.exit(1)
    main(sys.argv[1])
