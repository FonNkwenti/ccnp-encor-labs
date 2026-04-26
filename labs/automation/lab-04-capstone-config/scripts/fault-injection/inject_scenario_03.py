#!/usr/bin/env python3
"""
Fault Injection: Scenario 03

Target:     R3
Injects:    Replaces the EEM applet's syslog event pattern with one
            that will never match real OSPF syslog messages, so the
            applet never fires.
Fault Type: EEM syslog pattern mismatch

Two-phase injection: the existing applet is removed first, then a new
applet using the broken pattern is installed.  This ensures idempotency
-- running the script a second time produces identical end-state.

Before running, ensure the lab is in the SOLUTION state:
    python3 apply_solution.py --host <eve-ng-ip>
"""

from __future__ import annotations

import argparse
import sys

from netmiko import ConnectHandler

DEVICE_NAME  = "R3"
EVE_NG_HOST  = "192.168.x.x"  # EVE-NG server IP -- update to match your environment
CONSOLE_PORT = None            # Dynamic port from EVE-NG web UI / Console Access Table

# Phase 1: remove the existing applet
FAULT_COMMANDS_REMOVE = [
    "no event manager applet SYSLOG-MONITOR",
]

# Phase 2: install applet with broken pattern
FAULT_COMMANDS_ADD = [
    "event manager applet SYSLOG-MONITOR",
    ' event syslog pattern "OSPF-NONEXISTENT-PATTERN"',
    ' action 1.0 syslog msg "EEM: OSPF adjacency change detected"',
    ' action 2.0 cli command "enable"',
    ' action 3.0 cli command "show ip ospf neighbor"',
]

PREFLIGHT_CMD    = "show running-config | section event manager applet SYSLOG-MONITOR"
PREFLIGHT_EXPECT = "OSPF-5-ADJCHG"


def _require_port(port) -> int:
    if port is None:
        print(
            "[!] CONSOLE_PORT is not set.\n"
            "    Open the EVE-NG web UI, start the lab, and note the telnet port\n"
            "    assigned to R3.  Then update CONSOLE_PORT in this script.",
            file=sys.stderr,
        )
        sys.exit(2)
    return int(port)


def preflight(conn) -> bool:
    output = conn.send_command(PREFLIGHT_CMD)
    if PREFLIGHT_EXPECT not in output:
        print(f"[!] Pre-flight failed: '{PREFLIGHT_EXPECT}' not found in SYSLOG-MONITOR applet.")
        print("    Run apply_solution.py first to restore the known-good config.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Scenario 03 fault")
    parser.add_argument("--host", default=EVE_NG_HOST,
                        help="EVE-NG server IP (required)")
    parser.add_argument("--port", type=int, default=CONSOLE_PORT,
                        help="Console telnet port for R3 (from EVE-NG UI)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip the sanity check that target has expected config")
    args = parser.parse_args()

    host = args.host
    port = _require_port(args.port)

    print("=" * 60)
    print("Fault Injection: Scenario 03")
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
        print("[*] Phase 1: removing existing applet ...")
        conn.send_config_set(FAULT_COMMANDS_REMOVE, cmd_verify=False)
        print("[*] Phase 2: installing fault applet ...")
        conn.send_config_set(FAULT_COMMANDS_ADD, cmd_verify=False)
        conn.save_config()
    finally:
        conn.disconnect()

    print(f"[+] Fault injected on {DEVICE_NAME}. Scenario 03 is now active.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
