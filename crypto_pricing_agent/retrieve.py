# example test usage: python retrieve.py Qmhash...

import sys
import logging
import requests
import time
import subprocess
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

GATEWAYS = [
    "https://ipfs.io/ipfs/{}",
    "https://{}.ipfs.w3s.link",
    "https://cloudflare-ipfs.com/ipfs/{}",
    "https://dweb.link/ipfs/{}"
]

def fetch_via_gateway(cid, output_path):
    for template in GATEWAYS:
        url = template.format(cid)
        logging.info(f"Trying gateway: {url}")
        for attempt in range(1, 4):
            try:
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
                    output_path.write_bytes(r.content)
                    logging.info(f"✅ Saved to {output_path}")
                    return True
                logging.warning(f"{url} returned {r.status_code}")
            except requests.RequestException as e:
                logging.warning(f"Attempt {attempt} failed: {e}")
            time.sleep(2 ** attempt)
    return False

def fetch_via_local(cid, output_path):
    if shutil.which("ipfs"):
        logging.info("Falling back to local IPFS node")
        try:
            subprocess.run(["ipfs", "get", cid, "-o", str(output_path)], check=True)
            logging.info(f"✅ Saved to {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Local ipfs get failed: {e}")
    else:
        logging.warning("Local ipfs CLI not found")
    return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python retrieve.py <CID>")
        sys.exit(1)

    cid = sys.argv[1]
    downloads = Path("../downloads")
    downloads.mkdir(exist_ok=True, parents=True)
    output = downloads / f"{cid}.csv"

    if fetch_via_gateway(cid, output) or fetch_via_local(cid, output):
        sys.exit(0)

    logging.error("All retrieval attempts failed")
    sys.exit(1)

if __name__ == "__main__":
    main()
