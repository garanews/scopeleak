# ScopeLeak

**Know before you say yes.**

A client sends a new request. Is it covered by what you agreed, or is it extra
work you are about to do for free? ScopeLeak reads your agreement and the
client's message and tells you — `included`, `extra` or `ambiguous` — citing the
agreement lines and the words of the request that justify the verdict.

It runs on open-weight models (Gemma) on your own machine: client contracts
never leave your laptop.

> Work in progress for the DEV Hacktoberfest Open-Source AI Challenge, Week 2
> (Side Hustle). See [SCOPE.md](SCOPE.md) for what is being built this week and
> [BACKLOG.md](BACKLOG.md) for what is deliberately not.

## How it works

1. The agreement is split into numbered lines.
2. The model identifies each request in the message, cites the relevant lines
   and an exact quote from the message, reasons, and only then gives a verdict.
3. **Reference integrity validation**: code checks that every cited line exists
   and every quote really appears in the message. A verdict without valid
   references is downgraded to `ambiguous`. This guarantees the references are
   real — not that the reasoning is right. The freelancer decides.

## Run it

```bash
ollama pull gemma4:e4b
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app:app --port 8000
```

Open http://localhost:8000, paste or upload your agreement (PDF or TXT), paste
the client's message, and check it. The page loads nothing from the internet.
On a laptop CPU Gemma 4 E4B takes a few minutes per message; `gemma3:4b` is
about 5× faster and noticeably less accurate (see below).

## Evaluation

```bash
python -m eval.run --set dev --models baseline,gemma3:4b
python -m eval.run --set heldout --models baseline,gemma3:4b,gemma4:e4b
python -m unittest discover tests
```

Results, failure analysis and limits: [eval/LOG.md](eval/LOG.md). On a
held-out set labelled blind by two annotators: keyword baseline 30%,
Gemma 3 4B 55%, Gemma 4 E4B 85%.

Any OpenAI-compatible server works (Ollama, LM Studio, vLLM): set `base_url`
and `model` in `config.json`, or override them in an untracked
`config.local.json`.
