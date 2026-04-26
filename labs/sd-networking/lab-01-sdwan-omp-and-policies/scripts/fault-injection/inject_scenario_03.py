#!/usr/bin/env python3
"""
Fault Injection Script: Scenario 03

Injects:     apply-policy targets SITE1 instead of SITE2 on vSmart
Target:      vSmart (Viptela OS 20.6.2)
Fault Type:  Control Policy Applied to Wrong Site

This script connects to vSmart via EVE-NG console telnet and changes the
apply-policy block so that PREFER-SITE1-PATH is applied to site-list SITE1
instead of SITE2. The policy will affect vEdge1 (Site 1) instead of vEdge2
(Site 2), causing vEdge2's OMP table to show 192.168.1.0/24 with the default
preference 100 rather than the elevated preference 200.

Note: Run apply_solution.py to restore the correct state before each run.
Note: This fault is best-effort idempotent. Re-running when SITE1 is already
      targeted will produce a harmless 'no site-list SITE2' error (no-op).

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
# Change apply-policy from SITE2 to SITE1 (wrong site target)
FAULT_COMMANDS = [
    "apply-policy",
    "no site-list SITE2",
    "site-list SITE1",
    "control-policy PREFER-SITE1-PATH out",
    "commit",
]


def inject_fault(host: str, port: int) -> int:
    """Connect to vSmart and redirect the control policy to the wrong site."""
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
