#!/usr/bin/env python3
"""
Solution: Task 7 — Lock/Edit Candidate Datastore/Commit/Unlock.

Demonstrates the full candidate datastore workflow:
  1. Lock the candidate datastore
  2. Send edit-config targeting candidate (creates Loopback201)
  3. Send commit RPC to apply candidate to running
  4. Unlock the candidate datastore
  5. Verify Loopback201 appears in running config

This workflow requires: netconf-yang feature candidate-datastore on R1.
"""

from ncclient import manager
from ncclient.operations import RPCError
from ncclient.transport.errors import AuthenticationError, SSHError

ROUTER_IP = "10.1.12.1"
NETCONF_PORT = 830
USERNAME = "admin"
PASSWORD = "Encor-API-2026"

LOOPBACK201_CONFIG = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback201</name>
      <description>Staged via candidate datastore</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
        ianaift:softwareLoopback
      </type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>10.201.201.1</ip>
          <prefix-length>32</prefix-length>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""

VERIFY_FILTER = """
<filter type="subtree">
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback201</name>
    </interface>
  </interfaces>
</filter>
"""


def candidate_workflow():
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
            print("[+] Connected.")

            # Step 1: Lock candidate
            print("[*] Step 1: Locking candidate datastore...")
            m.lock(target="candidate")
            print("[+] Candidate datastore locked.")

            try:
                # Step 2: Edit-config targeting candidate
                print("[*] Step 2: Staging Loopback201 in candidate datastore...")
                reply = m.edit_config(target="candidate", config=LOOPBACK201_CONFIG)
                if not reply.ok:
                    raise RuntimeError(f"edit-config failed: {reply.error}")
                print("[+] edit-config to candidate: OK")

                # Step 3: Commit
                print("[*] Step 3: Committing candidate to running...")
                m.commit()
                print("[+] Commit: OK — Loopback201 is now in running config.")

            finally:
                # Step 4: Unlock (always runs, even on error)
                print("[*] Step 4: Unlocking candidate datastore...")
                m.unlock(target="candidate")
                print("[+] Candidate datastore unlocked.")

            # Step 5: Verify
            print("[*] Step 5: Verifying Loopback201 in running datastore...")
            verify_reply = m.get_config(source="running", filter=VERIFY_FILTER)
            if "Loopback201" in verify_reply.xml:
                print("[+] Verification PASSED — Loopback201 found in running config.")
            else:
                print("[!] Verification FAILED — Loopback201 not found in running config.")

    except RPCError as e:
        print(f"[!] NETCONF RPC error: {e}")
        print("    Hint: Verify 'netconf-yang feature candidate-datastore' is configured.")
    except AuthenticationError:
        print("[!] Authentication failed")
    except SSHError as e:
        print(f"[!] NETCONF connection error: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")


if __name__ == "__main__":
    candidate_workflow()
