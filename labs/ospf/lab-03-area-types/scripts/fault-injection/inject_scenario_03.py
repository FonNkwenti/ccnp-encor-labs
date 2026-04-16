#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Duplicate OSPF Routes for Area 2 Transit Subnets

Target:     R5 (ASBR in Area 2 NSSA)
Injects:    Strips the route-map scope from the redistribution commands on
            R5 for both OSPFv2 and OSPFv3 -- changing `redistribute
            connected subnets route-map REDIST_EXT` to bare `redistribute
            connected subnets` (and likewise for OSPFv3).
Fault Type: Unscoped Redistribution (Missing Route-Map Filter)

Result:     All connected interfaces on R5 -- including the transit link
            to R3 (10.2.35.0/24) and the LAN segment (192.168.2.0/24) --
            are redistributed as Type 7 LSAs in addition to being
            advertised via the OSPF `network` statements. Duplicate routes
            appear in the LSDB; routers in Area 0 and Area 1 see both an
            intra-area and an external entry for the same subnets.

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
DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "router ospf 1",
    "no redistribute connected subnets route-map REDIST_EXT",
    "redistribute connected subnets",
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "no redistribute connected route-map REDIST_EXT_V6",
    "redistribute connected",
    "exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
# Solution marker: R5 must have the scoped redistribution with route-map
PREFLIGHT_SOLUTION_MARKER = "route-map REDIST_EXT"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R5 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (R5 unscoped redistribution)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (R5 Unscoped Redistribution)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
