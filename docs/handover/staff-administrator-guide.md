# Staff and administrator guide

For museum staff and administrators. No technical knowledge needed. Every
change you make is live on the public website as soon as you save it, and
is recorded in the activity log.

**Signing in:** go to the website, choose **Sign in**, and use your work
email and password. Staff and administrators land on **Today at a glance**.
To see what visitors see, use **View the public site** at the top right.

Who can do what:

| | Staff | Administrator |
|---|:--:|:--:|
| Events, exhibitions, collection objects, images | ✓ | ✓ |
| Opening hours and visitor information | ✓ | ✓ |
| Bookings, check-in and event registrations | ✓ | ✓ |
| Membership applications, revoking access | | ✓ |
| Staff accounts and roles | | ✓ |
| Activity log | | ✓ |

---

## Today at a glance

Shows whether the museum is open today, how many visitors are booked and how
many have arrived, upcoming sessions (and which are nearly full), how many
collection records exist, and — for administrators — membership applications
waiting for approval. Click a figure to go to the matching screen.

## Events and workshops

**Add a session:** *Events & workshops* → **New session**. Fill in the
title, a description, the gallery, start and finish (same day), how many
places, the price and member price (in **cents**: 1500 = $15.00; 0 = free),
optional age guidance, and **interest tags** — members who chose those
interests will see the session in their recommendations.

- **Save as draft** keeps it off the website while you check it.
- **Publish** puts it on the Events page and the home page straight away.

**Change a session:** **Edit**. You can raise the number of places at any
time; you can't lower it below the places already taken.

**Cancel a session people have registered for:** **Cancel session**. It stays
on the website marked *Cancelled* and the registrations are kept. (**Delete**
is only offered while nobody is registered.) **Reinstate** undoes a
cancellation.

**Unpublish** takes a session with no registrations back to draft.

## Exhibitions and collection objects

*Exhibitions & collections* has two tabs.

- **Exhibitions** — title, a one-line summary, the longer description,
  gallery, start date and optional end date (leave empty for a long-term
  display), age guidance, interest tags. An exhibition with objects in it
  can't be deleted — move the objects or unpublish it instead.
- **Collection objects** — title, the museum's **accession number** (must be
  unique), description, category, gallery, period text and year range,
  materials, the exhibition it belongs to, and *Good for ages 10–14* (drives
  the family filter). A draft needs only a title; publishing needs the
  accession number, description, category and gallery.

**Images:** *Media library* → choose the object, exhibition or event →
upload (JPEG, PNG or WebP up to 5 MB; MP4/WebM video up to 40 MB). Mark one
image as **primary** — that's the one shown on cards and pages.

## Opening hours

*Opening hours* has the **weekly pattern** (each day: open/closed, times, an
optional note such as "Late opening") and **special dates** (public
holidays, closures, special events). A special date always wins over the
weekly pattern — on the website and in online booking. Make all your
changes, then **Save**; nothing is published until you do.

## Visitor information

*Visitor information* edits the public **Plan your visit** page: museum
name, address, phone, email, public transport, parking, the "about" text,
and the list of facilities and accessibility services (mark one
*unavailable* while, say, the lift is being repaired). **Save and publish**
updates the page.

## Bookings and check-in

*Bookings & check-in* → **Visitor bookings**:

- Choose a **day** to see everyone booked, grouped by arrival window, with
  totals and how many have arrived.
- **Needs** shows accessibility requests (step-free access, sensory backpack,
  hearing loop) — have them ready before the family reaches the desk.
- **Check in** when a booking arrives (today or a past date).
- **Cancel** when a visitor phones or emails to cancel; the places go back on
  sale.
- **Find a booking (any day)** searches by reference (e.g. SARHN-10006),
  name or email.

**Event registrations** tab: choose a session to see who is coming and how
many places are taken.

Payment is simulated in this prototype: amounts are shown, but no money is
taken.

---

## Administrators only

### Members
*Members* lists every membership with counts of pending, active and revoked.

- **Approve** a pending application — the person becomes a member at once
  (free entry tickets, recommendations).
- **Decline** — optionally give a reason.
- **Revoke** access when a membership is misused. A **reason is required**;
  it is recorded in the activity log. The person is signed out on their next
  click and can't sign in. Their bookings are kept.
- **Restore** undoes a revocation (an expired membership gets a fresh year).

### Staff accounts and roles
- **Make administrator / Make staff** changes someone's level.
- **Remove access** takes away the workspace; their own visitor account and
  any membership remain.
- **Disable / Re-enable** stops or allows sign-in.
- **Add someone to the team:** they first create an ordinary account on the
  public site (*Sign in* → *Create an account*); find it here by name or
  email and choose **Make staff**.

You can't change your own role or disable yourself — so the museum always
keeps at least one administrator.

### Activity log
Who did what and when: bookings, registrations, applications, approvals and
revocations (with reasons), content changes, role changes. Search by person,
record or reason, or filter by action.

---

## Handover checklist (first week)

1. An administrator account for the museum is created by the developers
   (`scripts/create_admin_user.py`).
2. The museum's administrator creates staff accounts (see *Add someone to the
   team*).
3. Replace the placeholder content: visitor information, opening hours,
   exhibitions, objects (with images), then events.
4. Ask the developers to remove the demo accounts and demo bookings.

**Problems?** Note what you were doing, the time, and any message on screen,
and send it to the technical contact in `technical-maintenance-notes.md`.
