# Fault Injection — SD-WAN Lab 01: OMP Routing and Control Policies

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Console ports are dynamic — obtain them from the EVE-NG web UI after lab creation
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip> --port <vEdge2-console-port>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip> --port <vEdge1-console-port>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip> --port <vSmart-console-port>   # Ticket 3
```

## Scenario Summary

### Ticket 1

Target: vEdge2

```bash
python3 inject_scenario_01.py --host <eve-ng-ip> --port <vEdge2-console-port>
```

Verify using `show omp routes` on vSmart.

### Ticket 2

Target: vEdge1

```bash
python3 inject_scenario_02.py --host <eve-ng-ip> --port <vEdge1-console-port>
```

Verify using `show bfd sessions` on vEdge1 and `ping vpn 1 192.168.2.1` from vEdge1.

### Ticket 3

Target: vSmart

```bash
python3 inject_scenario_03.py --host <eve-ng-ip> --port <vSmart-console-port>
```

Verify using `show omp routes vpn 1` on vEdge2 and `show policy from-vsmart` on vEdge2.

## Restore

After completing each ticket, restore all affected devices to the known-good state:

```bash
python3 apply_solution.py \
  --host <eve-ng-ip> \
  --vEdge2-port <port> \
  --vEdge1-port <port> \
  --vSmart-port <port>
```

The `--reset` flag is accepted for CLI consistency but is a no-op for Viptela OS
devices (no non-interactive config erase equivalent). Solution configs are pushed
additively and the commit overwrites any injected fault values.

## Typical Workflow

```bash
# 1. Reset lab to known-good state
python3 apply_solution.py --host <eve-ng-ip> --vEdge2-port <p> --vEdge1-port <p> --vSmart-port <p>

# 2. Inject fault for the ticket you want to practice
python3 inject_scenario_01.py --host <eve-ng-ip> --port <vEdge2-port>

# 3. Diagnose and fix using show commands (refer to workbook.md Section 9)

# 4. Restore before moving to the next ticket
python3 apply_solution.py --host <eve-ng-ip> --vEdge2-port <p> --vEdge1-port <p> --vSmart-port <p>
```
