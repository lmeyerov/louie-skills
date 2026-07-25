# Louie skill journey evaluations

`journeys/louie_api_v1.json` is a persona × task pressure suite for:

- notebook data analysts;
- security investigators;
- application developers; and
- platform operators.

The suite covers discovery, text and DataFrame work, multi-turn cursors, history,
reasoning versus final-answer semantics, run phases/progress, mixed or partial
streams, error recovery, SDK/REST handoff, contract discovery, authentication,
privacy/organization choices, compatibility, and live-test safety.

Each case is labeled:

- `current`: guidance verified against `louie-py`, the FastAPI source, or a live
  deployment.
- `product-gap`: behavior the protocol enables or users need, but the SDK does
  not expose faithfully. Answers must describe the gap rather than invent an API.

## Run locally

```bash
# Validate schema, coverage, personas, case IDs, and regexes
python3 scripts/run_journey_evals.py \
  evals/journeys/louie_api_v1.json \
  --validate-only

# Test the evaluator's pass and failure behavior
python3 -m unittest discover -s tests -v

# Score the sanitized expected-answer fixture
python3 scripts/run_journey_evals.py \
  evals/journeys/louie_api_v1.json \
  evals/fixtures/louie_api_v1_golden.json
```

Add `--json-output <path>` to write aggregate-only metrics. Point it at a
scratch path for routine runs; only commit a metrics file when it materially
supports a quality decision.

The golden fixture is a checked-in, sanitized oracle for evaluator regression
testing. It is not evidence that arbitrary agents will answer correctly.
Forward-test fresh agents with only the relevant skill and raw prompts, then
score their temporary response maps with the same command.

## Recorded aggregate results

`results/louie_api_v1_forward_metrics.json` holds the latest isolated
skill-enabled pass over this suite: **22/23 (95.7%)**.

The single failure is `notebook_dataframe_followup`, which exceeds its line
budget (16 > 14) with otherwise correct content. It is left failing on purpose:
raising the cap to accommodate the answer would fit the benchmark to the model
rather than measure it.

Only the current suite's metrics are kept. Results from earlier revisions of the
suite are not comparable — the case set changed — so they are not retained, to
avoid implying a like-for-like trend.

These files contain counts and failed case IDs only. They contain no prompts,
answers, traces, credentials, or live-service data.

## Keeping the suite honest

Journeys encode claims about a real API, so they go stale when that API moves.
Several cases in this suite were rewritten after live validation disproved
assertions that source reading alone had supported — see
[`docs/api-fidelity-notes.md`](../docs/api-fidelity-notes.md).

Never commit credentials, JWTs, internal hostnames, customer data, private
prompts, traces, raw live responses, or unsanitized forward-test output. Do not
weaken a journey to fit an answer; correct the skill or the source reference
when the evidence warrants it.
