#!/usr/bin/env python3
"""Render the topology tables inside each lab's topology/README.md.

Joins two sources:
  - labs/<chapter>/baseline.yaml      (links, devices, VLANs per chapter)
  - labs/_shared/platforms.yaml       (RAM, IOS version per platform)

...and writes tables between these sentinels in every lab's
topology/README.md (created by hand, see switching labs for format):

    <!-- GENERATED:TOPOLOGY:START -->
    ...generated Nodes / Links / Port Usage / VLAN tables...
    <!-- GENERATED:TOPOLOGY:END -->

Content outside the sentinels is preserved verbatim. Labs that don't yet
have the sentinels are skipped (with a warning) so hand-authored READMEs
aren't silently clobbered.

Usage:
    python scripts/render_topology_readme.py labs/switching
    python scripts/render_topology_readme.py labs/switching/lab-02-rstp-and-enhancements
    python scripts/render_topology_readme.py --all
    python scripts/render_topology_readme.py --all --check   # exit 1 if stale

--check writes nothing and exits non-zero when any README would change.
Intended for CI / pre-commit.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORMS_FILE = REPO_ROOT / "labs" / "_shared" / "platforms.yaml"

MARKER_START = "<!-- GENERATED:TOPOLOGY:START -->"
MARKER_END = "<!-- GENERATED:TOPOLOGY:END -->"


# ─────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────

@dataclass
class Platform:
    key: str
    display_name: str
    ios_version: str
    ram_mb: int | None


def load_platforms() -> dict[str, Platform]:
    data = yaml.safe_load(PLATFORMS_FILE.read_text(encoding="utf-8"))
    out: dict[str, Platform] = {}
    for key, spec in data["platforms"].items():
        out[key] = Platform(
            key=key,
            display_name=spec.get("display_name", key),
            ios_version=spec.get("ios_version", "n/a"),
            ram_mb=spec.get("ram_mb"),
        )
    return out


def load_baseline(chapter_dir: Path) -> dict:
    f = chapter_dir / "baseline.yaml"
    if not f.exists():
        raise FileNotFoundError(f"No baseline.yaml in {chapter_dir}")
    return yaml.safe_load(f.read_text(encoding="utf-8"))


def lab_device_names_from_baseline(baseline: dict, lab_folder: str) -> set[str]:
    """Look up the device-name list for a lab from baseline.yaml:labs[]."""
    for entry in baseline.get("labs", []):
        if entry.get("folder") == lab_folder:
            devs = entry.get("devices") or []
            return set(devs)
    raise KeyError(
        f"Lab folder '{lab_folder}' not found in baseline.yaml:labs[]. "
        f"Add an entry with a 'devices:' list."
    )


# ─────────────────────────────────────────────────────────────
# Baseline parsing helpers
# ─────────────────────────────────────────────────────────────

def parse_endpoint(raw: str) -> tuple[str, str]:
    """'SW1:GigabitEthernet0/0' -> ('SW1', 'Gi0/0')."""
    node, port = raw.split(":", 1)
    port = port.replace("GigabitEthernet", "Gi").replace("Ethernet", "e")
    return node, port


def lab_links(baseline: dict, lab_device_names: set[str]) -> list[dict]:
    """Return links whose endpoints are both in lab_device_names."""
    out = []
    for link in baseline["core_topology"]["links"]:
        a_node, _ = parse_endpoint(link["source"])
        b_node, _ = parse_endpoint(link["target"])
        if a_node in lab_device_names and b_node in lab_device_names:
            out.append(link)
    return out


def lab_devices(baseline: dict, lab_device_names: set[str]) -> list[dict]:
    """Return device entries in baseline order, filtered to lab_device_names."""
    all_devs = baseline["core_topology"]["devices"]
    all_devs += baseline.get("optional_devices") or []
    return [d for d in all_devs if d["name"] in lab_device_names]


# ─────────────────────────────────────────────────────────────
# Table renderers
# ─────────────────────────────────────────────────────────────

def render_nodes_table(devices: list[dict], platforms: dict[str, Platform]) -> str:
    lines = [
        "### Nodes",
        "",
        "| Node | Platform | IOS version | RAM | Mgmt IP | Role |",
        "|------|----------|-------------|-----|---------|------|",
    ]
    for d in devices:
        name = d["name"]
        plat_key = d.get("platform") or d.get("type")  # VPCs use 'type'
        plat = platforms.get(plat_key)
        if plat is None:
            raise KeyError(f"Unknown platform '{plat_key}' for device {name}")

        ios = plat.ios_version
        ram = f"{plat.ram_mb} MB" if plat.ram_mb else "n/a"

        mgmt = _mgmt_ip_for_device(d)
        role = d.get("role", "--")
        lines.append(
            f"| {name} | `{plat_key}` | {ios} | {ram} | {mgmt} | {role} |"
        )
    return "\n".join(lines)


def _mgmt_ip_for_device(d: dict) -> str:
    if d.get("management_ip"):
        vlan = d.get("management_vlan")
        suffix = f" (VLAN {vlan} SVI)" if vlan else ""
        return f"{d['management_ip']}{suffix}"
    if d.get("loopback0"):
        return f"Loopback0: {d['loopback0']}"
    if d.get("interfaces"):
        iface = d["interfaces"][0]
        gw = iface.get("gateway")
        gw_suffix = f" (gw {gw})" if gw else ""
        return f"{iface['ip']}{gw_suffix}"
    return "--"


def render_links_table(links: list[dict]) -> str:
    lines = [
        "### Links",
        "",
        "| ID | A-side | B-side | Type | Purpose |",
        "|----|--------|--------|------|---------|",
    ]
    for link in links:
        a_node, a_port = parse_endpoint(link["source"])
        b_node, b_port = parse_endpoint(link["target"])
        ltype = link.get("type", "--").capitalize()
        purpose = link.get("purpose", "--")
        lines.append(
            f"| {link['id']} | {a_node}:{a_port} | {b_node}:{b_port} | {ltype} | {purpose} |"
        )
    return "\n".join(lines)


def render_port_usage(devices: list[dict], links: list[dict]) -> str:
    """Per-node table of only the ports wired in this lab."""
    lines = ["### Port usage (only interfaces wired in this lab)", ""]

    # Collect port usage per node
    usage: dict[str, list[tuple[str, str, str, str]]] = {}
    for link in links:
        a_node, a_port = parse_endpoint(link["source"])
        b_node, b_port = parse_endpoint(link["target"])
        purpose = link.get("purpose", "")
        lid = link["id"]

        usage.setdefault(a_node, []).append((a_port, f"{b_node}:{b_port}", lid, purpose))
        usage.setdefault(b_node, []).append((b_port, f"{a_node}:{a_port}", lid, purpose))

    # Sort ports naturally (Gi0/0, Gi0/1, ..., Gi1/0) per node
    def port_sort_key(row):
        port = row[0]
        # Handle 'Gi0/0', 'e0/0', 'e0' etc.
        digits = [int(n) for n in "".join(c if c.isdigit() else " " for c in port).split()]
        return digits

    for d in devices:
        name = d["name"]
        if name not in usage:
            continue
        plat = d.get("platform") or d.get("type")
        rows = sorted(usage[name], key=port_sort_key)

        lines.append(f"**{name} (`{plat}`)**")
        lines.append("")
        lines.append("| Port | Peer | Link | Purpose |")
        lines.append("|------|------|------|---------|")
        for port, peer, lid, purpose in rows:
            lines.append(f"| {port} | {peer} | {lid} | {purpose} |")

        # Append Loopback0 row for routers, if present
        if d.get("loopback0"):
            lines.append(f"| Loopback0 | -- | -- | {d['loopback0']} (router ID / reachability anchor) |")

        lines.append("")

    return "\n".join(lines).rstrip()


def render_vlan_table(baseline: dict) -> str:
    vlans = baseline.get("vlans") or []
    if not vlans:
        return ""
    lines = [
        "### VLAN plan",
        "",
        "| VLAN ID | Name | Subnet | Gateway |",
        "|---------|------|--------|---------|",
    ]
    for v in vlans:
        lines.append(
            f"| {v['id']} | {v['name']} | {v['subnet']} | {v['gateway']} |"
        )
    return "\n".join(lines)


def render_block(baseline: dict, lab_folder: str, platforms: dict[str, Platform]) -> str:
    device_names = lab_device_names_from_baseline(baseline, lab_folder)
    devices = lab_devices(baseline, device_names)
    links = lab_links(baseline, device_names)

    parts = [
        render_nodes_table(devices, platforms),
        "",
        render_links_table(links),
        "",
        render_port_usage(devices, links),
    ]
    vlan_block = render_vlan_table(baseline)
    if vlan_block:
        parts.extend(["", vlan_block])

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────
# File I/O
# ─────────────────────────────────────────────────────────────

def splice_into_readme(readme_text: str, new_block: str) -> str:
    """Replace content between sentinels. Raise if sentinels missing."""
    if MARKER_START not in readme_text or MARKER_END not in readme_text:
        raise ValueError("README missing GENERATED:TOPOLOGY markers")

    before, _, rest = readme_text.partition(MARKER_START)
    _, _, after = rest.partition(MARKER_END)

    return (
        before
        + MARKER_START
        + "\n\n"
        + new_block
        + "\n\n"
        + MARKER_END
        + after
    )


def find_labs(target: Path) -> list[Path]:
    """Given a chapter dir or lab dir, return list of lab dirs."""
    if target.name.startswith("lab-"):
        return [target]
    if (target / "baseline.yaml").exists():
        return sorted(
            p for p in target.iterdir()
            if p.is_dir() and p.name.startswith("lab-")
        )
    raise FileNotFoundError(
        f"{target} is neither a chapter dir (has baseline.yaml) "
        f"nor a lab dir (name starts with 'lab-')"
    )


def find_all_chapters() -> list[Path]:
    labs_root = REPO_ROOT / "labs"
    return sorted(
        p.parent for p in labs_root.glob("*/baseline.yaml")
    )


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def process_lab(lab_dir: Path, platforms: dict[str, Platform], check_only: bool) -> tuple[str, bool]:
    """Return (status_string, changed_bool)."""
    chapter_dir = lab_dir.parent
    readme = lab_dir / "topology" / "README.md"
    if not readme.exists():
        return (f"  SKIP {lab_dir.name}: no topology/README.md", False)

    baseline = load_baseline(chapter_dir)
    new_block = render_block(baseline, lab_dir.name, platforms)

    current = readme.read_text(encoding="utf-8")
    try:
        new_text = splice_into_readme(current, new_block)
    except ValueError:
        return (f"  SKIP {lab_dir.name}: no GENERATED markers in README", False)

    if new_text == current:
        return (f"  OK   {lab_dir.name}: up to date", False)

    if check_only:
        return (f"  DIFF {lab_dir.name}: README is stale (run without --check)", True)

    readme.write_text(new_text, encoding="utf-8")
    return (f"  WROTE {lab_dir.name}", True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", nargs="?", help="chapter dir or lab dir")
    parser.add_argument("--all", action="store_true", help="render all chapters")
    parser.add_argument("--check", action="store_true",
                        help="dry-run; exit 1 if any README is stale")
    args = parser.parse_args(argv)

    if not args.all and not args.target:
        parser.error("provide a target path or --all")

    platforms = load_platforms()

    if args.all:
        lab_dirs: list[Path] = []
        for chap in find_all_chapters():
            lab_dirs.extend(find_labs(chap))
    else:
        target = Path(args.target).resolve()
        lab_dirs = find_labs(target)

    any_changed = False
    for lab_dir in lab_dirs:
        msg, changed = process_lab(lab_dir, platforms, check_only=args.check)
        print(msg)
        any_changed = any_changed or changed

    if args.check and any_changed:
        print("\nREADMEs are out of sync with baseline.yaml. Re-run without --check.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
