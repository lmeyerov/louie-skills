#!/usr/bin/env python3
"""Validate the small, portable skill-manifest subset used by this repository."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
REQUIRED_FIELDS = {"name", "description"}


def validate_manifest(path: Path) -> str:
    """Return the validated skill name or raise ValueError."""
    contents = path.read_text(encoding="utf-8")
    if not contents.startswith("---\n"):
        raise ValueError("lacks opening YAML front matter delimiter")
    end = contents.find("\n---\n", 4)
    if end < 0:
        raise ValueError("lacks closing YAML front matter delimiter")

    fields: dict[str, str] = {}
    for line_number, line in enumerate(contents[4:end].splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"front matter line {line_number} lacks ':'")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in fields:
            raise ValueError(f"duplicate front matter field: {key}")
        fields[key] = value.strip()

    if set(fields) != REQUIRED_FIELDS:
        missing = sorted(REQUIRED_FIELDS - set(fields))
        extra = sorted(set(fields) - REQUIRED_FIELDS)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unsupported " + ", ".join(extra))
        raise ValueError("invalid front matter fields: " + "; ".join(details))

    name = fields["name"]
    if NAME.fullmatch(name) is None:
        raise ValueError("name must use lowercase letters, digits, and hyphens")
    if path.parent.name != name:
        raise ValueError(
            f"skill folder {path.parent.name!r} does not match name {name!r}"
        )

    try:
        description = json.loads(fields["description"])
    except json.JSONDecodeError as exc:
        raise ValueError(
            "description must be a non-empty JSON/YAML double-quoted string"
        ) from exc
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be a non-empty string")
    return name


def main() -> int:
    manifests = sorted(SKILLS.glob("*/SKILL.md"))
    if not manifests:
        print("error: no skill manifests found", file=sys.stderr)
        return 1

    names: set[str] = set()
    for path in manifests:
        try:
            name = validate_manifest(path)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"error: {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
            return 1
        if name in names:
            print(f"error: duplicate skill name: {name}", file=sys.stderr)
            return 1
        names.add(name)

    print(f"validated {len(manifests)} skill manifest(s): {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
