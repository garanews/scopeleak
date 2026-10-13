# Evaluation log

19 annotated requests (scenarios `website` + `branding`), gemma3:4b
(Ollama ID `68ceab7e468a`, 3.9B, Q4_K_M, context 4096, Ollama 0.40.3) on a
laptop CPU (32 GB RAM, no usable GPU). "Raw" = the model's own verdict;
"final" = after reference integrity validation.

| Version | Change | Raw acc | Raw false extra | Final acc | Final false extra | Downgraded | s/request |
|---|---|---|---|---|---|---|---|
| baseline | keyword regex | 58% | 3 | 58% | 3 | – | 0 |
| v1 | exact quotes from agreement | 74% | 5 | 53% | 3 | 7 | 36 |
| v2 | numbered lines (integer schema), verdict last, revisions rule | 79% | 1 | 26% | 0 | 14 | 34 |
| v2.1 | line refs as strings (`"L18"`) — temp 0.1, no seed | 68% | 3 | 37% | 0 | 11 | 28 |
| v2.1 | same, temp 0, seed 42 (reference run) | 79% | 1 | 37% | 0 | 10 | 27 |
| v2.2 | reasoning before line refs | 74% | 1 | 42% | 0 | 8 | 27 |
| **v3** | covering / excluding line lists + "not mentioned ≠ extra" rule | 68% | 1 | **63%** | **0** | 2 | 26 |

v3 final metrics on `extra`: precision 100%, recall 73%, F1 84% (baseline: 70% / 64% / 67%).

## Findings

**v1 — evidence formatting failure.** The model's reasoning was often right,
but it left the quote list empty or glued a section heading onto the sentence
("Not included - Applications of…"), so exact-match validation rejected it.

**v2 — schema contract failure.** The prompt showed lines as `L18`; the output
schema accepted only integers. Under constrained decoding the model could not
write the `L`, and the shortest valid output was `[]` — in all 19 cases. The
reasoning still said "explicitly excluded (L18)".

**v2.1 — field order failure.** With strings allowed, the model cites lines
when a request is *included*, but leaves the list empty when it is *extra* and
names the exclusion line only later, in the reasoning. The references field
comes before the reasoning, so the model commits to "no evidence" before it
has looked for the exclusion clause.

**Noise.** Raw accuracy moved 79% → 68% between v2 and v2.1 although nothing
in the reasoning setup changed. Temperature 0.1 without a seed is too noisy
for 19 cases; the deterministic rerun of v2.1 gave 79% again. All later runs
use temperature 0 and seed 42.

**v2.2 — it was never the field order.** Moving the reasoning first changed
little: all 8 downgrades are `extra` verdicts with an empty line list, and no
`extra` verdict cites a single line. The reasoning got shorter and stopped
naming lines at all. For a 4B model, "lines that justify the verdict" means
"lines that cover the request" — and an extra request, by definition, has
none. It does not think of citing the clause that *excludes* it.

**v3 — ask for the evidence you mean.** Two lists instead of one:
`covering_lines` and `excluding_lines`, and the validator requires the kind
that matches the verdict (`extra` needs an excluding line). Two changes at
once, deliberately: the "not mentioned ≠ extra" rule is only enforceable when
the two kinds of evidence are separate. Result: downgrades 8 → 2, final
accuracy 42% → 63%, zero false extras. Every one of the 7 remaining errors is
an `ambiguous` with no lines cited — the model fails safe. It handles explicit
exclusions well but still misses *limits and processes*: a colour change is
not linked to "two rounds of revisions", a broken form not to "30 days of
support".

**What v3 does not guarantee.** The validator checks that an `extra` verdict
cites an existing line in the *excluding* list. It cannot check that the line
actually excludes *this* request: a real but irrelevant clause would pass.
Relevance stays probabilistic; that is why the freelancer reviews every
verdict with the cited lines in front of them.

**v3 is frozen** at tag `v3-frozen` (commit `2297252`). Results on the 19
development cases above are not independent: the prompt was shaped on them.
The held-out scenarios are annotated before any model sees them, and are not
used to change v3.

## Held-out challenge set (v3-frozen)

20 requests in two new scenarios (`it-support`, `social-media`), written
after the v3 error analysis — so a *challenge set*, not a random sample of
real messages. Labelled independently by a human reviewer and by ChatGPT
before any model ran on them: agreement 20/20, Cohen's kappa 1.00. Perfect
agreement also means these cases have clean boundaries; real client messages
will be messier. Labels frozen in commit `681335f`; classifier code unchanged
since `v3-frozen`.

| Model | Acc | Extra precision | Extra recall | False extra | Extra → included | s/request |
|---|---|---|---|---|---|---|
| baseline | 30% | 50% | 17% | 2 | 10 | 0 |
| gemma3:4b | 55% | 83% | 42% | 1 | 3 | 31 |
| gemma4:e4b (Ollama `dc35e8d9c606`) | **85%** | 85% | **92%** | 2 | 1 | 170 |

Gemma 3 4B misses every *quantitative limit* (6 hours used, 20 posts instead
of 12, ad budget 500 instead of 300) — and here it fails the expensive way,
calling them `included`. Gemma 4 E4B catches all three. Its three errors:

- `sm-08` newsletter → extra, citing "Platforms other than Instagram". The
  second annotator raised exactly this doubt while labelling. Debatable, not
  invented.
- `it-10` phishing training → extra, citing "Projects such as migrations…".
  A real clause stretched beyond its meaning.
- `it-03` Saturday emergency → included, citing the "Emergency interventions
  … billed at EUR 80" line as *covering* although it sits under NOT INCLUDED.

The first two are the documented limit of reference integrity validation: a
real but loosely relevant line passes. The third could be caught
deterministically (a line under a "Not included" heading cannot be a
covering line), but that fix would be inspired by the held-out set, so any
v4 result on it must be reported as exploratory.

The trade-off on a laptop CPU: Gemma 4 E4B is far more accurate and about
5.5× slower (~3 minutes per message).

Failure taxonomy so far:
- *Reasoning failure* — the model misreads the agreement.
- *Evidence generation failure* — right verdict, unusable references (v1, v2.1, v2.2).
- *Validation failure* — usable references rejected by the application (v1 headings, v2 integer schema).
