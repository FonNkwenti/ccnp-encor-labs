#!/usr/bin/env python3
"""
Fault Injection: Scenario 06 -- PC1 Access Port in Wrong VLAN

Target:     SW2 Gi1/1 (PC1's access port)
Injects:    'switchport access vlan 30' on PC1's port. The port
            otherwise stays up and in access mode -- it simply
            forwards PC1's frames onto VLAN 30 (Management-Hosts)
            instead of VLAN 10 (Sales).
Fault Type: Access-VLAN misassignment

Result:     - `show vlan brief` on SW2 shows Gi1/1 under VLAN 30,
              not VLAN 10.
            - PC1 cannot reach 192.168.10.1 (its gateway on VLAN 10).
            - PortFast + BPDU guard stay configured on the port;
              the port stays 'connected'.
            - No syslog warning -- purely a silent misassignment.

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


DEFAULT_LAB_PATH = "ccnp-encor/switching/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "SW2"
FAULT_COMMANDS = [
    "interface GigabitEthernet1/1",
    "switchport access vlan 30",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet1/1"
PREFLIGHT_SOLUTION_MARKER = "ACCESS_PC1_VLAN10"
PREFLIGHT_VLAN10_MARKER = "switchport access vlan 10"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Gi1/1 is missing description "
              f"'{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_VLAN10_MARKER not in output:
        print(f"[!] Pre-flight failed: SW2 Gi1/1 is missing '{PREFLIGHT_VLAN10_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 06 fault")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: 192.168.242.128)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 06 (Access-VLAN Misassignment on SW2 Gi1/1)")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 06 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
