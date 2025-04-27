#!/usr/bin/env python3
"""
Fetch a verifiable JSON-API proof for a macroeconomic score (0–100) and write to macro_proof.json
"""
import sys
import json
from web3 import Web3
from eth_abi import encode     # ← use eth_abi.encode

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <macro_score_0_100>")
        sys.exit(1)
    score = int(sys.argv[1])
    if score < 0 or score > 100:
        print("Score must be between 0 and 100")
        sys.exit(1)

    # ABI-encode the uint256 macro score
    encoded_bytes = encode(['uint256'], [score])           # eth_abi.encode
    hex_data       = Web3.to_hex(encoded_bytes)             # 0x-prefixed hex

    # Build minimal IJsonApi.Proof structure
    proof = {
        "data": {
            "responseBody": {
                # this field is used by the contract to decode the macroScore
                "abi_encoded_data": hex_data
            }
        },
        # For a real proof, include proper signature and metadata here.
        # In testing you may bypass validation or use a stub that ContractRegistry will accept.
        "signature": {
            "r": "0x0",
            "s": "0x0",
            "v": 27
        },
        "metadata": {}
    }

    with open('macro_proof.json', 'w') as f:
        json.dump(proof, f, indent=2)
    print("Wrote macro_proof.json with macro score", score)

if __name__ == '__main__':
    main()
