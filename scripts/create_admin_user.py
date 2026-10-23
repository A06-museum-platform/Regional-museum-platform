#!/usr/bin/env python3
"""Create an administrator account, or promote an existing one.

At handover the museum replaces the demo accounts with its own. Run this
once for the first real administrator; after that, administrators manage
everyone else on the "Staff accounts & roles" screen.

Usage (from the repository root, with the stack running):
  docker compose exec backend python /app/scripts/create_admin_user.py \
      --email jo.citizen@museum.org --first Jo --last Citizen
  (prompts for the password; --password is accepted for scripting)

Outside Docker set DATABASE_URL, e.g.
  DATABASE_URL=postgresql://museum:museum@localhost:5432/museum \
      python scripts/create_admin_user.py --email ... --first ... --last ...
"""

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

# Import the backend's own password hashing so the hash format always matches.
for candidate in (Path(__file__).resolve().parents[1] / "backend", Path("/app")):
    if (candidate / "app" / "core" / "security.py").exists():
        sys.path.insert(0, str(candidate))
        break

import asyncpg  # noqa: E402

from app.core.security import hash_password  # noqa: E402


async def main(args) -> int:
    url = os.environ.get("DATABASE_URL", "postgresql://museum:museum@localhost:5432/museum")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            user_id = await conn.fetchval(
                "SELECT user_id FROM user_account WHERE lower(email) = lower($1)", args.email)
            if user_id is None:
                if len(args.password) < 8:
                    print("Password must be at least 8 characters.", file=sys.stderr)
                    return 1
                user_id = await conn.fetchval(
                    "INSERT INTO user_account (email, password_hash, first_name, last_name) "
                    "VALUES ($1, $2, $3, $4) RETURNING user_id",
                    args.email, hash_password(args.password), args.first, args.last)
                action = "created"
            else:
                if args.password:
                    await conn.execute("UPDATE user_account SET password_hash = $1 WHERE user_id = $2",
                                       hash_password(args.password), user_id)
                await conn.execute("UPDATE user_account SET is_active = TRUE WHERE user_id = $1", user_id)
                action = "promoted"
            await conn.execute(
                "INSERT INTO user_role (user_id, role_id) SELECT $1, role_id FROM role "
                "WHERE lower(role_name) IN ('visitor', 'admin') ON CONFLICT DO NOTHING", user_id)
            await conn.execute(
                "INSERT INTO activity_log (actor_name, actor_role, action, target, subject_user_id) "
                "VALUES ('Setup script', 'system', 'role.changed', $1, $2)",
                f"{args.email} → admin", user_id)
    finally:
        await conn.close()
    print(f"Administrator {action}: {args.email}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--first", default="Museum")
    parser.add_argument("--last", default="Administrator")
    parser.add_argument("--password", help="omit to be prompted (recommended)")
    ns = parser.parse_args()
    if ns.password is None:
        ns.password = getpass.getpass("Password (leave blank to keep an existing account's password): ")
    sys.exit(asyncio.run(main(ns)))
