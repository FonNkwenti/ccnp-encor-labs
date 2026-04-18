#!/usr/bin/env python3
"""
Fault Injection: ALL SCENARIOS -- Multicast Lab 02

Applies all 3 faults to R1, R2, and R3 in a single run. Resets the lab
to the pre-broken state for all troubleshooting tickets.

Faults applied:
  R3: SSM range binding removed (Ticket 1)
  R1: bidir-enable removed (Ticket 2)
  R2: MSDP originator-id removed (Ticket 3)

Usage:
    python3 inject_all.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[4] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "multicast/lab-02-ssm-bidir-msdp.unl"

FAULTS: dict[str, list[str]] = {
    "R3": [
        "no ip pim ssm range SSM_RANGE",
    ],
    "R1": [
        "no ip pim bidir-enable",
    ],
    "R2": [
        "no ip msdp originator-id Loopback0",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject all 3 faults for Multicast lab-02")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    args = parser.parse_args()
    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: ALL SCENARIOS (Multicast Lab 02 -- 3 faults)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0
    for device, commands in FAULTS.items():
        port = ports.get(device)
        if port is None:
            print(f"[!] {device}: not found in lab.")
            fail += 1
            continue
        print(f"\n[*] {device}: injecting faults on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
            conn.send_config_set(commands)
            conn.save_config()
            conn.disconnect()
            print(f"[+] {device}: faults applied.")
        except Exception as exc:
            print(f"[!] {device}: failed -- {exc}")
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed.")
        return 1
    print("[+] All 3 faults injected. Lab is now in pre-broken state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
