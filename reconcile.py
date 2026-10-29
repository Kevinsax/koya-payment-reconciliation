#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py

Rules (see README):
  * A payment may be attempted several times under one txn_id; only the
    latest attempt (by ts, not by position in the file) counts.
  * A payment is collected only if its latest attempt is "success".
  * Lines that can't be read, and events without a txn_id, are ignored.
"""
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_ts(value):
    """Parse an ISO-8601 UTC timestamp such as 2026-09-21T15:30:26Z."""
    return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))


def parse_amount(value):
    """Amounts arrive as numbers or as strings like '4,804.15'."""
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return Decimal(str(value))


# txn_id -> (ts, line_number, event) for the latest attempt seen so far.
latest = {}

with open("payments.jsonl", "rb") as f:
    for line_no, raw in enumerate(f):
        try:
            event = json.loads(raw)
        except ValueError:  # truncated or otherwise unreadable line
            continue
        if not isinstance(event, dict):
            continue

        txn_id = event.get("txn_id")
        if not txn_id:  # missing, null or empty
            continue

        try:
            ts = parse_ts(event["ts"])
        except (KeyError, ValueError):
            continue

        # Later ts wins; if two attempts share a ts, the later line wins.
        key = (ts, line_no)
        current = latest.get(txn_id)
        if current is None or key > current[0]:
            latest[txn_id] = (key, event)

total = Decimal("0")
count = 0

for _, event in latest.values():
    if event.get("status") != "success":
        continue
    try:
        total += parse_amount(event["amount"])
    except (KeyError, InvalidOperation):
        continue
    count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{int(total.quantize(Decimal('1'), rounding=ROUND_HALF_UP))}")
