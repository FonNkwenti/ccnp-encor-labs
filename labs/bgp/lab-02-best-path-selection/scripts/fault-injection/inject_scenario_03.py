#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- R4 Missing network 192.168.2.0 Statement

Target:     R4
Injects:    'no network 192.168.2.0' under router bgp 65003 IPv4 AF.
Symptom:    R4's BGP session to R3 is Established. R4 still advertises
            172.16.4.0/24, so 'show bgp ipv4 unicast' on R1 does show
            R4's Loopback1 prefix. But 192.168.2.0/24 is silently missing.
            PC1 can ping 172.16.4.1 but NOT 192.168.2.10.
Teaches:    BGP 'network' statements are the most common reason an
            expected prefix is missing. They are silent -- no error when
            omitted, no log when the prefix fails to appear. Always check
            'show running-config | section router bgp' for the expected
            network statement when a prefix is missing end-to-end.

Before running, ensure the lab is in the solution state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "bgp/lab-02-best-path-selection.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router bgp 65003",
    " address-family ipv4",
    "  no network 192.168.2.0",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "network 192.168.2.0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R4 BGP does not have 'network 192.168.2.0'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (R4 missing network 192.168.2.0)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (R4 missing network 192.168.2.0)")
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
