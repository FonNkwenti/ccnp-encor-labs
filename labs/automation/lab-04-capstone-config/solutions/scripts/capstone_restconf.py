#!/usr/bin/env python3
"""
capstone_restconf.py — Lab 04 Automation Capstone: RESTCONF Tasks

Demonstrates RESTCONF operations against R2 using requests:
  1. GET /restconf/ to confirm service is active
  2. GET ietf-interfaces datastore — display all interfaces
  3. PUT Loopback88 via ietf-interfaces (create/replace)
  4. PATCH Loopback88 description field only
  5. DELETE Loopback88 and confirm 404 on subsequent GET
  6. Trigger each HTTP response code: 200, 204, 400, 401, 404

Usage:
    pip install requests
    python3 capstone_restconf.py --host <R2-mgmt-ip>
"""

import argparse
import json
import sys

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("[!] requests not installed. Run: pip install requests")
    sys.exit(1)

R2_HOST = "10.1.12.2"
BASE_URL = f"https://{R2_HOST}/restconf"
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
AUTH = ("admin", "Encor-API-2026")

LOOPBACK88_PAYLOAD = {
    "ietf-interfaces:interface": {
        "name": "Loopback88",
        "description": "RESTCONF-created capstone interface",
        "type": "iana-if-type:softwareLoopback",
        "enabled": True,
        "ietf-ip:ipv4": {
            "address": [
                {
                    "ip": "88.88.88.88",
                    "prefix-length": 32
                }
            ]
        }
    }
}

PATCH_PAYLOAD = {
    "ietf-interfaces:interface": {
        "name": "Loopback88",
        "description": "RESTCONF-patched description"
    }
}


def get(url, auth=AUTH, headers=None):
    return requests.get(url, auth=auth, headers=headers or HEADERS, verify=False)


def task1_get_root(base_url):
    print("\n[Task 1] GET /restconf/ — confirm service")
    print("-" * 50)
    r = get(f"{base_url}/")
    print(f"  Status: {r.status_code}")
    print(f"  Body:   {json.dumps(r.json(), indent=2)[:400]}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("[+] RESTCONF service confirmed active (200 OK)")


def task2_get_interfaces(base_url):
    print("\n[Task 2] GET ietf-interfaces datastore")
    print("-" * 50)
    url = f"{base_url}/data/ietf-interfaces:interfaces"
    r = get(url)
    print(f"  Status: {r.status_code}")
    data = r.json()
    ifaces = data.get("ietf-interfaces:interfaces", {}).get("interface", [])
    for iface in ifaces:
        print(f"    Interface: {iface.get('name')} — {iface.get('description', '(no description)')}")
    print(f"[+] Found {len(ifaces)} interface(s)")


def task3_put_loopback(base_url):
    print("\n[Task 3] PUT Loopback88 — create via ietf-interfaces")
    print("-" * 50)
    url = f"{base_url}/data/ietf-interfaces:interfaces/interface=Loopback88"
    r = requests.put(url, auth=AUTH, headers=HEADERS, json=LOOPBACK88_PAYLOAD, verify=False)
    print(f"  Status: {r.status_code}")
    if r.status_code in (200, 201, 204):
        print("[+] Loopback88 created/replaced successfully")
    else:
        print(f"[!] Unexpected status: {r.status_code} — {r.text[:200]}")


def task4_patch_description(base_url):
    print("\n[Task 4] PATCH Loopback88 description only")
    print("-" * 50)
    url = f"{base_url}/data/ietf-interfaces:interfaces/interface=Loopback88"
    r = requests.patch(url, auth=AUTH, headers=HEADERS, json=PATCH_PAYLOAD, verify=False)
    print(f"  Status: {r.status_code}")
    if r.status_code == 204:
        print("[+] PATCH accepted (204 No Content)")
    else:
        print(f"[!] Unexpected status: {r.status_code} — {r.text[:200]}")


def task5_delete_and_confirm(base_url):
    print("\n[Task 5] DELETE Loopback88 then confirm 404")
    print("-" * 50)
    url = f"{base_url}/data/ietf-interfaces:interfaces/interface=Loopback88"
    r = requests.delete(url, auth=AUTH, headers=HEADERS, verify=False)
    print(f"  DELETE status: {r.status_code}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}"
    print("[+] Loopback88 deleted (204 No Content)")

    r2 = get(url)
    print(f"  GET after DELETE status: {r2.status_code}")
    assert r2.status_code == 404, f"Expected 404, got {r2.status_code}"
    print("[+] Confirmed 404 after deletion")


def task6_response_codes(base_url):
    print("\n[Task 6] Trigger HTTP response codes")
    print("-" * 50)

    # 200 — valid GET
    r = get(f"{base_url}/data/ietf-interfaces:interfaces")
    print(f"  200 GET  → {r.status_code} {'OK' if r.status_code == 200 else 'UNEXPECTED'}")

    # 204 — PUT with valid payload (creates or replaces, no body returned)
    url_lo = f"{base_url}/data/ietf-interfaces:interfaces/interface=Loopback77"
    lo77 = {"ietf-interfaces:interface": {"name": "Loopback77", "type": "iana-if-type:softwareLoopback", "enabled": True}}
    r = requests.put(url_lo, auth=AUTH, headers=HEADERS, json=lo77, verify=False)
    print(f"  204 PUT  → {r.status_code} {'OK' if r.status_code in (200, 201, 204) else 'UNEXPECTED'}")

    # 400 — malformed JSON body
    r = requests.put(url_lo, auth=AUTH, headers=HEADERS, data="not-json", verify=False)
    print(f"  400 BAD  → {r.status_code} {'OK' if r.status_code == 400 else 'UNEXPECTED'}")

    # 401 — wrong credentials
    r = requests.get(f"{base_url}/data/ietf-interfaces:interfaces", auth=("baduser", "badpass"), headers=HEADERS, verify=False)
    print(f"  401 AUTH → {r.status_code} {'OK' if r.status_code == 401 else 'UNEXPECTED'}")

    # 404 — nonexistent resource
    r = get(f"{base_url}/data/ietf-interfaces:interfaces/interface=Loopback999")
    print(f"  404 NF   → {r.status_code} {'OK' if r.status_code == 404 else 'UNEXPECTED'}")

    # Cleanup Lo77
    requests.delete(url_lo, auth=AUTH, headers=HEADERS, verify=False)
    print("[+] Response code demonstration complete")


def main():
    parser = argparse.ArgumentParser(description="RESTCONF capstone tasks against R2")
    parser.add_argument("--host", default=R2_HOST, help="R2 management IP")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = f"https://{args.host}/restconf"

    print(f"[*] RESTCONF base URL: {BASE_URL}")
    try:
        task1_get_root(BASE_URL)
        task2_get_interfaces(BASE_URL)
        task3_put_loopback(BASE_URL)
        task4_patch_description(BASE_URL)
        task5_delete_and_confirm(BASE_URL)
        task6_response_codes(BASE_URL)
    except AssertionError as e:
        print(f"[!] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

    print("\n[+] All RESTCONF tasks completed.")


if __name__ == "__main__":
    main()
