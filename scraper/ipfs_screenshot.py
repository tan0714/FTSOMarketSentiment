import os
import tempfile
import requests

from dotenv import load_dotenv

load_dotenv()

PINATA_API_KEY = os.environ.get("PINATA_API_KEY")
PINATA_API_SECRET = os.environ.get("PINATA_API_SECRET")
PINATA_JWT = os.environ.get("PINATA_JWT")

if not PINATA_API_KEY or not PINATA_API_SECRET or not PINATA_JWT:
    raise Exception("Pinata credentials (PINATA_API_KEY, PINATA_API_SECRET, PINATA_JWT) must be set in the environment.")


def screenshot_element(element, file_path=None):
    """
    Takes a screenshot of a Selenium WebElement and saves it to a file.
    """
    if file_path is None:
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file_path = temp.name
        temp.close()
    
    # use screenshot_as_png for a robust capture
    png_data = element.screenshot_as_png
    with open(file_path, "wb") as f:
        f.write(png_data)
    
    if os.path.getsize(file_path) == 0:
        raise Exception("Screenshot file is empty")
    return file_path

def pin_file_to_ipfs(file_path):
    """
    Pins a file to IPFS using the Pinata API.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file)}
        response = requests.post(url, headers=headers, files=files)
    
    if response.status_code == 200:
        data = response.json()
        ipfs_hash = data.get("IpfsHash")
        return ipfs_hash
    else:
        raise Exception(f"Failed to pin file to IPFS: {response.text}")

def screenshot_and_pin(element, file_path=None):
    """
    Captures a screenshot of the given Selenium WebElement, uploads it to IPFS,
    and returns the resulting IPFS hash.
    """
    screenshot_path = screenshot_element(element, file_path)
    ipfs_hash = pin_file_to_ipfs(screenshot_path)
    os.remove(screenshot_path)
    return ipfs_hash

if __name__ == "__main__":
    print("IPFS screenshot module loaded successfully.")
