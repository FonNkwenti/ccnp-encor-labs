#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Network-Type Mismatch on Area 1 Transit

Target:     R4 (interface Gi0/0 -- the Area 1 transit to R2)
Injects:    Removes `ip ospf network point-to-point` from R4 Gi0/0, which
            reverts the interface to the Ethernet default (broadcast).
            R2 Gi0/1 stays configured as point-to-point.
Fault Type: OSPF Network-Type Mismatch

Result:     `show ip ospf neighbor` on both sides may still report the
            adjacency as FULL (p2p end doesn't require a DR; broadcast end
            runs a one-router election), but the LSDB is inconsistent --
            R4 advertises the transit as a stub/transit (Type 2 LSA on its
            side), while R2 describes it as a point-to-point link in its
            Type 1 LSA. SPF alternates results, Area 1 routes flap on R1.

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


DEFAULT_LAB_PATH = "ospf/lab-02-network-types.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "no ip ospf network point-to-point",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Solution marker: R4 Gi0/0 explicitly set to point-to-point
PREFLIGHT_SOLUTION_MARKER = "ip ospf network point-to-point"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R4 Gi0/0 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    The interface is already not in the expected solution state.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (R4 Gi0/0 network-type mismatch)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 (Network-Type Mismatch on R4 Gi0/0)")
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
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
