#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Missing Allowed VLAN on Trunk

Target:     SW1 (all four switch-facing trunks: Gi0/1, Gi0/2, Gi0/3, Gi1/0)
Injects:    Removes VLAN 20 from the trunk allowed list on every SW1 egress
            toward the access layer, blocking all paths from R1 to PC2.

            The topology is a triangular mesh (SW1-SW2-SW3 all interconnected),
            so faulting only the direct SW1-SW3 links (Gi0/3, Gi1/0) leaves an
            alternate path via SW1->SW2->SW3 that keeps the ping alive.
            All four switch-facing ports must be faulted to eliminate the bypass.

Fault Type: Trunk Allowed VLAN Restriction

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-00-vlans-and-trunking.unl"
DEVICE_NAME = "SW1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/1",
    "switchport trunk allowed vlan 10,30,99",
    "interface GigabitEthernet0/2",
    "switchport trunk allowed vlan 10,30,99",
    "interface GigabitEthernet0/3",
    "switchport trunk allowed vlan 10,30,99",
    "interface GigabitEthernet1/0",
    "switchport trunk allowed vlan 10,30,99",
]
# Sanity check: target must currently have VLAN 20 in the allowed list
# (otherwise we're breaking already-broken config)
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/1"
PREFLIGHT_MUST_CONTAIN = "allowed vlan"
PREFLIGHT_MUST_INCLUDE_VLAN = "20"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_MUST_CONTAIN not in output:
        print("[!] Pre-flight failed: Gi0/1 has no trunk 'allowed vlan' line.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    # Look at the line containing allowed vlan
    for line in output.splitlines():
        if PREFLIGHT_MUST_CONTAIN in line and PREFLIGHT_MUST_INCLUDE_VLAN in line:
            return True
    print("[!] Pre-flight failed: VLAN 20 not in Gi0/1 allowed list -- already injected?")
    return False


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
