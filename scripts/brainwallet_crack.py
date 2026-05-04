#!/usr/bin/env python3
"""
Brainwallet cracker: SHA256(passphrase) -> private key -> Bitcoin address
Checks against a target list of dormant addresses.

Usage:
    python brainwallet_crack.py --targets dormant_addresses_merged_bitcrack.txt --wordlist wordlist.txt
    python brainwallet_crack.py --targets dormant_addresses_merged_bitcrack.txt --generate
"""

import hashlib
import sys
import os
import time
import argparse
import itertools
from multiprocessing import Pool, cpu_count, Value

# secp256k1 curve parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def modinv(a, m=P):
    return pow(a, m - 2, m)

def point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if y1 != y2:
            return None
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

def privkey_to_address(privkey_bytes, compressed=True):
    k = int.from_bytes(privkey_bytes, 'big')
    if k == 0 or k >= N:
        return None, None
    point = scalar_mult(k)
    x, y = point
    if compressed:
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        pubkey = prefix + x.to_bytes(32, 'big')
    else:
        pubkey = b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    sha = hashlib.sha256(pubkey).digest()
    ripemd = hashlib.new('ripemd160', sha).digest()
    versioned = b'\x00' + ripemd
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    address_bytes = versioned + checksum
    alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = int.from_bytes(address_bytes, 'big')
    result = b''
    while n > 0:
        n, r = divmod(n, 58)
        result = alphabet[r:r + 1] + result
    for byte in address_bytes:
        if byte == 0:
            result = b'1' + result
        else:
            break
    return result.decode(), privkey_bytes.hex()

def check_phrase(phrase):
    privkey = hashlib.sha256(phrase.encode('utf-8')).digest()
    addr_c, key_c = privkey_to_address(privkey, compressed=True)
    addr_u, key_u = privkey_to_address(privkey, compressed=False)
    return phrase, addr_c, addr_u, key_c

def generate_passphrases():
    """Generate common brainwallet passphrases."""
    # Single common words
    common_words = [
        "password", "123456", "bitcoin", "letmein", "master", "dragon",
        "monkey", "shadow", "sunshine", "princess", "football", "charlie",
        "trustno1", "iloveyou", "welcome", "admin", "login", "abc123",
        "starwars", "hello", "freedom", "whatever", "qwerty", "ninja",
        "mustang", "access", "flower", "hottie", "loveme", "zaq1zaq1",
        "passw0rd", "test", "god", "love", "sex", "money", "power",
        "secret", "fuck", "fuckyou", "shit", "biteme", "asshole",
        "killer", "jordan", "hunter", "buster", "soccer", "hockey",
        "ranger", "harley", "andrew", "tiger", "robert", "pepper",
        "summer", "daniel", "david", "thomas", "george", "chicken",
        "hammer", "yankees", "joshua", "maggie", "butter", "cheese",
        "computer", "corvette", "mercedes", "diamond", "steelers",
        "cocacola", "fantasy", "nothing", "internet", "explorer",
        "midnight", "creative", "sparky", "ginger", "scooter",
        "peanut", "cookie", "bigdog", "barney", "batman", "cowboy",
        "eagles", "fishing", "baseball", "swimming", "dolphin",
        "gordon", "casper", "stupid", "phoenix", "lucky", "alexis",
        "samantha", "patrick", "rachel", "crystal", "andrea",
        "snoopy", "matrix", "whatever1", "princess1", "purple",
        "russell", "donald", "jessica", "jackson", "amanda",
        "wizard", "bandit", "braves", "ferrari", "knight",
        "bitcoin1", "satoshi", "nakamoto", "blockchain", "crypto",
        "wallet", "mining", "hodl", "moon", "lambo",
    ]
    for w in common_words:
        yield w

    # Numbers
    for i in range(1000000):
        yield str(i)

    # Common phrases
    phrases = [
        "correct horse battery staple",
        "to be or not to be",
        "the quick brown fox jumps over the lazy dog",
        "all your base are belong to us",
        "i love you",
        "i love bitcoin",
        "bitcoin is freedom",
        "in god we trust",
        "e pluribus unum",
        "hello world",
        "the meaning of life",
        "42",
        "how much wood would a woodchuck chuck",
        "to infinity and beyond",
        "live long and prosper",
        "may the force be with you",
        "i am satoshi nakamoto",
        "satoshi nakamoto",
        "hal finney",
        "nick szabo",
        "wei dai",
        "adam back",
        "genesis block",
        "chancellor on brink of second bailout for banks",
        "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks",
        "never gonna give you up",
        "here comes the sun",
        "stairway to heaven",
        "let it be",
        "bohemian rhapsody",
        "hotel california",
        "imagine all the people",
        "we are the champions",
        "another one bites the dust",
        "money money money",
        "dont worry be happy",
        "what is love",
        "sweet home alabama",
        "nothing else matters",
        "smells like teen spirit",
        "come as you are",
        "yesterday all my troubles seemed so far away",
        "all you need is love",
        "i cant get no satisfaction",
        "we will rock you",
        "born to run",
        "like a rolling stone",
        "purple rain",
        "supercalifragilisticexpialidocious",
        "abracadabra",
        "open sesame",
        "please please please",
        "test test test",
        "1234567890",
        "0987654321",
        "aaaaaaaaaa",
        "abcdefghij",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
        "the password is password",
        "pass",
        "passwd",
        "p@ssw0rd",
        "root",
        "toor",
        "administrator",
        "changeme",
        "default",
        "guest",
        "private",
        "public",
        "master key",
        "my bitcoin wallet",
        "my wallet",
        "brain wallet",
        "brainwallet",
    ]
    for p in phrases:
        yield p
        yield p.lower()
        yield p.upper()
        yield p.title()

    # Dictionary words with number suffixes
    for w in common_words[:50]:
        for n in range(100):
            yield f"{w}{n}"
        for year in range(1970, 2026):
            yield f"{w}{year}"

    # Word pairs from top words
    top_words = common_words[:30]
    for a, b in itertools.product(top_words, repeat=2):
        yield f"{a}{b}"
        yield f"{a} {b}"
        yield f"{a}_{b}"

    # Hex strings people might use
    for i in range(256):
        yield f"{i:02x}" * 16
    for i in range(16):
        yield f"{i:x}" * 64

    # Single characters repeated
    for c in "abcdefghijklmnopqrstuvwxyz0123456789":
        for length in range(1, 65):
            yield c * length

    # Bible verses, famous quotes
    quotes = [
        "in the beginning god created the heavens and the earth",
        "for god so loved the world",
        "i think therefore i am",
        "to be or not to be that is the question",
        "we hold these truths to be self evident",
        "ask not what your country can do for you",
        "i have a dream",
        "one small step for man one giant leap for mankind",
        "the only thing we have to fear is fear itself",
        "give me liberty or give me death",
        "et tu brute",
        "veni vidi vici",
        "cogito ergo sum",
        "e=mc2",
        "pi=3.14159265358979323846",
        "2.718281828459045",
        "1.618033988749895",
    ]
    for q in quotes:
        yield q
        yield q.title()


def load_targets(filepath):
    print(f"Loading targets from {filepath}...")
    targets = set()
    with open(filepath, 'r') as f:
        for line in f:
            addr = line.strip()
            if addr and addr.startswith('1'):
                targets.add(addr)
    print(f"  {len(targets):,} target addresses loaded")
    return targets


def load_wordlist(filepath):
    print(f"Loading wordlist from {filepath}...")
    count = 0
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            word = line.strip()
            if word:
                count += 1
                yield word
    print(f"  {count:,} words loaded")


def main():
    parser = argparse.ArgumentParser(description="Brainwallet cracker")
    parser.add_argument("--targets", required=True, help="File with target Bitcoin addresses")
    parser.add_argument("--wordlist", help="Wordlist file (one phrase per line)")
    parser.add_argument("--generate", action="store_true", help="Use built-in passphrase generator")
    parser.add_argument("--output", default="brainwallet_found.txt", help="Output file for found keys")
    parser.add_argument("--workers", type=int, default=0, help="Number of worker processes (0=auto)")
    args = parser.parse_args()

    if not args.wordlist and not args.generate:
        print("Error: specify --wordlist <file> or --generate (or both)")
        sys.exit(1)

    targets = load_targets(args.targets)
    if not targets:
        print("No targets loaded!")
        sys.exit(1)

    workers = args.workers if args.workers > 0 else cpu_count()
    print(f"Using {workers} worker processes")
    print(f"Checking both compressed and uncompressed addresses")
    print(f"Results will be saved to: {args.output}\n")

    found_count = 0
    checked = 0
    start_time = time.time()
    batch_size = 1000
    batch = []

    def process_batch(batch):
        nonlocal found_count, checked
        with Pool(workers) as pool:
            results = pool.map(check_phrase, batch)
        for phrase, addr_c, addr_u, privkey in results:
            checked += 1
            if addr_c in targets:
                found_count += 1
                msg = f"FOUND! Phrase: '{phrase}' | Address(c): {addr_c} | Key: {privkey}"
                print(f"\n{'='*70}\n{msg}\n{'='*70}")
                with open(args.output, 'a') as f:
                    f.write(f"{privkey} {addr_c} {phrase} (compressed)\n")
            if addr_u in targets:
                found_count += 1
                msg = f"FOUND! Phrase: '{phrase}' | Address(u): {addr_u} | Key: {privkey}"
                print(f"\n{'='*70}\n{msg}\n{'='*70}")
                with open(args.output, 'a') as f:
                    f.write(f"{privkey} {addr_u} {phrase} (uncompressed)\n")

        elapsed = time.time() - start_time
        rate = checked / elapsed if elapsed > 0 else 0
        print(f"\r  Checked: {checked:,} | Rate: {rate:.0f}/sec | Found: {found_count} | Elapsed: {elapsed:.0f}s", end="", flush=True)

    def run_phrases(phrase_iter):
        nonlocal batch
        for phrase in phrase_iter:
            batch.append(phrase)
            if len(batch) >= batch_size:
                process_batch(batch)
                batch = []
        if batch:
            process_batch(batch)
            batch = []

    if args.generate:
        print("Running built-in passphrase generator...")
        run_phrases(generate_passphrases())

    if args.wordlist:
        print(f"\nRunning wordlist: {args.wordlist}")
        run_phrases(load_wordlist(args.wordlist))

    elapsed = time.time() - start_time
    print(f"\n\n{'='*50}")
    print(f"COMPLETE")
    print(f"  Checked: {checked:,} passphrases")
    print(f"  Found: {found_count} keys")
    print(f"  Duration: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    print(f"  Results: {args.output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
