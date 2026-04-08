#!/usr/bin/env python3
"""
Extract early Bitcoin addresses (blocks 1-20000) from your local node.
Converts P2PK (raw pubkey) outputs to P2PKH addresses so BitCrack can target them.

Run on a machine that can reach your Bitcoin node at 192.168.55.108:8332

Usage:
    python extract_early_addresses.py [--blocks 20000] [--output targets.txt]
"""

import json
import sys
import time
import hashlib
import argparse
import base64
from urllib.request import Request, urlopen
from urllib.error import URLError

RPC_HOST = "192.168.55.108"
RPC_PORT = 8332
RPC_USER = "journalist_miner"
RPC_PASS = "discovery1999"

def rpc_call(method, params=None):
    if params is None:
        params = []
    payload = json.dumps({
        "jsonrpc": "1.0",
        "id": "extract",
        "method": method,
        "params": params
    }).encode()

    url = f"http://{RPC_HOST}:{RPC_PORT}/"
    req = Request(url, data=payload, headers={"Content-Type": "text/plain"})
    credentials = base64.b64encode(f"{RPC_USER}:{RPC_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")

    for attempt in range(4):
        try:
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                if result.get("error"):
                    raise Exception(f"RPC error: {result['error']}")
                return result["result"]
        except URLError as e:
            if attempt < 3:
                wait = 2 ** (attempt + 1)
                print(f"  Retry in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise

def pubkey_to_address(pubkey_hex):
    """Convert a raw public key (hex) to a P2PKH Bitcoin address."""
    pubkey_bytes = bytes.fromhex(pubkey_hex)
    sha256 = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160', sha256).digest()
    # Add version byte (0x00 for mainnet)
    versioned = b'\x00' + ripemd160
    # Double SHA256 checksum
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    # Base58Check encode
    payload = versioned + checksum
    # Base58 encoding
    alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = int.from_bytes(payload, 'big')
    result = b''
    while n > 0:
        n, r = divmod(n, 58)
        result = alphabet[r:r+1] + result
    # Leading zero bytes become '1'
    for byte in payload:
        if byte == 0:
            result = b'1' + result
        else:
            break
    return result.decode()

def extract_addresses_from_block(block_height):
    """Extract all output addresses from a block, including P2PK outputs."""
    addresses = set()
    block_hash = rpc_call("getblockhash", [block_height])
    block = rpc_call("getblock", [block_hash, 2])

    for tx in block.get("tx", []):
        for vout in tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            # Standard P2PKH/P2SH — node provides the address
            if "addresses" in spk:
                addresses.update(spk["addresses"])
            elif "address" in spk:
                addresses.add(spk["address"])
            # P2PK outputs (early Satoshi-era blocks) — derive address from raw pubkey
            elif spk.get("type") == "pubkey" and "asm" in spk:
                asm = spk["asm"]
                parts = asm.split()
                if parts and len(parts[0]) in (66, 130):  # compressed or uncompressed pubkey
                    try:
                        addr = pubkey_to_address(parts[0])
                        addresses.add(addr)
                    except Exception:
                        pass
    return addresses

def main():
    parser = argparse.ArgumentParser(description="Extract early Bitcoin addresses from local node")
    parser.add_argument("--blocks", type=int, default=20000, help="Number of blocks to scan (default: 20000)")
    parser.add_argument("--output", type=str, default="targets.txt", help="Output file (default: targets.txt)")
    args = parser.parse_args()

    print(f"Connecting to Bitcoin node at {RPC_HOST}:{RPC_PORT}...")
    info = rpc_call("getblockchaininfo")
    print(f"  Chain: {info['chain']}, Blocks: {info['blocks']}")
    print(f"  Scanning blocks 1 to {args.blocks} (including P2PK conversions)...\n")

    all_addresses = set()
    start_time = time.time()

    for height in range(1, args.blocks + 1):
        addrs = extract_addresses_from_block(height)
        all_addresses.update(addrs)

        if height % 500 == 0:
            elapsed = time.time() - start_time
            rate = height / elapsed
            eta = (args.blocks - height) / rate
            print(f"  Block {height}/{args.blocks} | {len(all_addresses)} unique addresses | {rate:.0f} blocks/s | ETA: {eta:.0f}s")

    p2pkh = sorted([a for a in all_addresses if a.startswith('1')])
    print(f"\nExtracted {len(p2pkh)} P2PKH addresses from blocks 1-{args.blocks}")

    with open(args.output, 'w') as f:
        for addr in p2pkh:
            f.write(addr + '\n')

    print(f"Written to {args.output}")
    print(f"\nTo run BitCrack:")
    print(f"  cuBitCrack.exe -i {args.output} --keyspace 1:FFFFFFFFFF")

if __name__ == "__main__":
    main()
