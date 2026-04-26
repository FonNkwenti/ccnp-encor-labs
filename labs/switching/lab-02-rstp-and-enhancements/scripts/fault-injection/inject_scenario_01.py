#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Superior BPDU Triggers Root Guard on SW1 Po2

Target:     SW3
Injects:    'spanning-tree vlan 10 priority 0' -- SW3 advertises itself
            as a superior root for VLAN 10, triggering SW1's root-guard
            on Po2 (the SW1<->SW3 PAgP link) to enter root-inconsistent state.
Fault Type: Rogue root bridge / root-guard violation

Result:     - %SPANTREE-2-ROOTGUARD_BLOCK syslog on SW1.
            - `show spanning-tree inconsistentports` on SW1 lists
              Po2 as Root Inconsistent for VLAN 10.
            - VLAN 10 traffic across Po2 is blocked until SW3 stops
              claiming root for that VLAN. PC1 (VLAN 10) loses
              inter-VLAN reachability through R1.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-02-rstp-and-enhancements.unl"
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "spanning-tree vlan 10 priority 0",
]
PREFLIGHT_CMD = "show running-config | include spanning-tree vlan"
PREFLIGHT_FAULT_MARKER = "spanning-tree vlan 10 priority 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present on SW3.")
        print("    Scenario 01 appears to be already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
