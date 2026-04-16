# Fault Injection -- OSPF Lab 00: Single-Area OSPFv2 Fundamentals

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `ospf/lab-00-single-area-ospfv2.unl` imported and **STARTED**
- EVE-NG REST credentials are admin/eve (the default)
- `pip install -r requirements.txt` (installs `netmiko` + `requests`)

Console ports are discovered automatically via the EVE-NG REST API -- no need
to edit port numbers in any script.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject one scenario at a time
python3 inject_scenario_01.py --host <eve-ng-ip>   # Ticket 1 -- R4<->R2 hello timer mismatch
python3 inject_scenario_02.py --host <eve-ng-ip>   # Ticket 2 -- R4 missing PC1 network
python3 inject_scenario_03.py --host <eve-ng-ip>   # Ticket 3 -- R3 passive on transit to R5

# 3. Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>
```

## Arguments

All scripts accept the same base arguments:

- `--host <ip>` (required): EVE-NG server IP
- `--lab-path <path>`: Path of the .unl on EVE-NG (default:
  `ospf/lab-00-single-area-ospfv2.unl`). Override if you imported the lab
  to a different folder.

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
| 01 | R4 Gi0/0 | `ip address 10.1.24.2` present, `ip ospf hello-interval 15` absent | Add `ip ospf hello-interval 15` -- timer mismatch with R2 |
| 02 | R4 `router ospf 1` | `network 192.168.1.0 0.0.0.255 area 0` present | Remove that network statement -- PC1 LAN not advertised |
| 03 | R3 `router ospf 1` | `network 10.2.35.0 0.0.0.3 area 0` present, `passive-interface Gi0/1` absent | Add `passive-interface Gi0/1` -- R3<->R5 Hellos suppressed |

## Exit codes

- `0` success
- `1` at least one device failed to restore (apply_solution.py only)
- `2` missing `--host`
- `3` EVE-NG API error (lab not running, auth failed, node not found)
- `4` pre-flight check failed (target not in expected state)
