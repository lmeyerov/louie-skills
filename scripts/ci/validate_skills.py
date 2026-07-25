#!/usr/bin/env python3
"""Validate the small, portable skill-manifest subset used by this repository."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
NAME = re.compile(r"^name:\s*([a-z0-9][a-z0-9-]*)\s*$", re.MULTILINE)
DESCRIPTION = re.compile(r"^description:\s*\S.+$", re.MULTILINE)


def main() -> int:
    manifests = sorted(SKILLS.glob("*/SKILL.md"))
    if not manifests:
        print("error: no skill manifests found", file=sys.stderr)
        return 1
    names: set[str] = set()
    for path in manifests:
        contents = path.read_text(encoding="utf-8")
        if not contents.startswith("---\n") or "\n---\n" not in contents:
            print(f"error: {path.relative_to(ROOT)} lacks YAML front matter", file=sys.stderr)
            return 1
        match = NAME.search(contents)
        if not match or not DESCRIPTION.search(contents):
            print(f"error: {path.relative_to(ROOT)} requires name and description", file=sys.stderr)
            return 1
        name = match.group(1)
        if name in names:
            print(f"error: duplicate skill name: {name}", file=sys.stderr)
            return 1
        names.add(name)
    print(f"validated {len(manifests)} skill manifest(s): {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
