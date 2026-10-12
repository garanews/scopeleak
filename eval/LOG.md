# Evaluation log

19 annotated requests (scenarios `website` + `branding`), gemma3:4b on a
laptop CPU (32 GB RAM, no usable GPU). "Raw" = the model's own verdict;
"final" = after reference integrity validation.

| Version | Change | Raw acc | Raw false extra | Final acc | Final false extra | Downgraded | s/request |
|---|---|---|---|---|---|---|---|
| baseline | keyword regex | 58% | 3 | 58% | 3 | – | 0 |
| v1 | exact quotes from agreement | 74% | 5 | 53% | 3 | 7 | 36 |
| v2 | numbered lines (integer schema), verdict last, revisions rule | 79% | 1 | 26% | 0 | 14 | 34 |
| v2.1 | line refs as strings (`"L18"`) | 68% | 3 | 37% | 0 | 11 | 28 |

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
for 19 cases; later runs use temperature 0 and a fixed seed.
