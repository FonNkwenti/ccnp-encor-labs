# Fault Injection -- Network Assurance Lab 00: Diagnostics

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab `network-assurance/lab-00-diagnostics.unl` imported and **STARTED**
- All nodes (R1, R2, R3, SW1, SW2) powered on in the EVE-NG web UI
- `pip install netmiko`
- Console port for R1 noted from the EVE-NG web UI (hover over the node
  or check the node properties panel)

## Configuration

Before running any script, open the script file and update two variables at
the top:

```python
EVE_NG_HOST  = "192.168.x.x"   # replace with your EVE-NG server IP
CONSOLE_PORT = 32768            # replace with R1's telnet port from EVE-NG UI
```

`apply_solution.py` uses `EVE_NG_HOST` and `CONSOLE_PORT_R1` — update both
in that file as well.

## Standard Workflow

```bash
# 1. Reset to known-good solution state
python3 apply_solution.py

# 2. Inject one scenario at a time
python3 inject_scenario_01.py   # Ticket 1
python3 inject_scenario_02.py   # Ticket 2
python3 inject_scenario_03.py   # Ticket 3

# 3. Between tickets, restore solution
python3 apply_solution.py
```

## Scenarios

| Scenario | Script | Target | Inject Commands |
|----------|--------|--------|----------------|
| 01 | `inject_scenario_01.py` | R1 | `no snmp-server community ENCOR-RO RO` + `snmp-server community ENCOR-READONLY RO` |
| 02 | `inject_scenario_02.py` | R1 | `ip access-list extended DEBUG-FILTER` + `no permit ip host 192.168.10.10 any` |
| 03 | `inject_scenario_03.py` | R1 | `logging buffered 16384 errors` |

## Restore

`apply_solution.py` restores all three affected areas on R1 in a single
pass. Run it before each new ticket to ensure a clean baseline.

Restore commands applied:
- `no snmp-server community ENCOR-READONLY RO` + `snmp-server community ENCOR-RO RO`
- `ip access-list extended DEBUG-FILTER` + `permit ip host 192.168.10.10 any`
- `logging buffered 16384 informational`
