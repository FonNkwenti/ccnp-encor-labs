#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Interface tracking decrement too small

Target:     R1
Injects:    Changes the track object decrement from 20 to 5. When R1's
            Gi0/1 (uplink to R3) goes down, R1's HSRP priority drops
            from 110 to 105 -- which is still above R2's 100. R1
            remains HSRP Active even though it has no working uplink.
Symptom:    After shutting down R1's Gi0/1, R1 stays HSRP Active.
            PCs can ARP to 192.168.1.1 but cannot reach 203.0.113.1
            because R1 has no path to R3. 'show standby' on R1 shows
            Active state with tracked object down but priority only
            dropped to 105.
Teaches:    The tracking decrement must exceed the difference between
            R1's priority (110) and R2's priority (100). A decrement
            of 5 is insufficient -- at least 11 is needed to trigger
            failover, and 20 is the recommended value for a clean margin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-02-hsrp.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no standby 1 track 1 decrement 20",
    " standby 1 track 1 decrement 5",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "standby 1 track 1 decrement 20"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R1 Gi0/0 does not have 'standby 1 track 1 decrement 20'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (R1 tracking decrement too small)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (R1 track decrement 20 -> 5)")
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
