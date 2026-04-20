# Fault Injection -- Automation Lab 04: API Capstone Config

Each script injects one fault.  Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `automation/lab-04-capstone-config.unl` imported and **STARTED**
- All nodes (R1, R2, R3) powered on
- `pip install netmiko` (version 4.x or later)
- Console telnet ports noted from the EVE-NG web UI

## Setup

Before running any script, open the EVE-NG web UI, start the lab, and
record the telnet port assigned to each node.  Update the `CONSOLE_PORT`
constant (inject scripts) or `CONSOLE_PORTS` dict (apply_solution.py) in
each file.  Also update `EVE_NG_HOST` to the real IP of your EVE-NG server.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py --host <eve-ng-ip>

# 2. Inject one scenario at a time
python3 inject_scenario_01.py --host <eve-ng-ip> --port <r1-console-port>
python3 inject_scenario_02.py --host <eve-ng-ip> --port <r2-console-port>
python3 inject_scenario_03.py --host <eve-ng-ip> --port <r3-console-port>

# 3. Between tickets, restore solution
python3 apply_solution.py --host <eve-ng-ip>

# 4. Use --reset for a guaranteed clean slate before injecting
python3 apply_solution.py --host <eve-ng-ip> --reset
```

## Available Scenarios

### Scenario 01
- **Target**: R1
- **Run**: `python3 inject_scenario_01.py --host <eve-ng-ip> --port <r1-console-port>`

### Scenario 02
- **Target**: R2
- **Run**: `python3 inject_scenario_02.py --host <eve-ng-ip> --port <r2-console-port>`

### Scenario 03
- **Target**: R3
- **Run**: `python3 inject_scenario_03.py --host <eve-ng-ip> --port <r3-console-port>`

## Arguments

All inject scripts accept:

- `--host <ip>`: EVE-NG server IP (overrides the `EVE_NG_HOST` constant)
- `--port <n>`: Console telnet port for the target device
- `--skip-preflight`: Bypass the sanity check that confirms the target is
  currently in the expected solution state.  Use only if you know what
  you are doing.

`apply_solution.py` accepts:

- `--host <ip>`: EVE-NG server IP
- `--reset`: Erase device configs before pushing the solution (two-phase:
  Phase 1 erase, Phase 2 push).  Guarantees a clean slate when stale
  fault configuration might otherwise linger.

## Why the pre-flight check?

Injecting a fault on top of a device that is already broken (or not yet
configured) usually produces confusing symptoms.  Each inject script reads
a relevant section of the running-config and verifies the expected
solution-state config is present.  If not, it stops with a clear error
pointing you at `apply_solution.py`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | At least one device failed to restore (`apply_solution.py` only) |
| `2`  | Missing required argument (host or port not set) |
| `3`  | Connection error |
| `4`  | Pre-flight check failed (target not in expected state) |
