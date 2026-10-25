#!/usr/bin/env python3
"""Remove the demo accounts that database/seed/seed.sql creates.

Keeps everything the museum publishes (exhibitions, collection objects,
events, opening hours, visitor information, ticket types, interest tags).
Removes the 12 demo people and everything that belongs only to them: their
roles, bookings, event registrations, memberships, interests and activity
log entries. Real accounts are never touched. Running it twice is harmless.

Usage (from the repository root, with the stack running):
  docker compose exec backend python /app/scripts/remove_demo_accounts.py
  (asks for confirmation; --yes skips the question)

Then create the first real administrator with scripts/create_admin_user.py.
"""

import argparse
import asyncio
import os
import sys

import asyncpg

DEMO_EMAILS = [
    "alice@example.com",
    "ben@example.com",
    "staff@museum.org",
    "admin@museum.org",
    "priya.sharma@example.com",
    "tom.nguyen@example.com",
    "grace.oconnor@example.com",
    "liam.papadopoulos@example.com",
    "mei.chen@example.com",
    "jack.robertson@example.com",
    "sofia.rossi@example.com",
    "noah.williams@example.com",
]


async def main(args) -> int:
    url = os.environ.get("DATABASE_URL", "postgresql://museum:museum@localhost:5432/museum")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        ids = [r["user_id"] for r in await conn.fetch(
            "SELECT user_id FROM user_account WHERE lower(email) = ANY($1::text[])", DEMO_EMAILS)]
        if not ids:
            print("No demo accounts found - nothing to do.")
            return 0
        print(f"Found {len(ids)} demo accounts.")
        if not args.yes:
            answer = input("Delete them and their bookings, registrations, memberships and activity? [y/N] ")
            if answer.strip().lower() not in ("y", "yes"):
                print("Cancelled.")
                return 1
        async with conn.transaction():
            counts = {}
            # Tables whose user foreign key has no ON DELETE CASCADE go first.
            for label, sql in [
                ("activity log entries",
                 "DELETE FROM activity_log WHERE actor_user_id = ANY($1::int[]) OR subject_user_id = ANY($1::int[])"),
                ("bookings", "DELETE FROM booking WHERE user_id = ANY($1::int[])"),
                ("old ticket reservations", "DELETE FROM ticket_reservation WHERE user_id = ANY($1::int[])"),
                ("event registrations", "DELETE FROM event_registration WHERE user_id = ANY($1::int[])"),
                ("memberships", "DELETE FROM membership WHERE user_id = ANY($1::int[])"),
                # Roles and interests cascade; media keeps its file (uploader set to NULL).
                ("accounts", "DELETE FROM user_account WHERE user_id = ANY($1::int[])"),
            ]:
                status = await conn.execute(sql, ids)
                counts[label] = int(status.split()[-1])
    finally:
        await conn.close()
    for label, n in counts.items():
        print(f"  removed {n} {label}")
    print("Demo accounts removed. Next: create your administrator with scripts/create_admin_user.py")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    sys.exit(asyncio.run(main(parser.parse_args())))
