#!/usr/bin/env python3
"""
Fault Injection Script: Scenario 02

Injects:     Organisation name mismatch on vEdge1 (ENCOR-LABS instead of ENCOR-LAB)
Target:      vEdge1 (Viptela OS 20.6.2)
Fault Type:  Organisation Name Mismatch

This script connects to vEdge1 via EVE-NG console telnet and changes the
organization-name in the system configuration from 'ENCOR-LAB' to 'ENCOR-LABS'
(extra trailing 'S'). The organisation name is case-sensitive and must match
exactly on all fabric components. vEdge1 will fail OMP peer authentication with
vSmart, leaving 'show omp peers' on vSmart empty.

Note: Run apply_solution.py to restore the correct state before each run.

Usage:
    python3 inject_scenario_02.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys

from netmiko import ConnectHandler

# Device Configuration
DEVICE_NAME = "vEdge1"
EVE_NG_HOST = "192.168.x.x"   # EVE-NG server IP — update to match your environment
CONSOLE_PORT = 0               # Dynamic port from EVE-NG web UI / Console Access Table

# Viptela OS fault commands — commit is the final step (no write memory)
FAULT_COMMANDS = [
    "system",
    "organization-name ENCOR-LABS",
    "commit",
]


def inject_fault(host: str, port: int) -> int:
    """Connect to vEdge1 and inject the wrong organisation name."""
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
    print("[!] Scenario 02 is now active.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
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
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    return inject_fault(args.host, args.port)


if __name__ == "__main__":
    sys.exit(main())
