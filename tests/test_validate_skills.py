from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "validate_skills.py"

SPEC = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SkillManifestValidationTests(unittest.TestCase):
    def _manifest(self, folder: str, frontmatter: str) -> Path:
        directory = Path(self.temp_directory.name) / folder
        directory.mkdir()
        path = directory / "SKILL.md"
        path.write_text(f"---\n{frontmatter}---\n\n# Test\n", encoding="utf-8")
        return path

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_quoted_description_with_colon_is_valid(self) -> None:
        path = self._manifest(
            "example",
            'name: example\ndescription: "Use this for workflows: including tests."\n',
        )
        self.assertEqual(VALIDATOR.validate_manifest(path), "example")

    def test_unquoted_description_is_rejected(self) -> None:
        path = self._manifest(
            "example",
            "name: example\ndescription: Invalid YAML: colon value\n",
        )
        with self.assertRaisesRegex(ValueError, "double-quoted"):
            VALIDATOR.validate_manifest(path)

    def test_unknown_frontmatter_field_is_rejected(self) -> None:
        path = self._manifest(
            "example",
            'name: example\ndescription: "Valid."\nversion: "1"\n',
        )
        with self.assertRaisesRegex(ValueError, "unsupported version"):
            VALIDATOR.validate_manifest(path)

    def test_folder_must_match_skill_name(self) -> None:
        path = self._manifest(
            "wrong-folder",
            'name: example\ndescription: "Valid."\n',
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            VALIDATOR.validate_manifest(path)
