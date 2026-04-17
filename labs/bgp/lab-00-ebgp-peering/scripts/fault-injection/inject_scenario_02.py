#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- R3 BGP Process AS Number Mismatch

Target:     R3
Injects:    Removes `router bgp 65002` and re-creates it as `router bgp 65099`
            with the same neighbor/network config.
            R1 expects remote-as 65002; the OPEN message R3 sends now
            advertises AS 65099. R1 rejects the OPEN and resets the session.
            Session flaps in/out of OpenSent.
Teaches:    OpenSent-stuck = AS mismatch or router-ID collision. TCP is
            fine (past Active); the content of the OPEN is wrong.

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


DEFAULT_LAB_PATH = "bgp/lab-00-ebgp-peering.unl"
DEVICE_NAME = "R3"
FAULT_COMMANDS = [
    "no router bgp 65002",
    "router bgp 65099",
    " bgp router-id 3.3.3.3",
    " bgp log-neighbor-changes",
    " neighbor 10.0.13.1 remote-as 65001",
    " neighbor 10.0.13.1 description eBGP_TO_R1_AS65001",
    " address-family ipv4",
    "  network 172.16.3.0 mask 255.255.255.0",
    "  neighbor 10.0.13.1 activate",
    " exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router bgp"
PREFLIGHT_SOLUTION_MARKER = "router bgp 65002"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R3 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (AS mismatch on R3)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (AS mismatch on R3)")
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
