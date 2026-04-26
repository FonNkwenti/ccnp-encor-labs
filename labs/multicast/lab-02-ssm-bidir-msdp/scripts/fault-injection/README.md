# Fault Injection — Multicast Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- Lab is up in EVE-NG with initial-configs pushed (`python3 ../../setup_lab.py`)
- Devices have converged PIM neighbours, OSPF adjacency, MSDP peer, and SSM state

## Inject a Fault

```
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3
```

## Restore

```
python3 apply_solution.py --host <eve-ng-ip>
```
