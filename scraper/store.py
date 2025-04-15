# store.py
import os
import sys
import json
import logging
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

SPACE_DID     = os.getenv("W3UP_SPACE_DID")
X_AUTH_SECRET = os.getenv("W3UP_XAUTH")
AUTHORIZATION = os.getenv("W3UP_AUTH")
BRIDGE        = "https://up.storacha.network/bridge"

if not all([SPACE_DID, X_AUTH_SECRET, AUTHORIZATION]):
    logging.error("Missing one of W3UP_SPACE_DID, W3UP_XAUTH or W3UP_AUTH in .env")
    sys.exit(1)

def generate_car(path):
    # Generate the CAR file for the CSV file.
    root = subprocess.check_output(["ipfs", "add", "-Q", path]).decode().strip()
    car_path = f"{path}.car"
    with open(car_path, "wb") as car_file:
        subprocess.run(["ipfs", "dag", "export", root], check=True, stdout=car_file)
    car_cid = subprocess.check_output(["ipfs-car", "hash", car_path]).decode().strip()
    car_size = os.path.getsize(car_path)
    return root, car_cid, car_path, car_size

def upload(root, car_cid, car_path, car_size):
    headers = {"X-Auth-Secret": X_AUTH_SECRET, "Authorization": AUTHORIZATION}
    body = {"tasks": [["store/add", SPACE_DID, {"link": {"/": car_cid}, "size": car_size}]]}
    resp = requests.post(BRIDGE, headers=headers, json=body).json()
    ok = resp[0]["p"]["out"]["ok"]
    upload_url = ok.get("url")
    if upload_url:
        logging.info("Uploading CAR — new allocation")
        hdrs = ok.get("headers", {})
        hdrs.setdefault("Content-Length", str(car_size))
        with open(car_path, "rb") as f:
            requests.put(upload_url, headers=hdrs, data=f)
    elif ok.get("status") == "done":
        logging.info("CAR already stored — skipping upload")
    else:
        sys.exit(logging.error("store/add missing URL and unexpected status:\n" + json.dumps(resp, indent=2)))
    reg = {"tasks": [["upload/add", SPACE_DID, {"root": {"/": root}, "shards": [{"/": car_cid}]}]]}
    requests.post(BRIDGE, headers=headers, json=reg)
    return root
