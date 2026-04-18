#!/usr/bin/env python3
"""
Fault Injection: Scenario 04 -- IPv6 Inter-Area Summary Absent from Area 0

Target:     R2 (ABR Area 0/1)
Injects:    Removes the OSPFv3 address-family `area 1 range 2001:DB8:1:4::/62`
            command from R2. The IPv4 summarization (area 1 range 10.1.4.0/22)
            remains intact and is unaffected.
Fault Type: Missing OSPFv3 AF Inter-Area Summarization

Result:     R1 shows four individual OI /64 IPv6 entries for
            2001:db8:1:4::/64 through 2001:db8:1:7::/64 instead of
            the single 2001:db8:1:4::/62 aggregate. IPv4 summarization
            continues to work correctly.

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


DEFAULT_LAB_PATH = "ospf/lab-04-summarization-filtering.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "no area 1 range 2001:DB8:1:4::/62",
    "exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router ospfv3"
PREFLIGHT_SOLUTION_MARKER = "area 1 range 2001:DB8:1:4::/62"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R2 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospfv3 config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 04 (missing OSPFv3 IPv6 area range on R2)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 04")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 04 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
