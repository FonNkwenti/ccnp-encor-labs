#!/usr/bin/env python3
"""
Fault Injection: Scenario 04 -- Superior BPDU Triggers Root Guard on SW1 Po1

Target:     SW2 (global spanning-tree priority tuning)
Injects:    'spanning-tree vlan 10 priority 0' on SW2, making SW2 the
            bridge with the lowest possible bridge ID for VLAN 10 and
            sending a superior BPDU across Po1 to SW1. SW1's Po1 has
            root-guard enabled.
Fault Type: Superior BPDU received on a root-guard-protected port

Result:     - %SPANTREE-2-ROOTGUARD_BLOCK syslog on SW1.
            - `show spanning-tree inconsistentports` on SW1 lists
              Po1 as Root Inconsistent for VLAN 10.
            - VLAN 10 traffic across Po1 is blocked until SW2 stops
              claiming root for that VLAN.

Before running, ensure the lab is in the SOLUTION state:
    python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "SW2"
FAULT_COMMANDS = [
    "no spanning-tree vlan 10,30,99 priority 28672",
    "spanning-tree vlan 30,99 priority 28672",
    "spanning-tree vlan 10 priority 0",
]
PREFLIGHT_CMD = "show running-config | include spanning-tree vlan"
PREFLIGHT_SOLUTION_MARKER = "spanning-tree vlan 10,30,99 priority 28672"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 is missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 04 fault")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: 192.168.242.128)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 04 (Superior BPDU / Root Guard on Po1)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    port = ports.get(DEVICE_NAME)
    if port is None:
        print(f"[!] {DEVICE_NAME} not found in lab {args.lab_path}.")
        return 3

    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3

    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        print("[*] Injecting fault configuration ...")
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 04 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
