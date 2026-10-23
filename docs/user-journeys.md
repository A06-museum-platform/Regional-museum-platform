# User journeys

## Journey map — a family visit (Sarah, primary persona)

How the platform replaces "posters, brochures and word of mouth" (Q14) at
each stage of a visit. Screens are the routes in the built app.

| Stage | 1. Discover | 2. Plan | 3. Book | 4. Visit | 5. Afterwards |
|---|---|---|---|---|---|
| **Sarah does** | Opens a link shared in a school group; scans what's on | Checks the day is open, the price, getting there, whether it suits an 11- and 13-year-old | Picks a date, arrival window and tickets; adds a sensory backpack; confirms | Shows the pass on her phone at the desk | Considers a family membership; Leo wants another workshop |
| **Screens** | `/` — open now, this week's hours, coming up, now showing | `/visit` — hours, special dates, prices, transport, parking, facilities; `/events?audience=families`; `/exhibitions/{slug}` | `/book` → sign in or `/register` → `/book/details` → `/book/confirmation/{ref}` | Pass with QR-style code and reference; staff use `/staff/bookings` | `/membership`; `/account` — recommendations, registrations |
| **She thinks** | "Is it even open this weekend?" | "Will the kids actually like it? What does it cost?" | "Please don't make me fill in ten things." | "Hope they have the backpack ready." | "Two visits and the family pass pays for itself." |
| **Feels** | Curious, sceptical | Reassured | Mildly anxious about effort → relieved | Welcomed | Engaged |
| **What the platform does** | Live opening status from staff-maintained hours; upcoming sessions with places left | One page answers every planning question; *Ages 10–14* labels; family filter | Choice survives sign-in; account creation inline; simulated payment clearly labelled; accessibility needs captured once | Staff see needs on today's list and check in with one click | Plans compared on one screen; recommendations from interests; activity history |
| **Pain points removed** | Out-of-date posters | Phoning to check hours | Paper forms, queues | Needs lost between booking and desk | No way to stay in touch |
| **Requirements** | FR-01, FR-03 | FR-08, FR-15, FR-16 | FR-05, FR-06 | FR-20 | FR-04, FR-18, FR-19 |

## Journey — staff publish a workshop (Emma)

1. **Draft** — `/staff/events` → *New session*: title, description, gallery,
   start and finish, capacity, prices, age guidance, interest tags. *Save as
   draft* keeps it off the public site.
2. **Check** — validation explains anything missing ("The finish time needs
   to be after the start time").
3. **Publish** — one click; the session appears on `/events`, the home page
   and in matching members' recommendations, and *Event published* is
   written to the activity log.
4. **Manage** — places taken update as visitors register; capacity can be
   raised, never lowered below places taken; *Cancel session* keeps
   registrants' records (deleting is only possible while nobody is
   registered).
5. **On the day** — `/staff/bookings` → *Event registrations* lists who is
   coming.

## Journey — an administrator handles a membership (James)

1. Dashboard shows *Membership applications: 2 waiting*.
2. `/admin/members` → filter *Pending* → *Approve*: the applicant becomes a
   member, gets free Member tickets and recommendations; the decision
   appears in their own activity and the audit log.
3. Later, a pass is shared: *Revoke* requires a reason, signs the member
   out on their next request, and can be undone with *Restore*.
4. `/admin/activity` shows who did what, when and why.

The detailed booking sequence is in `diagrams/booking-flow.md`.
