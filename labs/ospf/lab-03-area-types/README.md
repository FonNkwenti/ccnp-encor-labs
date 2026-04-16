# Lab 03 -- OSPF Area Types: Stub, Totally Stubby, and NSSA

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Intermediate
**Estimated time:** 90 minutes | **Blueprint:** 3.2.a

Evolves the lab-02 multi-area OSPFv2 + OSPFv3 topology by introducing area-type
specialization. Area 1 becomes Totally Stubby (suppressing all Type 3–7 LSAs,
injecting only a default route). Area 2 becomes NSSA so that R5 can redistribute
external prefixes as Type 7 LSAs while keeping external routes out of the LSDB on
internal routers. A new router R6 is added to Area 1, requiring the student to
bring it into the OSPF domain and apply the correct stub configuration.

- **Area 0 (backbone):** R1 DR (prio 255), R2 BDR (prio 200), R3 DROTHER (prio 0)
- **Area 1 (Totally Stubby):** R2 ABR uses `area 1 stub no-summary`; R4 and R6
  use `area 1 stub` only (internal routers do NOT use `no-summary`)
- **Area 2 (NSSA):** R3 ABR uses `area 2 nssa`; R5 ASBR redistributes Loopback1
  and Loopback2 as Type 7 LSAs via scoped route-map; R3 translates Type 7 → Type 5
- **Dual-stack:** OSPFv3 address-family syntax tracks all OSPFv2 area-type changes
- **New device:** R6 connects to R2 Gi0/2 and R4 Gi0/1 in Area 1

---

## Topology at a glance

```
              ┌──────────────────────────────────────────┐
              │              Area 0 (Backbone)           │
              │   ┌──────────┐         ┌──────────┐     │
              │   │    R2    │  SW-AREA0│    R3    │     │
              │   │ prio 200 ├──────────┤  prio 0  │     │
              │   │   BDR    │  multi-  │ DROTHER  │     │
              │   └──┬───────┘  access  └────┬─────┘     │
              │      │     ┌──────────┐      │           │
              │      │     │    R1    │      │           │
              │      │     │ prio 255 │      │           │
              │      │     │    DR    │      │           │
              │      │     └──────────┘      │           │
              └──────┼──────────────────────┼───────────┘
         Area 1      │ Gi0/1                │ Gi0/1       Area 2
      (Totally Stubby)│ p2p 10.1.24.0/30   │ p2p 10.2.35.0/30  (NSSA)
              ┌───────┴───────┐      ┌──────┴──────────┐
              │      R4       │      │       R5        │
              │  area 1 stub  │      │   area 2 nssa   │
              │ (internal)    │      │ ASBR: redist    │
              └──┬──────┬─────┘      │ Lo1+Lo2 as T7  │
            Gi0/2│ Gi0/1│            └──┬──────────────┘
                 │      │         Gi0/1 │
              ┌──┴──────┴─────┐   ┌────┴──────┐
              │      R6       │   │   PC2     │
              │  area 1 stub  │   └───────────┘
              │ (new, lab-03) │  192.168.2.0/24
              └───────────────┘
          PC1: 192.168.1.0/24
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

1. Import `topology/lab-03-area-types.unl` into EVE-NG (operator-exported)
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python3 setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API and applies
`initial-configs/<name>.cfg` to each router. R1–R5 start in the lab-02
solution state (full multi-area OSPFv2 + OSPFv3, DR/BDR tuned, transit
links point-to-point). R6 starts with IP addressing only -- no OSPF
configured. PC1/PC2 read their `.vpc` files directly from EVE-NG on boot.

**Done when:** `show ip ospf neighbor` on R1 shows R2 and R3 in FULL state;
R6 shows no OSPF output (correct -- student configures it).

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Sections 1-3: area-type theory (LSA types 1-7, stub variants, NSSA, Type 7
  translation), topology, cabling
- Section 4: base config review (= lab-02 solution + R6 base IP)
- Section 5: three tasks -- configure Totally Stubby Area 1, configure NSSA
  Area 2 with scoped ASBR redistribution, bring R6 into the OSPF domain
- Section 6: verification (`show ip ospf database`, `show ip route ospf`,
  `show ip ospf neighbor` on R6, Type 7 and Type 5 LSA inspection)
- Section 7: cheatsheet (area-type commands, LSA filtering, NSSA, verification)
- Section 8: solutions (click-to-reveal)

**Done when:** R4 and R6 receive only a default route (`O*IA`) in their
routing tables (no Type 3 summaries). R5's Loopback1/2 appear as `O E2` on
R1 but not in R4 or R6. R6 shows FULL adjacency with R2 and R4.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different area-type failure mode:

| Ticket | Target | Symptom                                                | Fault class                          |
|--------|--------|--------------------------------------------------------|--------------------------------------|
| 1      | R6     | R6 has no OSPF neighbors                               | Stub area E-bit mismatch             |
| 2      | R3     | External ISP routes invisible across the network       | Missing NSSA on ABR                  |
| 3      | R5     | Duplicate OSPF routes for Area 2 transit subnets       | Unscoped redistribution              |

Workflow for each:

```bash
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>           # reset
python3 scripts/fault-injection/inject_scenario_NN.py --host <eve-ng-ip>       # break
# diagnose + fix using show commands only
python3 scripts/fault-injection/apply_solution.py --host <eve-ng-ip>           # restore
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
| `initial-configs/` | Lab-02 solution state for R1-R5 + base IP for R6 + PC `.vpc` files |
| `solutions/` | Full lab-03 configs with area types, NSSA redistribution, and R6 OSPF |
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
