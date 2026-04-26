#!/usr/bin/env python3
"""
Fault Injection: Scenario 05 -- Wrong Subnet Suppressed by not-advertise

Target:     R2 (ABR Area 0/1)
Injects:    Removes `area 1 range 10.1.6.0 255.255.255.0 not-advertise`
            (the correct suppression) and adds
            `area 1 range 10.1.4.0 255.255.255.0 not-advertise` instead.
            Now 10.1.4.0/24 is suppressed from Area 0 (wrong subnet),
            while 10.1.6.0/24 is no longer suppressed (incorrectly reachable).
Fault Type: area range not-advertise Applied to Wrong Prefix

Result:     R3 cannot reach 10.1.4.0/24 (absorbed by not-advertise on the
            wrong prefix, breaking part of the /22 summary coverage).
            10.1.6.0/24 becomes reachable from Area 0 routers when it
            should be suppressed.

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
    "router ospf 1",
    "no area 1 range 10.1.6.0 255.255.255.0 not-advertise",
    "area 1 range 10.1.4.0 255.255.255.0 not-advertise",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_SOLUTION_MARKER = "area 1 range 10.1.6.0 255.255.255.0 not-advertise"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R2 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 05 (wrong not-advertise prefix on R2)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 05")
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
