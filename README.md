# louie-skills

Installable skills for AI coding agents. This repository follows the `skills`
CLI layout used by `graphistry-skills`, while keeping its guidance, examples,
and evaluation data specific to Louie.

## Included skills

- `louie`: route between SDK and REST workflows and enforce shared safety.
- `louie-py`: use the Python/notebook SDK — cursors, uploads, reasoning versus
  final-answer access, run phases, and stream status.
- `louie-rest-api`: use deployed OpenAPI and the direct streaming, upload,
  DataThread, binary, and dataframe contracts.
- `plan`: keep lightweight durable state for explicit multi-session work.
- `review`: perform read-only correctness, security, compatibility, test, and
  documentation review.

## Install

```bash
npx skills add lmeyerov/louie-skills \
  --agent codex \
  --agent claude-code \
  --skill louie \
  --skill louie-py \
  --skill louie-rest-api \
  --yes
```

## Development

```bash
python3 scripts/ci/validate_skills.py
python3 scripts/run_journey_evals.py \
  evals/journeys/louie_api_v1.json \
  --validate-only
python3 -m unittest discover -s tests -v
python3 scripts/run_journey_evals.py \
  evals/journeys/louie_api_v1.json \
  evals/fixtures/louie_api_v1_golden.json
./scripts/ci/secret-detection.sh
```

See [evals/README.md](evals/README.md) for the persona journey methodology and
[docs/api-fidelity-notes.md](docs/api-fidelity-notes.md) for how each API claim
was verified, plus the open gaps.

Do not commit credentials, API keys, internal hostnames, customer data, raw
logs, traces, live responses, or private prompts. See [SECURITY.md](SECURITY.md).
