# Lab 02 -- OSPF Network Types + DR/BDR Manipulation

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Intermediate
**Estimated time:** 75 minutes | **Blueprint:** 3.2.b

Evolves the lab-01 multi-area topology by tuning how OSPF runs on the
wire: forcing DR/BDR identity on the Area 0 broadcast segment via OSPF
priority, and converting the Area 1 and Area 2 transit /30 links to OSPF
network type point-to-point. Addressing, areas, and OSPFv3 configuration
are unchanged -- the lesson is purely about network types, election, and
LSDB shape.

- **Area 0 (broadcast, tuned):** R1 prio 255 (DR), R2 prio 200 (BDR),
  R3 prio 0 (ineligible -- DROTHER forever)
- **Area 1 (point-to-point):** R2 Gi0/1 <-> R4 Gi0/0 converted to
  `ip ospf network point-to-point`; Type 2 LSA removed
- **Area 2 (point-to-point):** R3 Gi0/1 <-> R5 Gi0/0 converted to
  `ip ospf network point-to-point`; Type 2 LSA removed
- **Dual-stack:** OSPFv3 for IPv6 from lab-01 persists; the changes in
  this lab apply only to OSPFv2

---

## Topology at a glance

```
                       ┌──────────┐
                       │    R1    │
                       │  prio    │
                       │  255 DR  │
                       └────┬─────┘
                            │ Gi0/0
                   ┌────────┴────────┐
                   │  SW-AREA0       │  10.0.123.0/24
                   │  (broadcast)    │
                   └──┬──────────┬───┘
                Gi0/0 │          │ Gi0/0
         ┌────────────┴──┐  ┌────┴────────────┐
         │       R2      │  │      R3         │
         │   prio 200    │  │    prio 0       │
         │     BDR       │  │   DROTHER       │
         └──────┬────────┘  └──┬──────────────┘
           Gi0/1│               │Gi0/1
           (p2p, Area 1)        │(p2p, Area 2)
           10.1.24/30           │10.2.35/30
            ┌───┴───┐        ┌──┴────────┐
            │  R4   │        │    R5     │
            └───┬───┘        └───┬───────┘
          Gi0/2 │                │ Gi0/1
            ┌───┴──┐          ┌──┴──────┐
            │ PC1  │          │   PC2   │
            └──────┘          └─────────┘
         192.168.1.0/24    192.168.2.0/24
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

1. Import `topology/lab-02-network-types.unl` into EVE-NG (operator-exported)
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API and applies
`initial-configs/<name>.cfg` to each router. The initial state is the
lab-01 solution -- full multi-area OSPFv2 + OSPFv3 dual-stack, no
priority tuning, all Ethernet interfaces at default broadcast.
PC1/PC2 read their `.vpc` files directly from EVE-NG on boot.

**Done when:** each router shows the correct hostname and `show ip ospf
neighbor` on R1 lists both R2 and R3 (DR/BDR chosen by router-ID).

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Sections 1-3: network-type theory (broadcast vs p2p, DR/BDR, priority,
  Type 2 LSAs), topology, cabling
- Section 4: base config review (= lab-01 solution)
- Section 5: five tasks -- observe the default, force R1=DR R2=BDR,
  exclude R3 with priority 0, convert both transits to p2p, verify LSDB
- Section 6: verification and analysis (`show ip ospf interface`,
  `show ip ospf neighbor`, `show ip ospf database network`,
  `show ip ospf database router`)
- Section 7: cheatsheet (priority, network-type, re-election, neighbor
  states, failure causes)
- Section 8: solutions (click-to-reveal)

**Done when:** R1 reports `State DR, Priority 255` on Gi0/0; R2 reports
`State BDR, Priority 200`; R3 reports `State DROTHER, Priority 0`; both
transit links show `Network Type POINT_TO_POINT`; `show ip ospf database
network` on R1 lists exactly one Type 2 LSA; PC1 can still ping PC2 on
both IPv4 and IPv6.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different network-type or DR/BDR failure mode:

| Ticket | Target | Symptom                                               | Fault class                              |
|--------|--------|-------------------------------------------------------|------------------------------------------|
| 1      | R4     | Adjacency appears FULL but Area 1 routes flap         | Network-type mismatch on transit         |
| 2      | R3     | R3 advertises Pri=255 despite design calling for 0    | DR/BDR priority misconfiguration         |
| 3      | R1     | R1 lists only one neighbor on the Area 0 segment      | Wrong network type on shared segment     |

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
| `initial-configs/` | Lab-01 solution state + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full lab-02 configs with priority + p2p network-type for each device |
| `setup_lab.py` | Push initial configs on first boot |
| `scripts/fault-injection/` | Inject + restore for troubleshooting scenarios |

Shared EVE-NG helpers live at
[`labs/common/tools/eve_ng.py`](../../common/tools/eve_ng.py).

---

## Exit codes (scripts)

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | One or more devices failed (apply_solution / setup_lab only) |
| 2    | `--host` not supplied |
| 3    | EVE-NG API error (lab not running, auth failed, node not found) |
| 4    | Pre-flight check failed (inject target not in expected state) |
