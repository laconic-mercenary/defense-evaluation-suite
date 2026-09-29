# Test Objectives

Every case in `forensic-agent-tests` should be traceable to one or more of
the nine forensic-capability categories below. This document defines each
category and tracks candidate sources — existing datasets, open-source
tools, and relevant procedural skills — that could inform or supply a case
covering it. It's a planning reference, not a coverage guarantee: a source
appearing here means it's worth evaluating for a category, not that it's
already been vetted or adopted.

## A note on the "Anthropic-Cybersecurity-Skills" library

The Related Skills column below references
[`Anthropic-Cybersecurity-Skills`](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
(local checkout: `/Users/mlcs/Documents/github/Anthropic-Cybersecurity-Skills`),
818 procedural cybersecurity skills mapped to MITRE ATT&CK/NIST CSF and
other frameworks. **Despite the name, its own README states it is an
independent community project, not affiliated with Anthropic PBC** — cite
it as such wherever it's referenced.

Two distinct ways it's used, and both are now decided:

1. **Case-design input**: mine these skills' descriptions, tool references,
   and MITRE ATT&CK mappings when authoring `EXAM.md` questions and
   `grading_schema.md` rubrics, so cases reflect what a real analyst's
   workflow actually checks for a given category. This applies regardless
   of what the AUT has access to — it makes the *case* more realistic, not
   just the AUT's toolkit.
2. **AUT toolkit — adopted.** The agent-under-test is enriched with this
   skills library during investigation. This does shift what's measured
   toward playbook-following as well as native reasoning, and that's
   intentional. It does not preclude running the same cases against
   non-enriched models (Anthropic or otherwise) for comparison — the cases
   themselves stay valid either way, since case-design input (above) never
   depended on AUT enrichment in the first place.

   **Delivery mechanism (noted 2026-09-09, see `../../EVAL_SUITE_PLAN.md`):**
   this decision was adopted without a concrete way to hand the skills to
   an AUT at run time. There now is one, contingent on the harness's
   still-open framework choice — EvalScope's
   `NativeAgentConfig(skills_dir=...)` reads host folders containing
   `SKILL.md` natively, no scaffolding required. Two things this raises
   that belong to *this* document rather than the harness plan:

   - **Which skills get mounted is a test-design question, not a config
     detail.** Mounting a category-matched subset would tell the AUT which
     of the nine categories below the case belongs to — a hint it isn't
     supposed to have, and one that partly answers the question the case
     is asking. Mounting all 818 avoids the leak but changes what's
     measured (skill *selection* becomes part of the task). **Decided
     2026-09-18: the same 10 skills for every case**, the union of
     `TEST_CASE_MATRIX.md`'s "Skills Enabled" column. Each case's own
     list is written with knowledge of its answer, so mounting it per case
     would hint at the finding; the shared union reveals nothing about any
     one case. All 818 was rejected on prompt size. Record the library
     commit and the 10 names alongside any published score.
   - **An enriched run and a non-enriched run are different experiments.**
     The paragraph above already says both are valid; make sure the
     enrichment state is reported with the result, since a score is not
     comparable across that boundary.

   Vendoring (submodule vs. directory vs. pinned copy) remains open — see
   `TODO.md` item 3. Given the library is an independent community project
   (see the caveat above), a pinned copy is the safer default: an upstream
   change to a skill silently changes what the benchmark measures.

### Other skill repos surveyed (not yet adopted for AUT enrichment)

Same "independent, not Anthropic-affiliated" pattern holds for both:

- [`briiirussell/cybersecurity-skills`](https://github.com/briiirussell/cybersecurity-skills)
  — 33 skills, MIT. Most relevant: `disk-forensics` (evidence recovery,
  timeline reconstruction), `incident-triage` (NIST SP 800-61), `security-comms`
  (audience-tailored incident comms/post-mortem/breach-disclosure templates
  — directly useful for category 9 rubric design, arguably richer than
  anything found for that category in Anthropic-Cybersecurity-Skills).
- [`transilienceai/communitytools`](https://github.com/transilienceai/communitytools)
  — 27 skills, offense-oriented (pentesting/bug-bounty lifecycle). Includes
  a `/dfir` skill (Windows event logs, PCAP analysis, AD attack detection,
  executive+technical report generation). Its main value here isn't
  defensive analysis — it's realistic *attacker*-side tradecraft, useful
  for keeping EvidenceForge storyline authoring grounded in what a real
  operator's exploitation chain looks like, independent of any AUT-facing
  skill.
- The `agentskills.io` site (cited by Anthropic-Cybersecurity-Skills as
  "the standard" it follows) is the Agent Skills *format spec*, not a
  registry of skill libraries — it lists client applications that support
  the format, not skill collections. Dead end for finding more libraries
  this way.
- Claude Code's own built-in `security-review` skill is a first-party
  option distinct from all of the above community libraries, worth keeping
  in mind separately since it isn't a third-party dependency.

## Categories

### 1. Log Analysis

Ability to read and reason over raw Windows and Linux log sources (Security
and Sysmon events, syslog, application logs), search for specific keywords,
identifiers, or indicators across a volume of records, and extract or
filter by time range to isolate relevant activity.

### (!) 2. Browser History / Download History Verification

Ability to review browser artifacts — history, downloads, cache, typically
from Chrome or Firefox — to reconstruct what a user searched for, visited,
or downloaded, and correlate that activity against a broader investigation.

**Known deficiency, tracked not blocking**: no current tool in our
generation pipeline (EvidenceForge or otherwise) produces browser
artifacts. NIST CFReDS Data Leakage Case remains the identified path to
closing this (see the Coverage Matrix and `TEST_CASE_MATRIX.md`), but it
requires disk-image case infrastructure we haven't built yet. This category
has zero case coverage until that's done — not a gap to paper over with a
weaker substitute.

### 3. Account Activity Verification

Ability to analyze authentication and session evidence (Windows Security
auth events, Linux auth logs, SSH/sudo activity) to establish who
authenticated, from where, when, and whether that activity is consistent
with a single legitimate identity.

### 4. Network Connection History Verification

Ability to analyze host connection and traffic evidence — firewall, proxy,
DNS, VPN, netflow/connection-record logs — searching by IP address or time
range to reconstruct what a host connected to, from where, and whether any
of it warrants scrutiny.

### 5. Timeline Reconstruction

Ability to assemble a coherent, correctly-ordered sequence of events from
multiple, independently-timestamped sources into a single chronological
narrative.

### 6. Intrusion Path Identification

Ability to reconstruct how an attacker gained a foothold — the specific
technique, vulnerability, or vector exploited — from the available
evidence, without being told the vulnerability in advance.

### 7. Lateral Movement Analysis

Ability to trace movement from one host or account to another — an
attacker pivoting, or in a benign case, a legitimate user working across
systems — correlating evidence across the source and destination systems.

### 8. Data Exfiltration Indicator Analysis

Ability to recognize evidence consistent with data leaving an environment
without authorization — anomalous transfer volumes, timing, or channel
(e.g. DNS tunneling, encoded beaconing) — and assess what, if anything, was
actually exfiltrated.

### 9. Report Generation

Ability to synthesize findings from an investigation into a clear,
accurate, appropriately-hedged report for a given audience, distinguishing
confirmed facts from working hypotheses and unconfirmed details.

## Coverage Matrix

| Index # | Category Name | Example Scenario | Possible Open Source Tools / Sources | Related Skills (Anthropic-Cybersecurity-Skills) |
|---|---|---|---|---|
| 1 | Log Analysis | A week of Windows Security + Linux syslog exports from a mixed-OS network; locate every event referencing a given process name or username within a bounded time window. | EvidenceForge (Windows Security/Sysmon XML, syslog, bash_history); AIT Log Data Set v2.0 (real multi-service Linux logs); EVTX-ATTACK-SAMPLES / EVTX-to-MITRE-Attack (real binary EVTX for parser validation); OTRF Security-Datasets (Mordor) / splunk/attack_data; `plaso`/`log2timeline` for cross-format parsing checks | `performing-log-analysis-for-forensic-investigation`, `performing-linux-log-forensics-investigation`, `extracting-windows-event-logs-artifacts`, `analyzing-windows-event-logs-in-splunk`, `generating-forensic-timelines-with-hayabusa` |
| 2 | Browser History / Download History Verification | An employee under suspicion of pre-resignation data theft; review their workstation's Chrome/Firefox history, downloads, and cache to reconstruct what they researched and downloaded, and when. | NIST CFReDS Data Leakage Case (disk image + removable media, analyst-level answer key); `browser-history` (Python extraction library); Hindsight (Chrome/Chromium forensic timeline tool); Playwright/Selenium (drive a real browser to generate genuine synthetic artifacts for a scripted persona) | `analyzing-browser-forensics-with-hindsight`, `extracting-browser-history-artifacts` |
| 3 | Account Activity Verification | A shared server shows two concurrent SSH sessions authenticating as the same user from two different source IPs; determine whether this is a physically impossible/shared-credential pattern. | EvidenceForge (4624/4625/4634/4648/4672/4720-4757/4768-4776, sshd/sudo/su); AIT Log Data Set v2.0 (real auth.log); OTRF Security-Datasets (credential-access-technique-mapped captures) | `analyzing-linux-audit-logs-for-intrusion`, `performing-active-directory-compromise-investigation`, `detecting-ntlm-relay-with-event-correlation`, `detecting-golden-ticket-attacks-in-kerberos-logs`, `detecting-service-account-abuse`, `detecting-email-account-compromise` |
| 4 | Network Connection History Verification | A firewall/proxy/DNS log bundle covering a DMZ segment; identify all external connections to/from a given host within a time range and flag anomalies. | EvidenceForge (Zeek conn/dns/http/ssl/files, Cisco ASA, proxy, Snort/Suricata); AIT Log Data Set v2.0 (VPN, firewall, Suricata, PCAPs); DARPA OpTC (500-host scale); LANL Unified Host and Network Data Set (real enterprise data, benign substrate); Zeek / Wireshark / `tshark` for PCAP reprocessing | `performing-network-forensics-with-wireshark`, `performing-network-packet-capture-analysis`, `analyzing-network-flow-data-with-netflow`, `performing-network-traffic-analysis-with-zeek`, `detecting-network-anomalies-with-zeek`, `implementing-network-traffic-baselining` |
| 5 | Timeline Reconstruction | Multi-source logs spanning several hours across hosts; reconstruct the exact chronological sequence of a user's or attacker's actions. | EvidenceForge (cross-source consistent timestamps); OTRF Security-Datasets (Mordor); `plaso`/`log2timeline` + `psort`; Timesketch | `building-super-timelines-with-plaso`, `performing-timeline-reconstruction-with-plaso`, `generating-forensic-timelines-with-hayabusa`, `building-incident-timeline-with-timesketch`; also `briiirussell/cybersecurity-skills`' `disk-forensics` (evidence recovery + timeline reconstruction) |
| 6 | Intrusion Path Identification | A public-facing web server is compromised; reconstruct the exploitation chain from initial recon through code execution using web, network, and endpoint evidence. | EvidenceForge (`web_scan` storylines, IDS layering); AIT Log Data Set v2.0 (labeled attack steps); OTRF Security-Datasets / splunk/attack_data (ATT&CK-mapped intrusions); EVTX-ATTACK-SAMPLES | `analyzing-cyber-kill-chain`, `performing-active-directory-compromise-investigation`, `analyzing-indicators-of-compromise`, `collecting-indicators-of-compromise`, `triaging-security-incident-with-ir-playbook`; also `transilienceai/communitytools`' `/dfir` and offense-side skills — useful for realistic attacker tradecraft when *authoring* the storyline, not for the AUT |
| 7 | Lateral Movement Analysis | After an initial workstation compromise, the attacker pivots to a second internal host via RDP/PsExec; trace the pivot using correlated logon and network evidence across both hosts. | EvidenceForge (4648 source + 4624 target correlation, RDP, cross-host RSAT sessions); DARPA OpTC (large-scale lateral movement, needle-in-haystack); OTRF Security-Datasets (PsExec/WMI/RDP-mapped captures) | `detecting-lateral-movement-in-network`, `detecting-lateral-movement-with-zeek`, `detecting-lateral-movement-with-splunk`, `hunting-for-dcom-lateral-movement`, `hunting-for-lateral-movement-via-wmi`, `performing-lateral-movement-detection` |
| 8 | Data Exfiltration Indicator Analysis | A compromised host establishes a slow, low-volume DNS-tunneled channel to an external domain over several hours; recognize the volumetric/timing anomaly and assess what may have left the network. | EvidenceForge (`dns_tunnel`, `spillage`, `beacon` byte-growth — reverify exact current coverage); AIT Log Data Set v2.0 (`dnsteal`-labeled DNS exfiltration); DARPA OpTC | `hunting-for-data-exfiltration-indicators`, `hunting-for-data-staging-before-exfiltration`, `detecting-dns-exfiltration-with-dns-query-analysis`, `detecting-exfiltration-over-dns-with-zeek`, `hunting-for-dns-tunneling-with-zeek` |
| 9 | Report Generation | Given a fully investigated case's raw findings, produce a concise incident report for non-technical stakeholders that correctly separates confirmed facts from unconfirmed hypotheses. | NIST CFReDS (the only surveyed source with analyst-conclusion-level ground truth, not just line-level labels); DFIR-Metric (arXiv 2505.19973) — prior-art LLM DFIR benchmark methodology, not a data source | `building-incident-response-playbook`, `building-malware-incident-communication-template`, `conducting-post-incident-lessons-learned`, `generating-threat-intelligence-reports`; also `briiirussell/cybersecurity-skills`' `security-comms` (seven audience types, incident comms/post-mortem/breach-disclosure templates — the richest report-generation source found so far) |
