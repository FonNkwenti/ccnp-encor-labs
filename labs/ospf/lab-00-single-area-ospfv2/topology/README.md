# Topology Assets -- OSPF Lab 00

This directory holds every artifact a student needs to *reconstruct the topology
in EVE-NG* before running `setup_lab.py`.

## Files

| File | Purpose | Authoritative for |
|------|---------|-------------------|
| `topology.drawio` | Conceptual diagram (devices, areas, subnets, interfaces) | **Design** -- read this first |
| `lab-00-single-area-ospfv2.unl` | EVE-NG native lab file | **EVE-NG build** -- import this |

> **If `lab-00-single-area-ospfv2.unl` is missing** from this folder, the repo
> maintainer hasn't exported it yet. Build the topology manually using
> `topology.drawio` as your reference.

## Why both a `.drawio` and a `.unl`?

- `.drawio` is **portable and reviewable** -- any contributor (or student)
  can open it without EVE-NG and see the intent: which routers, which links,
  which subnets, where the shared Area 0 segment sits.
- `.unl` is the **exact EVE-NG state** -- importing it gives the student
  the same node positions, interface assignments, and link IDs the lab
  author used. No manual wiring errors.

Ship both. `.drawio` is the spec; `.unl` is the build.

## Importing the `.unl` into EVE-NG

1. Open EVE-NG web UI (`http://<eve-ng-ip>`, creds `admin/eve`)
2. In the left sidebar, navigate to the folder where you want the lab (e.g.
   create `ospf/` if it doesn't exist)
3. Click **Add New Lab** -> (top right) **Import**
4. Upload `lab-00-single-area-ospfv2.unl`
5. Open the lab -> **More actions -> Start all nodes**
6. Wait ~90 seconds for nodes to finish booting (IOSv takes time)

The automation scripts (`setup_lab.py`, `apply_solution.py`, inject scripts)
discover console ports via the REST API using the lab path
`ospf/lab-00-single-area-ospfv2.unl`. If you import to a different folder,
pass `--lab-path <your/path.unl>` to each script.

## Exporting the `.unl` (maintainers only)

When you update the topology (added/removed nodes, changed links), re-export:

1. In EVE-NG: open the lab -> top toolbar -> **More actions -> Export**
2. Save the downloaded `.unl` file
3. Replace `topology/lab-00-single-area-ospfv2.unl` in this repo
4. Update `topology.drawio` to match (if layout changed)
5. Commit both files together -- they must stay in sync

## Manual topology build (fallback)

If you're rebuilding manually from `topology.drawio`:

- **Nodes:** R1-R5 (all `iosv`), SW-AREA0 (unmanaged switch), PC1 + PC2 (`vpc`)
- **Shared segment (Area 0 broadcast):**
  - R1:Gi0/0 <-> SW-AREA0:port1
  - R2:Gi0/0 <-> SW-AREA0:port2
  - R3:Gi0/0 <-> SW-AREA0:port3
- **Point-to-point transits:**
  - R2:Gi0/1 <-> R4:Gi0/0 (10.1.24.0/30 -- timer-tuned)
  - R3:Gi0/1 <-> R5:Gi0/0 (10.2.35.0/30)
- **PC LAN segments (passive-interface on router side):**
  - R4:Gi0/2 <-> PC1 (192.168.1.0/24)
  - R5:Gi0/1 <-> PC2 (192.168.2.0/24)
- **Startup configs:** in the EVE-NG node dialog, set each node to load from
  `/opt/unetlab/labs/.../<node>.cfg` -- or let `setup_lab.py` push them after
  first boot (recommended).
