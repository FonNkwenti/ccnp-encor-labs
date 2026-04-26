# Fault Injection — IP Services Lab 05

The lab loads with all 6 faults pre-embedded via `setup_lab.py`. Use
these scripts to re-inject individual faults after applying the solution,
or to inject all faults at once.

Work through the tickets in `workbook.md` Section 5 before looking at fixes.

## Prerequisites

- Lab topology running in EVE-NG
- Python dependencies: `pip install netmiko`

## Re-inject All Faults (reset to broken state)

```
python3 inject_all.py
```

## Inject Individual Faults

```
python3 inject_scenario_01.py   # R1: NAT inside/outside reversed
python3 inject_scenario_02.py   # R1: NAT-PAT ACL wrong subnet
python3 inject_scenario_03.py   # R1: VRRP track decrement=5
python3 inject_scenario_04.py   # R2: NTP key-string mismatch
python3 inject_scenario_05.py   # R2: VRRPv3 IPv6 AF missing
python3 inject_scenario_06.py   # R3: OSPF passive on Gi0/0
```

## Restore

```
python3 apply_solution.py
```
