#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import Web3RPCError

load_dotenv()

RPC_URL          = os.getenv("RPC_URL")
GOVERNOR_ADDRESS = os.getenv("GOVERNOR_ADDRESS")
ABI_PATH         = "artifacts/Governor.sol/TruthAnchorGovernor.json"

if not all([RPC_URL, GOVERNOR_ADDRESS]):
    sys.exit("❌ Please set RPC_URL and GOVERNOR_ADDRESS in your .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ Cannot connect to RPC")

GOVERNOR_ADDRESS = w3.to_checksum_address(GOVERNOR_ADDRESS)
with open(ABI_PATH) as f:
    GOV_ABI = json.load(f)["abi"]
gov = w3.eth.contract(address=GOVERNOR_ADDRESS, abi=GOV_ABI)

def human_time(block_number):
    try:
        blk = w3.eth.get_block(block_number)
        ts  = blk["timestamp"]
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Web3RPCError as e:
        # Filecoin calibration RPC disallows very old lookbacks
        return "N/A"

def check(proposal_id: int):
    snap     = gov.functions.proposalSnapshot(proposal_id).call()
    deadline = gov.functions.proposalDeadline(proposal_id).call()
    current  = w3.eth.block_number

    print(f"Proposal #{proposal_id}")
    print(f"  Snapshot (voting start) block:   {snap}  → {human_time(snap)}")
    print(f"  Deadline (voting end) block:     {deadline}  → {human_time(deadline)}")
    print(f"  Current block:                   {current}")

    if current < snap:
        print(f"  Voting opens in {snap - current} blocks")
    elif current > deadline:
        print("  Voting has already closed")
    else:
        print("  Voting is currently OPEN!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check voting window for a Governor proposal")
    parser.add_argument("proposal_id", type=int, help="ID of the proposal")
    args = parser.parse_args()
    check(args.proposal_id)
