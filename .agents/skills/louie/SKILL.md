---
name: louie
description: "Route Louie-specific requests to the focused Python SDK or REST API workflow while preserving least-privilege data handling. Use for any Louie.ai integration, investigation, or API request."
---

# Louie Router

- Use `louie-py` for Python, notebooks, `louieai`, `louie()`, cursors, uploads, response handling, SDK authentication, or Table AI overrides.
- Use `louie-rest-api` for curl/httpx/fetch, `/api/*`, OpenAPI, JSONL streaming, FastAPI routes, or server implementation.
- For mixed requests, use the SDK skill for the client journey and REST skill to verify the deployed endpoint contract.
- Reasoning, final-answer selection, run phases, terminal status, and raw stream messages are supported in recent `louieai`; confirm the installed version exposes a property before relying on it, and never invent one.
- The server declares the final answer. Do not present text position as the contract in either interface.

Never expose credentials, tokens, customer data, or private prompts. Prefer read-only inspection until the user authorizes an external side effect.
