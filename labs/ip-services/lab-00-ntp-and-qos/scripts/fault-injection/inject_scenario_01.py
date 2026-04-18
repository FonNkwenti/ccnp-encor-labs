#!/usr/bin/env python3
"""
Fault Injection: Scenario 01 -- NTP authentication key mismatch on R2

Target:     R2
Injects:    Replaces the shared MD5 key 'NTP_KEY_1' with 'WRONG_KEY' on R2.
Symptom:    R2's association to 1.1.1.1 never gets a '*' marker. stratum stays
            at 16 ('clock not set'). 'show ntp associations detail' reports
            'unauthenticated'.
Teaches:    Both peers must carry identical authentication-key strings. A
            mismatch silently prevents synchronization -- the association is
            sane and valid, but unauthenticated.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-00-ntp-and-qos.unl"
DEVICE_NAME = "R2"
FAULT_COMMANDS = [
    "no ntp authentication-key 1 md5 NTP_KEY_1",
    "ntp authentication-key 1 md5 WRONG_KEY",
]
PREFLIGHT_CMD = "show running-config | include ntp authentication-key"
PREFLIGHT_SOLUTION_MARKER = "NTP_KEY_1"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: R2 does not have NTP key 'NTP_KEY_1'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 (NTP auth key mismatch on R2)")
    parser.add_argument("--host", default="192.168.1.214",
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
