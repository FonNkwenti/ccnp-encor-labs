# Fault Injection — Automation Lab 01

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Python 3.x installed
- `netmiko` and `requests` libraries installed (`pip install netmiko requests`)

## Inject a Fault

Pass `--host` with your EVE-NG server IP:

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
python3 apply_solution.py --host <eve-ng-ip> --reset   # erase configs first (clean slate)
```

## Available Scenarios

| Scenario | Target | Inject Command |
|----------|--------|----------------|
| 01 | R1 | `python3 inject_scenario_01.py --host <eve-ng-ip>` |
| 02 | R1 | `python3 inject_scenario_02.py --host <eve-ng-ip>` |
| 03 | R1 | `python3 inject_scenario_03.py --host <eve-ng-ip>` |

## Notes

- Each inject script runs a pre-flight check before injecting. If the check fails,
  run `apply_solution.py` first to restore the known-good state.
- Use `--skip-preflight` to bypass the pre-flight check (not recommended).
- All scripts are idempotent — running the same script twice is safe.
