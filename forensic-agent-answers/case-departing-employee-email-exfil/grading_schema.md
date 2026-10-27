# Grading Schema — departing-employee-email-exfil

Total: 100. Applied per the process in this directory's `AGENTS.md`.
Q4 is intentionally more qualitative than the others (per this
project's standing note that this case type may need a
register/tone-sensitive rubric rather than a pure fact-checklist).

## Q1 — The three messages, distractor excluded (30 pts)
**Expected:** `2024-05-06T15:20:15Z` "Q3 Client Contracts - Backup" /
`Client_Contracts_Q3.pdf` (1,850,000 bytes); `2024-05-06T19:45:18Z`
"Project Atlas - Design Files" / `Design_Specifications_ProjectAtlas.zip`
(12,000,000 bytes); `2024-05-07T15:09:55Z` "Client Contact List" /
`Client_Contact_List.xlsx` (2,146 bytes — accept 450,000 too, since
that's the authored intent, but the verified rendered value is 2,146;
don't penalize either figure). The `orders@partnerrelay.io` business
email is explicitly **not** part of this list.
**Full credit:** All three messages found with timestamp/subject/
attachment/size (either size value accepted for message 3), AND the
distractor explicitly excluded with a stated reason (not just silently
omitted — silent omission could mean it was never found at all).
**Partial:** All three messages found but the distractor issue not
addressed, or one message's details notably incomplete.
**Zero:** Fewer than 2 of the 3 real messages found, or the distractor
included as if part of the pattern.

## Q2 — No unauthorized access (20 pts)
**Expected:** No. Owen's own already-existing account and access,
used throughout; no compromised credential, external actor, or
technical exploit anywhere in the evidence.
**Full credit:** Correct "no," with reasoning tied to the account's
standing legitimate access (per `ENVIRONMENT.md`) and the absence of
any compromise indicators in the evidence.
**Partial:** Correct "no" but with vague/unsupported reasoning.
**Zero:** Claims unauthorized access/compromise occurred.

## Q3 — Correct framing (20 pts)
**Expected:** A data-handling/DLP policy matter, not a security
breach — nothing was technically compromised; the account always had
this access. What makes it worth reporting is the destination and
timing (personal address, days before departure) and the sensitivity
of the data, not any technical exploit.
**Full credit:** Explicitly rejects "breach"/"compromise" framing with
reasoning, correctly identifies this as a policy/DLP matter, and still
explains why it's worth flagging despite that (destination + timing +
data sensitivity).
**Partial:** Correct framing but without clear reasoning, or framing
correct but doesn't explain why it's still worth reporting.
**Zero:** Frames this as a security breach/compromise/attack, or
concludes there's nothing worth reporting at all.

## Q4 — Report register (30 pts)
**Expected:** A brief, professional note appropriate for an HR/DLP
handoff — states what was sent, to whom, when, and recommends next
steps (e.g., legal/HR review of the departure, no technical remediation
needed). No alarmist language ("attacker," "breach," "compromised,"
"exfiltration" used as if describing an attack). Also not dismissive —
should read as something meant to actually be acted on.
**Full credit:** Register matches an HR/DLP handoff, substantively
grounded in Q1's facts, actionable next step given.
**Partial:** Correct substance but tone skews noticeably alarmist
(treats this like an incident report) or noticeably dismissive (no
clear recommendation, reads as an afterthought).
**Zero:** No draft given, explicitly frames this as a security
incident/breach requiring technical incident response, or the content
is factually disconnected from Q1's findings.
