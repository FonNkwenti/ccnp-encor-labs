#!/usr/bin/env python3
"""
Fault Injection: Scenario 02

Target:     R1
Injects:    Tunnel2 mode changed from GRE over IPsec to a raw IPsec VTI:
              - `tunnel mode gre ip` removed
              - `tunnel protection ipsec profile IPSEC-PROFILE` removed
              - `tunnel mode ipsec ipv4` applied
            IPsec VTI does not forward multicast; OSPF hellos
            (224.0.0.5/224.0.0.6) are silently dropped on Tunnel2.
Fault Type: Tunnel Mode Misconfiguration (multicast-incapable mode)

Result:     Tunnel2 line protocol shows UP (IPsec SA can still form).
            `show interface Tunnel2` shows "Tunnel protocol/transport IPSEC/IP"
            instead of "GRE/IP".
            `show ip ospf neighbor` on R1 never shows R4 on Tunnel2.
            OSPF process 3 has no neighbors; 10.4.4.6/32 is absent from the
            routing table. Tunnel1 (pure IPsec VTI) and Tunnel0 (GRE) are
            unaffected.

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


DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-03-ipsec-and-gre-over-ipsec.unl"
DEVICE_NAME = "R1"
FAULT_COMMANDS = [
    "interface Tunnel2",
    "no tunnel mode gre ip",
    "no tunnel protection ipsec profile IPSEC-PROFILE",
    "tunnel mode ipsec ipv4",
]
PREFLIGHT_CMD = "show running-config interface Tunnel2"
PREFLIGHT_EXPECT = "tunnel mode gre ip"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print("[!] Pre-flight failed: Tunnel2 does not have the expected tunnel mode.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print("[+] Fault injected. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
