#!/usr/bin/env python3
"""
Bitcoin Puzzle Sweep Tool
Builds a raw transaction and submits it via private relay (MARA Slipstream)
to avoid mempool front-running bots.

IMPORTANT: Do NOT broadcast via normal mempool! Use private relay only.

Usage:
    python puzzle_sweep.py --privkey <hex> --to <your_address>
"""

import hashlib
import struct
import sys
import argparse
import time
from urllib.request import Request, urlopen
from urllib.error import URLError
import json
import base64

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# --- EC Math ---

def modinv(a, m=P):
    return pow(a, m - 2, m)

def point_add(p1, p2):
    if p1 is None: return p2
    if p2 is None: return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if y1 != y2: return None
        lam = (3 * x1 * x1) * modinv(2 * y1) % P
    else:
        lam = (y2 - y1) * modinv(x2 - x1) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)

def scalar_mult(k, point=(Gx, Gy)):
    result = None
    addend = point
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result

# --- Address encoding ---

def hash160(data):
    return hashlib.new('ripemd160', hashlib.sha256(data).digest()).digest()

def base58check_encode(version, payload):
    data = bytes([version]) + payload
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    combined = data + checksum
    alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = int.from_bytes(combined, 'big')
    result = b''
    while n > 0:
        n, r = divmod(n, 58)
        result = alphabet[r:r+1] + result
    for byte in combined:
        if byte == 0:
            result = b'1' + result
        else:
            break
    return result.decode()

def base58check_decode(address):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = 0
    for c in address:
        n = n * 58 + alphabet.index(c)
    combined = n.to_bytes(25, 'big')
    version = combined[0]
    payload = combined[1:-4]
    checksum = combined[-4:]
    verify = hashlib.sha256(hashlib.sha256(combined[:-4]).digest()).digest()[:4]
    if checksum != verify:
        raise ValueError("Invalid checksum")
    return version, payload

def privkey_to_compressed_pubkey(privkey_int):
    point = scalar_mult(privkey_int)
    x, y = point
    prefix = b'\x02' if y % 2 == 0 else b'\x03'
    return prefix + x.to_bytes(32, 'big')

def pubkey_to_address(pubkey_bytes):
    h = hash160(pubkey_bytes)
    return base58check_encode(0, h)

# --- Transaction building ---

def varint(n):
    if n < 0xfd:
        return struct.pack('<B', n)
    elif n <= 0xffff:
        return b'\xfd' + struct.pack('<H', n)
    elif n <= 0xffffffff:
        return b'\xfe' + struct.pack('<I', n)
    else:
        return b'\xff' + struct.pack('<Q', n)

def create_p2pkh_scriptPubKey(address):
    version, h160 = base58check_decode(address)
    return b'\x76\xa9\x14' + h160 + b'\x88\xac'

def sign_transaction(privkey_int, pubkey_bytes, tx_hex, input_index, scriptPubKey):
    """Sign a transaction input using ECDSA."""
    tx_bytes = bytes.fromhex(tx_hex)

    # For signing, we need the transaction with scriptPubKey in the input
    # This is a simplified sighash computation for P2PKH
    sighash_type = 1  # SIGHASH_ALL

    # Build the pre-image for signing
    # Replace all scriptSigs with empty, then put scriptPubKey in the one being signed
    preimage = b''
    preimage += struct.pack('<I', 1)  # version

    # Parse and rebuild with correct scriptSig for signing
    offset = 4  # skip version
    num_inputs = tx_bytes[offset]
    offset += 1
    preimage += varint(num_inputs)

    for i in range(num_inputs):
        preimage += tx_bytes[offset:offset+32]  # txid
        offset += 32
        preimage += tx_bytes[offset:offset+4]  # vout
        offset += 4
        script_len = tx_bytes[offset]
        offset += 1
        offset += script_len  # skip original scriptSig
        if i == input_index:
            preimage += varint(len(scriptPubKey))
            preimage += scriptPubKey
        else:
            preimage += varint(0)
        preimage += tx_bytes[offset:offset+4]  # sequence
        offset += 4

    # outputs
    preimage += tx_bytes[offset:]

    # append sighash type
    preimage += struct.pack('<I', sighash_type)

    # Double SHA256
    sighash = hashlib.sha256(hashlib.sha256(preimage).digest()).digest()
    z = int.from_bytes(sighash, 'big')

    # ECDSA sign
    import secrets
    while True:
        k = secrets.randbelow(N - 1) + 1
        point = scalar_mult(k)
        r = point[0] % N
        if r == 0:
            continue
        s = (modinv(k, N) * (z + r * privkey_int)) % N
        if s == 0:
            continue
        # Use low-s
        if s > N // 2:
            s = N - s
        break

    # DER encode signature
    def der_encode_int(v):
        b = v.to_bytes((v.bit_length() + 8) // 8, 'big')
        return b'\x02' + bytes([len(b)]) + b

    r_der = der_encode_int(r)
    s_der = der_encode_int(s)
    der_sig = b'\x30' + bytes([len(r_der) + len(s_der)]) + r_der + s_der
    der_sig += bytes([sighash_type])

    # Build scriptSig: <sig> <pubkey>
    scriptSig = bytes([len(der_sig)]) + der_sig + bytes([len(pubkey_bytes)]) + pubkey_bytes

    return scriptSig


def build_sweep_transaction(privkey_hex, dest_address, utxos, fee_rate_sat_vbyte=100):
    """
    Build a raw transaction sweeping all UTXOs to dest_address.

    privkey_hex: hex string of private key
    dest_address: destination Bitcoin address (yours)
    utxos: list of dicts with 'txid', 'vout', 'amount' (in BTC), 'scriptPubKey'
    fee_rate_sat_vbyte: fee rate (default 100 sat/vbyte for fast confirmation)
    """
    privkey_int = int(privkey_hex, 16)
    pubkey = privkey_to_compressed_pubkey(privkey_int)
    source_address = pubkey_to_address(pubkey)

    print(f"  Source address:  {source_address}")
    print(f"  Dest address:    {dest_address}")
    print(f"  UTXOs:           {len(utxos)}")

    total_sats = sum(int(round(u['amount'] * 1e8)) for u in utxos)
    print(f"  Total input:     {total_sats} sats ({total_sats/1e8:.8f} BTC)")

    # Estimate tx size: ~148 bytes per input + 34 bytes per output + 10 overhead
    est_size = len(utxos) * 148 + 34 + 10
    fee = est_size * fee_rate_sat_vbyte
    output_sats = total_sats - fee

    if output_sats <= 0:
        raise ValueError(f"Fee ({fee} sats) exceeds total input ({total_sats} sats)")

    print(f"  Fee:             {fee} sats ({fee/1e8:.8f} BTC) @ {fee_rate_sat_vbyte} sat/vB")
    print(f"  Output:          {output_sats} sats ({output_sats/1e8:.8f} BTC)")

    # Build unsigned transaction
    version = struct.pack('<I', 1)
    locktime = struct.pack('<I', 0)

    # Inputs
    tx_ins = varint(len(utxos))
    for u in utxos:
        txid_bytes = bytes.fromhex(u['txid'])[::-1]  # reverse byte order
        tx_ins += txid_bytes
        tx_ins += struct.pack('<I', u['vout'])
        tx_ins += varint(0)  # empty scriptSig (to be filled after signing)
        tx_ins += struct.pack('<I', 0xffffffff)  # sequence

    # Output
    tx_outs = varint(1)
    tx_outs += struct.pack('<Q', output_sats)
    dest_script = create_p2pkh_scriptPubKey(dest_address)
    tx_outs += varint(len(dest_script))
    tx_outs += dest_script

    unsigned_tx = version + tx_ins + tx_outs + locktime
    unsigned_hex = unsigned_tx.hex()

    # Sign each input
    source_scriptPubKey = create_p2pkh_scriptPubKey(source_address)

    # Rebuild with signatures
    signed_tx = version
    signed_tx += varint(len(utxos))

    for i, u in enumerate(utxos):
        txid_bytes = bytes.fromhex(u['txid'])[::-1]
        signed_tx += txid_bytes
        signed_tx += struct.pack('<I', u['vout'])

        scriptSig = sign_transaction(privkey_int, pubkey, unsigned_hex, i, source_scriptPubKey)
        signed_tx += varint(len(scriptSig))
        signed_tx += scriptSig
        signed_tx += struct.pack('<I', 0xffffffff)

    signed_tx += tx_outs
    signed_tx += locktime

    return signed_tx.hex()


def get_utxos_from_node(address):
    """Get UTXOs from your local Bitcoin node."""
    payload = json.dumps({
        "jsonrpc": "1.0", "id": "sweep",
        "method": "scantxoutset",
        "params": ["start", [{"desc": f"addr({address})"}]]
    }).encode()
    req = Request(
        "http://192.168.55.108:8332/",
        data=payload,
        headers={"Content-Type": "text/plain"}
    )
    creds = base64.b64encode(b"journalist_miner:discovery1999").decode()
    req.add_header("Authorization", f"Basic {creds}")
    with urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())["result"]
    utxos = []
    for u in result.get("unspents", []):
        utxos.append({
            "txid": u["txid"],
            "vout": u["vout"],
            "amount": float(u["amount"]),
            "scriptPubKey": u.get("scriptPubKey", "")
        })
    return utxos


def main():
    parser = argparse.ArgumentParser(description="Sweep Bitcoin puzzle funds safely")
    parser.add_argument("--privkey", required=True, help="Private key in hex (from BitCrack results.txt)")
    parser.add_argument("--to", required=True, help="YOUR Bitcoin address to receive funds")
    parser.add_argument("--fee-rate", type=int, default=100, help="Fee rate in sat/vbyte (default: 100)")
    parser.add_argument("--broadcast", action="store_true", help="Actually submit (without this flag, just builds and shows)")
    args = parser.parse_args()

    print("=" * 60)
    print("BITCOIN PUZZLE SWEEP TOOL")
    print("=" * 60)
    print()
    print("WARNING: Do NOT broadcast via normal mempool!")
    print("         Use MARA Slipstream or similar private relay.")
    print()

    privkey_int = int(args.privkey, 16)
    pubkey = privkey_to_compressed_pubkey(privkey_int)
    source_address = pubkey_to_address(pubkey)

    print(f"Derived address: {source_address}")
    print(f"Looking up UTXOs on your Bitcoin node...")
    print()

    utxos = get_utxos_from_node(source_address)

    if not utxos:
        print("No UTXOs found for this address!")
        print("Either the address is empty or the key is wrong.")
        sys.exit(1)

    raw_tx = build_sweep_transaction(args.privkey, args.to, utxos, args.fee_rate)

    print()
    print("=" * 60)
    print("RAW SIGNED TRANSACTION")
    print("=" * 60)
    print()
    print(raw_tx)
    print()
    print(f"Transaction size: {len(raw_tx)//2} bytes")
    print()
    print("=" * 60)
    print("NEXT STEPS - READ CAREFULLY")
    print("=" * 60)
    print()
    print("1. DO NOT broadcast this via bitcoin-cli sendrawtransaction")
    print("   (that goes to the public mempool and WILL be front-run)")
    print()
    print("2. Submit via MARA Slipstream:")
    print("   https://slipstream.mara.com/")
    print("   Paste the raw transaction hex above")
    print()
    print("3. Alternative: ViaBTC transaction accelerator")
    print("   or contact a mining pool directly")
    print()
    print("4. Wait for 1 confirmation before celebrating")
    print()

    # Save to file
    with open("sweep_transaction.txt", "w") as f:
        f.write(f"Private Key: {args.privkey}\n")
        f.write(f"Source: {source_address}\n")
        f.write(f"Destination: {args.to}\n")
        f.write(f"Raw TX:\n{raw_tx}\n")
    print("Raw transaction saved to: sweep_transaction.txt")


if __name__ == "__main__":
    main()
