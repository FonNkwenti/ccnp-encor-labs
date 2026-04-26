#!/usr/bin/env python3
"""
capstone_netconf.py — Lab 04 Automation Capstone: NETCONF Tasks

Demonstrates NETCONF operations against R1 using ncclient:
  1. Connect to R1 on port 830 and display server capabilities
  2. Retrieve the running datastore (get-config)
  3. Create Loopback99 via edit-config on the candidate datastore
  4. Commit the candidate to running
  5. Lock/unlock the running datastore

Usage:
    pip install ncclient
    python3 capstone_netconf.py --host <R1-mgmt-ip>
"""

import argparse
import sys

try:
    from ncclient import manager
    from ncclient.xml_ import to_ele
except ImportError:
    print("[!] ncclient not installed. Run: pip install ncclient")
    sys.exit(1)

R1_HOST = "10.1.12.1"
NETCONF_PORT = 830
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

LOOPBACK99_CONFIG = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback99</name>
      <description>NETCONF-created capstone interface</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>99.99.99.99</ip>
          <prefix-length>32</prefix-length>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""


def connect(host, port, username, password):
    return manager.connect(
        host=host,
        port=port,
        username=username,
        password=password,
        hostkey_verify=False,
        device_params={"name": "iosxe"},
    )


def task1_capabilities(conn):
    print("\n[Task 1] NETCONF Server Capabilities")
    print("-" * 50)
    for cap in conn.server_capabilities:
        print(f"  {cap}")


def task2_get_config(conn):
    print("\n[Task 2] get-config (running datastore — interfaces only)")
    print("-" * 50)
    filter_xml = """
    <filter>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
    </filter>
    """
    result = conn.get_config(source="running", filter=("subtree", filter_xml))
    print(result.xml)


def task3_edit_config(conn):
    print("\n[Task 3] edit-config — create Loopback99 on candidate datastore")
    print("-" * 50)
    conn.edit_config(target="candidate", config=LOOPBACK99_CONFIG)
    print("[+] edit-config accepted by candidate datastore")


def task4_commit(conn):
    print("\n[Task 4] commit — push candidate to running")
    print("-" * 50)
    conn.commit()
    print("[+] Commit successful. Loopback99 is now in running config.")


def task5_lock_unlock(conn):
    print("\n[Task 5] lock / unlock — running datastore")
    print("-" * 50)
    with conn.locked("running"):
        print("[+] Running datastore locked")
        result = conn.get(filter=("subtree", """
        <filter>
          <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <hostname/>
          </native>
        </filter>
        """))
        print(f"  Hostname element: {result.xml[:200]}...")
    print("[+] Running datastore unlocked")


def main():
    parser = argparse.ArgumentParser(description="NETCONF capstone tasks against R1")
    parser.add_argument("--host", default=R1_HOST, help="R1 management IP")
    args = parser.parse_args()

    print(f"[*] Connecting to {args.host}:{NETCONF_PORT} via NETCONF...")
    try:
        with connect(args.host, NETCONF_PORT, USERNAME, PASSWORD) as conn:
            print("[+] NETCONF session established")
            task1_capabilities(conn)
            task2_get_config(conn)
            task3_edit_config(conn)
            task4_commit(conn)
            task5_lock_unlock(conn)
    except Exception as e:
        print(f"[!] NETCONF error: {e}")
        sys.exit(1)

    print("\n[+] All NETCONF tasks completed.")


if __name__ == "__main__":
    main()
