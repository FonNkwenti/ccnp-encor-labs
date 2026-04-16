#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Wrong Network Type on Area 0 Segment (R1)

Target:     R1 (interface Gi0/0 -- the Area 0 shared broadcast segment)
Injects:    Adds `ip ospf network point-to-point` to R1 Gi0/0. R2 and R3
            still run the default broadcast network type on the same
            segment.
Fault Type: OSPF Network-Type Mismatch on Shared Segment

Result:     R1 stops sending Hellos to the all-OSPF multicast in a way
            that R2/R3 can elect a DR with. R1 may still form a unicast
            adjacency with one of the two (the first it hears), but the
            second peer disappears from `show ip ospf neighbor` on R1.
            R2 and R3 continue to see each other normally and keep
            electing a DR among themselves.

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


DEFAULT_LAB_PATH = "ospf/lab-02-network-types.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "ip ospf network point-to-point",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Solution marker: R1 Gi0/0 carries priority 255 (proves it's in solution state)
PREFLIGHT_SOLUTION_MARKER = "ip ospf priority 255"
# Fault marker: point-to-point network type already set -> fault already injected
PREFLIGHT_FAULT_MARKER = "ip ospf network point-to-point"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R1 Gi0/0 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 03 appears to be already injected.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (R1 Gi0/0 wrong network type)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (Wrong Network Type on R1 Gi0/0)")
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
