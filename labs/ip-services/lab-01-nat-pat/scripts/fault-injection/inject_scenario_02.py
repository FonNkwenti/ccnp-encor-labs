#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- PAT ACL matches wrong source network

Target:     R1
Injects:    Replaces the NAT-PAT access-list so it permits 10.0.13.0/24
            (the outside subnet) instead of 192.168.1.0/24 (the LAN subnet).
Symptom:    PC2 cannot reach 203.0.113.1 via PAT. 'show ip nat translations'
            shows no dynamic entries for 192.168.1.x. 'show access-lists'
            reveals zero match hits on NAT-PAT for LAN traffic.
Teaches:    The ACL used in 'ip nat inside source list' must match the
            INSIDE LOCAL address range. A mismatch silently prevents
            translation without generating any error messages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-01-nat-pat.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "no ip access-list standard NAT-PAT",
    "ip access-list standard NAT-PAT",
    " permit 10.0.13.0 0.0.0.255",
]
PREFLIGHT_CMD = "show access-lists NAT-PAT"
PREFLIGHT_SOLUTION_MARKER = "192.168.1.0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: NAT-PAT ACL does not permit 192.168.1.0.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (PAT ACL wrong network)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
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
