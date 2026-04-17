#!/usr/bin/env python3
"""
Fault Injection: Scenario 05 -- Inter-Area Summary Route Missing from Area 0

Target:     R2 (ABR Area 0/1)
Injects:    Replaces `area 1 range 10.1.4.0 255.255.252.0` with
            `area 0 range 10.1.4.0 255.255.252.0` (wrong area number).
            Area 0 has no 10.1.4.x prefixes to summarize, so no aggregate
            is generated and the individual /24 Type 3 LSAs flood into Area 0.
Fault Type: Wrong Area Number in ABR area range Command

Before running, ensure the lab is in the solution state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ospf/lab-05-capstone-config.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "router ospf 1",
    "no area 1 range 10.1.4.0 255.255.252.0",
    "area 0 range 10.1.4.0 255.255.252.0",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_SOLUTION_MARKER = "area 1 range 10.1.4.0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R2 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 05 (wrong area number in area range on R2)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 05 (Wrong Area in area range on R2)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 05 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
