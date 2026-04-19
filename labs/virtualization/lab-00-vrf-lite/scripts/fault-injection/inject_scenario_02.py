#!/usr/bin/env python3
"""
Fault Injection: Scenario 02 -- Missing VRF Routes on R1 and R2

Targets:    R1 and R2
Injects:    VRF CUSTOMER-A static routes removed from R1 (to R2's LAN)
            and from R2 (to R1's LAN) — each site loses the remote LAN
            prefix from its VRF routing table.
Fault Type: VRF Static Route Removal (both endpoints)

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# labs/virtualization/lab-00-vrf-lite/scripts/fault-injection/ -> parents[3] = labs/
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402


DEFAULT_LAB_PATH = "ccnp-encor/virtualization/lab-00-vrf-lite.unl"

# (device_name, fault_commands, preflight_cmd, preflight_expect)
TARGETS = [
    (
        "R1",
        ["no ip route vrf CUSTOMER-A 192.168.2.0 255.255.255.0 172.16.13.2"],
        "show running-config | include ip route vrf CUSTOMER-A 192.168.2.0",
        "ip route vrf CUSTOMER-A 192.168.2.0",
    ),
    (
        "R2",
        ["no ip route vrf CUSTOMER-A 192.168.1.0 255.255.255.0 172.16.23.2"],
        "show running-config | include ip route vrf CUSTOMER-A 192.168.1.0",
        "ip route vrf CUSTOMER-A 192.168.1.0",
    ),
]


def preflight(conn, device_name: str, cmd: str, expect: str) -> bool:
    output = conn.send_command(cmd)
    if expect not in output:
        print(f"[!] Pre-flight failed: {device_name} does not have '{expect}'.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def inject_device(
    host: str,
    device_name: str,
    port: int,
    fault_commands: list,
    preflight_cmd: str,
    preflight_expect: str,
    skip_preflight: bool,
) -> bool:
    """Connect to one device, run preflight, inject fault. Returns True on success."""
    print(f"\n[*] Connecting to {device_name} on {host}:{port} ...")
    try:
        conn = connect_node(host, port)
    except Exception as exc:
        print(f"[!] Connection to {device_name} failed: {exc}", file=sys.stderr)
        return False

    try:
        if not skip_preflight and not preflight(conn, device_name, preflight_cmd, preflight_expect):
            return False
        print(f"[*] Injecting fault configuration on {device_name} ...")
        conn.send_config_set(fault_commands, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {device_name}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default="192.168.x.x",
                        help="EVE-NG server IP (required)")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH,
                        help=f"Lab .unl path (default: {DEFAULT_LAB_PATH})")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that targets have expected config")
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

    ok = fail = 0
    for device_name, fault_commands, preflight_cmd, preflight_expect in TARGETS:
        port = ports.get(device_name)
        if port is None:
            print(f"\n[!] {device_name} not found in lab {args.lab_path} -- skipping.")
            fail += 1
            continue
        if inject_device(host, device_name, port, fault_commands,
                         preflight_cmd, preflight_expect, args.skip_preflight):
            ok += 1
        else:
            fail += 1

    print("\n" + "=" * 60)
    print(f"Injection Complete: {ok} succeeded, {fail} failed")
    print("=" * 60)

    if fail > 0:
        print("[!] Some devices could not be faulted. Verify EVE-NG lab is running.")
        return 1

    print("[+] Scenario 02 is now active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
