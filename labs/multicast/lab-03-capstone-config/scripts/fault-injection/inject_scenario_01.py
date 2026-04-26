#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Multicast Lab 03 (Capstone I)

Injects Ticket 1 fault. Work through the ticket in workbook.md Section 9
before looking at the solution.

Usage:
    python3 inject_scenario_01.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[4] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "multicast/lab-03-capstone-config.unl"

FAULT: dict[str, list[str]] = {
    "R3": [
        "interface GigabitEthernet0/1",
        "no ip pim sparse-mode",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 for Multicast lab-03")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    args = parser.parse_args()
    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0
    for device, commands in FAULT.items():
        port = ports.get(device)
        if port is None:
            print(f"[!] {device}: not found in lab.")
            fail += 1
            continue
        print(f"\n[*] {device}: injecting fault on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
            conn.send_config_set(commands)
            conn.save_config()
            conn.disconnect()
            print(f"[+] {device}: fault injected.")
        except Exception as exc:
            print(f"[!] {device}: failed -- {exc}")
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed.")
        return 1
    print("[+] Scenario 01 injected. Work through Ticket 1 in workbook.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
