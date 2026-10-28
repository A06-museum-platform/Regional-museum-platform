# Staff and administrator guide

Website: https://regional-museum-platform.pages.dev/ . Use your existing live
website account. Local seed accounts in the README are for disposable demos.
Refresh after a deployment; if the session ends, sign in again. A 403 means
insufficient role rather than a missing Supabase permission.

## Content and images

1. Open **Exhibitions & collections** to create/edit a record and check whether
   it is Draft or Published. Draft records remain absent from public pages.
2. For an exhibition, use its **Manage images** link, or open **Media library**,
   choose a record type and select the record by title. The actual record ID is
   displayed alongside its publication status.
3. Check the **Images for …** heading before uploading. Changing type clears the
   previous selection; no separate numeric “Load images” step is needed.
4. Upload JPG/JPEG, PNG or WebP images (up to 5 MB); convert HEIC first. MP4/WebM
   video supports up to 40 MB but cannot be chosen as an image cover.
5. To replace the public cover with a file already linked to this record, choose
   **Use as cover**. This selects the file without uploading another copy.

Image IDs identify individual media rows; they are not exhibition IDs. Gaps in
these IDs after removals are normal. Selecting a different record does not move
an existing image. For a previous mislink, confirm the intended photo and record
title with the curator before repairing it. Do not delete an image to guess its
correct destination. Routine uploads use Supabase; R2 protection starts after
that file is mirrored by the scheduled or manually dispatched recovery job.

## Other staff tasks

Use Events & workshops for event content, capacity and publication; Opening
hours / Visitor information for visitor-facing details; Bookings & check-in for
front-desk search, attendance and event registrations. Verify changes on the
public site. Payment steps in this prototype simulate payment and do not charge
real cards.

## Administrator tasks

Under administrator pages, review membership applications, manage member access,
and manage staff roles. New team members register first, then an administrator
can use **Staff accounts & roles** to grant Staff access. Role changes are checked
by the backend on the next request. Preserve the last active administrator and
keep credentials out of group chats and repository documents.

Report a problem with the page URL, record title/ID, image ID and exact error;
never include passwords, tokens or payment details. Technical recovery is
covered by the [maintenance notes](technical-maintenance-notes.md).
