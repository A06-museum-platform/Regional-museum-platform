# Requirements traceability

Every requirement in `requirements.md`, the screens and API that implement
it, and the automated evidence that it works. Test files are under
`backend/tests/` (pytest; `integration/` runs against a real PostgreSQL
database) and `tests/e2e/` (Playwright browser scripts); load tests under
`tests/load/`.

Status as of 23 October 2026: **all Must and Should requirements
implemented and verified**, except NFR-03 and the staff half of NFR-04,
which need sessions with real participants (`usability-testing.md`).

| ID | Screens | API | Verified by | Status |
|---|---|---|---|---|
| FR-01 Home page | `/` — opening status, week's hours, upcoming sessions, exhibitions, highlights, member sign-in | `GET /api/opening-hours`, `/api/events?from=`, `/api/exhibitions`, `/api/collection-items?highlight=` | `test_content_public.py`; `e2e/crawl.py` | Done |
| FR-02 Collection search & item pages | `/collections`, `/collections/{slug}`; header search box | `GET /api/collection-items[/{slug}]` | `test_content_public.py::test_collection_search_and_filters`, `::test_collection_detail` | Done |
| FR-03 Publish & search events | `/staff/events`; `/events`, `/events/{slug}` | `/api/staff/events`, `GET /api/events` | `test_staff_content.py::test_event_publishing_workflow`; `e2e/staff_event_flow.py` | Done |
| FR-04 Membership status, last activity, recommendations | `/account` | `GET /api/memberships/me`, `/api/activity/me`, `/api/recommendations` | `test_member_portal.py`; `e2e/member_portal.py` | Done |
| FR-05 Sign up | `/register`, `/membership` | `POST /api/auth/register`, `POST /api/membership-applications` | `test_membership_flow.py::test_new_account_can_register_and_apply`; `e2e/register_and_mobile.py` | Done |
| FR-06 Tickets with simulated payment | `/book` → `/book/details` → `/book/confirmation/{ref}` | `/api/ticket-types`, `/api/bookings/availability`, `POST /api/bookings` | `test_booking_flow.py`, `unit/test_booking_create.py`; `e2e/booking_flow.py`; `load/race_last_places.py` | Done |
| FR-07 Staff create/edit events | `/staff/events` editor | `POST/PATCH/DELETE /api/staff/events` | `test_staff_content.py`; role matrix rows 10–11 | Done |
| FR-08 Staff update opening hours (seasonal) | `/staff/hours` — weekly pattern + dated exceptions | `PUT /api/staff/opening-hours` | `test_staff_content.py::test_opening_hours_update_closes_booking_dates`; role matrix row 12 | Done |
| FR-09 Admin revokes member access | `/admin/members` — revoke with reason, restore | `POST /api/admin/members/{id}/revoke` | `test_membership_flow.py::test_apply_approve_revoke`, `test_member_portal.py::test_revoke_reason_is_logged`; role matrix row 17 | Done |
| FR-10 RBAC | role-specific navigation, `RoleGuard`, access-refused page | router-level `require_staff` / `require_admin`; roles from the database | **`test_role_matrix.py`** — 19 rows × 5 callers; `permissions/*` | Done |
| FR-11 Capacity set at creation | event editor `capacity` | `POST /api/staff/events`; capacity ≥ places taken | `test_staff_content.py` (409 `CAPACITY_BELOW_REGISTRATIONS`); `test_event_registration.py` (`EVENT_FULL`) | Done |
| FR-12 Only staff create content | no public content forms | every write route under `/api/staff` or `/api/admin` | role matrix rows 10–14 | Done |
| FR-13 Placeholder data | — | `database/seed/seed.sql`: 12 accounts, 13 objects, 5 exhibitions, 11 events, bookings, memberships, activity; dates relative to load date | used by every integration test and e2e script | Done |
| FR-14 Staff manage exhibitions, items, visitor info | `/staff/content`, `/staff/media`, `/staff/visit` | `/api/staff/collection-items`, `/api/staff/exhibitions`, media, `PUT /api/staff/visitor-information` | `test_staff_content.py`, `test_visitor_information.py`, `permissions/test_media_permissions.py` | Done |
| FR-15 Exhibition pages | `/exhibitions`, `/exhibitions/{slug}` | `GET /api/exhibitions[/{slug}]` | `test_content_public.py::test_exhibitions` | Done |
| FR-16 Plan your visit | `/visit` | `/api/visitor-information`, `/api/opening-hours`, `/api/ticket-types` | `test_visitor_information.py`; `e2e/crawl.py` | Done |
| FR-17 Event registration | `/events/{slug}` panel; `/account` registrations | `POST /api/events/{slug}/registrations`, `/api/event-registrations/...` | `test_event_registration.py` | Done |
| FR-18 Membership application & approval | `/membership`; `/admin/members` | `/api/membership-plans`, `/api/membership-applications`, `/api/admin/members/...` | `test_membership_flow.py`, `permissions/test_admin_memberships.py` | Done |
| FR-19 Interest-based recommendations | `/account` — interests, recommendations; staff editors tag content | `/api/interest-tags`, `/api/me/interests`, `/api/recommendations` | `test_member_portal.py::test_recommendations_follow_interests` and four more | Done |
| FR-20 Staff manage bookings & registrations | `/staff/bookings` — by day, check-in, cancel; registrations per session | `/api/staff/bookings...`, `/api/staff/events/{id}/registrations` | `test_staff_bookings.py`; `e2e/admin_flows.py` | Done |
| FR-21 Admin dashboard | `/staff` "Today at a glance" | `GET /api/staff/today` | `test_staff_bookings.py::test_staff_list_and_check_in_today` | Done |
| FR-22 Roles & audit log | `/admin/accounts`, `/admin/activity` | `/api/users`, `/api/admin/activity-log` | `test_staff_bookings.py::test_admin_manages_staff_roles`, `test_staff_content.py::test_staff_actions_are_logged_for_admins` | Done |
| FR-23 Real payment | — | — | — | Out of scope (Q20) |
| NFR-01 100 users | — | — | `docs/load-testing.md`: 0 failures, p95 9 ms | Met |
| NFR-02 500 users | — | — | `docs/load-testing.md`: 0 failures, server p95 < 9 ms | Met |
| NFR-03 Families, ≥ 80% task completion | all visitor screens | — | `usability-testing.md` — sessions with family participants | **Plan ready; needs participants** |
| NFR-04 Staff publish unassisted | staff workspace | — | automated: `e2e/staff_event_flow.py`; human: staff task in `usability-testing.md` | Automated ✓; **human session pending** |
| NFR-05 Access control | — | — | `test_role_matrix.py` (incl. forged token, immediate demotion) | Met |
| NFR-06 Accessible | design tokens with measured contrast; labelled fields; accessibility needs at booking | — | design board contrast table; usability script includes keyboard-only task | Met (design); usability check pending |
| NFR-07 Phones | one breakpoint (768 px) | — | `e2e/register_and_mobile.py` — 0 px overflow on 8 pages at 390 px | Met |
| NFR-08 Deployable & handed over | — | — | `README.md`, `infra/deployment.md`, `handover/` | Met |
| NFR-09 Budget | — | — | proposal budget AUD 13,700 of 20,000; actual spend on free tiers | Met |
| NFR-10 Local demo path | — | — | `docker compose up` + seed runs with no external services | Met |
