# Lab 01 -- Multi-Area OSPFv2 + Dual-Stack

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Foundation
**Estimated time:** 75 minutes | **Blueprint:** 3.2.a, 3.2.b

Evolves the lab-00 single-area deployment into a three-area OSPFv2
topology and adds OSPFv3 for IPv6. R2 and R3 become ABRs; R4 is the
internal router for Area 1; R5 is the internal router for Area 2.
Troubleshoots three multi-area / dual-stack failure modes.

- **Area 0 backbone (broadcast):** R1, R2, R3 via unmanaged switch
- **Area 1 (point-to-point):** R2 <-> R4; PC1 LAN on R4 Gi0/2
- **Area 2 (point-to-point):** R3 <-> R5; PC2 LAN on R5 Gi0/1
- **Dual-stack:** every transit and LAN carries IPv4 and IPv6 with OSPFv3 area assignment mirroring OSPFv2

---

## Topology at a glance

```
                       ┌──────────┐
                       │    R1    │
                       │ (Area 0) │
                       └────┬─────┘
                            │ Gi0/0
                   ┌────────┴────────┐
                   │  SW-AREA0       │  10.0.123.0/24
                   │  (unmanaged)    │
                   └──┬──────────┬───┘
                Gi0/0 │          │ Gi0/0
             ┌────────┴──┐  ┌────┴────────┐
             │    R2     │  │    R3       │
             │ (ABR 0/1) │  │ (ABR 0/2)   │
             └────┬──────┘  └──┬──────────┘
            Gi0/1 │            │ Gi0/1
         (Area 1)              (Area 2)
          10.1.24/30            10.2.35/30
             ┌────┴──┐       ┌─┴────────┐
             │  R4   │       │   R5     │
             │(Area1)│       │ (Area 2) │
             └───┬───┘       └──┬───────┘
           Gi0/2 │              │ Gi0/1
             ┌───┴──┐       ┌──┴──────┐
             │ PC1  │       │  PC2    │
             └──────┘       └─────────┘
         192.168.1.0/24   192.168.2.0/24
```

Full device list, platforms, and links: see
[`topology/topology.drawio`](topology/topology.drawio) and
[`../baseline.yaml`](../baseline.yaml).

---

## Stages

### Stage 0 -- Prerequisites (your laptop)

```bash
pip install -r ../../../requirements.txt
```

Confirm:
- EVE-NG VM is running; you can reach `http://<eve-ng-ip>`
- You can ping `<eve-ng-ip>` from the laptop

### Stage 1 -- Build the topology in EVE-NG

1. Import `topology/lab-01-multi-area-ospfv2.unl` into EVE-NG (operator-exported)
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API and applies
`initial-configs/<name>.cfg` to each router. The initial state is the
lab-00 solution -- single-area OSPFv2 only. PC1/PC2 read their `.vpc`
files directly from EVE-NG on boot.

**Done when:** console prompt on each router shows the correct hostname
and `show ip ospf neighbor` lists the single-area neighbors from lab-00.

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Sections 1-3: multi-area OSPF concepts (ABRs, Type 3 LSAs, OSPFv3 address families), topology, cabling
- Section 4: base config review
- Section 5: core implementation tasks -- move R4 to Area 1 and R5 to Area 2, verify ABR status, enable OSPFv3 on every interface, verify dual-stack reachability
- Section 6: verification & analysis (`show ip ospf border-routers`, `show ip ospf database summary`, `show ospfv3 neighbor`)
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** R2 and R3 report "It is an area border router"; R1 has
`O IA` routes for every Area 1 and Area 2 prefix; PC1 can reach PC2 on
both IPv4 and IPv6.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different multi-area / dual-stack failure mode:

| Ticket | Target | Symptom | Fault class |
|--------|--------|---------|-------------|
| 1 | R4 | R2<->R4 adjacency stuck INIT/DOWN | OSPF area ID mismatch |
| 2 | R5 | IPv4 to PC2 works, IPv6 to PC2 fails | OSPFv3 missing on interface |
| 3 | R3 | PC2 unreachable from all routers | Missing OSPF network statement on ABR |

Workflow for each:

```bash
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # reset
python scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip> # break
# diagnose + fix using show commands only
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # restore
```

Scripts refuse to inject if the device isn't in the expected solution state
(pre-flight check). Bypass with `--skip-preflight` only if you know why.

See [`scripts/fault-injection/README.md`](scripts/fault-injection/README.md)
for inject / restore commands.

### Stage 5 -- Completion checklist

Section 10 of the workbook: tick each item before claiming the lab done.

---

## What's in this directory

| Path | Purpose |
|------|---------|
| `workbook.md` | Student-facing walkthrough (primary artifact) |
| `meta.yaml` | Machine-readable metadata |
| `topology/` | `.drawio` diagram (operator exports `.unl` into EVE-NG) |
| `initial-configs/` | Lab-00 solution state + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full multi-area OSPFv2 + OSPFv3 configs for each device |
| `setup_lab.py` | Push initial configs on first boot |
| `scripts/fault-injection/` | Inject + restore for troubleshooting scenarios |

Shared EVE-NG helpers live at
[`labs/common/tools/eve_ng.py`](../../common/tools/eve_ng.py).

---

## Exit codes (scripts)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | One or more devices failed (apply_solution / setup_lab only) |
| 2 | `--host` not supplied |
| 3 | EVE-NG API error (lab not running, auth failed, node not found) |
| 4 | Pre-flight check failed (inject target not in expected state) |
