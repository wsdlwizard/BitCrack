#!/usr/bin/env python3
"""
Monitor BitCrack results.txt for found keys.
Sends email and plays alarm sound when a key is found.

Run alongside BitCrack:
    python scripts\puzzle_monitor.py --watch results.txt
"""

import os
import sys
import time
import smtplib
import argparse
import winsound
from email.mime.text import MIMEText
from datetime import datetime

def send_email(subject, body, to_email):
    """Send alert email via Gmail SMTP."""
    from_email = to_email
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Using Gmail SMTP - you'll need an App Password
    # Go to: https://myaccount.google.com/apppasswords
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = to_email
    SMTP_PASS = "YOUR_APP_PASSWORD_HERE"  # Replace with Gmail App Password

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f"  Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"  Email failed: {e}")
        return False

def sound_alarm():
    """Play loud alarm sound on Windows."""
    try:
        for _ in range(20):
            winsound.Beep(1000, 500)
            winsound.Beep(1500, 500)
            winsound.Beep(2000, 500)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="Monitor BitCrack for found keys")
    parser.add_argument("--watch", default="results.txt", help="File to watch")
    parser.add_argument("--email", default="ngflower@gmail.com", help="Email for alerts")
    parser.add_argument("--interval", type=int, default=10, help="Check interval in seconds")
    parser.add_argument("--no-sound", action="store_true", help="Disable alarm sound")
    args = parser.parse_args()

    print("=" * 50)
    print("BITCRACK KEY MONITOR")
    print("=" * 50)
    print(f"  Watching:  {args.watch}")
    print(f"  Email:     {args.email}")
    print(f"  Interval:  {args.interval}s")
    print(f"  Sound:     {'off' if args.no_sound else 'on'}")
    print(f"  Started:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Waiting for BitCrack to find a key...")
    print("(This window must stay open)")
    print()

    last_size = 0
    alerted = set()

    while True:
        try:
            if os.path.exists(args.watch):
                size = os.path.getsize(args.watch)
                if size > 0 and size != last_size:
                    last_size = size
                    with open(args.watch, 'r') as f:
                        lines = f.readlines()

                    for line in lines:
                        line = line.strip()
                        if line and line not in alerted:
                            alerted.add(line)
                            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                            print()
                            print("!" * 60)
                            print(f"  KEY FOUND at {now}")
                            print(f"  {line}")
                            print("!" * 60)
                            print()

                            # Save with timestamp
                            with open("KEY_FOUND.txt", "a") as kf:
                                kf.write(f"[{now}] {line}\n")

                            # Send email
                            subject = "BITCRACK KEY FOUND!"
                            body = f"""BitCrack found a private key!

{line}

Time: {now}

NEXT STEPS:
1. DO NOT broadcast via normal mempool
2. Run: python scripts\\puzzle_sweep.py --privkey <key> --to <your_address>
3. Submit raw TX via https://slipstream.mara.com/
4. Wait for 1 confirmation

DO NOT TELL ANYONE until the transaction is confirmed!
"""
                            send_email(subject, body, args.email)

                            # Sound alarm
                            if not args.no_sound:
                                sound_alarm()

            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
