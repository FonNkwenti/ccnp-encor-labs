#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- HSRP preemption disabled on R1

Target:     R1
Injects:    Removes 'standby 1 preempt' from R1's Gi0/0. After R1
            experiences a brief failure and recovers, it cannot reclaim
            the Active role even though its priority (110) is higher
            than R2's (100).
Symptom:    After simulating R1's failure (shutdown/no shutdown Gi0/0 or
            rebooting R1), R2 remains HSRP Active indefinitely. R1 shows
            Standby state. 'show standby' on R1 shows no 'preempt' flag.
Teaches:    Preemption must be configured explicitly on the higher-priority
            router for automatic failback to work. Without it, the router
            that won the election first keeps Active state permanently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-02-hsrp.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no standby 1 preempt",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "standby 1 preempt"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R1 Gi0/0 does not have 'standby 1 preempt'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R1 HSRP preempt removed)")
    parser.add_argument("--host", default="192.168.1.214",
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: Scenario 02 (R1 HSRP preempt disabled)")
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
