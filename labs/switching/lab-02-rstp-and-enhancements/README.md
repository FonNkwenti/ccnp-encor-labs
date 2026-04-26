# Lab 02 -- Rapid STP and STP Enhancements

**Topic:** Switching | **Exam:** 350-401 | **Difficulty:** Intermediate
**Estimated time:** 90 minutes | **Blueprint:** 3.1.c

Builds on the Lab 01 EtherChannel backbone. Migrates the switched domain from
legacy PVST+ to Rapid PVST+ (802.1w), engineers per-VLAN root placement via
priority, and layers STP enhancements (PortFast, BPDU guard, root guard) on
the right edges and uplinks. Three troubleshooting tickets exercise root-guard
violations, STP mode mismatches, and port-cost-driven suboptimal paths.

- **RSTP** on SW1/SW2/SW3
- **Root placement:** SW1 primary for VLAN 10/30/99; SW2 primary for VLAN 20
- **Root guard** on SW1 downstream port-channels
- **PortFast + BPDU guard** on SW2:Gi1/1 (PC1) and SW3:Gi1/1 (PC2)

---

## Topology at a glance

Physical topology is identical to Lab 01 -- this lab layers STP config on top.

```
                    +------+
                    |  R1  |  ROAS trunk
                    +--+---+
                       | Gi0/0 -> SW1:Gi1/1
                       |
    Po1 (LACP 2-link)  v  Po2 (PAgP 2-link)
+-----+ =============+------+============= +-----+
| SW2 |              |  SW1 |              | SW3 |
+-----+              +------+              +-----+
   ||                                         ||
   ||              Po3 (Static 2-link)        ||
   ++=========================================++
   |                                          |
  PC1 (VLAN 10)                          PC2 (VLAN 20)
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
- Lab 01 concepts (port-channel bring-up, trunk verification) are familiar

### Stage 1 -- Build the topology in EVE-NG

Follow [`topology/README.md`](topology/README.md):
1. Import `topology/lab-02-rstp-and-enhancements.unl` into EVE-NG (or clone
   an existing Lab 01 lab -- the physical topology is identical)
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSvL2/IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The `initial-configs/` are the Lab 01 solution configs -- port-channels,
trunks, and inter-VLAN routing are already in place. RSTP + enhancements are
what you'll add in the workbook.

**Done when:** `show etherchannel summary` on SW1 shows all three Po's `SU`.

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Section 1-3: Rapid PVST+ vs PVST+, port roles/states, topology review
- Section 4: base config review (Lab 01 carried forward)
- Section 5: **8-task core implementation** -- switch to `rapid-pvst`,
  engineer per-VLAN root placement, verify port roles, apply root guard,
  PortFast + BPDU guard, verify edge-flap behavior, confirm STP over
  EtherChannel, end-to-end ping test
- Section 6: verification & analysis (`show spanning-tree`,
  `show spanning-tree inconsistentports`, detail dumps)
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** VLAN 10/30/99 root = SW1, VLAN 20 root = SW2,
`PC1 -> ping 192.168.20.10` succeeds, and PC-port edge flaps converge
in ~1-2 s.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different STP failure mode:

| Ticket | Target | Symptom | Fault class |
|--------|--------|---------|-------------|
| 1 | SW1 Po1 | Po1 in `root-inconsistent` for VLAN 10; VLAN 10 disconnected | Root guard violation |
| 2 | SW3 | Edge flaps converge in ~30 s instead of ~1-2 s | STP mode mismatch |
| 3 | SW3 VLAN 20 | VLAN 20 root port = Po2 (via SW1), not Po3 direct | Port-cost manipulation |

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
| `initial-configs/` | Lab 01 solution configs + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full working configs for each device (Lab 01 + RSTP) |
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
