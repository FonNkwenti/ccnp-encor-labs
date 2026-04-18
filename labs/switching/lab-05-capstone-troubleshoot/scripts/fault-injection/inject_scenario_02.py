#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Allowed VLAN Pruning on Po1 (SW2 side)

Target:     SW2 (Port-channel1 + members Gi0/1, Gi0/2)
Injects:    'switchport trunk allowed vlan 20,30,99' on Po1 and both
            physical members -- VLAN 10 is dropped from the allowed list.
Fault Type: Allowed-VLAN list pruning (silent, trunk stays up)

Result:     - VLAN 10 traffic is blackholed across Po1.
            - PC1 cannot reach its VLAN 10 gateway (192.168.10.1 on R1).
            - VLANs 20, 30, and the native 99 still traverse Po1 cleanly.
            - `show interfaces trunk` 'Vlans allowed on trunk' column
              diverges between SW1 (10,20,30,99) and SW2 (20,30,99).

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
    "interface Port-channel1",
    "switchport trunk allowed vlan 20,30,99",
    "interface GigabitEthernet0/1",
    "switchport trunk allowed vlan 20,30,99",
    "interface GigabitEthernet0/2",
    "switchport trunk allowed vlan 20,30,99",
]
PREFLIGHT_CMD = "show running-config interface Port-channel1"
PREFLIGHT_SOLUTION_MARKER = "LACP_PO1_TO_SW1"
PREFLIGHT_ALLOWED_MARKER = "switchport trunk allowed vlan 10,20,30,99"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Po1 is missing expected description "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_ALLOWED_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Po1 is missing '{PREFLIGHT_ALLOWED_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: 192.168.242.128)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
