#!/usr/bin/env python3
"""
Fault Injection: Scenario 01

Target:     R1
Injects:    IKEv2 keyring peer pre-shared-key replaced with an incorrect value.
            Both IPsec tunnels (Tunnel1 and Tunnel2) fail to establish because
            IKEv2 AUTH_FAILED is returned during Phase 1 negotiation.
Fault Type: IKEv2 Authentication Failure

Result:     Tunnel1 and Tunnel2 line protocol goes DOWN on R1 (and stays down).
            `show crypto ikev2 sa` shows no SA or shows DELETE/AUTH_FAILED.
            Tunnel0 (plain GRE, no IPsec) is unaffected and stays UP.
            Pings to 10.4.4.5 and 10.4.4.6 from R1 fail; 10.4.4.4 still works.

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
    "crypto ikev2 keyring IKEv2-KEYRING",
    "peer R4",
    "pre-shared-key WRONG-PSK-9999",
]
PREFLIGHT_CMD = "show running-config | section ikev2 keyring"
PREFLIGHT_EXPECT = "LAB-PSK-2026"


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print("[!] Pre-flight failed: IKEv2 keyring does not contain the expected PSK.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 01 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
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
        conn.send_config_set(FAULT_COMMANDS, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print("[+] Fault injected. Scenario 01 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
