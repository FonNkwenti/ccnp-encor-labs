#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- PC1 Cannot Reach PC2

Target:     R5 (Gi0/1, passive interface toward the PC2 LAN 192.168.2.0/24)
Injects:    Removes R5's OSPF network statement for the PC2 LAN so R5 stops
            advertising the 192.168.2.0/24 prefix into OSPF Area 0.
Fault Type: Missing OSPF Network Statement (Stub LAN)

Result:     All OSPF adjacencies remain FULL. Loopback reachability between
            all routers continues to work. However, 192.168.2.0/24 disappears
            from the LSDB and RIB of every router except R5 itself (which
            has the connected route). PC1 on 192.168.1.0/24 cannot reach
            PC2 on 192.168.2.0/24.

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
DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 192.168.2.0 0.0.0.255 area 0",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_EXPECT = "network 192.168.2.0 0.0.0.255 area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: R5 does not have '{PREFLIGHT_EXPECT}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (PC1 Cannot Reach PC2)")
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
