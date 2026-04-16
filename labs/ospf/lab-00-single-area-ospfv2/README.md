# Lab 00 -- Single-Area OSPFv2 Fundamentals

**Topic:** OSPF | **Exam:** 350-401 | **Difficulty:** Foundation
**Estimated time:** 60 minutes | **Blueprint:** 3.2.a / 3.2.b

Stands up one OSPFv2 process across five IOSv routers -- all in Area 0 --
to introduce the neighbor state machine, the LSDB, DR/BDR election on a
shared segment, passive-interfaces on LAN edges, and per-interface
hello/dead timer tuning.

- **Shared segment (R1, R2, R3):** 10.0.123.0/24 via SW-AREA0 -- DR/BDR election
- **Transit /30 with tuned timers:** R2 Gi0/1 <-> R4 Gi0/0 (hello=5, dead=20)
- **Standard transit /30:** R3 Gi0/1 <-> R5 Gi0/0
- **PC LANs (passive):** R4 Gi0/2 = 192.168.1.0/24, R5 Gi0/1 = 192.168.2.0/24

---

## Topology at a glance

```
                    +----+
                    | R1 |
                    +-+--+
                      | Gi0/0  10.0.123.1/24
                      |
               +------+------+
               |  SW-AREA0   |  10.0.123.0/24 (broadcast)
               +-+---------+-+
                 |         |
      10.0.123.2 |         | 10.0.123.3
              +--+--+   +--+--+
              | R2  |   | R3  |
              +--+--+   +--+--+
                 |         |
    10.1.24.0/30 |         | 10.2.35.0/30
      (hello=5)  |         |
              +--+--+   +--+--+
              | R4  |   | R5  |
              +--+--+   +--+--+
                 |         |
    192.168.1.0  |         |  192.168.2.0
              +--+--+   +--+--+
              | PC1 |   | PC2 |
              +-----+   +-----+
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
1. Import `topology/lab-00-single-area-ospfv2.unl` into EVE-NG (if the maintainer
   has exported it), or rebuild manually from `topology.drawio`
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

**Done when:** every router console prompt shows the correct hostname.

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Section 1-3: OSPF concepts (process/router-ID, network statements, states, DR/BDR, LSAs), topology, cabling
- Section 4: base config review
- Section 5: **8-task core implementation** -- enable OSPF, advertise networks,
  passive-interfaces, tune timers, verify neighbors / LSDB / routes / end-to-end
- Section 6: verification & analysis (`show ip ospf neighbor`,
  `show ip ospf interface`, `show ip ospf database`, `show ip route ospf`)
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** every router has FULL neighbors on its adjacent OSPF interfaces
and `PC1 -> ping 192.168.2.10` succeeds.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different OSPF failure mode:

| Ticket | Symptom | Fault class |
|--------|---------|-------------|
| 1 | R4 can ping 2.2.2.2 but not 1.1.1.1 | Missing network statement |
| 2 | R2 and R4 never reach FULL | Hello/dead timer mismatch |
| 3 | PC1 cannot reach PC2 despite FULL neighbors | Missing network statement (LAN) |

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
for the operational reference (prerequisites, arguments, exit codes).

### Stage 5 -- Completion checklist

Section 10 of the workbook: tick each item before claiming the lab done.

---

## What's in this directory

| Path | Purpose |
|------|---------|
| `workbook.md` | Student-facing walkthrough (primary artifact) |
| `meta.yaml` | Machine-readable metadata |
| `topology/` | `.drawio` diagram, EVE-NG `.unl` (if exported), import README |
| `initial-configs/` | Bare-minimum starting configs + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full working configs for each router |
| `setup_lab.py` | Push initial configs on first boot |
| `scripts/fault-injection/` | Inject + restore for troubleshooting scenarios |

Shared EVE-NG helpers live at
[`labs/common/tools/eve_ng.py`](../../common/tools/eve_ng.py).

---

## Exit codes (scripts)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | One or more devices failed (apply_solution only) |
| 2 | `--host` not supplied |
| 3 | EVE-NG API error (lab not running, auth failed, node not found) |
| 4 | Pre-flight check failed (inject target not in expected state) |
