# Requirements register

Milestone M1. Each requirement records **where it came from** — the client's
written answers to the team questionnaire (`Q1`–`Q20`), the approved project
proposal (scope, deliverables D1–D6, evaluation criteria) or the risk
register — and its **MoSCoW priority**. The client said "all [features] are
equally important" (Q19), so everything the client named is a **Must**;
items the team added to make those work end to end are **Should**.

How each requirement is implemented and verified: `requirements-traceability.md`.

## Client context

| | |
|---|---|
| Client | South Australian Regional Heritage Network |
| Problem | "Create online presence" (Q17) — information currently travels "through posters, brochures and word of mouth" (Q14) |
| Primary users | "Visitors and members of the museum" (Q18); "very popular with families having kids aged 10–14" (Q8) |
| Success | "The demo of a fully functional prototype" (Q12), "capable of handling typical concurrent user load of 100" (Q1) |
| Content | "Filled by staff. Start with placeholder data" (Q9, Q16); "all content will be created / controlled by staff. Users can't post any content" (Q10) |
| Out of scope | "A functional payment system" (Q20); native mobile apps and integration with other systems (proposal exclusions) |
| Budget | AUD 20,000 (Q15) |

## Functional requirements

| ID | Requirement | Source | Priority |
|---|---|---|---|
| FR-01 | A home page with general information — opening hours, timed and upcoming events — and the option for members to sign in | Q3(i) | Must |
| FR-02 | Search the museum's collections, with a page for each item | Q3(ii) | Must |
| FR-03 | Staff can publish event details; visitors can search for events | Q3(iii) | Must |
| FR-04 | Members can view their membership status, last activity and recommendations | Q3(iv) | Must |
| FR-05 | New members can sign up | Q3(iv) | Must |
| FR-06 | Buy tickets online for general admission, ending at a **simulated** payment step | Q3(v), Q20 | Must |
| FR-07 | Staff create and edit event pages | Q4(a) | Must |
| FR-08 | Staff update opening hours, which change seasonally | Q4(a), Q11 | Must |
| FR-09 | Administrators can revoke member access | Q4(b) | Must |
| FR-10 | Role-based access control: visitor/member, staff, administrator | Q5, proposal D2 | Must |
| FR-11 | Event capacity is set when the event is created | Q7 | Must |
| FR-12 | Only staff create content; the public cannot post | Q10 | Must |
| FR-13 | Placeholder content sufficient to demonstrate every function | Q9, Q16, D3 | Must |
| FR-14 | Staff manage exhibitions, collection items and visitor information | Proposal scope ("Content Management") | Must |
| FR-15 | Exhibition pages, distinct from collection items | Proposal scope | Should |
| FR-16 | "Plan your visit": address, hours, transport, parking, prices, contact, facilities, accessibility | Proposal scope | Should |
| FR-17 | Visitors register for events | Proposal scope | Should |
| FR-18 | Membership options and an application that staff approve | Proposal scope | Should |
| FR-19 | Recommendations based on selected interests, by an interest-based filtering algorithm | Proposal scope | Should |
| FR-20 | Staff manage ticket reservations and event registrations | Proposal scope ("Booking Management") | Should |
| FR-21 | An administrator dashboard / overview of museum activity | Proposal scope ("Admin Dashboard") | Should |
| FR-22 | Administrators assign roles and view an audit log | Role-permission matrix | Should |
| FR-23 | Real payment gateway | Proposal (optional "if time permits"), excluded by Q20 | Won't |

## Non-functional requirements

| ID | Requirement | Measure (proposal evaluation criteria) | Source | Priority |
|---|---|---|---|---|
| NFR-01 | Typical load | Stable response with 100 concurrent users | Q1 | Must |
| NFR-02 | Peak load | Degrades gracefully and remains available at 500 | Q2 | Must |
| NFR-03 | Suitable for families with children aged 10–14 | ≥ 80% task completion in usability testing | Q8 | Must |
| NFR-04 | Staff can manage content without technical help | Staff complete the event publishing workflow unassisted | Proposal criterion "Content Manageability" | Must |
| NFR-05 | Access control cannot be bypassed | All role-permission tests pass; no privileged endpoint reachable without the role; enforced server-side | Proposal criterion, risk register | Must |
| NFR-06 | Accessible | WCAG AA contrast (measured), 15 px minimum body text, keyboard-operable forms, accessibility needs captured at booking | Design board; Q8 | Should |
| NFR-07 | Works on phones without a separate app | One responsive web app; no horizontal scrolling at 390 px | Proposal exclusions | Should |
| NFR-08 | Deployable and handed over | Docker Compose setup, environment template, deployment and maintenance notes | D4, D6 | Must |
| NFR-09 | Within budget | ≤ AUD 20,000 | Q15 | Must |
| NFR-10 | Demonstration never depends on internet services | A full local deployment path | Risk register | Should |

## Constraints and decisions

- **One museum, four galleries** (Main Hall, Telegraph, Monster Mine,
  Encounter Bay) — the multi-site precinct model in early wireframes is not
  built (locked before the M3 design freeze).
- **One account per membership**, recording how many adults and children it
  covers; no household hierarchy.
- **No separate mobile designs**; responsiveness is handled in the build.
- **Stack:** React (Vite), FastAPI, PostgreSQL, Docker Compose.

Changes to these decisions are recorded in `decisions.md`.
