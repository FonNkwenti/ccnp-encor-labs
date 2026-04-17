#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Passive-Interface on Transit Link (R1)

Target:     R1
Injects:    Adds 'passive-interface GigabitEthernet0/1' under router eigrp 100
            on R1. This blocks EIGRP hellos on R1's link toward R3,
            tearing down the R1-R3 adjacency. The R1-R2 adjacency stays
            up. Routes still reach R3 via R2 (triangle base), so
            connectivity is degraded but not lost -- a subtle fault.
Fault Type: Passive-interface on transit link

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


DEFAULT_LAB_PATH = "eigrp/lab-00-classic-eigrp.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router eigrp 100",
    "passive-interface GigabitEthernet0/1",
    "exit",
]
PREFLIGHT_CMD = "show running-config | section router eigrp"
PREFLIGHT_SOLUTION_MARKER = "network 10.13.0.0 0.0.0.3"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R1 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if "passive-interface GigabitEthernet0/1" in output:
        print("[!] Pre-flight failed: R1 already has passive-interface on Gi0/1.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (passive-interface on R1 transit link)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (passive-interface on R1 transit link)")
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
