#!/usr/bin/env python3
"""
Check brainwallet found keys against your Bitcoin node for unspent funds.
Batches all addresses into a single scantxoutset call.

Usage:
    python check_balances.py --found brainwallet_found.txt
"""

import json
import base64
import sys
import time
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError

RPC_HOST = "192.168.55.108"
RPC_PORT = 8332
RPC_USER = "journalist_miner"
RPC_PASS = "discovery1999"

def rpc_call(method, params=None, timeout=600):
    payload = json.dumps({
        "jsonrpc": "1.0",
        "id": "check",
        "method": method,
        "params": params or []
    }).encode()
    req = Request(
        f"http://{RPC_HOST}:{RPC_PORT}/",
        data=payload,
        headers={"Content-Type": "text/plain"}
    )
    credentials = base64.b64encode(f"{RPC_USER}:{RPC_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")
    for attempt in range(4):
        try:
            with urlopen(req, timeout=timeout) as resp:
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

def main():
    parser = argparse.ArgumentParser(description="Check brainwallet keys for unspent funds")
    parser.add_argument("--found", default="brainwallet_found.txt", help="File with found keys")
    parser.add_argument("--output", default="funded_wallets.txt", help="Output file for funded wallets")
    args = parser.parse_args()

    print(f"Loading found keys from {args.found}...")
    entries = {}
    with open(args.found, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                privkey = parts[0]
                address = parts[1]
                phrase = " ".join(parts[2:])
                entries[address] = (privkey, phrase)

    print(f"  {len(entries)} unique addresses to check")
    print(f"  Connecting to Bitcoin node at {RPC_HOST}:{RPC_PORT}...")

    # Build a single batch scan with all addresses
    descriptors = [{"desc": f"addr({addr})"} for addr in entries.keys()]

    print(f"  Scanning UTXO set for all {len(descriptors)} addresses in one call...")
    print(f"  This may take 1-2 minutes, please wait...\n")

    result = rpc_call("scantxoutset", ["start", descriptors], timeout=600)

    total_amount = result.get("total_amount", 0)
    unspents = result.get("unspents", [])
    searched = result.get("txouts", 0)

    print(f"  Scanned {searched:,} UTXOs")
    print()

    # Group unspents by address
    funded = {}
    for utxo in unspents:
        addr = utxo.get("desc", "")
        # Extract address from descriptor like "addr(1xxx...)#checksum"
        if "addr(" in addr:
            addr = addr.split("addr(")[1].split(")")[0]
        else:
            addr = utxo.get("scriptPubKey", {}).get("address", addr)

        if addr not in funded:
            funded[addr] = {"amount": 0, "utxos": []}
        funded[addr]["amount"] += float(utxo.get("amount", 0))
        funded[addr]["utxos"].append(utxo)

    print("=" * 60)
    print(f"RESULTS")
    print(f"  Total addresses checked: {len(entries)}")
    print(f"  Empty:                   {len(entries) - len(funded)}")
    print(f"  FUNDED:                  {len(funded)}")
    print(f"  Total BTC found:         {float(total_amount)}")
    print("=" * 60)

    if funded:
        print()
        print("!!! FUNDED WALLETS FOUND !!!")
        print()
        total_btc = 0
        with open(args.output, 'w') as f:
            for addr, info in sorted(funded.items(), key=lambda x: -x[1]["amount"]):
                privkey, phrase = entries.get(addr, ("unknown", "unknown"))
                btc = info["amount"]
                total_btc += btc
                print(f"  {addr}")
                print(f"    Balance: {btc:.8f} BTC")
                print(f"    Phrase:  {phrase}")
                print(f"    Key:     {privkey}")
                print(f"    UTXOs:   {len(info['utxos'])}")
                print()
                f.write(f"{privkey} {addr} {btc:.8f} BTC | {phrase}\n")
                for u in info["utxos"]:
                    f.write(f"  txid: {u.get('txid','')} vout: {u.get('vout','')} amount: {u.get('amount','')}\n")

        print(f"  TOTAL: {total_btc:.8f} BTC")
        print(f"  Details saved to: {args.output}")
    else:
        print("\n  No funded wallets found. All addresses are empty.")

if __name__ == "__main__":
    main()
