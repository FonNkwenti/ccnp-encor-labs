#!/usr/bin/env python3
"""
Generate EVE-NG .unl files for every lab in a topic from baseline.yaml.

Reads:   labs/<topic>/baseline.yaml
Writes:  labs/<topic>/<lab-folder>/<lab-folder>.unl

Each lab gets its own .unl (matches setup_lab.py's DEFAULT_LAB_PATH
convention). All labs in a topic share the same core_topology — extra
nodes for a specific lab can be added under that lab's optional_devices
once the schema supports it.

Startup configs from <lab>/initial-configs/<node>.cfg (and .vpc) are
base64-embedded in the .unl so EVE-NG boots the lab pre-configured.
Use --no-embed-configs to skip embedding (then setup_lab.py pushes via
console, the original flow).

Usage:
    python labs/common/tools/gen_unl.py switching
    python labs/common/tools/gen_unl.py switching --no-embed-configs
    python labs/common/tools/gen_unl.py switching --only lab-02-rstp-and-enhancements
"""

from __future__ import annotations

import argparse
import base64
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from eve_platforms import PLATFORMS, interface_id, short_iface  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parents[2]
LABS_DIR = REPO_ROOT / "labs"


# ────────────────────────────────────────────────────────────────────
# Layout — USER-CONTRIBUTED
# ────────────────────────────────────────────────────────────────────

def compute_layout(devices: List[dict]) -> Dict[str, Tuple[int, int]]:
    """Return {device_name: (left, top)} for canvas placement.

    Reference coordinates from the manually-built switching baseline:
        R1   (507,  81)   — router on top
        SW1  (513, 327)   — distribution switch in middle
        SW2  (228, 522)   — access switch bottom-left
        SW3  (798, 522)   — access switch bottom-right
        PC1  (231, 699)   — host below SW2
        PC2  (801, 699)   — host below SW3

    TODO (you): implement a layout strategy. Options to consider:
      - Hierarchical by platform: routers top, L3 switches middle,
        L2 switches lower, hosts bottom (works for most lab topics).
      - Role-based: read `role` field from baseline and group.
      - Per-topic hardcoded dict if visual precision matters.

    Trade-offs:
      - A generic auto-layout is reusable across topics (BGP, OSPF, etc.)
        but may produce ugly diagrams for unusual topologies.
      - Per-topic dicts are precise but require an edit each time you
        add a topic.

    Replace the body below with your strategy.
    """
    tiers = {"iosv": 80, "iosvl2": 420, "vpc": 700}
    groups: Dict[str, List[str]] = {"iosv": [], "iosvl2": [], "vpc": []}
    for d in devices:
        plat = d.get("platform") or d.get("type")
        if plat in groups:
            groups[plat].append(d["name"])
    layout: Dict[str, Tuple[int, int]] = {}
    for plat, names in groups.items():
        for i, name in enumerate(names):
            layout[name] = (200 + i * 300, tiers[plat])
    return layout


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def split_endpoint(ep: str) -> Tuple[str, str]:
    """'SW1:GigabitEthernet0/1' -> ('SW1', 'GigabitEthernet0/1')"""
    node, iface = ep.split(":", 1)
    return node.strip(), iface.strip()


def load_config(lab_dir: Path, node_name: str, platform: str) -> str | None:
    """Return startup config text for a node, or None if missing."""
    ext = ".vpc" if platform == "vpc" else ".cfg"
    path = lab_dir / "initial-configs" / f"{node_name}{ext}"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


# ────────────────────────────────────────────────────────────────────
# Generator
# ────────────────────────────────────────────────────────────────────

def build_unl(
    lab_name: str,
    lab_dir: Path,
    devices: List[dict],
    links: List[dict],
    embed_configs: bool,
    author: str = "gen_unl.py",
) -> ET.ElementTree:
    """Build a .unl XML tree for one lab."""
    layout = compute_layout(devices)

    # Assign node ids in declaration order; build name -> id lookup.
    node_ids: Dict[str, int] = {d["name"]: i + 1 for i, d in enumerate(devices)}

    # Group links by their endpoints to assign one network per link.
    # network_id assignment is sequential in link declaration order.
    network_ids: Dict[str, int] = {link["id"]: i + 1 for i, link in enumerate(links)}

    # Walk links and accumulate {node_name: [(iface_id, iface_short_name, network_id), ...]}
    node_ifaces: Dict[str, List[Tuple[int, str, int]]] = {d["name"]: [] for d in devices}
    for link in links:
        net_id = network_ids[link["id"]]
        for ep in (link["source"], link["target"]):
            node_name, iface_name = split_endpoint(ep)
            platform = next(d for d in devices if d["name"] == node_name).get(
                "platform"
            ) or "vpc"  # vpc devices use 'type: vpc' instead of 'platform'
            iid = interface_id(platform, iface_name)
            node_ifaces[node_name].append((iid, short_iface(iface_name), net_id))

    # ── Build XML ─────────────────────────────────────────────────
    lab = ET.Element(
        "lab",
        attrib={
            "name": lab_name,
            "version": "1",
            "scripttimeout": "300",
            "lock": "0",
            "author": author,
        },
    )
    ET.SubElement(lab, "description").text = (
        f"Auto-generated from baseline.yaml by gen_unl.py for lab '{lab_name}'."
    )
    topology = ET.SubElement(lab, "topology")
    nodes_el = ET.SubElement(topology, "nodes")
    networks_el = ET.SubElement(topology, "networks")

    embedded_configs: List[Tuple[int, str]] = []  # (node_id, base64_cfg)

    for device in devices:
        name = device["name"]
        platform = device.get("platform") or device.get("type")  # 'vpc' uses 'type'
        if platform not in PLATFORMS:
            raise ValueError(
                f"Unknown platform '{platform}' for device '{name}'. "
                f"Add it to eve_platforms.PLATFORMS."
            )
        attrs = dict(PLATFORMS[platform])
        nid = node_ids[name]
        left, top = layout[name]

        cfg_text = load_config(lab_dir, name, platform) if embed_configs else None
        config_attr = "1" if cfg_text else "0"

        node_attrs = {
            "id": str(nid),
            "name": name,
            **attrs,
            "uuid": str(uuid.uuid4()),
            "config": config_attr,
            "left": str(left),
            "top": str(top),
        }
        # vpc nodes have no uuid in the reference sample — drop it cleanly.
        if platform == "vpc":
            node_attrs.pop("uuid", None)

        node_el = ET.SubElement(nodes_el, "node", attrib=node_attrs)

        # Sort interfaces by id for stable output.
        for iid, short_name, net_id in sorted(set(node_ifaces[name])):
            ET.SubElement(
                node_el,
                "interface",
                attrib={
                    "id": str(iid),
                    "name": short_name,
                    "type": "ethernet",
                    "network_id": str(net_id),
                },
            )

        if cfg_text:
            embedded_configs.append((nid, base64.b64encode(cfg_text.encode()).decode()))

    # Networks — one per link, named after the source endpoint for readability.
    for link in links:
        src_node, _ = split_endpoint(link["source"])
        net_id = network_ids[link["id"]]
        # Position network at the midpoint of its two endpoints.
        sx, sy = layout[src_node]
        tgt_node, _ = split_endpoint(link["target"])
        tx, ty = layout[tgt_node]
        ET.SubElement(
            networks_el,
            "network",
            attrib={
                "id": str(net_id),
                "type": "bridge",
                "name": f"Net-{link['id']}",
                "left": str((sx + tx) // 2),
                "top": str((sy + ty) // 2),
                "visibility": "0",
                "icon": "lan.png",
            },
        )

    # Embedded configs go in <objects><configs>.
    if embedded_configs:
        objects_el = ET.SubElement(lab, "objects")
        configs_el = ET.SubElement(objects_el, "configs")
        for nid, b64 in embedded_configs:
            cfg_el = ET.SubElement(configs_el, "config", attrib={"id": str(nid)})
            cfg_el.text = b64

    ET.indent(lab, space="  ")
    return ET.ElementTree(lab)


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate EVE-NG .unl files for a topic.")
    parser.add_argument("topic", help="Topic name (folder under labs/), e.g. 'switching'")
    parser.add_argument("--only", help="Generate only this lab folder name")
    parser.add_argument(
        "--no-embed-configs",
        action="store_true",
        help="Skip embedding initial-configs/*.cfg into the .unl",
    )
    args = parser.parse_args()

    topic_dir = LABS_DIR / args.topic
    baseline_path = topic_dir / "baseline.yaml"
    if not baseline_path.exists():
        print(f"[!] Not found: {baseline_path}", file=sys.stderr)
        return 2

    with baseline_path.open(encoding="utf-8") as f:
        baseline = yaml.safe_load(f)

    core = baseline["core_topology"]
    devices = core["devices"]
    links = core["links"]

    embed_configs = not args.no_embed_configs

    for lab in baseline["labs"]:
        folder = lab["folder"]
        if args.only and folder != args.only:
            continue
        lab_dir = topic_dir / folder
        if not lab_dir.exists():
            print(f"[!] Skipping {folder}: directory does not exist", file=sys.stderr)
            continue

        tree = build_unl(
            lab_name=folder,
            lab_dir=lab_dir,
            devices=devices,
            links=links,
            embed_configs=embed_configs,
        )
        topology_dir = lab_dir / "topology"
        topology_dir.mkdir(parents=True, exist_ok=True)
        out_path = topology_dir / f"{folder}.unl"
        tree.write(out_path, encoding="UTF-8", xml_declaration=True)
        print(f"[+] Wrote {out_path.relative_to(REPO_ROOT)}")

        # EVE-NG only imports .zip uploads. Preserve the topic folder inside
        # the archive so it imports to /opt/unetlab/labs/<topic>/<folder>.unl.
        zip_path = topology_dir / f"{folder}.zip"
        arcname = f"{args.topic}/{folder}.unl"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(out_path, arcname=arcname)
        print(f"[+] Wrote {zip_path.relative_to(REPO_ROOT)}  ({arcname})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
