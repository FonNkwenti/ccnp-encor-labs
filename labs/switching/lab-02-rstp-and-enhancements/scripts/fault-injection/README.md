# Fault Injection -- Switching Lab 02: Rapid STP and STP Enhancements

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `switching/lab-02-rstp-and-enhancements.unl` imported and **STARTED**
- EVE-NG REST credentials are admin/eve (the default)
- `pip install -r requirements.txt` (installs `netmiko` + `requests`)

Console ports are discovered automatically via the EVE-NG REST API -- no need
to edit port numbers in any script.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject one scenario at a time
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 -- Root guard trips on SW1 Po1
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 -- STP mode mismatch (SW3 on PVST+)
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 -- Suboptimal VLAN 20 path via SW1

# 3. Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>
```

## Arguments

All scripts accept the same base arguments:

- `--host <ip>` (required): EVE-NG server IP
- `--lab-path <path>`: Path of the .unl on EVE-NG (default:
  `switching/lab-02-rstp-and-enhancements.unl`). Override if you imported
  the lab to a different folder.

Inject scripts additionally accept:

- `--skip-preflight`: Bypass the sanity check that confirms the target is
  currently in the expected solution state. Use only if you know what you're
  doing.

## Why the pre-flight check?

Injecting a fault on top of a device that's already broken (or not yet
configured) usually produces confusing symptoms. Each inject script first
reads a target `show running-config ...` and verifies the expected
solution-state config is present (and the fault is not already injected). If
not, it stops with a clear error pointing you at `apply_solution.py`.

## Fault matrix

| Scenario | Target | Pre-flight check | Fault |
|----------|--------|------------------|-------|
| 01 | SW2 | `spanning-tree vlan 20 priority 4096` present, `spanning-tree vlan 10 priority 0` absent | Add `spanning-tree vlan 10 priority 0` -- superior BPDU trips SW1's root guard on Po1 |
| 02 | SW3 | `spanning-tree mode rapid-pvst` present | Switch to `spanning-tree mode pvst` -- legacy mode breaks fast convergence |
| 03 | SW2 Po3 | description `STATIC_PO3_TO_SW3` present, no `spanning-tree vlan 20 cost` override | Add `spanning-tree vlan 20 cost 200000000` on Po3 -- SW3 shifts its VLAN 20 root port to Po2 (via SW1) |

## Exit codes

- `0` success
- `1` at least one device failed to restore (apply_solution.py only)
- `2` missing `--host`
- `3` EVE-NG API error (lab not running, auth failed, node not found)
- `4` pre-flight check failed (target not in expected state)
