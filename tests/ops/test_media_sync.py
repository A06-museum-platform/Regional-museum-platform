"""Prevent a standby sync from overwriting outage uploads or using a local DB guard."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MediaSyncSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.calls = self.directory / "calls"
        for name, body in {
            "docker": '[ "${OPS_DB_FAIL:-0}" = 1 ] && exit 1\nprintf "%s\\n" "${OPS_R2_ROWS:-0}"',
            "rclone": 'printf "%s\\n" "$*" >> "$OPS_CALLS"',
        }.items():
            path = self.directory / name
            path.write_text("#!/bin/sh\n" + body + "\n")
            path.chmod(0o700)
        self.env = dict(os.environ, PATH=self.temp.name + os.pathsep + os.environ["PATH"],
                        DB_TARGET="staging", DATABASE_URL_STAGING="postgresql://test-transport/unused",
                        MIRROR_DIR=str(self.directory / "mirror"), LOG=str(self.directory / "mirror.log"),
                        OPS_CALLS=str(self.calls))

    def tearDown(self):
        self.temp.cleanup()

    def script(self, script, *arguments, **environment):
        return subprocess.run(["bash", str(ROOT / "scripts" / script), *arguments], cwd=ROOT,
                              env=dict(self.env, **environment), capture_output=True, text=True)

    def test_local_database_cannot_authorize_remote_sync(self):
        result = self.script("mirror_media.sh", "--dest", "r2", DB_TARGET="local")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_database_failure_prevents_transfers(self):
        result = self.script("nightly_media.sh", OPS_DB_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_r2_outage_uploads_are_backed_up_without_supabase_overwrite(self):
        result = self.script("nightly_media.sh", OPS_R2_ROWS="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        self.assertNotIn("supabase:", calls)
        self.assertIn("sync r2:museum-media", calls)
        self.assertIn("check r2:museum-media " + str(self.directory / "mirror/r2"), calls)

    def test_normal_sync_checks_the_actual_mirror_directory(self):
        result = self.script("nightly_media.sh", OPS_R2_ROWS="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        self.assertIn("sync supabase:museum-media r2:museum-media", calls)
        self.assertIn("check supabase:museum-media r2:museum-media --download", calls)
        self.assertIn("check supabase:museum-media " + str(self.directory / "mirror/supabase"), calls)


if __name__ == "__main__":
    unittest.main()
