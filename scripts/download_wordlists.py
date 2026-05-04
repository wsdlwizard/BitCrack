#!/usr/bin/env python3
"""
Generate a large brainwallet wordlist from multiple sources.
Creates combined_wordlist.txt with millions of candidate passphrases.
"""

import os
import sys

def generate_large_wordlist(output_file="combined_wordlist.txt"):
    print(f"Generating comprehensive brainwallet wordlist -> {output_file}")
    seen = set()
    count = 0

    with open(output_file, 'w', encoding='utf-8') as f:
        def add(phrase):
            nonlocal count
            if phrase not in seen and len(phrase) > 0:
                seen.add(phrase)
                f.write(phrase + '\n')
                count += 1

        # 1. All numbers 0 to 10,000,000
        print("  Adding numbers 0-10M...")
        for i in range(10_000_001):
            add(str(i))

        # 2. Hex numbers
        print("  Adding hex numbers...")
        for i in range(1_000_000):
            add(hex(i))
            add(hex(i)[2:])

        # 3. Common passwords (rockyou-style top entries)
        print("  Adding common passwords...")
        common = [
            "password", "123456", "12345678", "qwerty", "abc123", "monkey",
            "1234567", "letmein", "trustno1", "dragon", "baseball", "iloveyou",
            "master", "sunshine", "ashley", "michael", "shadow", "123123",
            "654321", "superman", "qazwsx", "michael", "football", "password1",
            "password123", "batman", "login", "hello", "charlie", "donald",
            "admin", "qwerty123", "love", "princess", "rockyou", "nicole",
            "daniel", "babygirl", "lovely", "jessica", "0", "654321",
            "michelle", "amanda", "lakers", "justin", "andrea", "ginger",
            "cookie", "jesus", "summer", "starwars", "computer", "buster",
            "whatever", "pepper", "freedom", "pass", "thunder", "ranger",
            "matrix", "sparky", "snoopy", "silver", "pokemon", "maverick",
            "falcon", "alexander", "mercedes", "camaro", "corvette",
            "bitcoin", "satoshi", "nakamoto", "ethereum", "crypto", "hodl",
            "blockchain", "mining", "wallet", "moon", "lambo", "defi",
            "altcoin", "litecoin", "ripple", "dogecoin", "nft", "web3",
        ]
        for w in common:
            add(w)
            add(w.upper())
            add(w.title())
            for n in range(1000):
                add(f"{w}{n}")
                add(f"{n}{w}")
            for y in range(1950, 2027):
                add(f"{w}{y}")
            add(f"{w}!")
            add(f"{w}!!")
            add(f"{w}@")
            add(f"{w}#")
            add(f"{w}$")
            add(f"{w}1!")

        # 4. Dictionary words (English)
        print("  Adding dictionary words...")
        dict_paths = [
            "/usr/share/dict/words",
            "/usr/share/dict/american-english",
            "C:\\Windows\\System32\\catroot2\\words.txt",
        ]
        for dp in dict_paths:
            if os.path.exists(dp):
                with open(dp, 'r', errors='ignore') as df:
                    for line in df:
                        w = line.strip()
                        if w:
                            add(w)
                            add(w.lower())

        # 5. Famous phrases and quotes
        print("  Adding famous phrases...")
        phrases = [
            "correct horse battery staple",
            "to be or not to be",
            "to be or not to be that is the question",
            "the quick brown fox jumps over the lazy dog",
            "all your base are belong to us",
            "i love you", "i love bitcoin", "i hate you",
            "hello world", "goodbye world",
            "in god we trust", "e pluribus unum",
            "we the people", "life liberty and the pursuit of happiness",
            "i think therefore i am", "cogito ergo sum",
            "veni vidi vici", "et tu brute",
            "the meaning of life", "42", "the answer is 42",
            "do or do not there is no try",
            "may the force be with you", "use the force luke",
            "i am your father", "luke i am your father",
            "live long and prosper", "beam me up scotty",
            "to infinity and beyond", "hakuna matata",
            "just keep swimming", "let it go",
            "winter is coming", "valar morghulis",
            "one ring to rule them all",
            "my precious", "you shall not pass",
            "i see dead people", "here's johnny",
            "frankly my dear i dont give a damn",
            "toto i have a feeling we're not in kansas anymore",
            "there's no place like home",
            "i'll be back", "hasta la vista baby",
            "say hello to my little friend",
            "show me the money", "you cant handle the truth",
            "houston we have a problem",
            "elementary my dear watson",
            "bond james bond", "shaken not stirred",
            "i am satoshi nakamoto", "satoshi nakamoto",
            "hal finney", "nick szabo", "wei dai", "adam back",
            "genesis block", "block 0",
            "chancellor on brink of second bailout for banks",
            "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks",
            "never gonna give you up", "never gonna let you down",
            "stairway to heaven", "highway to hell",
            "hotel california", "bohemian rhapsody",
            "let it be", "hey jude", "yesterday",
            "imagine all the people", "all you need is love",
            "we are the champions", "we will rock you",
            "another one bites the dust",
            "under pressure", "dont stop me now",
            "money money money", "dancing queen",
            "smells like teen spirit", "come as you are",
            "nothing else matters", "enter sandman",
            "sweet child o mine", "welcome to the jungle",
            "back in black", "thunderstruck",
            "smoke on the water", "deep purple",
            "born to run", "like a rolling stone",
            "purple rain", "when doves cry",
            "superstition", "isnt she lovely",
            "what a wonderful world", "over the rainbow",
            "fly me to the moon", "my way",
            "new york new york", "la vie en rose",
            "dont worry be happy", "three little birds",
            "one love", "redemption song", "no woman no cry",
            "every breath you take", "message in a bottle",
            "roxanne", "walking on the moon",
            "billie jean", "thriller", "beat it",
            "smooth criminal", "bad", "dangerous",
            "bitcoin to the moon", "buy the dip",
            "not your keys not your coins",
            "be your own bank", "stack sats",
            "number go up", "have fun staying poor",
            "few understand this", "we are all satoshi",
            "the genesis block",
            "0000000000000000000000000000000000000000000000000000000000000001",
            "0000000000000000000000000000000000000000000000000000000000000000",
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "deadbeef", "cafebabe", "8badf00d", "1badb002",
        ]
        for p in phrases:
            add(p)
            add(p.lower())
            add(p.upper())
            add(p.title())
            add(p.replace(" ", ""))
            add(p.replace(" ", "_"))
            add(p.replace(" ", "-"))

        # 6. Email-style patterns
        print("  Adding email-style patterns...")
        names = ["john", "james", "robert", "michael", "david", "richard",
                 "joseph", "thomas", "charles", "william", "daniel", "mark",
                 "paul", "steven", "andrew", "kenneth", "george", "edward",
                 "brian", "kevin", "jason", "matthew", "timothy", "ronald",
                 "mary", "patricia", "jennifer", "linda", "elizabeth", "susan",
                 "jessica", "sarah", "karen", "nancy", "lisa", "margaret",
                 "betty", "sandra", "ashley", "dorothy", "kimberly", "emily",
                 "donna", "michelle", "carol", "amanda", "melissa", "deborah",
                 "alice", "bob", "charlie", "dave", "eve", "frank",
                 "satoshi", "vitalik", "gavin", "roger", "nick"]
        for name in names:
            add(name)
            for n in range(100):
                add(f"{name}{n}")
            for y in range(1950, 2010):
                add(f"{name}{y}")

        # 7. Keyboard walks
        print("  Adding keyboard patterns...")
        walks = [
            "qwerty", "qwertyuiop", "asdfghjkl", "zxcvbnm",
            "qweasdzxc", "1qaz2wsx", "1qaz2wsx3edc",
            "qweasd", "zaqwsx", "1q2w3e4r", "1q2w3e4r5t",
            "qazwsx", "qazwsxedc", "zaq12wsx",
            "1234qwer", "qwer1234", "asdf1234",
            "!@#$%^&*", "1234!@#$",
        ]
        for w in walks:
            add(w)
            for n in range(100):
                add(f"{w}{n}")

        # 8. Dates
        print("  Adding dates...")
        for y in range(1900, 2027):
            for m in range(1, 13):
                for d in range(1, 32):
                    add(f"{y}{m:02d}{d:02d}")
                    add(f"{d:02d}{m:02d}{y}")
                    add(f"{m:02d}{d:02d}{y}")
                    add(f"{y}-{m:02d}-{d:02d}")
                    add(f"{d:02d}/{m:02d}/{y}")

    print(f"\nDone! {count:,} unique passphrases written to {output_file}")
    size_mb = os.path.getsize(output_file) / 1024 / 1024
    print(f"File size: {size_mb:.1f} MB")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "combined_wordlist.txt"
    generate_large_wordlist(output)
