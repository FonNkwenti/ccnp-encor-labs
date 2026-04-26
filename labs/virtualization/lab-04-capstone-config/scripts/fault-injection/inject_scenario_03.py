#!/usr/bin/env python3
"""
Fault Injection: Scenario 03

Targets:    R1 and R4
Injects:    `tunnel protection ipsec profile IPSEC-PROFILE` removed from
            Tunnel0 on BOTH endpoints. Both routers revert to plain GRE;
            the GRE tunnel stays UP, OSPF process 2 adjacency stays FULL,
            and traffic to 10.4.4.4 continues to flow — but in cleartext.
Fault Type: IPsec Profile Removed Both Ends (Unencrypted GRE Tunnel)

Result:     Tunnel0 line protocol remains UP on both R1 and R4.
            `show interface Tunnel0` still shows `Tunnel protocol/transport GRE/IP`.
            `show ip ospf 2 neighbor` still shows the remote peer in FULL state.
            `show crypto ipsec sa` shows no protected interface or SA counters.
            `show crypto ikev2 sa` shows no established SA.
            Traffic to 10.4.4.4 succeeds but is not encrypted.

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


DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-04-capstone-config.unl"
FAULT_COMMANDS = [
    "interface Tunnel0",
    "no tunnel protection ipsec profile IPSEC-PROFILE",
]
PREFLIGHT_CMD = "show running-config interface Tunnel0"
PREFLIGHT_EXPECT = "tunnel protection ipsec profile IPSEC-PROFILE"
TARGETS = ["R1", "R4"]


def preflight(conn, name: str) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed on {name}: Tunnel0 does not have the expected IPsec protection.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def inject_device(host: str, name: str, port: int, skip_preflight: bool) -> bool:
    print(f"[*] Connecting to {name} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection failed on {name}: {exc}", file=sys.stderr)
        return False

    try:
        if not skip_preflight and not preflight(conn, name):
            return False
        print(f"[*] Injecting fault on {name} ...")
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
        print(f"[+] {name} done.")
        return True
    finally:
        conn.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that targets have expected config")
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

    fail = 0
    for name in TARGETS:
        port = ports.get(name)
        if port is None:
            print(f"[!] {name} not found in lab {args.lab_path}.")
            fail += 1
            continue
        if not inject_device(host, name, port, args.skip_preflight):
            fail += 1

    print("=" * 60)
    if fail == 0:
        print("[+] Fault injected on all targets. Scenario 03 is now active.")
    else:
        print(f"[!] Scenario 03 partially injected ({fail} target(s) failed).")
    print("=" * 60)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
