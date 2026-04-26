"""
EVE-NG platform attribute map.

Maps the abstract platform names used in baseline.yaml (`iosv`, `iosvl2`, `vpc`)
to the exact attributes EVE-NG expects in a .unl <node> element. Values are
specific to this EVE-NG installation (image filenames, RAM, qemu options) —
update here when images are upgraded or replaced.

Source of truth: a hand-built .unl exported from EVE-NG (see baseline.unl
sample). Add a new platform by exporting one node of that platform from
EVE-NG and copying its attributes here.
"""

from __future__ import annotations

QEMU_OPTIONS = (
    "-machine type=pc,accel=kvm -serial mon:stdio -nographic "
    "-no-user-config -nodefaults -rtc base=utc -cpu host"
)

PLATFORMS = {
    "iosv": {
        "type": "qemu",
        "template": "vios",
        "image": "vios-159-3",
        "console": "telnet",
        "cpu": "1",
        "cpulimit": "0",
        "ram": "512",
        "ethernet": "4",
        "qemu_options": QEMU_OPTIONS,
        "qemu_version": "2.4.0",
        "qemu_arch": "x86_64",
        "delay": "0",
        "icon": "Router-2D-Gen-White-S.svg",
    },
    "iosvl2": {
        "type": "qemu",
        "template": "viosl2",
        "image": "viosl2-2020",
        "console": "telnet",
        "cpu": "1",
        "cpulimit": "0",
        "ram": "768",
        "ethernet": "8",
        "qemu_options": QEMU_OPTIONS,
        "qemu_version": "2.4.0",
        "qemu_arch": "x86_64",
        "delay": "0",
        "icon": "Switch-2D-L3-Generic-S.svg",
    },
    "vpc": {
        "type": "vpcs",
        "template": "vpcs",
        "image": "",
        "ethernet": "1",
        "delay": "0",
        "icon": "PC-2D-Desktop-Generic-S.svg",
    },
}


def interface_id(platform: str, name: str) -> int:
    """Map an interface name to EVE-NG's integer id.

    iosv/iosvl2: GigabitEthernet<slot>/<port> -> slot*4 + port (4 ports per slot).
    vpc: eth0 -> 0.
    """
    if platform == "vpc":
        if name != "eth0":
            raise ValueError(f"VPC only supports 'eth0', got '{name}'")
        return 0
    # iosv/iosvl2: accept "GigabitEthernet0/1" or "Gi0/1"
    suffix = name.replace("GigabitEthernet", "").replace("Gi", "")
    slot_str, port_str = suffix.split("/")
    return int(slot_str) * 4 + int(port_str)


def short_iface(name: str) -> str:
    """Return EVE-NG's short interface label (Gi0/1, eth0)."""
    if name.startswith("GigabitEthernet"):
        return "Gi" + name[len("GigabitEthernet"):]
    return name
