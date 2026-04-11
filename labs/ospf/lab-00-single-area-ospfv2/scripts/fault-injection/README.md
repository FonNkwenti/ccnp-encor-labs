# Fault Injection -- OSPF Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip>   # Scenario 01 -- Target: R4
python3 inject_scenario_02.py --host <eve-ng-ip>   # Scenario 02 -- Target: R4
python3 inject_scenario_03.py --host <eve-ng-ip>   # Scenario 03 -- Target: R3
```

## Restore All Devices

```bash
python3 apply_solution.py --host <eve-ng-ip>
```

Pushes the full solution configs from `../../solutions/` to all 5 routers
(R1-R5), removing any injected faults and restoring the lab to working state.
