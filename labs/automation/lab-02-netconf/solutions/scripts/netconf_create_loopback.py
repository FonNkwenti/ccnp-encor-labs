#!/usr/bin/env python3
"""
Solution: Task 5 — Create Loopback200 via NETCONF edit-config.

Sends an edit-config RPC targeting the running datastore to create
Loopback200 (10.200.200.1/32) using the ietf-interfaces YANG model.
"""

from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError

ROUTER_IP = "10.1.12.1"
NETCONF_PORT = 830
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

CONFIG_XML = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback200</name>
      <description>Created via NETCONF</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
        ianaift:softwareLoopback
      </type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>10.200.200.1</ip>
          <prefix-length>32</prefix-length>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""


def create_loopback():
    print(f"[*] Connecting to {ROUTER_IP}:{NETCONF_PORT}...")
    try:
        with manager.connect(
            host=ROUTER_IP,
            port=NETCONF_PORT,
            username=USERNAME,
            password=PASSWORD,
            hostkey_verify=False,
            device_params={"name": "csr"},
            timeout=30,
        ) as m:
            print("[+] Connected. Sending edit-config RPC (target=running)...")
            reply = m.edit_config(target="running", config=CONFIG_XML)

            if reply.ok:
                print("[+] edit-config succeeded — Loopback200 created.")
                print("    Verify on router: show interfaces Loopback200")
            else:
                print(f"[!] edit-config returned errors: {reply.error}")

    except AuthenticationError:
        print("[!] Authentication failed — check username/password")
    except SSHError as e:
        print(f"[!] SSH/NETCONF connection error: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")


if __name__ == "__main__":
    create_loopback()
