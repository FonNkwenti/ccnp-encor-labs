#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Distribute-List Has No Effect on R1

Target:     R1 (Backbone Router Area 0)
Injects:    Replaces the correct distribute-list reference
            (`distribute-list prefix BLOCK_10_1_5 in`) with one that
            references a non-existent prefix-list name
            (`distribute-list prefix BLOCK_10_1_5_TYPO in`).
            The prefix-list BLOCK_10_1_5 still exists but the
            distribute-list now points to the wrong name.
Fault Type: Distribute-List — Prefix-List Name Mismatch (Typo)

Result:     R1's OSPF distribute-list has no effect because it
            references a prefix-list that does not exist. Routes
            including 10.1.5.0/24 (via the /22 summary or as a
            specific /24 if summarization is also removed) are
            installed in R1's routing table normally.

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
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "router ospf 1",
    "no distribute-list prefix BLOCK_10_1_5 in",
    "distribute-list prefix BLOCK_10_1_5_TYPO in",
]
PREFLIGHT_CMD = "show running-config | section router ospf"
PREFLIGHT_SOLUTION_MARKER = "distribute-list prefix BLOCK_10_1_5 in"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R1 missing '{PREFLIGHT_SOLUTION_MARKER}' in ospf config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (distribute-list name typo on R1)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (Distribute-List Name Typo on R1)")
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
