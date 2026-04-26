#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- Stub Designation Missing on R4

Target:     R4
Injects:    Removes `eigrp stub connected` from R4's IPv4 and IPv6 AFs.
            R4 still forms neighbors and exchanges routes normally, but
            it no longer advertises the stub TLV -- so R2 (and all other
            neighbors) will send EIGRP queries through R4 during
            convergence, risking SIA events on a production network.
Teaches:    Stub is a per-AF feature and must be applied in BOTH IPv4 and
            IPv6 AFs. Removing it does not break adjacencies, which makes
            the fault silent until you check `show ip eigrp neighbors detail`.

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


DEFAULT_LAB_PATH = "eigrp/lab-02-stub-summarization-variance.unl"
DEVICE_NAME = "R4"
FAULT_COMMANDS = [
    "router eigrp EIGRP-LAB",
    " address-family ipv4 unicast autonomous-system 100",
    "  no eigrp stub connected",
    " exit-address-family",
    " address-family ipv6 unicast autonomous-system 100",
    "  no eigrp stub connected",
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
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (stub missing on R4)")
    parser.add_argument("--host", default="192.168.242.128",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 01")
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
