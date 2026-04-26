#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- NAT inside/outside interfaces reversed on R1

Target:     R1
Injects:    Moves 'ip nat inside' to GigabitEthernet0/1 (uplink) and 'ip nat
            outside' to GigabitEthernet0/0 (LAN). This is the reverse of the
            correct orientation.
Symptom:    PC1 and PC2 can no longer reach 203.0.113.1. 'show ip nat
            translations' shows no dynamic translations. Static NAT entry for
            PC1 is present but traffic is blackholed. 'debug ip nat' shows
            no translation attempts.
Teaches:    NAT requires inside/outside designation on the correct interfaces.
            IOS translates packets arriving on 'inside' interfaces destined
            for 'outside'. Reversing the labels means no traffic matches the
            NAT policy. Always verify with 'show ip interface GigabitEthernetX'
            and look for 'NAT: inside' or 'NAT: outside'.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ip-services/lab-04-capstone-config.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface GigabitEthernet0/0",
    " no ip nat inside",
    " ip nat outside",
    "interface GigabitEthernet0/1",
    " no ip nat outside",
    " ip nat inside",
]
PREFLIGHT_CMD = "show running-config interface GigabitEthernet0/0"
PREFLIGHT_SOLUTION_MARKER = "ip nat inside"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: R1 Gi0/0 does not have 'ip nat inside'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R1 NAT inside/outside reversed)")
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
