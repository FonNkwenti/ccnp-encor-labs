# Fault Injection — Network Assurance Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `ccnp-encor/network-assurance/lab-02-span-rspan.unl` running with all nodes started
- `netmiko` installed: `pip install netmiko`
- Initial configs loaded via `setup_lab.py` (or solution restored via `apply_solution.py`)

## Inject a Fault

```bash
cd labs/network-assurance/lab-02-span-rspan/scripts/fault-injection

python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Run `apply_solution.py` between tickets to reset to a known-good state.
