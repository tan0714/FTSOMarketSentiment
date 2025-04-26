#FRONTEND USE: python token_interact.py balance 0xYourAddress
#ADMIN USE: python token_interact.py mint 0xYourAddress 1000
import os
import sys
import json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL       = os.getenv("RPC_URL")
PRIVATE_KEY   = os.getenv("PRIVATE_KEY")
TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS")  # address of deployed TruthToken
ABI_PATH      = "artifacts/Governance_token.sol/TruthToken.json"

if not all([RPC_URL, PRIVATE_KEY, TOKEN_ADDRESS]):
    sys.exit("❌ Missing RPC_URL, PRIVATE_KEY or TOKEN_ADDRESS in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)
TOKEN_ADDRESS = w3.to_checksum_address(TOKEN_ADDRESS)

with open(ABI_PATH) as f:
    token_abi = json.load(f)["abi"]
token = w3.eth.contract(address=TOKEN_ADDRESS, abi=token_abi)

def send_tx(tx: dict):
    # insert the nonce last, so that we don't confuse estimate_gas
    tx["nonce"] = w3.eth.get_transaction_count(acct.address)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("✅ tx hash:", h.hex())
    return h

def balance_of(who: str):
    bal = token.functions.balanceOf(who).call()
    decimals = token.functions.decimals().call()
    print(f"Balance of {who}: {bal / 10**decimals:g} TAT")

def mint(to: str, amount: float):
    to = w3.to_checksum_address(to)
    decimals = token.functions.decimals().call()
    amt = int(amount * 10**decimals)

    # 1) estimate gas
    est = token.functions.mint(to, amt).estimate_gas({"from": acct.address})
    gas_limit = int(est * 1.2)
    print(f"🔧 mint(): estimated {est}, using gas limit {gas_limit}")

    # 2) build tx
    tx = token.functions.mint(to, amt).build_transaction({
        "from": acct.address,
        "gas": gas_limit,
        "gasPrice": w3.to_wei("20", "gwei"),
    })

    # 3) send
    send_tx(tx)

def delegate(to: str):
    to = w3.to_checksum_address(to)

    # 1) estimate gas
    est = token.functions.delegate(to).estimate_gas({"from": acct.address})
    gas_limit = int(est * 1.2)
    print(f"🔧 delegate(): estimated {est}, using gas limit {gas_limit}")

    # 2) build tx
    tx = token.functions.delegate(to).build_transaction({
        "from": acct.address,
        "gas": gas_limit,
        "gasPrice": w3.to_wei("20", "gwei"),
    })

    # 3) send
    send_tx(tx)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    b = sub.add_parser("balance");  b.add_argument("who")
    m = sub.add_parser("mint");     m.add_argument("to"); m.add_argument("amount", type=float)
    d = sub.add_parser("delegate"); d.add_argument("to")
    args = p.parse_args()

    if args.cmd == "balance":
        balance_of(args.who)
    elif args.cmd == "mint":
        mint(args.to, args.amount)
    elif args.cmd == "delegate":
        delegate(args.to)
    else:
        p.print_help()
