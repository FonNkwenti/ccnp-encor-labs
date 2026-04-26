# Fault Injection — Automation Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab running with all nodes started (R1, R2, R3)
- Lab in the solution state (run `apply_solution.py` first)
- Python 3.8+ with `netmiko` installed: `pip install netmiko`

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore to Solution State

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Use `--reset` for a guaranteed clean slate (erases device configs before pushing):

```bash
python3 apply_solution.py --host <eve-ng-ip> --reset
```

## Notes

- Each inject script runs a pre-flight check to confirm the lab is in the solution
  state before injecting. Use `--skip-preflight` to bypass if needed.
- Scripts are idempotent where possible — safe to run multiple times.
- All three tickets target R3 (the EEM host).
- See `workbook.md` Section 9 for the troubleshooting challenge for each ticket.
