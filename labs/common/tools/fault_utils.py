from netmiko import ConnectHandler


class FaultInjector:
    def __init__(self, host="192.168.x.x"):
        """
        host: EVE-NG server IP. Override with the actual IP of your EVE-NG server.
        """
        self.host = host

    def _connect(self, port):
        """Create a Netmiko connection to an EVE-NG console port (telnet)."""
        device = {
            "device_type": "cisco_ios_telnet",
            "host": self.host,
            "port": port,
            "username": "",
            "password": "",
            "secret": "",
            "timeout": 10,
        }
        return ConnectHandler(**device)

    def execute_commands(self, port, commands, description="Injecting fault"):
        """
        Connects to an EVE-NG console port via Netmiko and executes IOS
        configuration commands.
        """
        try:
            conn = self._connect(port)
            output = conn.send_config_set(commands)
            conn.disconnect()
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False


if __name__ == "__main__":
    injector = FaultInjector()
    print("FaultInjector utility loaded.")
