#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- R4 Cannot Reach R1 Loopback

Target:     R2 (shared Ethernet segment Gi0/0, member of 10.0.123.0/24 segment)
Injects:    Removes R2's OSPF network statement for the shared segment so R2
            no longer advertises or forms adjacencies via that interface.
Fault Type: Missing OSPF Network Statement (Shared Segment)

Result:     R2 loses its adjacency with R1 on the 10.0.123.0/24 segment.
            R4 can still reach R2's loopback (2.2.2.2) via the R2<->R4 P2P
            link but cannot reach R1's loopback (1.1.1.1) because R1's LSA
            is no longer reachable from R4's OSPF topology.

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


DEFAULT_LAB_PATH = "ospf/lab-00-single-area-ospfv2.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 10.0.123.0 0.0.0.255 area 0",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_EXPECT = "network 10.0.123.0 0.0.0.255 area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: R2 does not have '{PREFLIGHT_EXPECT}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
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
    print("Fault Injection: Scenario 01 (R4 Cannot Reach R1 Loopback)")
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
