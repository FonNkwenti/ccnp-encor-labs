#!/usr/bin/env python3
"""
Fault Injection: Scenario 03 -- Rogue policer on class-default

Target:     R1
Injects:    Adds 'police cir 8000' under 'class class-default' in policy-map
            LAN-OUT, rate-limiting every unclassified packet to 8 kbps.
Symptom:    PC1 cannot reach 203.0.113.1 (pings time out). 'show policy-map
            interface Gi0/1' shows enormous drop counters in class-default.
Teaches:    Read 'show policy-map interface' counters first. If drops appear
            under class-default, inspect the policy-map stanza for unexpected
            actions on the catch-all class.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-00-ntp-and-qos.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "policy-map LAN-OUT",
    " class class-default",
    "  police cir 8000",
]
PREFLIGHT_CMD = "show running-config | section policy-map LAN-OUT"
PREFLIGHT_SOLUTION_MARKER = "fair-queue"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print(f"[!] Pre-flight failed: policy-map LAN-OUT class-default missing 'fair-queue'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 (rogue class-default policer)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
