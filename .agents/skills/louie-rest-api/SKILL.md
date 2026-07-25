---
name: louie-rest-api
description: "Build, debug, document, or test direct Louie FastAPI/REST integrations: authentication, streaming and singleshot chat, uploads, DataThreads, dataframe retrieval, run-tree metadata, and OpenAPI contracts. Use for curl, httpx, fetch, `/api/*`, FastAPI routes, or server-side Louie API requests."
---

# Louie REST API

Use direct HTTP only when it is the requested integration surface; otherwise prefer `louie-py`. Do not guess contracts. Inspect `GET /api/openapi.json` or `/api/docs` on the target deployment first. For local server source work, inspect `graphistrygpt/api/api.py` and `graphistrygpt/api/routes/` in an available `graphistrygpt` checkout.

The service mounts routes below `/api`. Verified paths include:

- `GET /api/health`, `/api/openapi.json`, `/api/docs`
- `POST /api/auth/basic`, `/api/auth/keypair`, `/api/auth/token/refresh`, `/api/auth/token/verify`
- `POST /api/chat/` (JSONL stream) and `/api/chat_singleshot/`
- `POST /api/chat_upload/` for multipart data/media uploads
- `GET /api/dthreads` (list) and `GET /api/dthread/{identifier}` (lookup by ID or name) — note the plural/singular split
- `GET /api/dthread/{dthread_id}/df/block/{block_id}/arrow` for Arrow IPC, or `/json`
- `GET /api/chat/{dthread_id}/binary/{element_id}` with optional `/download` or `/info`

Deployments may also expose skill-management and capability routes such as `/api/skills/*`, `/api/dthreads/{dthread_id}/active-skills`, `/api/capabilities`, and `/api/account`. Confirm them per deployment.

## What OpenAPI does and does not tell you

OpenAPI is authoritative for routes, path/query parameters, and the multipart upload body. It is **not** a complete contract for chat: the chat request body is declared as a free-form object, and the `StreamingApiMessage*` records are not published as schemas. Take stream and chat-field shapes from server source or these notes, and verify against the deployment.

Typical chat fields include `query`, `agent`, `dthread_id`, `share_mode`, `ignore_traces`, and `include_reasoning`. `include_reasoning` defaults to false; enabling it adds provisional draft text, not just the final answer.

## Authentication

Use `Authorization: Bearer $LOUIE_JWT`; never put a JWT in a query string, source, or log. `/api/auth/basic` takes `username` and `password` as **query parameters**, so those credentials can reach access logs and shell history — prefer keypair or personal-key auth for anything non-interactive, and treat any basic-auth URL as sensitive. On 401/403, diagnose credentials and organization access before retrying.

## Stream records

Handle discriminated records instead of treating every line as an element:

- `StreamingApiMessageStart` — `{dthread_id}`, thread identity.
- `StreamingApiMessageOutputUpdate` — `{payload, position}`; the element lives in `payload`, whose `id` repeats as it updates. Upsert by `payload.id`.
- `StreamingApiMessageTrace` — trace payload, emitted only conditionally. Do not assume it appears just because traces were requested.
- `StreamingApiMessageRunUpdate` — `{run_node}` with `id`, `parent_id`, `children`, `state`, `node_type` (`Run` root, `MethodRun` phase), `run_type`, `results`, `token_flow`, and `final_answer`.
- `StreamingApiMessageTerminal` — `{success, error}`, the stream-level outcome. Uploads may emit more than one.

Run-tree specifics: hierarchy is `run_node.parent_id` plus `run_node.children`, nested under `run_node`. `final_answer` stays null until the root run reaches `state="Done"`, then holds the output element ID. Run updates repeat per node, so upsert by `run_node.id` for a progress UI. Observed states include `Running`, `Done`, and `Cancelled`; a child phase can end `Cancelled` while the root ends `Done`, so never infer overall failure from a child.

Select the final element by the root run's `final_answer` ID. For older streams without it, a last-text fallback is client policy, not a server guarantee. Absence of a terminal record means the outcome is unknown, not success.

## Other contracts

`/api/chat_singleshot/` returns a JSON array of the complete message sequence. `/api/chat_upload/` uses multipart form fields; do not send its files as ordinary JSON. Exception output elements carry their message in the server's `text` field; verify legacy aliases before assuming `message`.

Start chats private. On timeout or a missing terminal message, preserve the thread ID and determine whether the work completed before resubmitting. Treat development-only endpoints as non-portable.

## Authorized live testing

Only after explicit authorization may a live test target a non-production deployment; use the URL the user provides rather than assuming one. Supply credentials via untracked environment variables, announce the remote side effect, and use a small non-sensitive request with `Private` visibility. If the deployment uses a private CA, fix local trust instead of disabling certificate verification in committed code. Never persist credentials, tokens, sensitive prompts, or raw responses.
