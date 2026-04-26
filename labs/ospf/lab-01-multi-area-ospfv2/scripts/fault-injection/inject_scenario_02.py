#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- OSPFv3 Missing on R5 Gi0/0

Target:     R5 (interface GigabitEthernet0/0 -- transit to R3, Area 2)
Injects:    Removes `ospfv3 1 ipv6 area 2` from R5 Gi0/0.
Fault Type: OSPFv3 Interface Not Enabled

Result:     OSPFv3 adjacency between R3 and R5 is never formed on the
            Gi0/0 <-> Gi0/1 link. OSPFv2 (IPv4) still converges, so
            `ping 192.168.2.10` from PC1 succeeds, but
            `ping 2001:db8:2:2::10` from PC1 fails -- the IPv6 route for
            2001:DB8:2:2::/64 never reaches R1.

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
DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    "no ospfv3 1 ipv6 area 2",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
# Solution marker: OSPFv3 must currently be enabled on the interface
PREFLIGHT_SOLUTION_MARKER = "ospfv3 1 ipv6 area 2"
# Sanity marker: confirms we are looking at the right interface
PREFLIGHT_INTERFACE_MARKER = "ip address 10.2.35.2"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_INTERFACE_MARKER not in output:
        print(f"[!] Pre-flight failed: R5 Gi0/0 does not have "
              f"'{PREFLIGHT_INTERFACE_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_SOLUTION_MARKER}' absent on R5 Gi0/0.")
        print("    Scenario 02 appears to be already injected, or OSPFv3 was never enabled.")
        print("    Restore with apply_solution.py.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault (OSPFv3 missing on R5 Gi0/0)")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
