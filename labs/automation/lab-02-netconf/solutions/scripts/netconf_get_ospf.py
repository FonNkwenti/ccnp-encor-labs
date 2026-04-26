#!/usr/bin/env python3
"""
Solution: Task 6 — Retrieve OSPF Operational Data via NETCONF get.

Sends a get RPC (operational data, not config) targeting the
Cisco-IOS-XE-ospf-oper YANG model to list OSPF neighbors on R1.

IMPORTANT: The exact YANG path varies by IOS-XE release.
This script uses the path validated for CSR1000v 17.03.05.
Before running on a different version, retrieve the current schema:

    python3 netconf_get_schema.py  (see solutions/scripts/)

The OSPF oper path on 17.03.05:
  Module: Cisco-IOS-XE-ospf-oper
  Namespace: http://cisco.com/ns/yang/Cisco-IOS-XE-ospf-oper
  Root container: ospf-oper-data
"""

from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
import xml.etree.ElementTree as ET

ROUTER_IP = "10.1.12.1"
NETCONF_PORT = 830
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

OSPF_OPER_NS = "http://cisco.com/ns/yang/Cisco-IOS-XE-ospf-oper"

# Subtree filter — retrieves all OSPF neighbor entries under all instances/areas/interfaces
OSPF_FILTER = """
<filter type="subtree">
  <ospf-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf-oper">
    <ospf-state>
      <ospf-instance>
        <ospf-area>
          <ospf-interface>
            <ospf-neighbor/>
          </ospf-interface>
        </ospf-area>
      </ospf-instance>
    </ospf-state>
  </ospf-oper-data>
</filter>
"""


def get_ospf_neighbors():
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
            print("[+] Connected. Sending get RPC for OSPF operational data...")
            reply = m.get(filter=OSPF_FILTER)

            root = ET.fromstring(reply.xml)
            ns = {"ospf": OSPF_OPER_NS}

            neighbors = root.findall(".//ospf:ospf-neighbor", ns)
            if not neighbors:
                print("[!] No OSPF neighbors found in response.")
                print("    Check that OSPF is running and the YANG path matches your IOS-XE version.")
                return

            print(f"\n{'Neighbor ID':<18} {'Interface':<20} {'State':<15} {'Dead Timer'}")
            print("-" * 65)
            for nbr in neighbors:
                nbr_id = nbr.findtext("ospf:nbr-rid", "N/A", ns)
                state = nbr.findtext("ospf:nbr-state", "N/A", ns)
                dead = nbr.findtext("ospf:dead-timer", "N/A", ns)
                iface = nbr.findtext("ospf:interface-name", "N/A", ns)
                print(f"{nbr_id:<18} {iface:<20} {state:<15} {dead}")

    except AuthenticationError:
        print("[!] Authentication failed")
    except SSHError as e:
        print(f"[!] NETCONF connection error: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")


if __name__ == "__main__":
    get_ospf_neighbors()
