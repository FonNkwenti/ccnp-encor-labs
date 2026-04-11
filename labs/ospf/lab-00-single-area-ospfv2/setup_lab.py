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
    def __init__(self, devices, eve_ng_host, use_ssh=False):
        self.devices = devices        # List of (name, port, config_path)
        self.eve_ng_host = eve_ng_host
        self.use_ssh = use_ssh

    def push_config(self, host, port, config_file):
        device_type = "cisco_ios" if self.use_ssh else "cisco_ios_telnet"
        print(f"Connecting to {host}:{port} ({device_type})...")
        try:
            if not os.path.exists(config_file):
                print(f"  Error: Config file {config_file} not found.")
                return False

            conn_params = {
                "device_type": device_type,
                "host": host,
                "port": port,
                "timeout": 10,
            }
            if not self.use_ssh:
                # Telnet to EVE-NG console — credentials typically empty
                conn_params.update({"username": "", "password": "", "secret": ""})

            conn = ConnectHandler(**conn_params)

            # Read config lines, skipping blanks and comments
            with open(config_file, 'r') as f:
                commands = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith('!')
                ]

            # Push configuration commands
            conn.send_config_set(commands)

            # Save configuration
            conn.send_command("write memory", read_timeout=10)
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    devices = [
        ("R1", 32768, os.path.join(script_dir, "initial-configs", "R1.cfg")),
        ("R2", 32769, os.path.join(script_dir, "initial-configs", "R2.cfg")),
        ("R3", 32770, os.path.join(script_dir, "initial-configs", "R3.cfg")),
        ("R4", 32771, os.path.join(script_dir, "initial-configs", "R4.cfg")),
        ("R5", 32772, os.path.join(script_dir, "initial-configs", "R5.cfg")),
    ]
    lab = LabSetup(devices, eve_ng_host=args.host, use_ssh=args.ssh)
    lab.run()
