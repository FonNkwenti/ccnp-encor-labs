#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- VRRPv3 IPv6 address-family missing on R2

Target:     R2
Injects:    Removes the 'vrrp 1 address-family ipv6' block from R2 Gi0/0.
            The IPv6 VRRP group no longer has a backup router. If R1 fails,
            IPv6 hosts lose their gateway with no failover.
Symptom:    'show vrrp' on R2 shows only the IPv4 address-family for group 1.
            IPv6 address-family is absent. PC1/PC2 IPv6 traffic has no redundancy.
            Failover test: shutting R1 Gi0/0 leaves IPv6 hosts with no gateway.
Teaches:    VRRPv3 requires separate address-family configuration for IPv4 and
            IPv6 even when using the same group number. Omitting one AF silently
            breaks redundancy for that protocol family.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-03-vrrp-dual-stack.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no vrrp 1 address-family ipv6",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "address-family ipv6"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R2 Gi0/0 does not have VRRPv3 IPv6 address-family.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R2 VRRPv3 IPv6 AF removed)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (R2 VRRPv3 IPv6 address-family removed)")
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
