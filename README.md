# louie-skills

Installable skills for AI coding agents. This repository follows the `skills` CLI layout used by `graphistry-skills`, while keeping its contents, examples, and test data specific to Louie.

## Install

```bash
npx skills add lmeyerov/louie-skills \
  --agent codex \
  --agent claude-code \
  --skill louie \
  --yes
```

## Included skills

- `louie`: the starter routing skill. Expand it or add focused skills under `.agents/skills/`.

## Development

```bash
python3 scripts/ci/validate_skills.py
./scripts/ci/secret-detection.sh
```

Do not commit credentials, API keys, customer data, raw logs, or private prompts. See [SECURITY.md](SECURITY.md).
