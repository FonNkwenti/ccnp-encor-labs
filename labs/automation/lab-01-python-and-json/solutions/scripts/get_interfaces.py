#!/usr/bin/env python3
"""Task 2 solution: annotated RESTCONF GET for interface list."""

import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Data types in Script A ---
ROUTER_IP   = "10.1.12.1"              # str
AUTH        = ("admin", "Encor-API-2026")  # tuple
MAX_RETRIES = 3                         # int
DEBUG       = True                      # bool
EXCLUDED    = None                      # NoneType
HEADERS     = {                         # dict
    "Accept":       "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
interface_names = []                    # list


def get_interfaces():
    url = f"https://{ROUTER_IP}/restconf/data/ietf-interfaces:interfaces"
    try:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
        resp.raise_for_status()            # raises HTTPError on 4xx/5xx
        data = resp.json()
        iface_list = data["ietf-interfaces:interfaces"]["interface"]
        for iface in iface_list:
            interface_names.append(iface["name"])
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to router")
    except json.JSONDecodeError:
        print("Invalid JSON in response")
    return interface_names


if __name__ == "__main__":
    names = get_interfaces()
    print(f"Found {len(names)} interfaces: {names}")
