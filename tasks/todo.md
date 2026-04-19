# CCNP ENCOR Lab Build Tracker

## Phase 1: Exam Planner
- [x] Generate topic-plan.yaml from blueprint

## Phase 2: Spec Creator (per topic)
- [x] switching — 6 labs (spec.md + baseline.yaml + folders)
- [x] ospf — 7 labs
- [x] eigrp — 5 labs
- [x] bgp — 5 labs
- [x] ip-services — 6 labs
- [x] multicast — 5 labs
- [x] virtualization — 6 labs
- [x] network-assurance — 6 labs
- [x] security — 6 labs
- [x] automation — 6 labs
- [x] network-design — 5 labs (hybrid: reference + PBR standard)
- [x] sd-networking — 6 labs (hybrid: SD-WAN standard + SD-Access reference)
- [x] overlay-technologies — 3 labs (reference)
- [x] security-concepts — 3 labs (reference)

## Phase 3: Lab Builder (per lab)

Build order follows topic-plan.yaml. Each lab needs: workbook.md, initial-configs/,
solutions/, topology.drawio, setup_lab.py, scripts/fault-injection/, meta.yaml.
Reference-format labs only need: workbook.md (+ optional topology.drawio).

### 1. switching (6 labs)
- [x] lab-00-vlans-and-trunking (built during test run)
- [x] lab-01-etherchannel
- [x] lab-02-rstp
- [x] lab-03-mst
- [x] lab-04-capstone-config
- [x] lab-05-capstone-troubleshoot

### 2. ospf (7 labs)
- [x] lab-00-single-area-ospfv2 (built during test run)
- [x] lab-01-multi-area-ospfv2
- [x] lab-02-network-types
- [x] lab-03-area-types
- [x] lab-04-summarization-filtering
- [x] lab-05-capstone-config
- [x] lab-06-capstone-troubleshoot

### 3. eigrp (5 labs)
- [x] lab-00-classic-eigrp
- [x] lab-01-named-mode-dual-stack
- [x] lab-02-stub-summarization-variance
- [x] lab-03-capstone-config
- [x] lab-04-capstone-troubleshoot

### 4. bgp (5 labs)
- [x] lab-00-ebgp-peering
- [x] lab-01-ibgp-and-dual-stack
- [x] lab-02-best-path-selection
- [x] lab-03-capstone-config
- [x] lab-04-capstone-troubleshoot

### 5. ip-services (6 labs)
- [x] lab-00-ntp-and-qos
- [x] lab-01-nat-pat
- [x] lab-02-hsrp
- [x] lab-03-vrrp-dual-stack
- [x] lab-04-capstone-config
- [x] lab-05-capstone-troubleshoot

### 6. multicast (5 labs)
- [x] lab-00-pim-sm-and-igmp
- [x] lab-01-rp-discovery-and-igmpv3
- [x] lab-02-ssm-bidir-msdp
- [x] lab-03-capstone-config
- [x] lab-04-capstone-troubleshoot

### 7. virtualization (6 labs)
- [x] lab-00-vrf-lite
- [x] lab-01-vrf-dual-stack
- [x] lab-02-gre-tunnels
- [x] lab-03-ipsec-and-gre-over-ipsec
- [x] lab-04-capstone-config
- [x] lab-05-capstone-troubleshoot

### 8. network-assurance (6 labs)
- [x] lab-00-diagnostics
- [x] lab-01-flexible-netflow
- [x] lab-02-span-rspan
- [x] lab-03-ip-sla
- [x] lab-04-capstone-config
- [x] lab-05-capstone-troubleshoot

### 9. security (6 labs)
- [ ] lab-00-device-access
- [ ] lab-01-aaa
- [ ] lab-02-acls
- [ ] lab-03-copp
- [ ] lab-04-capstone-config
- [ ] lab-05-capstone-troubleshoot

### 10. automation (6 labs)
- [ ] lab-00-eem-applets
- [ ] lab-01-python-and-json
- [ ] lab-02-netconf
- [ ] lab-03-restconf
- [ ] lab-04-capstone-config
- [ ] lab-05-capstone-troubleshoot

### 11. network-design (5 labs — hybrid)
- [ ] lab-00-design-principles (reference)
- [ ] lab-01-high-availability (reference)
- [ ] lab-02-policy-based-routing (standard)
- [ ] lab-03-capstone-config (hybrid)
- [ ] lab-04-capstone-troubleshoot (hybrid)

### 12. sd-networking (6 labs — hybrid)
- [ ] lab-00-sdwan-fabric-bringup (standard)
- [ ] lab-01-sdwan-omp-and-policies (standard)
- [ ] lab-02-sdwan-data-plane (standard)
- [ ] lab-03-sd-access-concepts (reference)
- [ ] lab-04-capstone-config (hybrid)
- [ ] lab-05-capstone-troubleshoot (hybrid)

### 13. overlay-technologies (3 labs — reference)
- [ ] lab-00-device-virtualization
- [ ] lab-01-lisp-and-vxlan
- [ ] lab-02-capstone-review

### 14. security-concepts (3 labs — reference)
- [ ] lab-00-security-design
- [ ] lab-01-catalyst-center-and-apis
- [ ] lab-02-capstone-review

---

## Summary
- **Total labs:** 75
- **Built:** 46 (switching 00-05; ospf 00-06; eigrp 00-04; bgp 00-04; ip-services 00-05; multicast 00-04; virtualization 00-05; network-assurance 00-05)
- **Remaining:** 29
- **Next up:** security/lab-00-device-access
