#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- SW2 Drops VLAN 30 from MST Instance 2

Target:     SW2
Injects:    Inside `spanning-tree mst configuration`, replaces
            `instance 2 vlan 20, 30` with `instance 2 vlan 20`, so VLAN
            30 falls back to MST 0 (IST) on SW2 only.
Fault Type: MST region VLAN-to-instance mapping mismatch

Result:     SW1 and SW3 keep VLAN 30 mapped to MST Instance 2; SW2 now
            maps VLAN 30 to MST 0 (IST). The MST configuration digest
            on SW2 no longer matches SW1/SW3, creating a subtle
            region-identity mismatch -- VLAN 30 forwarding across SW2's
            boundary ports follows the IST path, not MST 2.

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-03-mst.unl"
DEVICE_NAME = "SW2"
FAULT_COMMANDS = [
    "spanning-tree mst configuration",
    "no instance 2 vlan 20, 30",
    "instance 2 vlan 20",
    "exit",
]
PREFLIGHT_CMD = "show spanning-tree mst configuration"
# Solution marker: VLAN 30 is currently mapped to Instance 2 on SW2
# `show spanning-tree mst configuration` prints the mapping on the line for
# instance 2 -- e.g. "2        20,30" or "2        20, 30".
PREFLIGHT_SOLUTION_MARKER = "30"
PREFLIGHT_INSTANCE_MARKER = "2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    # Look for a line beginning with instance "2" that also contains VLAN 30
    found = False
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] != PREFLIGHT_INSTANCE_MARKER:
            continue
        # must be the "2 ..." instance line, not "20..." etc.
        tokens = stripped.split(None, 1)
        if tokens and tokens[0] == PREFLIGHT_INSTANCE_MARKER and PREFLIGHT_SOLUTION_MARKER in stripped:
            found = True
            break
    if not found:
        print("[!] Pre-flight failed: SW2 does not currently map VLAN 30 to MST Instance 2.")
        print("    Run apply_solution.py first to restore the known-good config.")
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
    print("Fault Injection: Scenario 03 (SW2 Drops VLAN 30 from MST Instance 2)")
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
