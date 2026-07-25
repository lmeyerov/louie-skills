# Contributing

Contributions should be focused, safe, and reviewable.

Before opening a pull request, run:

```bash
python3 scripts/ci/validate_skills.py
./scripts/ci/secret-detection.sh
```

Add skills under `.agents/skills/<skill-name>/SKILL.md`. Keep examples synthetic and redacted, never commit credentials or private data, and follow [SECURITY.md](SECURITY.md) for sensitive reports.
