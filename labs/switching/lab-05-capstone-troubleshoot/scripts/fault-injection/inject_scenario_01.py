#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Native VLAN Mismatch on Po2 (SW3 side)

Target:     SW3 (Port-channel2 + members Gi0/3, Gi1/0)
Injects:    'switchport trunk native vlan 1' on Po2 and both physical
            members. SW1 keeps native VLAN 99; the two ends of the
            bundle now disagree.
Fault Type: Native VLAN mismatch on a trunk

Result:     - %CDP-4-NATIVE_VLAN_MISMATCH syslog every 60 s on SW1/SW3.
            - Untagged traffic over Po2 is dropped onto VLAN 1 on the
              SW3 side, silently blackholing native-VLAN 99 traffic.
            - `show interfaces trunk` Native vlan column diverges.
            - Data plane (tagged VLANs 10/20/30) keeps flowing.

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
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "interface Port-channel2",
    "switchport trunk native vlan 1",
    "interface GigabitEthernet0/3",
    "switchport trunk native vlan 1",
    "interface GigabitEthernet1/0",
    "switchport trunk native vlan 1",
]
PREFLIGHT_CMD = "show running-config interface Port-channel2"
PREFLIGHT_SOLUTION_MARKER = "PAGP_PO2_TO_SW1"
PREFLIGHT_NATIVE_99_MARKER = "switchport trunk native vlan 99"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Po2 is missing expected description "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_NATIVE_99_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Po2 is missing '{PREFLIGHT_NATIVE_99_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: 192.168.1.214)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 (Native VLAN Mismatch on Po2)")
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
