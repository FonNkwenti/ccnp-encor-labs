#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- R1 NAT-PAT ACL matches wrong subnet

Target:     R1
Injects:    Replaces NAT-PAT ACL permit statement with 10.0.13.0/24 instead
            of 192.168.1.0/24. PAT overload rule no longer matches LAN traffic.
Symptom:    PC1 static NAT still works (static entries bypass ACL matching).
            PC2 and other LAN hosts cannot reach internet via PAT. Dynamic
            translations not created for 192.168.1.x hosts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "ip access-list standard NAT-PAT",
    " no permit 192.168.1.0 0.0.0.255",
    " permit 10.0.13.0 0.0.0.255",
]
PREFLIGHT_CMD = "show ip access-lists NAT-PAT"
PREFLIGHT_SOLUTION_MARKER = "192.168.1.0"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_SOLUTION_MARKER not in output:
        print("[!] Pre-flight failed: NAT-PAT ACL does not permit 192.168.1.0.")
        print("    Run apply_solution.py first.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 (R1 NAT-PAT ACL wrong subnet)")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    host = require_host(args.host)
    print("=" * 60)
    print("Fault Injection: Scenario 02 (R1 NAT-PAT ACL wrong subnet)")
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
    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
