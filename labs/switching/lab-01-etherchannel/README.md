# Lab 01 -- Static and Dynamic EtherChannels

**Topic:** Switching | **Exam:** 350-401 | **Difficulty:** Foundation -> Intermediate
**Estimated time:** 75 minutes | **Blueprint:** 3.1.b

Builds three port-channels between SW1/SW2/SW3 -- one per protocol -- then
uses them as the backbone for inter-VLAN routing and troubleshoots three
EtherChannel-specific failure modes.

- **Po1** LACP (SW1 active <-> SW2 passive)
- **Po2** PAgP (SW1 desirable <-> SW3 auto)
- **Po3** Static "mode on" (SW2 <-> SW3)

---

## Topology at a glance

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
- You can ping `<eve-ng-ip>` from the laptop

### Stage 1 -- Build the topology in EVE-NG

Follow [`topology/README.md`](topology/README.md):
1. Import `topology/lab-01-etherchannel.unl` into EVE-NG
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSvL2/IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API and applies
`initial-configs/<name>.cfg` to each node. PC1/PC2 read their `.vpc` files
directly from EVE-NG on boot.

**Done when:** console prompt on each device shows the correct hostname.

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Section 1-3: EtherChannel concepts (LACP, PAgP, static), topology, cabling
- Section 4: base config review
- Section 5: **6-task core implementation** -- build all three port-channels,
  configure load balancing, verify trunks
- Section 6: verification & analysis (`show etherchannel summary`,
  `show lacp neighbor`, `show pagp neighbor`)
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** all three port-channels show `SU` in
`show etherchannel summary` and `PC1 -> ping 192.168.20.10` succeeds.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets -- each a different EtherChannel failure mode:

| Ticket | Bundle | Symptom | Fault class |
|--------|--------|---------|-------------|
| 1 | Po1 (LACP) | One member in `I` state | Trunk parameter mismatch |
| 2 | Po2 (PAgP/LACP) | Bundle down | Protocol mismatch |
| 3 | Po3 (Static/LACP) | Bundle down | Mode mismatch |

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
| 1 | One or more devices failed (apply_solution only) |
| 2 | `--host` not supplied |
| 3 | EVE-NG API error (lab not running, auth failed, node not found) |
| 4 | Pre-flight check failed (inject target not in expected state) |
