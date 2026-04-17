#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- External Routes Not Fully Summarized on R5

Target:     R5 (ASBR Area 2)
Injects:    Replaces `summary-address 172.16.0.0 255.255.0.0` (/16)
            with `summary-address 172.16.5.0 255.255.255.0` (/24 — too narrow).
            The /24 summary only covers 172.16.5.0/24, leaving 172.16.6.0/24
            as an unsummarized individual Type 7 LSA.
Fault Type: ASBR Summarization — Wrong Mask (Summary Too Narrow)

Result:     R1 sees two O E2 external entries (172.16.5.0/24 and
            172.16.6.0/24) instead of the single 172.16.0.0/16 aggregate.
            `show ip ospf database external` shows two Type 5 LSAs.

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


DEFAULT_LAB_PATH = "ospf/lab-04-summarization-filtering.unl"
DEVICE_NAME = "R5"
FAULT_COMMANDS = [
    "router ospf 1",
    "no summary-address 172.16.0.0 255.255.0.0",
    "summary-address 172.16.5.0 255.255.255.0",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_SOLUTION_MARKER = "summary-address 172.16.0.0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R5 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (ASBR summary wrong mask on R5)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (ASBR Summary Wrong Mask on R5)")
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
