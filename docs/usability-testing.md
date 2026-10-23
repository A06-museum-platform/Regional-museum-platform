# Usability testing — plan, script and record

**Evaluation criteria (proposal §6):**
- *Audience Suitability* — **at least 80% task completion** with
  representative family users (children aged 10–14 and their parents).
- *Content Manageability* — staff testers complete the **full event
  publishing workflow without developer assistance**.

**Status:** plan and materials ready; sessions to be run in Week 9 (M6).
Results go in the tables at the end and in the A2 report.

## Participants

| Group | Number | Recruit | Matches persona |
|---|---:|---|---|
| Families (one parent + one child aged 10–14, tested together) | 4–5 pairs | friends and family of the team, a local school contact | Sarah & Leo |
| Older visitor / member | 1–2 | relatives, museum volunteers | Margaret |
| Staff stand-ins (non-technical) | 2–3 | classmates outside the team, or the client's staff if available | Emma |

Five family pairs is enough to surface most usability problems; the 80%
criterion is calculated over all family tasks attempted.

Participants must not have seen the system before. Children take part with
a parent present and the parent's consent; no personal data beyond first
names is recorded.

## Setup

- Local stack with a **freshly loaded seed** (`docker compose …` + `seed.sql`) so dates are current.
- A laptop browser for the parent tasks and a **phone** (or browser at 390 px) for at least two tasks.
- Facilitator reads the script; note-taker records time, completion and quotes. Optionally record the screen (with consent).
- Think-aloud: "Please say what you're looking for and what you expect to happen."

## Script

> "Thanks for helping. We're testing the website, not you — if something is
> hard, that's what we need to know. Please think aloud. I can't help you
> during a task, but you can stop any time."

### Family tasks (parent and child together)

| # | Task as read to the participant | Success = | Max time |
|---|---|---|---|
| F1 | "Is the museum open this Saturday? What time does it close?" | States the correct hours (home page or Plan your visit) | 2 min |
| F2 *(child leads)* | "Find an object in the collection made of copper and open its page." | Reaches any copper object page via search or browsing | 3 min |
| F3 *(child leads)* | "Find a hands-on workshop that suits a 12-year-old." | Opens an event with ages covering 12 | 3 min |
| F4 | "Book general admission for two adults and two children next Saturday morning. Ask for a sensory backpack. You don't need to pay." | Reaches the confirmation page with correct tickets and the backpack requested (account creation allowed) | 6 min |
| F5 | "Change of plans — cancel that booking." | Booking shows Cancelled | 3 min |
| F6 | "How much would a family membership cost, and what does it include?" | States $120/year, 2 adults + up to 3 children | 2 min |
| F7 *(on a phone)* | "Register the two of you for a workshop." | Registration confirmed | 4 min |

### Member task (older visitor, signed in as Ben)

| # | Task | Success = | Max time |
|---|---|---|---|
| M1 | "When does your membership run out?" | States the expiry date from the account page | 2 min |
| M2 | "Tell the museum you're interested in family history, then find something it recommends." | Saves interest; opens a recommended item | 4 min |

### Staff tasks (signed in as staff; **no help given**)

| # | Task | Success = | Max time |
|---|---|---|---|
| S1 | "Publish a new workshop: 'Telegraph Codebreakers', next Friday 10:00–11:30, Telegraph Gallery, 15 places, $12, $0 for members, ages 10–14." | Event visible on the public Events page with the right details | 8 min |
| S2 | "The museum closes on [date] for a staff training day. Update the website." | Dated exception saved; that date shows closed when booking | 5 min |
| S3 | "A family has arrived for today's 11:00 booking. Check them in." | Booking shows Checked in | 3 min |

### Accessibility spot check (one participant or a team member)
Complete F4 using the **keyboard only** (Tab / Shift-Tab / Enter / Space).
Record any control that can't be reached or whose focus isn't visible.

## After each session

Ask: "What was the easiest part? The hardest? Anything you expected to find
but didn't?" and the **System Usability Scale** (10 questions, 1–5) for the
parent and staff participants.

## Recording

Completion: ✓ completed unaided · ◐ completed after a hint (counts as **not**
completed for the 80% criterion) · ✗ not completed / gave up / timed out.

### Family results

| Participant | F1 | F2 | F3 | F4 | F5 | F6 | F7 | Completed | Notes |
|---|---|---|---|---|---|---|---|---:|---|
| P1 | | | | | | | | /7 | |
| P2 | | | | | | | | /7 | |
| P3 | | | | | | | | /7 | |
| P4 | | | | | | | | /7 | |
| P5 | | | | | | | | /7 | |
| **Rate** | | | | | | | | **__ %** | target ≥ 80% |

### Member and staff results

| Participant | M1 | M2 | S1 | S2 | S3 | Unassisted? | SUS | Notes |
|---|---|---|---|---|---|---|---:|---|
| | | | | | | | | |

### Issues log

| # | Task | What happened | Severity (1 cosmetic – 4 blocks task) | Fix | Status |
|---|---|---|---|---|---|
| | | | | | |

Severity 3–4 issues are fixed before M6 sign-off (proposal: "priority
defects resolved").
