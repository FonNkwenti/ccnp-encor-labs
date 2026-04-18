#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- R4 and R6 Are Not OSPF Neighbors

Target:     R4 (Area 1 internal router)
Injects:    Adds passive-interface GigabitEthernet0/1 to router ospf 1
            and the OSPFv3 address-family. R4 stops sending OSPF hellos
            on the transit link to R6. R4-R6 adjacency drops.
Fault Type: Passive Interface on Transit Link

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


DEFAULT_LAB_PATH = "ospf/lab-06-capstone-troubleshoot.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router ospf 1",
    "passive-interface GigabitEthernet0/1",
    "exit",
    "router ospfv3 1",
    "address-family ipv6 unicast",
    "passive-interface GigabitEthernet0/1",
    "exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_SOLUTION_MARKER = "passive-interface GigabitEthernet0/2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if "passive-interface GigabitEthernet0/1" in output:
        print("[!] Pre-flight: R4 Gi0/1 already passive — fault may already be injected.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R4 OSPF config looks unexpected.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (passive-interface on R4 Gi0/1)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
