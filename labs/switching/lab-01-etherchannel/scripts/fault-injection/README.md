# Fault Injection — Switching Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)
- Update `EVE_NG_HOST` in each script to match your EVE-NG server IP

## Inject a Fault

```bash
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py
```

`apply_solution.py` removes all injected faults and returns all affected devices
to their known-good state. Run it between tickets to reset the lab.

## Scenario Reference

| Script | Target | Ticket |
|--------|--------|--------|
| `inject_scenario_01.py` | SW2 | Ticket 1 — workbook.md Section 9 |
| `inject_scenario_02.py` | SW3 | Ticket 2 — workbook.md Section 9 |
| `inject_scenario_03.py` | SW3 | Ticket 3 — workbook.md Section 9 |

## Recommended Workflow

```bash
# Reset to known-good, then inject one ticket at a time
python3 ../../setup_lab.py --host <eve-ng-ip>              # full reset (optional)
python3 scripts/fault-injection/inject_scenario_01.py      # Ticket 1
# ... diagnose and fix using show commands only ...
python3 scripts/fault-injection/apply_solution.py          # restore before next ticket

python3 scripts/fault-injection/inject_scenario_02.py      # Ticket 2
# ... diagnose and fix ...
python3 scripts/fault-injection/apply_solution.py

python3 scripts/fault-injection/inject_scenario_03.py      # Ticket 3
# ... diagnose and fix ...
python3 scripts/fault-injection/apply_solution.py
```
