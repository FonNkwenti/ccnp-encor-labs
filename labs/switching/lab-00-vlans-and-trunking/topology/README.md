# Topology Assets -- Switching Lab 00

This directory holds every artifact a student needs to *reconstruct the topology
in EVE-NG* before running `setup_lab.py`.

## Files

| File | Purpose | Authoritative for |
|------|---------|-------------------|
| `topology.drawio` | Conceptual diagram (devices, links, VLANs) | **Design** -- read this first |
| `lab-00-vlans-and-trunking.unl` | EVE-NG native lab file | **EVE-NG build** -- import this |

> **If `lab-00-vlans-and-trunking.unl` is missing** from this folder, the repo
> maintainer hasn't exported it yet. Build the topology manually using the
> tables below.

## Manual build reference

The tables below are **auto-generated** by `scripts/render_topology_readme.py`
from `labs/switching/baseline.yaml` (link/device authority) joined with
`labs/_shared/platforms.yaml` (platform specs, projected from
`.agent/skills/eve-ng/SKILL.md`). Do not hand-edit between the markers --
update `baseline.yaml` and re-run the renderer instead.

<!-- GENERATED:TOPOLOGY:START -->

### Nodes

| Node | Platform | IOS version | RAM | Mgmt IP | Role |
|------|----------|-------------|-----|---------|------|
| SW1 | `iosvl2` | 15.x (high_iron_20200929) | 768 MB | 192.168.99.1/24 (VLAN 99 SVI) | Distribution switch / root bridge candidate |
| SW2 | `iosvl2` | 15.x (high_iron_20200929) | 768 MB | 192.168.99.2/24 (VLAN 99 SVI) | Access switch (PC1 segment) |
| SW3 | `iosvl2` | 15.x (high_iron_20200929) | 768 MB | 192.168.99.3/24 (VLAN 99 SVI) | Access switch (PC2 segment) |
| R1 | `iosv` | 15.9(3)M6 | 512 MB | Loopback0: 1.1.1.1/32 | Inter-VLAN router (router-on-a-stick) |
| PC1 | `vpc` | n/a (VPCS) | n/a | 192.168.10.10/24 (gw 192.168.10.1) | -- |
| PC2 | `vpc` | n/a (VPCS) | n/a | 192.168.20.10/24 (gw 192.168.20.1) | -- |

### Links

| ID | A-side | B-side | Type | Purpose |
|----|--------|--------|------|---------|
| L1 | R1:Gi0/0 | SW1:Gi0/0 | Trunk | Router-on-a-stick trunk (carries all VLANs) |
| L2 | SW1:Gi0/1 | SW2:Gi0/1 | Trunk | SW1-SW2 link 1 (EtherChannel member from lab-01) |
| L3 | SW1:Gi0/2 | SW2:Gi0/2 | Trunk | SW1-SW2 link 2 (EtherChannel member from lab-01) |
| L4 | SW1:Gi0/3 | SW3:Gi0/3 | Trunk | SW1-SW3 link 1 (EtherChannel member from lab-01) |
| L5 | SW1:Gi1/0 | SW3:Gi1/0 | Trunk | SW1-SW3 link 2 (EtherChannel member from lab-01) |
| L6 | SW2:Gi0/3 | SW3:Gi0/1 | Trunk | SW2-SW3 link 1 (EtherChannel member from lab-01) |
| L7 | SW2:Gi1/0 | SW3:Gi0/2 | Trunk | SW2-SW3 link 2 (EtherChannel member from lab-01) |
| L8 | PC1:eth0 | SW2:Gi1/1 | Access | PC1 access port (VLAN 10) |
| L9 | PC2:eth0 | SW3:Gi1/1 | Access | PC2 access port (VLAN 20) |

### Port usage (only interfaces wired in this lab)

**SW1 (`iosvl2`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| Gi0/0 | R1:Gi0/0 | L1 | Router-on-a-stick trunk (carries all VLANs) |
| Gi0/1 | SW2:Gi0/1 | L2 | SW1-SW2 link 1 (EtherChannel member from lab-01) |
| Gi0/2 | SW2:Gi0/2 | L3 | SW1-SW2 link 2 (EtherChannel member from lab-01) |
| Gi0/3 | SW3:Gi0/3 | L4 | SW1-SW3 link 1 (EtherChannel member from lab-01) |
| Gi1/0 | SW3:Gi1/0 | L5 | SW1-SW3 link 2 (EtherChannel member from lab-01) |

**SW2 (`iosvl2`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| Gi0/1 | SW1:Gi0/1 | L2 | SW1-SW2 link 1 (EtherChannel member from lab-01) |
| Gi0/2 | SW1:Gi0/2 | L3 | SW1-SW2 link 2 (EtherChannel member from lab-01) |
| Gi0/3 | SW3:Gi0/1 | L6 | SW2-SW3 link 1 (EtherChannel member from lab-01) |
| Gi1/0 | SW3:Gi0/2 | L7 | SW2-SW3 link 2 (EtherChannel member from lab-01) |
| Gi1/1 | PC1:eth0 | L8 | PC1 access port (VLAN 10) |

**SW3 (`iosvl2`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| Gi0/1 | SW2:Gi0/3 | L6 | SW2-SW3 link 1 (EtherChannel member from lab-01) |
| Gi0/2 | SW2:Gi1/0 | L7 | SW2-SW3 link 2 (EtherChannel member from lab-01) |
| Gi0/3 | SW1:Gi0/3 | L4 | SW1-SW3 link 1 (EtherChannel member from lab-01) |
| Gi1/0 | SW1:Gi1/0 | L5 | SW1-SW3 link 2 (EtherChannel member from lab-01) |
| Gi1/1 | PC2:eth0 | L9 | PC2 access port (VLAN 20) |

**R1 (`iosv`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| Gi0/0 | SW1:Gi0/0 | L1 | Router-on-a-stick trunk (carries all VLANs) |
| Loopback0 | -- | -- | 1.1.1.1/32 (router ID / reachability anchor) |

**PC1 (`vpc`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| eth0 | SW2:Gi1/1 | L8 | PC1 access port (VLAN 10) |

**PC2 (`vpc`)**

| Port | Peer | Link | Purpose |
|------|------|------|---------|
| eth0 | SW3:Gi1/1 | L9 | PC2 access port (VLAN 20) |

### VLAN plan

| VLAN ID | Name | Subnet | Gateway |
|---------|------|--------|---------|
| 10 | SALES | 192.168.10.0/24 | 192.168.10.1 |
| 20 | ENGINEERING | 192.168.20.0/24 | 192.168.20.1 |
| 30 | MANAGEMENT_HOSTS | 192.168.30.0/24 | 192.168.30.1 |
| 99 | NATIVE_MGMT | 192.168.99.0/24 | 192.168.99.1 |

<!-- GENERATED:TOPOLOGY:END -->

## Lab-00 notes

- **No EtherChannel bundles yet.** The seven inter-switch links are configured
  as plain 802.1Q trunks in this lab. Lab 01 bundles them into Po1 (LACP),
  Po2 (PAgP), and Po3 (static).
- **DTP behavior matters here** -- parts of the exercise set specific trunks
  to DTP modes (`dynamic auto`, `dynamic desirable`) to verify negotiation
  outcomes. See `workbook.md` for the per-link DTP plan.

## Why both a `.drawio` and a `.unl`?

- `.drawio` is **portable and reviewable** -- any contributor (or student) can
  open it without EVE-NG and see the intent: which devices, which links,
  which VLANs.
- `.unl` is the **exact EVE-NG state** -- importing it gives the student the
  same node positions, interface assignments, and link IDs the lab author
  used. No manual wiring errors.

Ship both. `.drawio` is the visual spec; `.unl` is the build; the tables above
are the machine-readable truth (derived from `baseline.yaml`).

## Importing the `.unl` into EVE-NG

1. Open EVE-NG web UI (`http://<eve-ng-ip>`, creds `admin/eve`)
2. In the left sidebar, navigate to the folder where you want the lab (e.g.
   create `switching/` if it doesn't exist)
3. Click **Add New Lab** -> (top right) **Import**
4. Upload `lab-00-vlans-and-trunking.unl`
5. Open the lab -> **More actions -> Start all nodes**
6. Wait ~90 seconds for nodes to finish booting (IOSvL2 and IOSv take time)

The automation scripts (`setup_lab.py`, `apply_solution.py`, inject scripts)
discover console ports via the REST API using the lab path
`switching/lab-00-vlans-and-trunking.unl`. If you import to a different
folder, pass `--lab-path <your/path.unl>` to each script.

## Exporting the `.unl` (maintainers only)

When you update the topology (added/removed nodes, changed links), re-export:

1. In EVE-NG: open the lab -> top toolbar -> **More actions -> Export**
2. Save the downloaded `.unl` file
3. Replace `topology/lab-00-vlans-and-trunking.unl` in this repo
4. Update `topology.drawio` to match (if layout changed)
5. Update `labs/switching/baseline.yaml` if node/link set changed, then run
   `python scripts/render_topology_readme.py labs/switching` to regenerate
   the tables above
6. Commit all changed files together -- they must stay in sync
