# Backlog — Ideas That Did Not Make the Cut

Good ideas, honestly. They were proposed after the scope in
[SCOPE.md](SCOPE.md) was agreed, so ScopeLeak treats them the way it would
treat any client request: politely, and later.

| Proposed feature | Why it is out (for now) |
| --- | --- |
| Historical analysis of entire conversations | The single-message flow proves the use case first |
| Scope Timeline visualisation | Nice to look at, not needed to prove detection works |
| Model Manager UI (Refresh models, Test connection) | Two config fields cover laptop → workstation |
| Explicit LM Studio / vLLM adapters | Already reachable through the OpenAI-compatible endpoint |
| Benchmark inside the UI | A CLI script produces the same numbers |
| AI-estimated hours | Invented estimates are the easiest thing to get wrong. **The first user asked for it** ("I want 'extra, ~X hours, £Y', not just the verdict"): the strongest candidate for v0.2, maybe as a range the user confirms |
| Database, multi-user, "ScopeLeak Studio" | One freelancer, one project, one message |
| PDF export of proposals | Copy-to-clipboard is enough |
| Gmail / Outlook / WhatsApp / Stripe integrations | More complexity and more privacy surface |
| Docker Compose | Ollama on Windows + Docker adds friction, not value |
| Telling *claims* (SLA credits, refunds) and *rights* (portfolio use) apart from *work requests* | Found in the SaaS test, confirmed by the first user ("not extra: it's my right"). A new verdict type; for now the user leaves hours empty and the draft points to the clause |
| Multiple contracts, ticket history, end-of-project "what did I not bill" view | Asked by the first user; needs storage, which v0.1 deliberately has none of |
| Customisable reply tone | Asked by the first user; the draft is plain text he edits anyway |
