#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Area ID Mismatch on R4 Gi0/0

Target:     R4 (router ospf 1 -- network statement for 10.1.24.0/30)
Injects:    Replaces `network 10.1.24.0 0.0.0.3 area 1` with
            `network 10.1.24.0 0.0.0.3 area 0` on R4.
Fault Type: OSPF Area Mismatch

Result:     R2 (Gi0/1 in area 1) and R4 (Gi0/0 now in area 0) cannot
            form an OSPFv2 adjacency. `show ip ospf neighbor` on both
            sides bounces INIT/DOWN or is empty, and PC1's LAN is
            unreachable from Area 0.

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


DEFAULT_LAB_PATH = "ospf/lab-01-multi-area-ospfv2.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router ospf 1",
    "no network 10.1.24.0 0.0.0.3 area 1",
    "network 10.1.24.0 0.0.0.3 area 0",
]
PREFLIGHT_CMD = "show running-config | section router ospf 1"
# Solution marker: 10.1.24.0/30 correctly placed in area 1
PREFLIGHT_SOLUTION_MARKER = "network 10.1.24.0 0.0.0.3 area 1"
# Fault marker: area 0 variant already present -> fault already injected
PREFLIGHT_FAULT_MARKER = "network 10.1.24.0 0.0.0.3 area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R4 router ospf 1 missing "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 01 appears to be already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault (area ID mismatch)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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
