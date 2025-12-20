import unittest
import os
import shutil
import json
import subprocess
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI_MODULE = "photo_meta_organizer.cli"

TEST_ROOT = Path("/tmp/pmo_e2e_test")
SRC_DIR = TEST_ROOT / "src"
DST_DIR = TEST_ROOT / "dst"
CONFIG_FILE = TEST_ROOT / "config.yaml"
PARAMS_FILE = TEST_ROOT / "params.json"


class TestPhotoMetaOrganizerE2E(unittest.TestCase):
    def setUp(self):
        # Clean start
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)
        TEST_ROOT.mkdir(parents=True)
        SRC_DIR.mkdir()
        DST_DIR.mkdir()

        # Env setup
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    def tearDown(self):
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)

    def create_dummy_file(self, path: Path, size_mb: float = 0.001):
        with open(path, "wb") as f:
            f.write(b"\0" * int(size_mb * 1024 * 1024))

    def run_cli(self, args):
        cmd = ["uv", "run", "python", "-m", CLI_MODULE] + args
        result = subprocess.run(
            cmd, env=self.env, capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result

    def test_clean_junk(self):
        # Create small file
        junk_file = SRC_DIR / "small.jpg"
        self.create_dummy_file(junk_file, size_mb=0.1)

        # Create params
        params = {
            "task": "clean-junk",
            "input_dirs": [str(SRC_DIR)],
            "threshold": 0.5,
            "dry_run": False,
        }
        with open(PARAMS_FILE, "w") as f:
            json.dump(params, f)

        # Run
        res = self.run_cli(["run-task", str(PARAMS_FILE)])
        self.assertEqual(res.returncode, 0, f"CLI Failed: {res.stderr}")

        # Verify
        # Check if small.jpg is gone from source root
        self.assertFalse((SRC_DIR / "small.jpg").exists(), "small.jpg should be moved")

        junk_dir = SRC_DIR / "junk"
        self.assertTrue(junk_dir.exists())
        self.assertTrue((junk_dir / "small.jpg").exists())

    def test_organize_fallback(self):
        # Create photo
        photo = SRC_DIR / "test.jpg"
        self.create_dummy_file(photo, size_mb=1.0)

        # Set mtime to 2023-01-01
        date_time = time.mktime((2023, 1, 1, 12, 0, 0, 0, 0, 0))
        os.utime(photo, (date_time, date_time))

        # Create params
        params = {
            "task": "organize",
            "input_dirs": [str(SRC_DIR)],
            "output_dir": str(DST_DIR),
            "dry_run": False,
        }
        with open(PARAMS_FILE, "w") as f:
            json.dump(params, f)

        # Run
        res = self.run_cli(["run-task", str(PARAMS_FILE)])
        self.assertEqual(res.returncode, 0, f"CLI Failed: {res.stderr}")

        # Verify
        # Should be in DST/2023/2023-01/test.jpg (based on file default strategy)
        # Note: Actual structure depends on implementation details of organize_photos.py
        # Let's just search recursively
        moved_files = list(DST_DIR.rglob("test.jpg"))
        self.assertEqual(len(moved_files), 1, "File should be in destination")
        self.assertIn("2023", str(moved_files[0]))

    def test_rename(self):
        # Create photo
        photo = SRC_DIR / "rename_me.jpg"
        self.create_dummy_file(photo, size_mb=1.0)

        # Set mtime
        date_time = time.mktime((2023, 5, 20, 10, 0, 0, 0, 0, 0))
        os.utime(photo, (date_time, date_time))

        # Create params
        params = {"task": "rename", "input_dirs": [str(SRC_DIR)], "dry_run": False}
        with open(PARAMS_FILE, "w") as f:
            json.dump(params, f)

        # Run
        res = self.run_cli(["run-task", str(PARAMS_FILE)])
        self.assertEqual(res.returncode, 0, f"CLI Failed: {res.stderr}")

        # Verify
        renamed = list(SRC_DIR.glob("*.jpg"))
        self.assertEqual(len(renamed), 1)
        # Expected: 20230520_100000_sys_rename_me.jpg (or similar)
        self.assertIn("20230520", renamed[0].name)
        self.assertNotEqual(renamed[0].name, "rename_me.jpg")


if __name__ == "__main__":
    unittest.main()
