import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from factory.version import template_commit


class LocalReleaseTests(unittest.TestCase):
    def test_archive_provenance_without_git_and_detect_changed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "office.py"
            source.write_text("print('test')", encoding="utf-8")
            (root / "factory-release.json").write_text(json.dumps({
                "commit": "a" * 40,
                "files": {"office.py": hashlib.sha256(source.read_bytes()).hexdigest()},
            }), encoding="utf-8")
            self.assertEqual(template_commit(root), "a" * 40)
            source.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "изменён"):
                template_commit(root)

    def test_manifest_cannot_read_outside_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "factory-release.json").write_text(json.dumps({
                "commit": "b" * 40, "files": {"../private": "0" * 64},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Отсутствует"):
                template_commit(root)
