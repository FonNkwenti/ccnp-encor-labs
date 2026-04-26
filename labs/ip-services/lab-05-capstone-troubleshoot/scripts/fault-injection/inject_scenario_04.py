#!/usr/bin/env python3
"""
Fault Injection: Scenario 04 -- R2 NTP authentication key-string mismatch

Target:     R2
Injects:    Changes NTP authentication key 1 from NTP_KEY_1 to NTP_KEY_WRONG.
            R2 sends NTP requests to R1 with a key that R1 does not recognise.
            R1 rejects the association.
Symptom:    'show ntp associations' on R2 shows no synced peer (no * marker).
            'show ntp status' shows 'Clock is unsynchronized'. Stratum remains
            at 16 (unsynchronized).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "no ntp authentication-key 1 md5 NTP_KEY_1",
    "ntp authentication-key 1 md5 NTP_KEY_WRONG",
]
PREFLIGHT_CMD = "show ntp status"
PREFLIGHT_SOLUTION_MARKER = "synchronized"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R2 NTP is not synchronized.")
        print("    Run apply_solution.py first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 04 (R2 NTP key mismatch)")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
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
        print(f"[!] {DEVICE_NAME} not found.")
        return 3
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}", file=sys.stderr)
        return 3
    try:
        if not args.skip_preflight and not preflight(conn):
            return 4
        conn.send_config_set(FAULT_COMMANDS)
        conn.save_config()
    finally:
        conn.disconnect()
    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 04 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
