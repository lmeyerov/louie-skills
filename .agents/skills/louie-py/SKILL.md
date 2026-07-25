---
name: louie-py
description: "Build, debug, or explain Python and notebook workflows using the louieai SDK: authentication, cursors and threads, DataFrame/image/binary uploads, streaming, reasoning and final-answer access, run phases, response handling, sharing, and Table AI overrides. Use for louieai, louie-py, `louie()`, `Cursor`, or Python integration with Louie."
---

# Louie Python SDK

Use this for Python/notebook integrations; use `louie-rest-api` for direct HTTP or FastAPI work. The reasoning-aware accessors below require a recent `louieai`. When a local `louie-py` checkout is available, inspect its `src/louieai/` and `docs/`; otherwise confirm the installed version exposes a property before relying on it. Never recommend private attributes.

## Cursor basics

```python
from louieai import louie

lui = louie(share_mode="Private")
lui("Summarize the anomalies.")
print(lui.text)
```

The cursor returns itself and continues its thread. `lui[-1]`, `lui[-2]`, ... return history proxies exposing the same properties for earlier responses. Use `lui.new()` for a fresh thread with inherited configuration, and `lui.thread_id` / `lui.url` to reference it.

Analyze pandas data with `lui("question", df)` or `lui(df, "question")`. Use `upload_image()` or `upload_binary()` for media. `format=` defaults to parquet and also accepts csv, json, jsonl, and arrow.

## Final answers, reasoning, phases, and status

The server declares which output element is the final answer, and the SDK surfaces it. Do not treat text position as the contract.

- `lui.text` / `lui.final_text`: the server-declared final answer when present, otherwise the **last** non-reasoning text.
- Lower-level `Response.text` returns the **first** non-reasoning text unless `include_reasoning` is true and a final-answer pointer exists. `Cursor.text` and `Response.text` are deliberately different; never claim they match.
- `lui.final_texts` / `lui.final_text_elements`: all non-reasoning text output.
- `lui.reasoning_text`, `lui.reasoning_texts`, `lui.reasoning_elements`: provisional draft text, populated only when reasoning was requested.
- `lui.status`: normalized `scheduled`, `running`, `succeeded`, `failed`, `cancelled`, `interrupted`, or `unknown`. A terminal failure outranks run state.
- `lui.succeeded`, `lui.terminal`, `lui.terminal_error`: stream-level outcome, distinct from agent run state. `succeeded` is `None` when no terminal record arrived, which is how you detect a truncated or timed-out stream.
- `lui.run_updates` (ordered snapshots), `lui.phases` (latest per phase node), `lui.phase_updates`, `lui.root_run`, `lui.token_flow`.
- `lui.stream_messages`: ordered raw stream envelopes when fidelity matters.
- `lui.trace_events`: server trace payloads. Distinct from the `traces` request flag, and often empty — the server emits trace records only conditionally, so never assume they arrive.

Request reasoning and traces per session or per call; both are also constructor arguments:

```python
lui = louie(share_mode="Private", include_reasoning=True, traces=True)
lui.include_reasoning = False                       # session default
lui("Explain the spike", include_reasoning=True)    # per-query override
print(lui.reasoning_text)                           # draft chatter
print(lui.text)                                     # server-declared final answer
```

Reasoning is off by default; keep it off unless the user wants draft output. With it on, `lui.elements` gains normalized `{"type": "reasoning"}` entries.

## Run-tree shape

Each `StreamingApiMessageRunUpdate` carries a `run_node` with `id`, `parent_id`, `children`, `state`, `node_type` (`Run` for the root, `MethodRun` for phases), `run_type`, `results`, `token_flow`, and `final_answer`. Note:

- The hierarchy fields are `parent_id` and `children`, nested under `run_node`.
- `final_answer` is `None` until the root run reaches `state="Done"`.
- Run updates repeat per node, so upsert by `run_node.id`; `lui.phases` already does this.
- A child phase can end `Cancelled` while the root ends `Done`. Child state does not imply overall failure — use `lui.status` or `lui.succeeded`.

## Errors and the normalized elements view

Check `lui.has_errors`, then read the raw dicts in `lui.errors`. The current server `ExceptionElement` carries its message in `text`.

Treat `lui.elements` as a lossy convenience view, not a protocol record. It emits `{"type", "value"}` entries that **drop element IDs**, so it cannot be correlated with the server's final-answer pointer, and it **reorders**, hoisting errors ahead of text rather than preserving server position. Its error branch reads `message`, so current server errors can render as `"Unknown error"`. For fidelity use `lui.errors`, `lui.final_text`, or `lui.stream_messages`. Report these as `louie-py` bugs rather than silently working around them. Never surface a traceback by default.

## Authentication, sharing, and recovery

- Prefer an authenticated PyGraphistry client or environment configuration. Service accounts use `GRAPHISTRY_PERSONAL_KEY_ID`, `GRAPHISTRY_PERSONAL_KEY_SECRET`, and optional `GRAPHISTRY_ORG_NAME`.
- Other environment configuration: `GRAPHISTRY_USERNAME`, `GRAPHISTRY_PASSWORD`, `GRAPHISTRY_API_KEY`, `LOUIE_URL`, `LOUIE_TIMEOUT`, `LOUIE_STREAMING_TIMEOUT`.
- For explicit enterprise configuration use `graphistry_server=` for the Graphistry auth host and `server_url=` for Louie. The legacy `server=` client parameter is rejected.
- Local desktop deployments may support `anonymous=True`, which cannot be combined with Graphistry credentials. A pre-fetched `token=` is supported; never log or persist it.
- Start with `Private`; choose `Organization` only for the intended active-org audience. Keep credentials, tokens, and secrets out of prompts, notebooks, URLs, logs, and committed examples.
- Default service is `https://den.louie.ai`. Tune `timeout` and `streaming_timeout` instead of retrying blindly. After an inactivity timeout, check `lui.succeeded` / `lui.status` before assuming the work finished, and reuse `lui.thread_id` rather than resubmitting.
- Use `TableAIOverrides` or documented `table_ai_*` parameters; do not invent override names.

## Authorized live testing

Only after the user authorizes it, point `LOUIE_URL` at their dev deployment using untracked environment variables. Announce the remote side effect first, keep requests small, non-sensitive, and `Private`, and never persist credentials, tokens, prompts, or raw responses. If the deployment uses a private CA, fix local trust rather than disabling verification in committed code.
