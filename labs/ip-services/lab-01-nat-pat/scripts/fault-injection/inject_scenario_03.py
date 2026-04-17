#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Static NAT maps PC1 to wrong public IP

Target:     R1
Injects:    Removes the correct static NAT entry (192.168.1.10 -> 10.0.13.10)
            and replaces it with a mapping to 10.0.13.99 (an address not
            reachable from 203.0.113.1 via routing).
Symptom:    PC1 can still reach 203.0.113.1 via PAT overload (fallback), but
            the expected fixed public address 10.0.13.10 is not in the
            translation table. 'show ip nat translations' reveals 10.0.13.99
            in the static entry instead of the expected 10.0.13.10.
Teaches:    Read 'show ip nat translations' carefully. A static entry with the
            wrong inside-global IP is syntactically valid and causes no error --
            the only way to detect it is to verify the translation table against
            the intended address design.
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
    "no ip nat inside source static 192.168.1.10 10.0.13.10",
    "ip nat inside source static 192.168.1.10 10.0.13.99",
]
PREFLIGHT_CMD = "show ip nat translations"
PREFLIGHT_SOLUTION_MARKER = "10.0.13.10"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: static NAT entry for 10.0.13.10 not found.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (static NAT wrong public IP)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03 (R1 static NAT wrong outside IP)")
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
