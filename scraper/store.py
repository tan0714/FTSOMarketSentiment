#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv
from web3 import Web3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PINATA_JWT   = os.getenv("PINATA_JWT")
SPACE_DID    = os.getenv("W3UP_SPACE_DID")
RPC_URL      = os.getenv("RPC_URL")
PRIVATE_KEY  = os.getenv("PRIVATE_KEY")
OWNER_ADDR   = os.getenv("OWNER_ADDRESS")
CONTRACT_ADDR= os.getenv("CONTRACT_ADDR")

for name, v in [
    ("PINATA_JWT", PINATA_JWT),
    ("W3UP_SPACE_DID", SPACE_DID),
    ("RPC_URL", RPC_URL),
    ("PRIVATE_KEY", PRIVATE_KEY),
    ("OWNER_ADDRESS", OWNER_ADDR),
    ("CONTRACT_ADDR", CONTRACT_ADDR),
]:
    if not v:
        logging.critical(f"❌ Missing {name} in .env")
        sys.exit(1)

# ─── WEB3 / CONTRACT SETUP ────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    logging.critical("❌ Cannot connect to RPC")
    sys.exit(1)

OWNER_ADDR   = w3.to_checksum_address(OWNER_ADDR)
CONTRACT_ADDR= w3.to_checksum_address(CONTRACT_ADDR)

with open("artifacts/AIDatasetRegistry.sol/AIDatasetRegistry.json") as f:
    ABI = json.load(f)["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDR, abi=ABI)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_store_headers():
    """
    Generate a fresh never-expiring UCAN for store/add, upload/add, deal/add.
    """
    cmd = [
        "w3", "bridge", "generate-tokens", SPACE_DID,
        "-c", "store/add", "-c", "upload/add", "-c", "deal/add", "-j"
    ]
    out = subprocess.check_output(cmd)
    tokens = json.loads(out)
    return {
        "X-Auth-Secret": tokens["X-Auth-Secret"],
        "Authorization": tokens["Authorization"]
    }

def pin_to_pinata(path: str) -> str:
    """Pin a file to IPFS via Pinata and return the CID."""
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    with open(path, "rb") as fp:
        r = requests.post(url, headers=headers, files={"file": (Path(path).name, fp)})
    r.raise_for_status()
    cid = r.json()["IpfsHash"]
    logging.info(f"📦 Pinned → {cid}")
    return cid

def make_car(path: str):
    """ipfs add → root CID; ipfs dag export → CAR; ipfs-car hash → carCID."""
    root = subprocess.check_output(["ipfs", "add", "-Q", path]).decode().strip()
    car_path = f"{path}.car"
    with open(car_path, "wb") as out:
        subprocess.run(["ipfs", "dag", "export", root], check=True, stdout=out)
    car_cid = subprocess.check_output(["ipfs-car", "hash", car_path]).decode().strip()
    size = Path(car_path).stat().st_size
    logging.info(f"🗂 CAR ready: root={root}, carCID={car_cid}, size={size}")
    return root, car_cid, car_path, size

def upload_car(root, car_cid, car_path, size):
    """1) store/add 2) PUT CAR if needed 3) upload/add shards."""
    headers = get_store_headers()
    body = {"tasks":[["store/add", SPACE_DID, {"link":{"/":car_cid}, "size":size}]]}
    resp = requests.post("https://up.storacha.network/bridge", headers=headers, json=body).json()
    out  = resp[0]["p"]["out"]

    # error handling
    if "error" in out:
        msg = out["error"].get("message", json.dumps(out["error"]))
        logging.error("🚨 store/add failed:\n" + msg)
        sys.exit(1)

    ok = out.get("ok", {})
    if ok.get("url"):
        logging.info("⬆️ Uploading CAR — new allocation")
        hdrs = ok.get("headers", {}) or {}
        hdrs.setdefault("Content-Length", str(size))
        with open(car_path, "rb") as f:
            r = requests.put(ok["url"], headers=hdrs, data=f)
        r.raise_for_status()
    elif ok.get("status") == "done":
        logging.info("🔁 CAR already stored — skipping upload")
    else:
        logging.critical("❌ Unexpected store/add OK payload:\n" + json.dumps(ok, indent=2))
        sys.exit(1)

    # register shards
    headers = get_store_headers()
    body2 = {"tasks":[["upload/add", SPACE_DID, {"root":{"/":root}, "shards":[{"/":car_cid}] }]]}
    r2 = requests.post("https://up.storacha.network/bridge", headers=headers, json=body2)
    r2.raise_for_status()
    logging.info("✅ CAR registered on StorAcha")

def create_deal(root, car_cid, miner=None, duration=None):
    """Start a Filecoin deal via StorAcha."""
    headers = get_store_headers()
    payload = {"root":{"/":root}, "car":{"/":car_cid}}
    if miner:    payload["miner"]   = miner
    if duration: payload["duration"] = duration
    body = {"tasks":[["deal/add", SPACE_DID, payload]]}
    resp = requests.post("https://up.storacha.network/bridge", headers=headers, json=body).json()
    logging.info("🎯 Deal response: " + json.dumps(resp, indent=2))
    return resp

def register_on_chain(root_cid, size, deal_id, title, description, price, preview):
    """Call addDataset once per CID (skips if already exists)."""
    # skip duplicates
    _,_,_,_,_,_,_, exists = contract.functions.datasets(root_cid).call()
    if exists:
        logging.info("ℹ️ Dataset already on-chain → skipping")
        return

    nonce = w3.eth.get_transaction_count(OWNER_ADDR)
    data_input = (title, root_cid, size, description, price, deal_id, preview)

    txp = {
        "from": OWNER_ADDR,
        "nonce": nonce,
        "gasPrice": w3.to_wei("50", "gwei")
    }
    est = contract.functions.addDataset(root_cid, data_input).estimate_gas(txp)
    gas_limit = int(est * 1.2)
    txp["gas"] = gas_limit
    logging.info(f"🔧 gas est={est}, using limit={gas_limit}")

    tx = contract.functions.addDataset(root_cid, data_input).build_transaction(txp)
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    txh    = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("✅ On-chain tx:", txh.hex())

# ─── CLI ENTRYPOINT ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--file",        required=True)
    p.add_argument("--title",       required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--price",       required=True, type=int)
    p.add_argument("--preview",     required=True)
    p.add_argument("--miner",       help="opt")
    p.add_argument("--duration",    type=int, help="opt")
    args = p.parse_args()

    if not Path(args.file).exists():
        sys.exit(f"❌ File not found: {args.file}")

    # 1) Pin to IPFS
    root_cid = pin_to_pinata(args.file)

    # 2) CAR + upload
    root, car_cid, car_path, size = make_car(args.file)
    upload_car(root, car_cid, car_path, size)

    # 3) Deal
    deal = create_deal(root, car_cid, miner=args.miner, duration=args.duration)
    try:
        deal_id = deal[0]["p"]["out"]["dealId"]
    except:
        logging.warning("⚠️ Couldn't parse dealId; defaulting to 0")
        deal_id = 0

    # 4) On-chain
    register_on_chain(root_cid, size, deal_id,
                     args.title, args.description, args.price, args.preview)
