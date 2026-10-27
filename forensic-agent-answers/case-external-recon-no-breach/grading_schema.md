# Grading Schema — external-recon-no-breach

Total: 100. Applied per the process in this directory's `AGENTS.md`.

## Q1 — Characterize the scan (20 pts)
**Expected:** Source `203.0.113.77`, destination `10.30.30.10` (`WEB-01`),
21 distinct ports probed, `2024-06-11 14:09:59`-`14:10:02` UTC. Cites
Event ID `106023` (and/or `302013`/`302014`) in `cisco_asa.log`.
**Full credit:** All four facts (source, destination, port count, time
window) correct, with the specific ASA message type cited.
**Partial:** 2-3 of the four facts correct/cited.
**Zero:** Wrong source or destination, or no specific log-message
citation at all.

## Q2 — Ports that got through (25 pts)
**Expected:** Two ports, 443 and 22. Port 443: Zeek `conn_state: RSTO`,
connection reset almost immediately, no data exchanged (`orig_bytes: 53`,
`resp_bytes: 0`). Port 22: Zeek `conn_state: SF`, `service: ssh`, clean
close after a completed exchange (`orig_bytes: 98`, `resp_bytes: 674`).
**Full credit:** Both ports identified, correct `conn_state` for each,
and a correct (even if brief) description of what happened on each —
not just "these two got through."
**Partial:** Both ports identified but `conn_state`/outcome details
missing or wrong for one or both; or only one of the two ports found.
**Zero:** Wrong ports named, or asserts all 21 were denied (missing both
real connections), or asserts a successful exploit/compromise via
either connection.

## Q3 — The SSH authentication attempt (20 pts)
**Expected:** Failed. Evidence: `WEB-01`'s `syslog.log` — "Invalid user
unknown," "Failed password for invalid user unknown," "Connection
closed by invalid user unknown ... [preauth]." No successful-auth log
line exists anywhere in this data.
**Full credit:** Correctly states the attempt failed, citing the actual
syslog lines (not just the Zeek `conn_state: SF`, which only shows the
TCP session closed cleanly — SF does NOT mean the login succeeded, and
an answer that reasons from `conn_state` alone without checking the
host-level auth log has the right instinct but the wrong evidence).
**Partial:** Correct conclusion (failed) but only cites the network-level
connection record, not the host-level syslog auth-failure lines the
question specifically asks for.
**Zero:** States the login succeeded, or states no authentication was
attempted at all (missing it entirely).

## Q4 — Policy comparison (15 pts)
**Expected:** Partial mismatch. Port 443 being reachable matches stated
policy (80/443 are supposed to be reachable). Port 22 (SSH) responding
to an external connection does NOT match policy — `ENVIRONMENT.md`
states SSH should only be reachable internally, never from the internet.
**Full credit:** Correctly identifies the SSH-exposure mismatch
specifically (not just a generic "some things matched, some didn't"),
and correctly does NOT flag port 443 as a mismatch.
**Partial:** Notices something doesn't match policy but doesn't specify
which port or why.
**Zero:** States everything matched policy (missing the SSH mismatch
entirely), or flags port 443 as a policy violation (it isn't).

## Q5 — Compromise conclusion + report (20 pts)
**Expected:** No evidence of compromise, persistence, or follow-on
activity anywhere in the data — on any host. Report should convey: (a)
a scan happened and one weak/generic SSH probe attempt failed; (b) no
compromise occurred; (c) the SSH-exposure policy gap from Q4 is worth
fixing regardless of whether this specific scan succeeded; (d) a
recommendation scaled to reality (e.g., "close SSH to the internet on
WEB-01" / "confirm no other DMZ hosts have the same exposure" — not
"activate incident response" and not "nothing happened, no action
needed").
Two parts: (1) fact-finding — correctly concludes no compromise, checked
across hosts (not just the web server); (2) report — proportionate tone,
includes the SSH-exposure recommendation, doesn't over-alarm or dismiss.
Part (1) fails if the answer asserts compromise with no supporting
evidence. Part (2) fails if the report escalates to "breach" language or
recommends no action at all despite the real policy-gap finding.
**Full credit:** Both parts met.
**Partial:** Exactly one of the two parts met.
**Zero:** Neither part met.
