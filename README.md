# CCNP ENCOR (350-401) Lab Series

Hands-on labs for the CCNP ENCOR (350-401) exam, built for EVE-NG on Intel/Windows.

Each lab is self-contained: topology file, initial and solution configs, a
student workbook, and automation scripts for initial setup, fault injection,
and solution restoration.

---

## End-to-End Workflow

The full path from a cold laptop to a running lab:

```
[VMware Workstation]                         (host the EVE-NG Ubuntu VM)
         |
         v
[EVE-NG web UI: http://<eve-ng-ip>]          (admin / eve)
         |
         v  import topology/<lab>.unl        (Add New Lab -> Import)
         |
         v  Start all nodes
         |
         v
[Your laptop: terminal]
         |
         v  pip install -r requirements.txt
         |
         v  python setup_lab.py --host <eve-ng-ip>      (push initial configs)
         |
         v
[Open workbook.md, work through Sections 1-8]
         |
         v  (optional) troubleshooting scenarios
         |     apply_solution.py   -> reset to known-good
         |     inject_scenario_NN.py -> break something
         |     diagnose + fix
         |     apply_solution.py   -> restore before next ticket
         v
[Complete checklist in workbook Section 10]
```

---

## Getting Started

### 1. Clone (with submodules)

```bash
git clone --recurse-submodules https://github.com/FonNkwenti/ccnp-encor-labs.git
cd ccnp-encor-labs
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### 2. Install Python dependencies

Required on whichever machine runs the automation scripts (usually your
laptop, not the EVE-NG host itself):

```bash
pip install -r requirements.txt
```

This installs `netmiko` (console automation) and `requests` (EVE-NG REST
API port discovery).

### 3. Prepare EVE-NG

- Start VMware Workstation and boot the EVE-NG Ubuntu VM
- Note the VM's IP address (shown at the console login prompt)
- Browse to `http://<eve-ng-ip>` — default credentials: `admin` / `eve`
- Confirm the images listed in
  [`.agent/skills/eve-ng/SKILL.md`](.agent/skills/eve-ng/SKILL.md) Section 8
  are present under **System -> System status -> Installed Images**

### 4. Pick a lab

```bash
cd labs/switching/lab-00-vlans-and-trunking
```

Each lab directory has:

| File / Folder | Purpose |
|--------------|---------|
| `README.md` | Lab-specific quick-start (stages, timing, exam refs) |
| `meta.yaml` | Machine-readable metadata (devices, difficulty, blueprint refs) |
| `workbook.md` | Student-facing walkthrough — this is where you spend most time |
| `topology/` | `.drawio` diagram + EVE-NG `.unl` file + import README |
| `initial-configs/` | Starting configs pushed by `setup_lab.py` (bare-minimum) |
| `solutions/` | Full solution configs used by `apply_solution.py` |
| `setup_lab.py` | One-shot initial config loader |
| `scripts/fault-injection/` | Troubleshooting scenarios + solution restore |

### 5. Build the topology

Import `topology/<lab-name>.unl` into EVE-NG (see
`topology/README.md` in each lab for the exact steps). Start all nodes.

### 6. Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

Ports are discovered automatically via the EVE-NG REST API — no port-number
editing required.

### 7. Work the workbook

Open `workbook.md` and follow Sections 1-8. Section 9 contains optional
troubleshooting scenarios; Section 10 is the completion checklist.

---

## Repository Layout

```
ccnp-encor-labs/
  blueprint/350-401/       # Exam blueprint (source of truth for scope)
  specs/                   # Topic-level planning: topic-plan.yaml
  labs/
    <topic>/               # e.g. switching/, ospf/, bgp/
      spec.md              # Topic spec (design decisions)
      baseline.yaml        # Shared topology core across labs in this topic
      lab-NN-<slug>/       # One lab per blueprint sub-objective
    common/tools/          # Shared automation (eve_ng.py, lab_utils.py)
  tasks/                   # todo.md, lessons.md (planning + retrospectives)
  .agent/skills/           # Submodule: platform-agnostic skill library
  requirements.txt
```

---

## Three-Phase Lab Development Workflow

Lab authors use a repeatable pipeline:

1. **Plan** — upload blueprint, run `exam-planner` skill → generates
   `specs/topic-plan.yaml` + empty `labs/<topic>/` folders
2. **Spec** — run `spec-creator` per topic → generates `spec.md` +
   `baseline.yaml` (reviewed before next step)
3. **Build** — run `lab-workbook-creator` per lab → generates workbook,
   configs, topology, scripts (reviewed before next lab)

See [`CLAUDE.md`](CLAUDE.md) and
[`.agent/skills/CLAUDE.md`](.agent/skills/CLAUDE.md) for skill details.

---

## Updating the skills submodule

```bash
git submodule update --remote .agent/skills
git add .agent/skills
git commit -m "chore: bump skills submodule"
```

---

## Exam

- **CCNP ENCOR 350-401** -- current blueprint at
  [`blueprint/350-401/blueprint.md`](blueprint/350-401/blueprint.md)
- **Platform:** EVE-NG on Dell Latitude 5540 (Intel/Windows)
- **Image inventory:** confirmed on this lab host; see eve-ng skill Section 8
