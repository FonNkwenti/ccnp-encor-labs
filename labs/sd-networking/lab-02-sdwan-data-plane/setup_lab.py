from netmiko import ConnectHandler
import sys
import argparse
import os

# EVE-NG server IP — override with --host argument or set here
DEFAULT_EVE_NG_HOST = "192.168.x.x"

def parse_args():
    parser = argparse.ArgumentParser(description="Push initial configs to EVE-NG lab nodes")
    parser.add_argument("--host", default=DEFAULT_EVE_NG_HOST,
                        help="EVE-NG server IP (default: %(default)s)")
    parser.add_argument("--ssh", action="store_true",
                        help="Use SSH instead of telnet (requires management network on nodes)")
    return parser.parse_args()


class LabSetup:
    def __init__(self, ios_devices, eve_ng_host, use_ssh=False):
        self.ios_devices = ios_devices
        self.eve_ng_host = eve_ng_host
        self.use_ssh = use_ssh

    def push_ios_config(self, name, port, config_file):
        device_type = "cisco_ios" if self.use_ssh else "cisco_ios_telnet"
        print(f"Connecting to {name} ({self.eve_ng_host}:{port}, {device_type})...")
        try:
            if not os.path.exists(config_file):
                print(f"  Error: Config file {config_file} not found.")
                return False

            conn_params = {
                "device_type": device_type,
                "host": self.eve_ng_host,
                "port": port,
                "timeout": 15,
            }
            if not self.use_ssh:
                conn_params.update({"username": "", "password": "", "secret": ""})

            conn = ConnectHandler(**conn_params)

            with open(config_file, 'r') as f:
                commands = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith('!')
                ]

            conn.send_config_set(commands)
            conn.send_command("write memory", read_timeout=10)
            print(f"  Successfully loaded {config_file}")
            conn.disconnect()
            return True
        except Exception as e:
            print(f"  Failed: {e}")
            return False

    def print_viptela_instructions(self):
        print()
        print("=" * 60)
        print("Viptela SD-WAN Devices — Manual Configuration Required")
        print("=" * 60)
        print()
        print("initial-configs/ for this lab is the complete lab-01 solutions state.")
        print("Apply each Viptela config via console to reset to the known-good fabric.")
        print()
        print("  1. Open each device console via EVE-NG web UI")
        print("  2. Enter config mode: config")
        print("  3. Paste the contents of initial-configs/<Device>.cfg")
        print("  4. Commit: commit")
        print()
        viptela_cfgs = [
            ("vManage",  "initial-configs/vManage.cfg"),
            ("vSmart",   "initial-configs/vSmart.cfg"),
            ("vBond",    "initial-configs/vBond.cfg"),
            ("vEdge1",   "initial-configs/vEdge1.cfg"),
            ("vEdge2",   "initial-configs/vEdge2.cfg"),
        ]
        for name, cfg in viptela_cfgs:
            status = "Found" if os.path.exists(cfg) else "MISSING"
            print(f"  {name:12s} <- {cfg}  [{status}]")
        print()

    def run(self):
        print(f"SD-WAN Lab 02 — Setup Automation (EVE-NG: {self.eve_ng_host})")
        print()

        print("--- IOS Device Configuration ---")
        for name, port, config in self.ios_devices:
            print(f"Setting up {name}...")
            self.push_ios_config(name, port, config)

        self.print_viptela_instructions()

        print("Lab Setup Complete.")
        print("After applying Viptela initial-configs, proceed to workbook.md Task 1.")


if __name__ == "__main__":
    args = parse_args()

    # Populate console port from EVE-NG web UI (Console Access Table in workbook.md Section 3)
    ios_devices = [
        ("R-TRANSPORT", 0, "initial-configs/R-TRANSPORT.cfg"),  # replace 0 with actual EVE-NG port
    ]

    lab = LabSetup(
        ios_devices=ios_devices,
        eve_ng_host=args.host,
        use_ssh=args.ssh,
    )
    lab.run()
