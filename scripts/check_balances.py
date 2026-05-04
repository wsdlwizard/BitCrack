#!/usr/bin/env python3
"""
Check brainwallet found keys against your Bitcoin node for unspent funds.
Uses scantxoutset to check the live UTXO set.

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

def rpc_call(method, params=None):
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
            with urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                if result.get("error"):
                    raise Exception(f"RPC error: {result['error']}")
                return result["result"]
        except URLError as e:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
            else:
                raise

def check_address(addr):
    """Check if an address has unspent outputs in the UTXO set."""
    result = rpc_call("scantxoutset", ["start", [{"desc": f"addr({addr})"}]])
    if result and result.get("total_amount", 0) > 0:
        return result["total_amount"], result.get("unspents", [])
    return 0, []

def main():
    parser = argparse.ArgumentParser(description="Check brainwallet keys for unspent funds")
    parser.add_argument("--found", default="brainwallet_found.txt", help="File with found keys")
    parser.add_argument("--output", default="funded_wallets.txt", help="Output file for funded wallets")
    args = parser.parse_args()

    print(f"Loading found keys from {args.found}...")
    entries = []
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
                entries.append((privkey, address, phrase))

    print(f"  {len(entries)} keys to check")
    print(f"  Connecting to Bitcoin node at {RPC_HOST}:{RPC_PORT}...")
    print()

    funded = []
    empty = 0

    for i, (privkey, address, phrase) in enumerate(entries):
        try:
            amount, unspents = check_address(address)
            if amount > 0:
                btc_value = float(amount)
                funded.append((privkey, address, phrase, btc_value, unspents))
                print(f"  [{i+1}/{len(entries)}] *** FUNDED *** {address}")
                print(f"             Balance: {btc_value} BTC")
                print(f"             Phrase:  {phrase}")
                print(f"             Key:     {privkey}")
                print(f"             UTXOs:   {len(unspents)}")
                print()
            else:
                empty += 1
                print(f"  [{i+1}/{len(entries)}] Empty: {address} ({phrase})")
        except Exception as e:
            print(f"  [{i+1}/{len(entries)}] Error checking {address}: {e}")

    print()
    print("=" * 60)
    print(f"RESULTS")
    print(f"  Total checked: {len(entries)}")
    print(f"  Empty:         {empty}")
    print(f"  FUNDED:        {len(funded)}")
    print("=" * 60)

    if funded:
        print()
        print("!!! FUNDED WALLETS FOUND !!!")
        print()
        total_btc = 0
        with open(args.output, 'w') as f:
            for privkey, address, phrase, btc, unspents in funded:
                total_btc += btc
                print(f"  {address}: {btc} BTC (phrase: {phrase})")
                f.write(f"{privkey} {address} {btc} BTC | {phrase}\n")
                for u in unspents:
                    f.write(f"  txid: {u.get('txid','')} vout: {u.get('vout','')} amount: {u.get('amount','')}\n")
        print(f"\n  TOTAL: {total_btc} BTC")
        print(f"  Details saved to: {args.output}")
    else:
        print("\n  No funded wallets found. All addresses are empty.")

if __name__ == "__main__":
    main()
