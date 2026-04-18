#!/usr/bin/env python3
"""
Fault Injection: Scenario 04 -- R4 Stub set to Receive-Only (IPv4)

Target:     R4
Injects:    Replaces `eigrp stub connected` with `eigrp stub receive-only`
            under R4's IPv4 AF.
            R4 keeps a healthy adjacency with R2 but advertises NOTHING --
            not its loopback, not PC2 LAN. Hub routers see the neighbor
            but receive no routes from it.
            IPv6 AF still runs `eigrp stub connected`, so IPv6 prefixes
            from R4 continue to flow.
Teaches:    `receive-only` is the "accept but don't advertise" stub type.
            Symptom: neighbor up, no routes learned. Must be replaced
            with `connected` (or combined with summary/static/redistributed).

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


DEFAULT_LAB_PATH = "eigrp/lab-04-capstone-troubleshoot.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router eigrp EIGRP-LAB",
    " address-family ipv4 unicast autonomous-system 100",
    "  no eigrp stub connected",
    "  eigrp stub receive-only",
    " exit-address-family",
]
PREFLIGHT_CMD = "show running-config | section router eigrp"
PREFLIGHT_SOLUTION_MARKER = "eigrp stub connected"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R4 missing '{PREFLIGHT_SOLUTION_MARKER}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 04 (R4 stub receive-only IPv4)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 04")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 04 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
