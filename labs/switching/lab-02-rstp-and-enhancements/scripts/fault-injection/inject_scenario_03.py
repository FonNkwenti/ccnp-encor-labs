#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Suboptimal VLAN 20 Path (Port Cost Override)

Target:     SW2 (Port-channel3 -- direct link to SW3)
Injects:    'spanning-tree vlan 20 cost 200000000' on SW2 Po3.
Fault Type: STP port-cost manipulation

Result:     SW3's VLAN 20 root port moves from Po3 (direct to SW2, the
            VLAN 20 root) to Po2 (through SW1), because the artificially
            high cost on Po3 makes the Po2->SW1->Po1 path appear cheaper.
            VLAN 20 traffic now hairpins through SW1 instead of taking
            the direct SW2<->SW3 bundle.

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


DEFAULT_LAB_PATH = "switching/lab-02-rstp-and-enhancements.unl"
DEVICE_NAME = "SW2"
FAULT_COMMANDS = [
    "interface Port-channel3",
    "spanning-tree vlan 20 cost 200000000",
]
PREFLIGHT_CMD = "show running-config interface Port-channel3"
# Solution marker: Po3 exists with the expected description
PREFLIGHT_SOLUTION_MARKER = "STATIC_PO3_TO_SW3"
# Fault marker: if already present, the fault is already injected -- bail out
PREFLIGHT_FAULT_MARKER = "spanning-tree vlan 20 cost"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Po3 does not have expected description "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present on Po3.")
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
    print("Fault Injection: Scenario 03 (Suboptimal VLAN 20 Path)")
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
