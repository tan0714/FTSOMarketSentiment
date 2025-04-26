# USAGE: python list_datasets.py --from-block 2612103
import os
import sys
import json
import logging
from web3 import Web3
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

RPC_URL       = os.getenv("RPC_URL")
CONTRACT_ADDR = os.getenv("CONTRACT_ADDR") or "0x8fa300Faf24b9B764B0D7934D8861219Db0626e5"
ABI_PATH      = "artifacts/AIDatasetRegistry.sol/AIDatasetRegistry.json"

if not RPC_URL:
    sys.exit("❌ Missing RPC_URL in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ Cannot connect to RPC")

CONTRACT_ADDR = w3.to_checksum_address(CONTRACT_ADDR)
with open(ABI_PATH) as f:
    ABI = json.load(f)["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDR, abi=ABI)

def list_datasets(from_block: int = 0, to_block: int = "latest"):
    evt = contract.events.DatasetAdded
    filt = evt.create_filter(from_block=from_block, to_block=to_block)
    entries = filt.get_all_entries()
    if not entries:
        print("No DatasetAdded events found in that range.")
        return

    for ev in entries:
        a = ev["args"]
        cid = a.cid
        # build two common gateway URLs:
        w3s_url    = f"https://{cid}.ipfs.w3s.link"
        pinata_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
        print(f"\nBlock: {ev['blockNumber']}  Tx: {ev['transactionHash'].hex()}")
        print(f"  DatasetId:      {cid}")
        print(f"  Title:          {a.title}")
        print(f"  Size:           {a.size}")
        print(f"  Description:    {a.description}")
        print(f"  Price (wei):    {a.price}")
        print(f"  FilecoinDealId: {a.filecoinDealId}")
        print(f"  Preview:        {a.preview}")
        print(f"  → Fetch full CSV via w3s.link gateway:    {w3s_url}")
        print(f"  → Or via Pinata gateway:                  {pinata_url}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--from-block", type=int, default=0, help="starting block")
    p.add_argument("--to-block",   type=int, default=None, help="ending block (default latest)")
    args = p.parse_args()
    list_datasets(from_block=args.from_block, to_block=args.to_block or "latest")
