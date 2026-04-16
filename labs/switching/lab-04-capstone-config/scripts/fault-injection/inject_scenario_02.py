#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- EtherChannel Protocol Mismatch on Po2

Target:     SW3 (Po2 members Gi0/3 and Gi1/0 -- SW3 side of SW1<->SW3 bundle)
Injects:    Change SW3 side from PAgP 'channel-group 2 mode auto' to
            LACP 'channel-group 2 mode passive'. SW1 is still PAgP
            'desirable', so the two ends now speak different
            aggregation protocols.
Fault Type: EtherChannel protocol/mode mismatch

Result:     - Po2 never bundles. `show etherchannel summary` on SW1
              reports Po2 as (SD) -- layer-2, down.
            - Member interfaces on SW3 show up as suspended or
              independent (I)/(s) because LACP never finishes.
            - PC2 loses its redundant path to R1; only Po3 remains.
            - Depending on STP state, VLAN 20 traffic via SW3 can fail
              (SW2's direct Po3 should still carry it but convergence
              may take seconds).

The fix (students figure out): put SW3 members back to PAgP auto so the
PAgP desirable+auto pair re-bundles.

Before running, ensure the lab is in the SOLUTION state:
    python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-04-capstone-config.unl"
DEVICE_NAME = "SW3"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/3",
    "no channel-group 2 mode auto",
    "channel-group 2 mode passive",
    "interface GigabitEthernet1/0",
    "no channel-group 2 mode auto",
    "channel-group 2 mode passive",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/3"
# Solution marker: Gi0/3 on SW3 is in channel-group 2 mode auto (PAgP auto)
PREFLIGHT_SOLUTION_MARKER = "channel-group 2 mode auto"
# Fault marker: if already present, the fault is already injected -- bail out
PREFLIGHT_FAULT_MARKER = "channel-group 2 mode passive"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW3 Gi0/3 does not have "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_FAULT_MARKER in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_FAULT_MARKER}' already present.")
        print("    Scenario 02 appears to be already injected. Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: 192.168.1.214)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (EtherChannel Protocol Mismatch on Po2)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
