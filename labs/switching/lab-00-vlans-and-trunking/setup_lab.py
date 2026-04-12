#!/usr/bin/env python3
"""
Initial Lab Setup

Pushes each node's bare-minimum starting configuration from initial-configs/
via the EVE-NG console (telnet). Run this once after you build the topology
in EVE-NG and before you begin Section 4 of the workbook.

For troubleshooting scenarios, use scripts/fault-injection/apply_solution.py
instead — it pushes the full solution config.
"""

from netmiko import ConnectHandler
import argparse
import os
import sys

# EVE-NG server IP — override with --host argument
DEFAULT_EVE_NG_HOST = "192.168.x.x"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Push initial configs to EVE-NG lab nodes via console telnet"
    )
    parser.add_argument("--host", default=DEFAULT_EVE_NG_HOST,
                        help="EVE-NG server IP (default: %(default)s)")
    return parser.parse_args()


class LabSetup:
    def __init__(self, devices, eve_ng_host):
        self.devices = devices        # List of (name, port, config_path)
        self.eve_ng_host = eve_ng_host

    def push_config(self, host, port, config_file):
        print(f"Connecting to {host}:{port} (cisco_ios_telnet)...")
        try:
            if not os.path.exists(config_file):
                print(f"  Error: Config file {config_file} not found.")
                return False

            conn = ConnectHandler(
                device_type="cisco_ios_telnet",
                host=host,
                port=port,
                username="",
                password="",
                secret="",
                timeout=10,
            )

            # Read config lines, skipping blanks and comments
            with open(config_file, "r") as f:
                commands = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith("!")
                ]

            conn.send_config_set(commands)
            # save_config() handles the "Destination filename?" prompt correctly
            conn.save_config()
            print(f"  Successfully loaded {config_file}")

            conn.disconnect()
            return True
        except Exception as e:
            print(f"  Failed to connect or push config: {e}")
            return False

    def run(self):
        print(f"Starting Lab Setup Automation (EVE-NG host: {self.eve_ng_host})...")
        for name, port, config in self.devices:
            print(f"--- Setting up {name} ---")
            self.push_config(self.eve_ng_host, port, config)
        print("Lab Setup Complete.")


# --- Device Mapping ---
# Ports are dynamic EVE-NG console ports.
# Replace the port numbers below with actual values from your EVE-NG lab.
# Check: EVE-NG web UI or GET /api/labs/<lab>/nodes
if __name__ == "__main__":
    args = parse_args()
    if args.host == DEFAULT_EVE_NG_HOST:
        print(f"[!] --host not set (still '{DEFAULT_EVE_NG_HOST}'). "
              "Pass --host <eve-ng-ip>.", file=sys.stderr)
        sys.exit(2)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    devices = [
        ("SW1", 32768, os.path.join(script_dir, "initial-configs", "SW1.cfg")),
        ("SW2", 32769, os.path.join(script_dir, "initial-configs", "SW2.cfg")),
        ("SW3", 32770, os.path.join(script_dir, "initial-configs", "SW3.cfg")),
        ("R1",  32771, os.path.join(script_dir, "initial-configs", "R1.cfg")),
    ]
    lab = LabSetup(devices, eve_ng_host=args.host)
    lab.run()
