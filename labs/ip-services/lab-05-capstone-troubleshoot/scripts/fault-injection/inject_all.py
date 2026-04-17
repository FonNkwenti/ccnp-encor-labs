#!/usr/bin/env python3
"""
Fault Injection: ALL SCENARIOS -- IP Services Capstone II

Applies all 6 concurrent faults to R1, R2, R3 in a single run. This resets
the lab to the pre-broken state equivalent to setup_lab.py initial-configs.

Use this after apply_solution.py to re-start the capstone troubleshooting
challenge from the beginning.

Faults applied:
  R1: NAT inside/outside reversed
  R1: NAT-PAT ACL wrong subnet
  R1: VRRP track decrement 5
  R2: NTP key-string mismatch
  R2: VRRPv3 IPv6 AF missing
  R3: OSPF passive on Gi0/0

Usage:
    python3 inject_all.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[3] / "common" / "tools"))
from eve_ng import EveNgError, connect_node, discover_ports, require_host  # noqa: E402

DEFAULT_LAB_PATH = "ip-services/lab-05-capstone-troubleshoot.unl"

FAULTS: dict[str, list[str]] = {
    "R1": [
        # Fault 1: NAT reversed
        "interface GigabitEthernet0/0",
        " no ip nat inside",
        " ip nat outside",
        "interface GigabitEthernet0/1",
        " no ip nat outside",
        " ip nat inside",
        # Fault 2: PAT ACL wrong subnet
        "ip access-list standard NAT-PAT",
        " no permit 192.168.1.0 0.0.0.255",
        " permit 10.0.13.0 0.0.0.255",
        # Fault 3: VRRP decrement too small
        "interface GigabitEthernet0/0",
        " vrrp 1 address-family ipv4",
        "  no track 1 decrement 20",
        "  track 1 decrement 5",
    ],
    "R2": [
        # Fault 4: NTP key mismatch
        "no ntp authentication-key 1 md5 NTP_KEY_1",
        "ntp authentication-key 1 md5 NTP_KEY_WRONG",
        # Fault 5: VRRPv3 IPv6 AF missing
        "interface GigabitEthernet0/0",
        " no vrrp 1 address-family ipv6",
    ],
    "R3": [
        # Fault 6: OSPF passive on Gi0/0
        "router ospf 1",
        " passive-interface GigabitEthernet0/0",
        "ipv6 router ospf 1",
        " passive-interface GigabitEthernet0/0",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject all 6 faults for Capstone II")
    parser.add_argument("--host", default="192.168.1.214")
    parser.add_argument("--lab-path", default=DEFAULT_LAB_PATH)
    args = parser.parse_args()
    host = require_host(args.host)

    print("=" * 60)
    print("Fault Injection: ALL SCENARIOS (Capstone II — 6 faults)")
    print("=" * 60)

    try:
        ports = discover_ports(host, args.lab_path)
    except EveNgError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 3

    fail = 0
    for device, commands in FAULTS.items():
        port = ports.get(device)
        if port is None:
            print(f"[!] {device}: not found in lab.")
            fail += 1
            continue
        print(f"\n[*] {device}: injecting faults on {host}:{port} ...")
        try:
            conn = connect_node(host, port)
            conn.send_config_set(commands)
            conn.save_config()
            conn.disconnect()
            print(f"[+] {device}: faults applied.")
        except Exception as exc:
            print(f"[!] {device}: failed -- {exc}")
            fail += 1

    print("\n" + "=" * 60)
    if fail:
        print(f"[!] {fail} device(s) failed.")
        return 1
    print("[+] All 6 faults injected. Lab is now in pre-broken state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
