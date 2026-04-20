#!/usr/bin/env python3
"""
Fault Injection: Scenario 02

Target:     R2
Injects:    Removes the local authentication requirement from the HTTP
            server so that RESTCONF requests return 401 Unauthorized
            instead of processing normally.
Fault Type: HTTP authentication misconfiguration

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys

from netmiko import ConnectHandler

DEVICE_NAME  = "R2"
EVE_NG_HOST  = "192.168.x.x"  # EVE-NG server IP -- update to match your environment
CONSOLE_PORT = None            # Dynamic port from EVE-NG web UI / Console Access Table

FAULT_COMMANDS = [
    "no ip http authentication local",
]

PREFLIGHT_CMD    = "show running-config | include ip http authentication"
PREFLIGHT_EXPECT = "ip http authentication local"


def _require_port(port) -> int:
    if port is None:
        print(
            "[!] CONSOLE_PORT is not set.\n"
            "    Open the EVE-NG web UI, start the lab, and note the telnet port\n"
            "    assigned to R2.  Then update CONSOLE_PORT in this script.",
            file=sys.stderr,
        )
        sys.exit(2)
    return int(port)


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_EXPECT}' not found in running-config.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 02 fault")
    parser.add_argument("--host", default=EVE_NG_HOST,
                        help="EVE-NG server IP (required)")
    parser.add_argument("--port", type=int, default=CONSOLE_PORT,
                        help="Console telnet port for R2 (from EVE-NG UI)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = args.host
    port = _require_port(args.port)

    print("=" * 60)
    print("Fault Injection: Scenario 02")
    print("=" * 60)

    print(f"[*] Connecting to {DEVICE_NAME} on {host}:{port} ...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios_telnet",
            host=host,
            port=port,
            username="",
            password="",
            secret="",
            timeout=10,
        )
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

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 02 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
