#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Hello/Dead Timer Mismatch

Target:     R4 (Gi0/0 -- link to R2)
Injects:    'ip ospf hello-interval 15' on R4 Gi0/0. Dead interval
            auto-scales to 60, while R2 Gi0/1 stays at the default 10/40.
Fault Type: OSPF Timer Mismatch

Result:     R4 and R2 drop the adjacency on the 10.1.24.0/30 link; R4
            shows zero OSPF neighbors and no OSPF routes learned from the
            Area 0 backbone.

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
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "ip ospf hello-interval 15",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Fault marker: if already present, the fault is already injected -- bail out
PREFLIGHT_FAULT_MARKER = "ip ospf hello-interval 15"
# Solution marker: confirms the interface is in the expected state
PREFLIGHT_SOLUTION_MARKER = "ip address 10.1.24.2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: Gi0/0 does not have '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 01 appears to be already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01 (Hello Timer Mismatch)")
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
