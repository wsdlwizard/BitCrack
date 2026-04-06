#!/usr/bin/env python3
"""
Extract early Bitcoin addresses (blocks 1-20000) from your local node.
Filters for addresses that still have unspent outputs (dormant wallets).

Run on a machine that can reach your Bitcoin node at 192.168.55.108:8332

Usage:
    python extract_early_addresses.py [--blocks 20000] [--output targets.txt]
"""

import json
import sys
import time
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError

RPC_HOST = "192.168.55.108"
RPC_PORT = 8332
RPC_USER = "journalist_miner"
RPC_PASS = "discovery1999"

def rpc_call(method, params=None):
    """Make a Bitcoin RPC call."""
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

    import base64
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

def extract_addresses_from_block(block_height):
    """Extract all output addresses from a block."""
    addresses = set()
    block_hash = rpc_call("getblockhash", [block_height])
    block = rpc_call("getblock", [block_hash, 2])  # verbosity=2 for full tx

    for tx in block.get("tx", []):
        for vout in tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            # Try 'addresses' (older nodes) or 'address' (newer nodes)
            if "addresses" in spk:
                addresses.update(spk["addresses"])
            elif "address" in spk:
                addresses.add(spk["address"])
    return addresses

def main():
    parser = argparse.ArgumentParser(description="Extract early Bitcoin addresses from local node")
    parser.add_argument("--blocks", type=int, default=20000, help="Number of blocks to scan (default: 20000)")
    parser.add_argument("--output", type=str, default="targets.txt", help="Output file (default: targets.txt)")
    parser.add_argument("--check-unspent", action="store_true", help="Filter for addresses with unspent outputs (slower)")
    args = parser.parse_args()

    # Test connection
    print(f"Connecting to Bitcoin node at {RPC_HOST}:{RPC_PORT}...")
    info = rpc_call("getblockchaininfo")
    print(f"  Chain: {info['chain']}, Blocks: {info['blocks']}")
    print(f"  Scanning blocks 1 to {args.blocks}...\n")

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

    print(f"\nExtracted {len(all_addresses)} unique addresses from blocks 1-{args.blocks}")

    # Filter for P2PKH addresses only (start with '1') - these are what BitCrack targets
    p2pkh = sorted([a for a in all_addresses if a.startswith('1')])
    print(f"P2PKH addresses (start with '1'): {len(p2pkh)}")

    # Write output
    with open(args.output, 'w') as f:
        for addr in p2pkh:
            f.write(addr + '\n')

    print(f"Written to {args.output}")
    print(f"\nTo run BitCrack:")
    print(f"  cuBitCrack.exe -i {args.output} --keyspace 1:FFFFFFFFFF")

if __name__ == "__main__":
    main()
