# Fault Injection — Virtualization Lab 04

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab started with all nodes powered on
- Solution config loaded: `python3 apply_solution.py --host <eve-ng-ip>`
- Python 3 with the `netmiko` package installed
- EVE-NG server reachable on the network

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore to Known-Good

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Run the restore script between tickets to ensure each scenario starts from
a clean baseline.

## Notes

- All scripts require `--host` to be set to your EVE-NG server's IP address.
- Console ports are discovered automatically via the EVE-NG REST API.
- Each inject script performs a pre-flight check. If the pre-flight fails,
  run `apply_solution.py` first.
- Use `--skip-preflight` to bypass the pre-flight check if needed.
