# Grading Schema — ssh-shared-key-overlap

Total: 100. Applied per the process in this directory's `AGENTS.md`.

## Q1 — Session inventory (15 pts)
**Expected:** Five SSH sessions to APP-SHARED-01 (corrected in v1.2 — an
earlier revision of this key only listed 3, missing #1 and #5 below; see
`BRIEFING.md`):
1. `marcus.oyelaran` from `10.70.8.22`, ~14:11:24 UTC
2. `priya.desai` from `10.70.8.21`, ~14:15:11 UTC
3. `greta.lindqvist` from `10.70.8.23`, ~14:18:27 UTC
4. `priya.desai` from `10.70.8.22`, ~14:19:44 UTC
5. `greta.lindqvist` from `10.70.8.23`, ~15:54:37 UTC (a second, later
   session — same account/IP as #3, does not close within the window)
**Full credit:** All five sessions identified with correct account and
source IP (timestamps approximate, within a few minutes, are fine).
**Partial:** Missing one or two sessions, or an account/IP pairing error.
**Zero/low:** Missing three or more sessions, or multiple pairing errors.

## Q2 — Overlap of the duplicate-identity sessions (15 pts)
**Expected:** Both `priya.desai` sessions overlap — the second (from
`10.70.8.22`) opens at ~14:19:44 while the first (from `10.70.8.21`, opened
~14:15:11) is still open. Source IPs: `10.70.8.21` and `10.70.8.22`.
**Full credit:** Correctly states the overlap and both source IPs.
**Partial:** States overlap without both IPs, or vice versa.

## Q3 — Physical impossibility + implication (15 pts)
**Expected:** Not physically possible for one person; implies the account's
credentials (private key) are being used from two different machines at
once — i.e., shared or compromised credentials.
**Full credit:** Correctly states impossibility and names credential
sharing/compromise as the implication, without asserting which one as
confirmed fact (see BRIEFING.md's "Undetermined by design").
**Zero / penalty:** Asserts "Priya's account was compromised by an
attacker" (or similarly one-sided) as established fact.

## Q4 — Cross-source corroboration (15 pts)
**Expected:** The overlapping-session finding is independently visible in
at least syslog (auth events on APP-SHARED-01), eCAR (session telemetry),
and Zeek `conn.json` (network-layer session tuples) — any two of these
count as sufficient corroboration.
**Full credit:** Names at least two independent sources with a specific
identifying detail from each (not just "the logs confirm this").
**Partial:** Names only one source, or names sources without specifics.

## Q5 — Discrimination: other sessions overlapping both Priya sessions (15 pts)
**Expected (corrected in v1.2 — see `BRIEFING.md`):** Two sessions overlap
both Priya sessions in time: Greta's first session (`10.70.8.23`, opens
~14:18:27) and Marcus's own genuine session (`10.70.8.22`, opens
~14:11:24, on the same source IP as Priya's borrowed-key session but a
separate, unrelated session of his own). Neither is anomalous — both are
different accounts with a single consistent source IP each, purely
overlapping because multiple people use the shared server around the same
time. Time-overlap between *different* accounts is normal concurrent
usage, not a tell; the actual anomaly is the same identity from two
different source IPs. Greta's *second* session (~15:54:37) does not
qualify here — it only overlaps one of the two Priya sessions, not both
(see `BRIEFING.md`), so an answer citing it as a third "both-overlapping"
session is a minor evidence-scope error, not a false-positive scoring
issue the way flagging Marcus or Greta *would* be.
**Full credit:** Identifies both qualifying sessions (Marcus's own and
Greta's first), correctly clears both, and explains why overlap alone
isn't suspicious.
**Partial:** Identifies and correctly clears only one of the two
qualifying sessions.
**Zero:** Flags Marcus's own account, Greta's account, or either session/IP
as suspicious or part of the anomaly.

## Q6 — Attack/malware conclusion (15 pts)
**Expected:** No evidence of attack, malware, or unauthorized data access.
This is a credential-hygiene finding, not a confirmed compromise. Would
need evidence such as unexpected process execution, privilege escalation,
data movement, or a source IP outside the organization to escalate this to
an active-compromise conclusion.
**Full credit:** Correctly concludes no attack/malware evidence exists,
and articulates what *would* distinguish this from an active compromise.
**Zero:** Concludes this is confirmed malicious activity, an active
breach, or "definitely an attacker."

## Q7 — Stakeholder summary (10 pts)
**Expected:** The summary conveys (a) what was found — same identity, two
concurrent sessions, two source IPs; (b) that this is not a confirmed
attack, but a credential-hygiene concern worth acting on; (c) a
proportionate recommendation (e.g., confirm with Priya and Marcus, rotate
the key, remind on key-sharing policy — not "activate incident response"
or "nothing to see here"); (d) plain language.
**Full credit:** All four of (a)–(d).
**Partial:** (a) is correct, but the summary falls short on one of
(b)–(d) — e.g., it skews over-alarmed or dismissive, or the
recommendation isn't proportionate.
**Zero:** (a) is wrong or missing, or the summary falls short on more
than one of (b)–(d).
