"""Exercise the real migration runner against disposable PostgreSQL databases.

MIGRATION_TEST_CONTAINER is a test-only PostgreSQL container. Only the docker
transport is redirected; all migration SQL and transaction handling run in PG.
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = os.environ.get("MIGRATION_TEST_CONTAINER")
DOCKER = shutil.which("docker")


@unittest.skipUnless(CONTAINER and DOCKER, "needs an explicitly selected test container")
class MigrationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.database = "museum_ops_" + uuid.uuid4().hex[:12] + "_test"
        self.psql("CREATE DATABASE " + self.database, database="postgres")
        self.temp = tempfile.TemporaryDirectory()
        shim = Path(self.temp.name) / "docker"
        shim.write_text("""#!/usr/bin/env python3
import os, subprocess, sys
a = sys.argv[1:]
if not a or a[0] != 'run' or 'psql' not in a:
    raise SystemExit('Only test psql transport is allowed')
i = a.index('psql')
raise SystemExit(subprocess.run([os.environ['OPS_DOCKER_BIN'], 'exec', '-i',
    os.environ['MIGRATION_TEST_CONTAINER'], 'psql', '-U', 'museum', '-d',
    os.environ['OPS_DATABASE'], *a[i + 2:]]).returncode)
""")
        shim.chmod(0o700)
        self.env = dict(
            os.environ,
            PATH=self.temp.name + os.pathsep + os.environ["PATH"],
            OPS_DOCKER_BIN=DOCKER,
            OPS_DATABASE=self.database,
            DB_TARGET="staging",
            DATABASE_URL_STAGING="postgresql://test-transport/unused",
        )

    def tearDown(self):
        self.temp.cleanup()
        self.psql("DROP DATABASE " + self.database, database="postgres")

    def psql(self, sql, database=None, atomic=False, check=True):
        command = [DOCKER, "exec", "-i", CONTAINER, "psql", "-U", "museum",
                   "-d", database or self.database, "-v", "ON_ERROR_STOP=1", "-tA"]
        if atomic:
            command.append("--single-transaction")
        result = subprocess.run(command, input=sql, text=True, capture_output=True)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def script(self, name, check=True, database=None):
        result = subprocess.run(["bash", str(ROOT / "scripts" / name)], cwd=ROOT,
                                env=dict(self.env, OPS_DATABASE=database or self.database),
                                text=True, capture_output=True)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def render(self, path):
        return subprocess.check_output(
            ["python3", str(ROOT / "scripts/lib/migration_sql.py"), str(path)], text=True)

    def versions(self):
        return self.psql("SELECT filename FROM schema_migrations ORDER BY filename;").stdout

    def test_fresh_database_and_replay(self):
        self.assertNotEqual(self.script("check_migrations.sh", check=False).returncode, 0)
        self.script("apply_migrations.sh")
        expected = [p.name for p in sorted((ROOT / "database/migrations").glob("0*.sql"))]
        self.assertEqual(self.versions().splitlines(), expected)
        self.script("check_migrations.sh")
        before = self.versions()
        self.script("apply_migrations.sh")
        self.assertEqual(self.versions(), before)

    def test_october_snapshot_preserves_materials_and_accounts(self):
        snapshot = (ROOT / "database/regional_museum_1010.sql").read_text()
        snapshot = snapshot.replace("SET transaction_timeout = 0;\n", "")
        self.psql(snapshot, atomic=True)
        query = "SELECT item_id,materials FROM collection_item ORDER BY item_id;"
        before = self.psql(query).stdout
        accounts = self.psql("SELECT count(*) FROM user_account;").stdout
        self.script("apply_migrations.sh")
        self.assertEqual(self.psql(query).stdout, before)
        self.assertEqual(self.psql("SELECT count(*) FROM user_account;").stdout, accounts)
        self.script("check_migrations.sh")
        self.script("apply_migrations.sh")
        # Compare real column shapes, not only version records. Snapshot-only
        # fields may stay, but every canonical field must exist compatibly.
        reference = self.database + "_reference_test"
        self.psql("CREATE DATABASE " + reference, database="postgres")
        try:
            self.script("apply_migrations.sh", database=reference)
            columns = (
                "SELECT table_name,column_name,data_type,"
                "coalesce(character_maximum_length::text,''),is_nullable "
                "FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name<>'schema_migrations';"
            )
            required = set(self.psql(columns, database=reference).stdout.splitlines())
            actual = set(self.psql(columns).stdout.splitlines())
            self.assertFalse(required - actual, "Missing/incompatible canonical fields: " + str(required - actual))
        finally:
            self.psql("DROP DATABASE " + reference, database="postgres")

    def test_failed_migration_rolls_back_ddl_data_and_version(self):
        self.psql("CREATE TABLE schema_migrations(filename text PRIMARY KEY);")
        path = Path(self.temp.name) / "999_transaction_probe.sql"
        path.write_text("CREATE TABLE transaction_probe(id int); SELECT 1/0;")
        result = self.psql(self.render(path), atomic=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.psql("SELECT count(*) FROM schema_migrations;").stdout.strip(), "0")
        self.assertEqual(self.psql("SELECT to_regclass('transaction_probe') IS NULL;").stdout.strip(), "t")
        path.write_text("CREATE TABLE transaction_probe(id int); INSERT INTO transaction_probe VALUES (1);")
        self.psql(self.render(path), atomic=True)
        self.psql(self.render(path), atomic=True)
        self.assertEqual(self.psql("SELECT count(*) FROM transaction_probe;").stdout.strip(), "1")

    def test_incompatible_legacy_column_is_not_silently_accepted(self):
        self.psql("CREATE TABLE schema_migrations(filename text PRIMARY KEY); "
                  "CREATE TABLE collection_item(materials integer); "
                  "INSERT INTO collection_item VALUES (123);")
        migration = ROOT / "database/migrations/009_content_enrichment.sql"
        result = self.psql(self.render(migration), atomic=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incompatible", result.stderr)
        self.assertEqual(self.psql("SELECT materials FROM collection_item;").stdout.strip(), "123")
        self.assertEqual(self.psql("SELECT count(*) FROM schema_migrations;").stdout.strip(), "0")

    def test_two_runners_do_not_duplicate_migrations(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.script("apply_migrations.sh"), range(2)))
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.script("check_migrations.sh")


if __name__ == "__main__":
    unittest.main()
