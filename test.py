#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import logging
from pathlib import Path
import requests
from dotenv import load_dotenv
from web3 import Web3
import argparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

# ─── CONFIG: Pinata ───────────────────────────────────────────────────────────
PINATA_JWT = os.getenv("PINATA_JWT")
if not PINATA_JWT:
    sys.exit("❌ Missing PINATA_JWT in .env")

# ─── CONFIG: StorAcha Bridge ──────────────────────────────────────────────────
BRIDGE    = "https://up.storacha.network/bridge"
SPACE_DID = os.getenv("W3UP_SPACE_DID")
if not SPACE_DID:
    sys.exit("❌ Missing W3UP_SPACE_DID in .env")

# ─── CONFIG: Web3 / Contract ─────────────────────────────────────────────────
RPC_URL       = os.getenv("RPC_URL")
PRIVATE_KEY   = os.getenv("PRIVATE_KEY")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS")
CONTRACT_ADDR = "0x8fa300Faf24b9B764B0D7934D8861219Db0626e5"

if not all([RPC_URL, PRIVATE_KEY, OWNER_ADDRESS]):
    sys.exit("❌ Missing RPC_URL / PRIVATE_KEY / OWNER_ADDRESS in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    sys.exit("❌ Cannot connect to RPC")

OWNER_ADDRESS = w3.to_checksum_address(OWNER_ADDRESS)
CONTRACT_ADDR = w3.to_checksum_address(CONTRACT_ADDR)

with open("artifacts/AIDatasetRegistry.sol/AIDatasetRegistry.json") as f:
    ABI = json.load(f)["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDR, abi=ABI)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_store_headers():
    """
    Generate a fresh X-Auth-Secret + Authorization JWT that never expires,
    covering store/add, upload/add, and deal/add.
    """
    cmd = [
        "w3", "bridge", "generate-tokens", SPACE_DID,
        "-c", "store/add", "-c", "upload/add", "-c", "deal/add",
        "-j"
    ]
    out = subprocess.check_output(cmd)
    tokens = json.loads(out)
    return {
        "X-Auth-Secret": tokens["X-Auth-Secret"],
        "Authorization": tokens["Authorization"]
    }

def pin_to_pinata(path: str) -> str:
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    with open(path, "rb") as fp:
        files = {"file": (Path(path).name, fp)}
        r = requests.post(url, headers=headers, files=files)
    r.raise_for_status()
    cid = r.json()["IpfsHash"]
    logging.info(f"📦 Pinned → {cid}")
    return cid

def make_car(path: str):
    root = subprocess.check_output(["ipfs", "add", "-Q", path]).decode().strip()
    car_path = f"{path}.car"
    with open(car_path, "wb") as out:
        subprocess.run(["ipfs", "dag", "export", root], check=True, stdout=out)
    car_cid = subprocess.check_output(["ipfs-car", "hash", car_path]).decode().strip()
    size = Path(car_path).stat().st_size
    logging.info(f"🗂 CAR ready: root={root}, carCID={car_cid}, size={size}")
    return root, car_cid, car_path, size

def upload_car(root, car_cid, car_path, size):
    # fetch fresh headers
    headers = get_store_headers()

    # 1) store/add
    body = {
      "tasks": [
        ["store/add", SPACE_DID, {"link":{"/":car_cid}, "size":size}]
      ]
    }
    resp = requests.post(BRIDGE, headers=headers, json=body).json()
    out  = resp[0]["p"]["out"]

    # 2) error?
    if "error" in out:
        msg = out["error"].get("message", json.dumps(out["error"]))
        logging.error("🚨 store/add failed:\n" + msg)
        sys.exit(1)

    # 3) ok → upload or skip
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
        sys.exit("❌ store/add returned ok but no url or done:\n" + json.dumps(ok, indent=2))

    # 4) upload/add
    headers = get_store_headers()
    body2 = {
      "tasks": [
        ["upload/add", SPACE_DID, {"root":{"/":root}, "shards":[{"/":car_cid}]}]
      ]
    }
    r2 = requests.post(BRIDGE, headers=headers, json=body2)
    r2.raise_for_status()
    logging.info("✅ CAR registered on StorAcha")

def create_deal(root, car_cid, miner=None, duration=None):
    headers = get_store_headers()
    payload = {"root":{"/":root}, "car":{"/":car_cid}}
    if miner:    payload["miner"]   = miner
    if duration: payload["duration"] = duration
    body = {"tasks":[["deal/add", SPACE_DID, payload]]}
    resp = requests.post(BRIDGE, headers=headers, json=body).json()
    logging.info("🎯 Deal response: " + json.dumps(resp, indent=2))
    return resp

def register_on_chain(root_cid, size, deal_id, title, description, price, preview):
    # get next nonce
    nonce = w3.eth.get_transaction_count(OWNER_ADDRESS)
    payload = (title, root_cid, size, description, price, deal_id, preview)

    # gasPrice + dynamic gas limit
    tx_params = {
        "from": OWNER_ADDRESS,
        "nonce": nonce,
        "gasPrice": w3.to_wei("50", "gwei"),
    }
    estimated = contract.functions.addDataset(root_cid, payload).estimate_gas(tx_params)
    gas_limit = int(estimated * 1.2)
    tx_params["gas"] = gas_limit
    logging.info(f"🔧 Estimated gas {estimated}, using limit {gas_limit}")

    # build / sign / send
    tx = contract.functions.addDataset(root_cid, payload).build_transaction(tx_params)
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    txh    = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("✅ On-chain tx:", txh.hex())


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file",        required=True, help="path to dataset file")
    p.add_argument("--title",       required=True, help="dataset title")
    p.add_argument("--description", required=True, help="dataset description")
    p.add_argument("--price",       required=True, type=int, help="access fee in wei")
    p.add_argument("--preview",     required=True, help="short preview text")
    p.add_argument("--miner",       help="(opt) Filecoin miner address")
    p.add_argument("--duration",    type=int, help="(opt) deal duration in epochs")
    args = p.parse_args()

    if not Path(args.file).exists():
        sys.exit(f"❌ File not found: {args.file}")

    # 1) Pin to IPFS
    root_cid = pin_to_pinata(args.file)

    # 2) Make & upload CAR
    root, car_cid, car_path, size = make_car(args.file)
    upload_car(root, car_cid, car_path, size)

    # 3) Create Storage Deal
    deal_resp = create_deal(root, car_cid, miner=args.miner, duration=args.duration)
    try:
        deal_id = deal_resp[0]["p"]["out"]["dealId"]
    except:
        logging.warning("⚠️ Couldn't parse dealId; defaulting to 0")
        deal_id = 0

    # 4) Register on-chain
    register_on_chain(
        root_cid, size, deal_id,
        args.title, args.description, args.price, args.preview
    )

if __name__ == "__main__":
    main()
