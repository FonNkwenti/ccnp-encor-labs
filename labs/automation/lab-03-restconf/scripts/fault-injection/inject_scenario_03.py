#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Automation Lab 03 (RESTCONF)

Injects Ticket 3 fault. Work through the ticket in workbook.md Section 9
before looking at the solution.

Usage:
    python3 inject_scenario_03.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[4] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "automation/lab-03-restconf.unl"

FAULT: dict[str, list[str]] = {
    "R1": [
        "no ip http secure-server",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 for Automation lab-03")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP — update to match your environment")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    args = parser.parse_args()
    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
    print("[+] Scenario 03 injected. Work through Ticket 3 in workbook.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
