# ScopeLeak — Agreed Scope (MVP v0.1)

> Every feature proposed after this document was frozen is treated as a
> potential out-of-scope request. If it does not directly prove the core use
> case, it goes to [BACKLOG.md](BACKLOG.md).

Frozen: 2026-10-12 · Deadline: 2026-10-18 23:59 PDT

## Core use case

A freelancer receives a new message from a client. Before replying, they paste
it into ScopeLeak together with the original agreement and learn whether the
request is **included**, **extra**, or **ambiguous** — with quotes from both
documents that justify the verdict.

**Know before you say yes.**

## In scope

1. Load the original agreement (PDF or TXT).
2. Paste a new client message.
3. AI extraction and classification of the request(s) in the message.
4. Three verdicts only: `included`, `extra`, `ambiguous`.
5. Every verdict cites the agreement and the message; citations are verified
   deterministically by code. A verdict whose citations cannot be found is
   downgraded to `ambiguous`.
6. Hours and hourly rate are entered by the user — the AI never invents them.
7. A copyable draft reply to the client.
8. Configurable model endpoint and model ID (any OpenAI-compatible server;
   default: Ollama on localhost).
9. An evaluation dataset (4 scenarios, 30–40 annotated requests) and a
   command-line evaluation script, kept separate from the UI.

## Out of scope

Everything else. See [BACKLOG.md](BACKLOG.md).

## Non-negotiables

- Real client documents are processed locally by default.
- Remote inference is used only with synthetic or anonymised data.
- The tool suggests; the freelancer decides. Nothing is sent to the client
  automatically.
