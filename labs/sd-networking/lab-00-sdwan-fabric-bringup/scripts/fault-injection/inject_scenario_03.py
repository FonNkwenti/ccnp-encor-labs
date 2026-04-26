#!/usr/bin/env python3
"""
Fault Injection Script: Scenario 03

Injects:     Default route removed from VPN 0 on vSmart (172.16.0.254 gateway deleted)
Target:      vSmart (Viptela OS 20.6.2)
Fault Type:  Missing VPN 0 Default Route

This script connects to vSmart via EVE-NG console telnet and removes the
default route (0.0.0.0/0 via 172.16.0.254) from VPN 0. Without this route
vSmart loses reachability to vBond and all vEdges, causing the vBond control
connection to drop and all OMP peer sessions to go down.

Idempotency note: If the default route is already absent (e.g. inject run twice),
Viptela will return an error message but no route will be affected. This is
expected and benign — the fault state (route absent) is already present.

Note: Run apply_solution.py to restore the correct state before each run.

Usage:
    python3 inject_scenario_03.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys

from netmiko import ConnectHandler

# Device Configuration
DEVICE_NAME = "vSmart"
EVE_NG_HOST = "192.168.x.x"   # EVE-NG server IP — update to match your environment
CONSOLE_PORT = 0               # Dynamic port from EVE-NG web UI / Console Access Table

# Viptela OS fault commands — commit is the final step (no write memory)
# If the route is already absent the 'no ip route' line will produce a benign
# error from Viptela; commit still succeeds and the device state remains correct.
FAULT_COMMANDS = [
    "vpn 0",
    "no ip route 0.0.0.0/0 172.16.0.254",
    "commit",
]


def inject_fault(host: str, port: int) -> int:
    """Connect to vSmart and remove the VPN 0 default route."""
    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="admin",
            password="admin",
            secret="",
            timeout=15,
        )
    except ConnectionRefusedError:
        print(f"[!] Error: Could not connect to {host}:{port}")
        print(f"[!] Make sure the EVE-NG lab is running and {DEVICE_NAME} is started.")
        return 1
    except Exception as exc:
        print(f"[!] Connection failed: {exc}")
        return 1

    print(f"[+] Connected to {DEVICE_NAME}.")
    print("[*] Injecting fault configuration ...")
    try:
        conn.send_config_set(
            FAULT_COMMANDS,
            config_mode_command="config",
            cmd_verify=False,
            exit_config_mode=False,
        )
    except Exception as exc:
        print(f"[!] Fault injection failed: {exc}")
        return 1
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}.")
    print("[!] Scenario 03 is now active.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument(
        "--host",
        default=EVE_NG_HOST,
        help="EVE-NG server IP (required)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=CONSOLE_PORT,
        help=f"Console port for {DEVICE_NAME} (default: {CONSOLE_PORT})",
    )
    args = parser.parse_args()

    if args.host in {"192.168.x.x", "", None}:
        print("[!] --host is not set. Pass --host <eve-ng-ip>.", file=sys.stderr)
        return 2

    print("=" * 60)
    print("Fault Injection: Scenario 03")
    print("=" * 60)

    return inject_fault(args.host, args.port)


if __name__ == "__main__":
    sys.exit(main())
