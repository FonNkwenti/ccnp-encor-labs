import os

from netmiko import ConnectHandler


class LabSetup:
    def __init__(self, devices, eve_ng_host="192.168.x.x"):
        self.devices = devices          # List of (name, port, config_path)
        self.eve_ng_host = eve_ng_host  # EVE-NG server IP

    def _connect(self, host, port):
        """Create a Netmiko connection to an EVE-NG console port."""
        device = {
            "device_type": "cisco_ios_telnet",
            "host": host,
            "port": port,
            "username": "",
            "password": "",
            "secret": "",
            "timeout": 10,
        }
        return ConnectHandler(**device)

    def push_config(self, host, port, config_file):
        print(f"Connecting to {host}:{port}...")
        try:
            if not os.path.exists(config_file):
                print(f"  Error: Config file {config_file} not found.")
                return False

            commands = []
            with open(config_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('!'):
                        commands.append(line.strip())

            conn = self._connect(host, port)
            conn.send_config_set(commands)
            conn.send_command("write memory", read_timeout=10)
            print(f"  Successfully loaded {config_file}")
            conn.disconnect()
            return True
        except Exception as e:
            print(f"  Failed to connect or push config: {e}")
            return False

    def run(self):
        print(f"Starting Lab Setup Automation (EVE-NG: {self.eve_ng_host})...")
        for name, port, config in self.devices:
            print(f"--- Setting up {name} ---")
            self.push_config(self.eve_ng_host, port, config)


class LabRefresher:
    def __init__(self, devices, eve_ng_host="192.168.x.x"):
        self.devices = devices          # List of (name, port, config_path)
        self.eve_ng_host = eve_ng_host  # EVE-NG server IP

    def _connect(self, host, port):
        """Create a Netmiko connection to an EVE-NG console port."""
        device = {
            "device_type": "cisco_ios_telnet",
            "host": host,
            "port": port,
            "username": "",
            "password": "",
            "secret": "",
            "timeout": 10,
        }
        return ConnectHandler(**device)

    def _parse_cleanup_commands(self, config_file):
        """Parse config to find interfaces and routing protocols to reset."""
        interfaces = []
        routers = []
        with open(config_file, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('interface '):
                    interfaces.append(stripped.split(' ', 1)[1])
                elif stripped.startswith('router '):
                    routers.append(stripped)
        cleanup = []
        for iface in interfaces:
            cleanup.append(f"default interface {iface}")
        for router in routers:
            cleanup.append(f"no {router}")
        return cleanup

    def push_config(self, host, port, config_file):
        print(f"Refreshing {host}:{port} with {config_file}...")
        try:
            conn = self._connect(host, port)

            # Default all interfaces and remove routing protocols
            cleanup = self._parse_cleanup_commands(config_file)
            if cleanup:
                conn.send_config_set(cleanup)

            # Push initial config
            commands = []
            with open(config_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('!'):
                        commands.append(line.strip())

            conn.send_config_set(commands)
            conn.send_command("write memory", read_timeout=10)
            print(f"  Successfully refreshed.")
            conn.disconnect()
            return True
        except Exception as e:
            print(f"  Failed: {e}")
            return False

    def run(self):
        for name, port, config_path in self.devices:
            self.push_config(self.eve_ng_host, port, config_path)
