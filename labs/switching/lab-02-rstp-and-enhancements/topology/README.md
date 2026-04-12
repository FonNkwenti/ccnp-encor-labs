# Topology Assets -- Switching Lab 02

This directory holds every artifact a student needs to *reconstruct the topology
in EVE-NG* before running `setup_lab.py`.

## Files

| File | Purpose | Authoritative for |
|------|---------|-------------------|
| `topology.drawio` | Conceptual diagram (devices, port-channels, VLANs) | **Design** -- read this first |
| `lab-02-rstp-and-enhancements.unl` | EVE-NG native lab file | **EVE-NG build** -- import this |

> **If `lab-02-rstp-and-enhancements.unl` is missing** from this folder, the
> repo maintainer hasn't exported it yet. Build the topology manually using
> `topology.drawio` as your reference (it is identical to Lab 01's physical
> topology -- this lab layers RSTP and STP enhancements on top of the Lab 01
> EtherChannel backbone).

## Progressive lab -- same physical topology as Lab 01

Lab 02 reuses the Lab 01 wiring exactly. Only the device configs change:

- **RSTP** (`spanning-tree mode rapid-pvst`) replaces legacy PVST+
- **Root placement** is engineered per-VLAN via `spanning-tree vlan N priority`
- **STP enhancements** (PortFast, BPDU guard, root guard) are applied on the
  right edges/uplinks

If you already built the Lab 01 `.unl` in EVE-NG, you can clone it and apply
the Lab 02 `initial-configs/` instead of re-wiring from scratch.

## Why both a `.drawio` and a `.unl`?

- `.drawio` is **portable and reviewable** -- any contributor (or student)
  can open it without EVE-NG and see the intent.
- `.unl` is the **exact EVE-NG state** -- importing it gives the student
  the same node positions, interface assignments, and link IDs.

Ship both. `.drawio` is the spec; `.unl` is the build.

## Importing the `.unl` into EVE-NG

1. Open EVE-NG web UI (`http://<eve-ng-ip>`, creds `admin/eve`)
2. In the left sidebar, navigate to (or create) the `switching/` folder
3. Click **Add New Lab** -> (top right) **Import**
4. Upload `lab-02-rstp-and-enhancements.unl`
5. Open the lab -> **More actions -> Start all nodes**
6. Wait ~90 seconds for IOSvL2 and IOSv to finish booting

The automation scripts discover console ports via the REST API using the lab
path `switching/lab-02-rstp-and-enhancements.unl`. If you imported to a
different folder, pass `--lab-path <your/path.unl>` to each script.

## Exporting the `.unl` (maintainers only)

When you update the topology, re-export:

1. In EVE-NG: open the lab -> top toolbar -> **More actions -> Export**
2. Save the downloaded `.unl` file
3. Replace `topology/lab-02-rstp-and-enhancements.unl` in this repo
4. Update `topology.drawio` to match (if layout changed)
5. Commit both files together -- they must stay in sync

## Manual topology build (fallback)

If you're rebuilding manually from `topology.drawio`:

- **Nodes:** SW1, SW2, SW3 (all `iosvl2`), R1 (`iosv`), PC1 + PC2 (`vpc`)
- **Port-channels (from Lab 01, unchanged):**
  - **Po1 LACP:** SW1(Gi0/1, Gi0/2) <-> SW2(Gi0/1, Gi0/2)
  - **Po2 PAgP:** SW1(Gi0/3, Gi1/0) <-> SW3(Gi0/3, Gi1/0)
  - **Po3 Static:** SW2(Gi0/3, Gi1/0) <-> SW3(Gi0/1, Gi0/2)
- **Other links:**
  - R1:Gi0/0 <-> SW1:Gi1/1 (router-on-a-stick trunk)
  - PC1      <-> SW2:Gi1/1 (access VLAN 10)
  - PC2      <-> SW3:Gi1/1 (access VLAN 20)
