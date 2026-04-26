# Lab 00 -- Single-Area OSPFv2 Fundamentals

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Foundation
**Estimated time:** 60 minutes | **Blueprint:** 3.2.a, 3.2.b

Builds a single-area OSPFv2 deployment across five IOSv routers: three
Area 0 backbone routers on a shared broadcast segment, two internal
routers reached through point-to-point links, and two PCs for end-to-end
reachability. Troubleshoots three classic OSPF failure modes.

- **Area 0 broadcast segment:** R1, R2, R3 via unmanaged switch
- **Point-to-point transits:** R2<->R4 (Area 1 in later labs), R3<->R5 (Area 2 in later labs)
- **LAN edges:** R4<->PC1, R5<->PC2

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
             │    R2     │  │    R3        │
             └────┬──────┘  └──┬──────────┘
            Gi0/1 │            │ Gi0/1
         10.1.24/30            10.2.35/30
             ┌────┴──┐       ┌─┴────────┐
             │  R4   │       │   R5     │
             └───┬───┘       └──┬───────┘
           Gi0/2 │              │ Gi0/1
             ┌───┴──┐       ┌──┴──────┐
             │ PC1  │       │  PC2    │
             └──────┘       └─────────┘
         192.168.1.0/24   192.168.2.0/24
```

Full device list, platforms, and links: see
[`topology/README.md`](topology/README.md) and
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

Follow [`topology/README.md`](topology/README.md):
1. Import `topology/lab-00-single-area-ospfv2.unl` into EVE-NG
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API and applies
`initial-configs/<name>.cfg` to each router. PC1/PC2 read their `.vpc`
files directly from EVE-NG on boot.

**Done when:** console prompt on each router shows the correct hostname.

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Sections 1-3: OSPF concepts (LSA types, adjacency, passive interfaces), topology, cabling
- Section 4: base config review
- Section 5: **8-task core implementation** -- enable OSPF, advertise networks,
  configure passive interfaces, adjust timers
- Section 6: verification & analysis (`show ip ospf neighbor`, `show ip ospf database`,
  `show ip ospf interface`)
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** all five routers see each other as FULL neighbors and
PC1 -> ping 192.168.2.10 succeeds.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different OSPF failure mode:

| Ticket | Target | Symptom | Fault class |
|--------|--------|---------|-------------|
| 1 | R4 | No OSPF neighbors | Hello/dead timer mismatch |
| 2 | R4 | PC1 unreachable from remote | Missing network statement |
| 3 | R3/R5 | Adjacency won't form | Passive on transit link |

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
for the fault matrix and exit codes.

### Stage 5 -- Completion checklist

Section 10 of the workbook: tick each item before claiming the lab done.

---

## What's in this directory

| Path | Purpose |
|------|---------|
| `workbook.md` | Student-facing walkthrough (primary artifact) |
| `meta.yaml` | Machine-readable metadata |
| `topology/` | `.drawio` diagram, EVE-NG `.unl`, import README |
| `initial-configs/` | Bare-minimum starting configs + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full working configs for each device |
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
