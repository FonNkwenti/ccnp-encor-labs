#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Native VLAN Mismatch on Po1 (SW2 side)

Target:     SW2 (Port-channel1 and its physical members Gi0/1, Gi0/2)
Injects:    'switchport trunk native vlan 1' on Po1 and both of its
            physical members. SW1 still carries native VLAN 99, so the
            two ends of the bundle now disagree on the native VLAN.
Fault Type: Native VLAN mismatch on a trunk

Result:     - %CDP-4-NATIVE_VLAN_MISMATCH syslog messages fire every 60 s
              on both SW1 and SW2.
            - Untagged traffic (VLAN 99 management, plus the management
              SVI reachability across the bundle) is black-holed on Po1.
            - `show interfaces trunk` on SW1 and SW2 show different
              Native vlan values for Po1.
            - PC1 <-> PC2 end-to-end ping breaks because VLAN 99
              (management) is effectively severed between SW1 and SW2
              and VLAN 20 hair-pinning through SW3 is not guaranteed
              when Po1 drops untagged/native flow metadata.

The fault is applied on BOTH the physical members AND the Port-channel
interface so the running-config stays consistent and student
`show interfaces trunk` output for Po1 actually reflects native 1
(otherwise the Port-channel overrides what members show individually
once renegotiated).

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-04-capstone-config.unl"
DEVICE_NAME = "SW2"
FAULT_COMMANDS = [
    "interface Port-channel1",
    "switchport trunk native vlan 1",
    "interface GigabitEthernet0/1",
    "switchport trunk native vlan 1",
    "interface GigabitEthernet0/2",
    "switchport trunk native vlan 1",
]
PREFLIGHT_CMD = "show running-config interface Port-channel1"
# Solution marker: SW2 Po1 has description LACP_PO1_TO_SW1 and native vlan 99
PREFLIGHT_SOLUTION_MARKER = "LACP_PO1_TO_SW1"
PREFLIGHT_NATIVE_99_MARKER = "switchport trunk native vlan 99"
# Fault marker: if already present, the fault is already injected -- bail out
PREFLIGHT_FAULT_MARKER = "switchport trunk native vlan 1\n"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Po1 does not have expected description "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_NATIVE_99_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Po1 does not have '{PREFLIGHT_NATIVE_99_MARKER}'.")
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
    print("Fault Injection: Scenario 01 (Native VLAN Mismatch on Po1)")
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
