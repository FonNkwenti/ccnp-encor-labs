#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Passive Interface on Transit Link

Target:     R3 (router ospf 1)
Injects:    'passive-interface GigabitEthernet0/1' on R3. Gi0/1 is the
            transit link to R5 (10.2.35.0/30).
Fault Type: OSPF Interface Configuration Error

Result:     R3 stops sending Hellos on Gi0/1, so the R3<->R5 adjacency
            never forms. R5 becomes isolated from the Area 0 backbone
            and PC2 (192.168.2.0/24) is unreachable from PC1.

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
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "router ospf 1",
    "passive-interface GigabitEthernet0/1",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
# Fault marker: if already present, the fault is already injected -- bail out
PREFLIGHT_FAULT_MARKER = "passive-interface GigabitEthernet0/1"
# Solution marker: confirms OSPF still advertises the transit link
PREFLIGHT_SOLUTION_MARKER = "network 10.2.35.0 0.0.0.3 area 0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R3 OSPF does not advertise '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 03 appears to be already injected. Restore with apply_solution.py.")
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
    print("Fault Injection: Scenario 03 (Passive Interface on Transit)")
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
