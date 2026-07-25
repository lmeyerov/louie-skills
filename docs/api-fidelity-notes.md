# API fidelity notes

These notes record what the Louie skills assert, how each claim was verified, and
what remains unresolved. Skills are only as good as the contract they describe,
so anything here that goes stale should be re-verified before the skills are
trusted again.

Verification levels used below:

- **live** — observed against a running deployment.
- **source** — read from `louie-py` or `graphistrygpt` source.

## REST contract

| Claim | Level | Note |
| --- | --- | --- |
| Routes for health, auth, chat, singleshot, upload, dthreads, dataframe blocks, and binaries exist as documented | live | Confirmed against the deployment's published OpenAPI |
| `GET /api/dthreads` lists, `GET /api/dthread/{identifier}` looks up | live | The plural/singular split is real and easy to get wrong |
| Dataframe blocks are served at `/df/block/{block_id}/arrow` (Arrow IPC) and `/json` | live | |
| Deployments may also expose `/api/skills/*`, `/api/dthreads/{id}/active-skills`, `/api/capabilities`, `/api/account`, `/api/auth/sso/*`, `/api/image` | live | Not covered by the skills; confirm per deployment |

### Corrections that live testing forced

1. **OpenAPI is not a complete chat contract.** The chat request body is declared
   as a free-form object and the `StreamingApiMessage*` records are not published
   as schemas. OpenAPI is authoritative for routes, parameters, and the multipart
   upload body only. Earlier guidance told readers to "check OpenAPI for fields",
   which would have dead-ended them.
2. **`/api/auth/basic` takes credentials as query parameters.** They can reach
   access logs, proxies, and shell history. Non-interactive callers should prefer
   keypair or personal-key auth.

## Stream records

Observed record types: `StreamingApiMessageStart` (`dthread_id`),
`StreamingApiMessageOutputUpdate` (`payload`, `position`),
`StreamingApiMessageRunUpdate` (`run_node`), and
`StreamingApiMessageTerminal` (`success`, `error`).

`run_node` carries `id`, `parent_id`, `children`, `state`, `node_type`,
`run_type`, `results`, `token_flow`, and `final_answer`.

| Claim | Level | Note |
| --- | --- | --- |
| Hierarchy fields are `run_node.parent_id` and `run_node.children` | live | Earlier drafts said a top-level `parent`; that was wrong |
| `final_answer` is null until the root run reaches `state="Done"` | live | Then it holds an output element ID, matching an emitted element |
| Run updates repeat per node | live | 8 records for 2 nodes; consumers must upsert by `run_node.id` |
| A child `MethodRun` can end `Cancelled` while the root ends `Done` | live | Child state does not imply overall failure |
| `StreamingApiMessageTrace` is emitted only conditionally | **unverified** | No trace record appeared even with traces and reasoning enabled on small queries. Treat trace availability as unproven |

## SDK surface

The reasoning-aware accessors (`stream_messages`, `run_updates`, `phases`,
`root_run`, `status`, `terminal`, `succeeded`, `final_text`, `reasoning_text`,
and friends) are present on both the cursor and its history proxies.

| Claim | Level | Note |
| --- | --- | --- |
| `Cursor.text` resolves the server-declared final answer, falling back to the last non-reasoning text | live | |
| `Response.text` returns the *first* non-reasoning text | source | Deliberately different from the cursor; do not conflate |
| `louie(traces=True, include_reasoning=True)` is accepted, and both are overridable per call | live | An earlier draft asserted the opposite; that assertion was written against an older release |
| `include_reasoning=True` adds a normalized `{"type": "reasoning"}` entry and populates `reasoning_texts` | live | |
| `succeeded` is `None` when no terminal record arrived | source | This is how callers detect a truncated stream |
| History proxies retain run metadata | live | `lui[-2].run_updates` is populated |

**Basis.** The SDK behavior above was verified against `louie-py` commit
`88181e4`. That work merged to `main` as `d0eedbd` ("feat: reasoning-aware
response API", PR #44); the only source difference between the two is a
docstring that replaced example credentials with placeholders, so these notes
describe what actually landed.

**Version sensitivity.** As of that merge the accessors sit under `[Unreleased]`
in the changelog — the newest tag is `v0.8.1`, which predates them. Anyone
installing a published `louieai` will not have them. Guard with `hasattr` or a
version check; `text`, `errors`, and `has_errors` exist in both generations.

Re-verify this table when the next release tags, and re-run the journey suite
after any change touching streaming, elements, or auth.

## Open product gaps

These are tracked as `product-gap` journeys so the skills keep describing the
gap instead of papering over it.

1. **`Cursor.elements` is lossy.** It emits `{"type", "value"}` entries that drop
   element IDs, so entries cannot be correlated with the server's `final_answer`
   pointer, and it reorders output, hoisting errors ahead of text rather than
   preserving server position. Fidelity alternatives: `stream_messages`,
   `final_text`, `errors`.
   *Desired:* preserve element IDs and server ordering in the normalized view.

2. **`Cursor.elements` error alias mismatch.** The error branch reads a `message`
   field, but the current server `ExceptionElement` carries its message in
   `text`, so real errors can render as `"Unknown error"`.
   *Desired:* read `text` with `message` as a legacy fallback.

Both are `louie-py` issues. This repository only documents them; it does not
carry a fix.

## Unverified and out of scope

- Trace record emission (see above).
- Upload, binary, and dataframe-block round trips were checked against the
  published contract but not exercised end to end with real payloads.
- Behavior of releases other than the one inspected. Re-run the journey suite
  after any SDK or server change that touches streaming, elements, or auth.
