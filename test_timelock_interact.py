#python timelock_interact.py schedule 0xContract… 0 "" --delay 3600
import os, sys, json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL        = os.getenv("RPC_URL")
PRIVATE_KEY    = os.getenv("PRIVATE_KEY")
TIMELOCK_ADDR  = os.getenv("TIMELOCK_ADDRESS")
ABI_PATH       = "artifacts/MyTimelockController.json"

if not all([RPC_URL, PRIVATE_KEY, TIMELOCK_ADDR]):
    sys.exit("Missing RPC_URL, PRIVATE_KEY or TIMELOCK_ADDRESS")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)
TIMELOCK_ADDR = w3.to_checksum_address(TIMELOCK_ADDR)

with open(ABI_PATH) as f:
    tl_abi = json.load(f)["abi"]
timelock = w3.eth.contract(address=TIMELOCK_ADDR, abi=tl_abi)

def send(tx):
    tx.update({"nonce": w3.eth.get_transaction_count(acct.address)})
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.rawTransaction)
    print("tx hash", h.hex())

def schedule(target, value, data, predecessor, salt, delay):
    tx = timelock.functions.schedule(
        target, value, data, predecessor, salt, delay
    ).build_transaction({
        "from": acct.address, "gas": 300_000, "gasPrice": w3.to_wei("20", "gwei")
    })
    send(tx)

def execute(target, value, data, predecessor, salt):
    tx = timelock.functions.execute(
        target, value, data, predecessor, salt
    ).build_transaction({
        "from": acct.address, "gas": 300_000, "gasPrice": w3.to_wei("20", "gwei")
    })
    send(tx)

if __name__=="__main__":
    import argparse, eth_utils
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    sch = sub.add_parser("schedule")
    sch.add_argument("target"); sch.add_argument("value", type=int)
    sch.add_argument("data"); sch.add_argument("--delay", type=int, default=0)
    sch.add_argument("--pre", default=eth_utils.to_bytes(0))
    sch.add_argument("--salt", default=eth_utils.to_bytes(0))
    exe = sub.add_parser("execute")
    exe.add_argument("target"); exe.add_argument("value", type=int)
    exe.add_argument("data"); exe.add_argument("--pre", default=eth_utils.to_bytes(0))
    exe.add_argument("--salt", default=eth_utils.to_bytes(0))
    args = p.parse_args()

    if args.cmd=="schedule":
        schedule(
            w3.to_checksum_address(args.target),
            args.value,
            bytes.fromhex(args.data),
            args.pre,
            args.salt,
            args.delay
        )
    elif args.cmd=="execute":
        execute(
            w3.to_checksum_address(args.target),
            args.value,
            bytes.fromhex(args.data),
            args.pre,
            args.salt
        )
    else:
        p.print_help()
