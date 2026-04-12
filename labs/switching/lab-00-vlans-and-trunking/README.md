# Lab 00 -- VLANs and Trunk Negotiation

**Topic:** Switching | **Exam:** 350-401 | **Difficulty:** Foundation
**Estimated time:** 60 minutes | **Blueprint:** 3.1, 3.1.a

A progressive lab covering VLAN creation, 802.1Q trunking, DTP negotiation,
native VLAN handling, and router-on-a-stick inter-VLAN routing, followed by
three troubleshooting tickets.

---

## Topology at a glance

```
+-----+        +-----+        +-----+
| SW1 |--------| SW2 |--------| SW3 |
+--+--+  trunk +-----+  trunk +--+--+
   |                              |
   | trunk                        |
   |                              |
  +---+                          +---+
  |R1 |                          |PC2| (VLAN 20)
  +---+                          +---+
   ROAS
     +--+ PC1 (VLAN 10)
```

Full device list, platforms, and links: see
[`topology/README.md`](topology/README.md) and
[`../baseline.yaml`](../baseline.yaml).

---

## Stages

Work through in order. Each stage has a clear done-condition.

### Stage 0 -- Prerequisites (your laptop)

```bash
pip install -r ../../../requirements.txt
```

Confirm:
- EVE-NG VM is running; you can reach `http://<eve-ng-ip>`
- You can ping `<eve-ng-ip>` from the laptop

### Stage 1 -- Build the topology in EVE-NG

Follow [`topology/README.md`](topology/README.md):
1. Import `topology/lab-00-vlans-and-trunking.unl` into EVE-NG
2. Start all nodes (**More actions -> Start all nodes**)
3. Wait ~90 seconds for IOSvL2/IOSv to finish booting

**Done when:** every node shows a green icon in the EVE-NG web UI.

### Stage 2 -- Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

The script discovers console ports via the REST API, connects each node via
telnet, and applies `initial-configs/<name>.cfg`.

**Done when:** console prompt on each device shows the correct hostname
(`SW1#`, `SW2#`, `SW3#`, `R1#`).

### Stage 3 -- Work the workbook (Sections 1-8)

Open [`workbook.md`](workbook.md) and progress through:
- Section 1-3: concepts, topology, hardware reference
- Section 4: base config review
- Section 5: **the 8-task lab challenge** -- build VLANs, trunks, ROAS
- Section 6: verification
- Section 7: command cheatsheet
- Section 8: solutions (click-to-reveal)

**Done when:** `PC1> ping 192.168.20.10` (from PC1 to PC2) succeeds.

### Stage 4 -- Troubleshooting (optional, Section 9)

Three tickets simulate realistic faults. Workflow for each:

```bash
# from the lab dir
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # reset
python scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip> # break
# diagnose + fix using show commands only
python scripts/fault-injection/apply_solution.py --host <eve-ng-ip>     # restore
# move on to ticket 2, 3
```

Scripts refuse to inject if the device isn't in the expected solution state
(pre-flight check). Bypass with `--skip-preflight` only if you know why.

See [`scripts/fault-injection/README.md`](scripts/fault-injection/README.md)
for full details and exit codes.

### Stage 5 -- Completion checklist

Section 10 of the workbook: tick each item before claiming the lab done.
Any unchecked item means a concept or command hasn't been exercised.

---

## What's in this directory

| Path | Purpose |
|------|---------|
| `workbook.md` | Student-facing walkthrough (primary artifact) |
| `meta.yaml` | Machine-readable metadata |
| `topology/` | `.drawio` diagram, EVE-NG `.unl`, import README |
| `initial-configs/` | Bare-minimum starting configs (hostname, line settings) + `PC1.vpc`, `PC2.vpc` |
| `solutions/` | Full working configs for each device |
| `setup_lab.py` | Push initial configs on first boot |
| `scripts/fault-injection/` | Inject + restore for troubleshooting scenarios |

Shared EVE-NG helpers live at
[`labs/common/tools/eve_ng.py`](../../common/tools/eve_ng.py) (REST port
discovery, netmiko wrapper, host validation).

---

## Exit codes (scripts)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | One or more devices failed (apply_solution only) |
| 2 | `--host` not supplied |
| 3 | EVE-NG API error (lab not running, auth failed, node not found) |
| 4 | Pre-flight check failed (inject target not in expected state) |
