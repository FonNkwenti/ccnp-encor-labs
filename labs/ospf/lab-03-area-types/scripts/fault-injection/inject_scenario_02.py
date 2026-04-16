#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- External ISP Routes Invisible Across the Network

Target:     R3 (ABR between Area 0 and Area 2)
Injects:    Removes `area 2 nssa` from both the OSPFv2 process and the
            OSPFv3 address-family on R3. R5 (ASBR) retains its NSSA
            configuration.
Fault Type: NSSA Area-Type Mismatch

Result:     With Area 2 no longer declared NSSA on the ABR, R3 stops
            translating Type 7 LSAs to Type 5 LSAs. The external routes
            redistributed by R5 (172.16.5.0/24, 172.16.6.0/24) become
            invisible in Area 0 and Area 1. Additionally, the area-type
            mismatch causes R3 and R5 to be unable to maintain adjacency.

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


DEFAULT_LAB_PATH = "ospf/lab-03-area-types.unl"
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router ospf 1",
    "no area 2 nssa",
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "no area 2 nssa",
    "exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
# Solution marker: R3 must have `area 2 nssa` configured
PREFLIGHT_SOLUTION_MARKER = "area 2 nssa"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R3 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R3 NSSA area-type mismatch)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (R3 NSSA Area-Type Mismatch)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
