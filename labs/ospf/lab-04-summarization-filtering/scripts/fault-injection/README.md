# Fault Injection — OSPF Lab 04

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `ospf/lab-04-summarization-filtering.unl` is running with all nodes started
- Lab is in the solution state: `python3 apply_solution.py --host <eve-ng-ip>`
- Python dependencies installed: `pip install netmiko`
- EVE-NG server reachable at your configured IP (default: 192.168.242.128)

## Inject a Fault

Run from the `scripts/fault-injection/` directory:

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
python3 inject_scenario_04.py --host <eve-ng-ip>   # Ticket 4
python3 inject_scenario_05.py --host <eve-ng-ip>   # Ticket 5
```

## Restore

```
python3 apply_solution.py --host <eve-ng-ip>
```

Restores all six routers (R1-R6) to the lab-04 solution state.

## Notes

- Each inject script includes a pre-flight check. If the check fails, the lab is
  not in the expected solution state — run `apply_solution.py` first.
- Use `--skip-preflight` to bypass the pre-flight check if needed.
- Only inject one fault at a time. Run `apply_solution.py` between scenarios.
