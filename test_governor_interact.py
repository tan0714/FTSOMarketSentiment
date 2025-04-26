#!/usr/bin/env python3
# Usage examples:
#   python test_governor_interact.py propose TestExample
#   python test_governor_interact.py cast 1 1

import os
import sys
import json
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import Web3RPCError, ContractCustomError

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
    Sign & send; if nonce collision or underpriced, bump gasPrice 10% and retry.
    """
    nonce = w3.eth.get_transaction_count(acct.address)
    tx["nonce"] = nonce
    signed = acct.sign_transaction(tx)
    try:
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        print("✅ tx hash:", h.hex())
        return h
    except Web3RPCError as e:
        msg = str(e)
        if "already in mpool" in msg or "underpriced" in msg:
            old = tx.get("gasPrice", w3.to_wei("20","gwei"))
            bumped = int(old * 1.1)
            print(f"🔧 bumping gasPrice from {old} to {bumped}")
            tx["gasPrice"] = bumped
            signed = acct.sign_transaction(tx)
            h2 = w3.eth.send_raw_transaction(signed.raw_transaction)
            print("✅ replacement tx hash:", h2.hex())
            return h2
        raise

def propose(handle: str):
    try:
        est = gov.functions.proposeTwitterHandle(handle).estimate_gas({"from": acct.address})
        gas = int(est * 1.2)
        print(f"🔧 proposeTwitterHandle(): est {est}, gas {gas}")
        tx = gov.functions.proposeTwitterHandle(handle).build_transaction({
            "from": acct.address, "gas": gas, "gasPrice": w3.to_wei("20","gwei")
        })
        send_tx(tx)
    except ContractCustomError as e:
        print("❌ Propose failed:", e)
        print("   You need ≥5 TAT delegated. Delegate with:")
        print("     python test_governor_interact.py delegate <your_address>")

def state(pid: int):
    st = gov.functions.state(pid).call()
    print(f"Proposal {pid} state:", st)

def votes(pid: int):
    tp = gov.functions.twitterProposals(pid).call()
    print(f"TwitterProposal #{pid} → handle={tp[0]}, for={tp[1]}, against={tp[2]}, abstain={tp[3]}")

def cast(pid: int, support: int):
    try:
        est = gov.functions.castVote(pid, support).estimate_gas({"from": acct.address})
        gas = int(est * 1.2)
        print(f"🔧 castVote(): est {est}, gas {gas}")
        tx = gov.functions.castVote(pid, support).build_transaction({
            "from": acct.address, "gas": gas, "gasPrice": w3.to_wei("20","gwei")
        })
        send_tx(tx)
    except ContractCustomError as e:
        # most likely “Governor: vote not currently active”
        print("❌ Cast vote failed:", e)
        curr = gov.functions.state(pid).call()
        print(f"   Proposal {pid} is in state {curr}. Voting may not be active yet.")

def queue(pid: int):
    est = gov.functions.queue(pid).estimate_gas({"from": acct.address})
    tx = gov.functions.queue(pid).build_transaction({
        "from": acct.address, "gas": int(est*1.2), "gasPrice": w3.to_wei("20","gwei")
    })
    send_tx(tx)

def execute(pid: int):
    est = gov.functions.execute(pid).estimate_gas({"from": acct.address})
    tx = gov.functions.execute(pid).build_transaction({
        "from": acct.address, "gas": int(est*1.2), "gasPrice": w3.to_wei("20","gwei")
    })
    send_tx(tx)

def help_msg():
    print("""
Usage: python test_governor_interact.py <cmd> [args...]

Commands:
  propose <twitterHandle>       → propose a new handle
  state   <proposalId>          → show proposal state
  votes   <proposalId>          → show vote tallies
  cast    <pid> <0|1|2>         → castVote (0=against,1=for,2=abstain)
  queue   <proposalId>          → queue a passed proposal
  execute <proposalId>          → execute a queued proposal
""")

if __name__=="__main__":
    if len(sys.argv)<2:
        help_msg(); sys.exit(1)
    cmd = sys.argv[1]
    if cmd=="propose" and len(sys.argv)==3:
        propose(sys.argv[2])
    elif cmd=="state"   and len(sys.argv)==3:
        state(int(sys.argv[2]))
    elif cmd=="votes"   and len(sys.argv)==3:
        votes(int(sys.argv[2]))
    elif cmd=="cast"    and len(sys.argv)==4:
        cast(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd=="queue"   and len(sys.argv)==3:
        queue(int(sys.argv[2]))
    elif cmd=="execute" and len(sys.argv)==3:
        execute(int(sys.argv[2]))
    else:
        help_msg()
