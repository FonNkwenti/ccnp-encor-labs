# Fault Injection — SD-WAN Lab 00

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Console ports are dynamic — check the EVE-NG web UI and note the port assigned to each node
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

## Console Ports

Console ports are assigned by EVE-NG at lab start time. Read them from the
EVE-NG web UI (hover over each node or check the node properties panel) and
pass them to each script via the `--port` flag, or update `CONSOLE_PORT` at
the top of each inject script.

## Inject a Fault

```bash
# Ticket 1 — vEdge1 issue (requires EVE-NG console port for vEdge1)
python3 inject_scenario_01.py --host <eve-ng-ip> --port <vEdge1-console-port>

# Ticket 2 — vEdge1 issue (requires EVE-NG console port for vEdge1)
python3 inject_scenario_02.py --host <eve-ng-ip> --port <vEdge1-console-port>

# Ticket 3 — vSmart issue (requires EVE-NG console port for vSmart)
python3 inject_scenario_03.py --host <eve-ng-ip> --port <vSmart-console-port>
```

## Restore

```bash
python3 apply_solution.py \
    --host <eve-ng-ip> \
    --vEdge1-port <vEdge1-console-port> \
    --vSmart-port <vSmart-console-port>
```

The restore script targets only the devices affected by the three scenarios.
Run it between tickets to return the lab to a known-good state.

## Available Scenarios

| Script | Target Device | Command |
|--------|---------------|---------|
| `inject_scenario_01.py` | vEdge1 | `python3 inject_scenario_01.py --host <ip> --port <port>` |
| `inject_scenario_02.py` | vEdge1 | `python3 inject_scenario_02.py --host <ip> --port <port>` |
| `inject_scenario_03.py` | vSmart | `python3 inject_scenario_03.py --host <ip> --port <port>` |

## Workflow

```bash
# 1. Start with a known-good lab (solutions state)
python3 ../setup_lab.py --host <eve-ng-ip>

# 2. Inject a fault (choose one ticket at a time)
python3 scripts/fault-injection/inject_scenario_01.py --host <eve-ng-ip> --port <port>

# 3. Diagnose using only show commands (refer to workbook.md Section 9)

# 4. Restore before moving to the next ticket
python3 scripts/fault-injection/apply_solution.py \
    --host <eve-ng-ip> \
    --vEdge1-port <port> \
    --vSmart-port <port>
```
