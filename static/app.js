const $ = (id) => document.getElementById(id);

// First user: "'potentially extra' is too vague". The badge is now direct; the
// cited clauses right below it are what keeps it honest.
const VERDICTS = {
  included: { badge: "Included", text: "Covered by your agreement." },
  extra: { badge: "Extra", text: "Not covered by your agreement: quote it before you start. Check the clauses below." },
  ambiguous: { badge: "Needs clarification", text: "Your agreement doesn't settle this one. Agree on it with the client before you start." },
};

let requests = [];
let agreementFile = null;

function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function clause(text) {
  return (text || "").replace(/^[-•*]\s*/, "");
}

// A rate written in a cited clause ("EUR 120/hour", "€55 per hour") wins over
// the default rate: quoting €50 next to a clause that says €120 contradicts itself.
const RATE_IN_TEXT = /(EUR|GBP|USD|€|£|\$)\s?(\d+(?:[.,]\d+)?)\s*(?:\/|per\s+)h(?:ou)?r?\b/i;
const SYMBOL = { eur: "€", gbp: "£", usd: "$" };

function rateFromClauses(r) {
  for (const c of [...r.evidence.excluding_lines, ...r.evidence.covering_lines]) {
    const match = c.valid && c.text.match(RATE_IN_TEXT);
    if (match) {
      const amount = match[2].replace(/[.,](?=\d{3}$)/, "").replace(",", ".");
      return { rate: parseFloat(amount), currency: SYMBOL[match[1].toLowerCase()] || match[1],
               source: String(c.line) };
    }
  }
  return null;
}

// The agreement's own currency is the default unit for every request.
function currencyOf(lines) {
  const match = lines.join(" ").match(/\b(EUR|GBP|USD)\b|[€£$]/i);
  if (!match) return "€";
  return SYMBOL[(match[1] || "").toLowerCase()] || match[0];
}

let defaultCurrency = "€";

function rateOf(r) {
  const own = parseFloat(r.rate);
  return Number.isFinite(own) ? own : (parseFloat($("rate").value) || 0);
}

function show(which) {
  for (const id of ["empty", "working", "error", "output"]) $(id).hidden = id !== which;
}

async function checkStatus() {
  try {
    const status = await (await fetch("/api/status")).json();
    $("model-info").textContent = `Model: ${status.model}`;
    if (status.ready) {
      $("status").textContent = status.local ? `${status.model} · local` : status.model;
      $("status").className = "status ok";
    } else {
      $("status").textContent = "Model unavailable";
      $("status").className = "status bad";
      $("status").title = status.error;
      $("error").textContent = status.error;
      show("error");
    }
  } catch {
    $("status").textContent = "Server unreachable";
    $("status").className = "status bad";
  }
}

function renderCards() {
  $("cards").innerHTML = requests.map((r, i) => {
    const v = VERDICTS[r.verdict] || VERDICTS.ambiguous;
    const refs = [
      ...r.evidence.covering_lines.filter((c) => c.valid).map((c) => ["Covered by", c]),
      ...r.evidence.excluding_lines.filter((c) => c.valid).map((c) => ["Excluded / limited by", c]),
    ];
    const refList = refs.length
      ? `<ul class="refs">${refs.map(([kind, c]) =>
          `<li><span class="ref-kind">${kind}</span><span class="ref-line">${esc(String(c.line))}</span><span>${esc(clause(c.text))}</span></li>`
        ).join("")}</ul>`
      : `<p class="hint">No clause of the agreement was cited.</p>`;
    const downgraded = !r.evidence.downgraded ? ""
      : r.evidence.downgrade_reason === "conflicting_evidence"
        ? `<p class="downgraded">The model suggested “included”, but it also cited a clause that excludes or limits this request. ScopeLeak won't tell you to do it for free: check the clauses.</p>`
        : `<p class="downgraded">The model suggested “${esc(r.model_verdict)}” but did not cite a clause of the right kind, so ScopeLeak asks you to check.</p>`;
    const hours = r.verdict === "extra"
      ? `<div class="hours">
           <label>Your estimate <input type="number" min="0" step="0.5" data-field="hours" data-i="${i}" value="${r.hours ?? ""}"> hours</label>
           <label>at ${esc(r.currency || defaultCurrency)} <input type="number" min="0" step="5" data-field="rate" data-i="${i}" value="${r.rate ?? ""}" placeholder="${esc($("rate").value)}">/hour</label>
           ${r.rateSource ? `<span class="hint">rate from ${esc(r.rateSource)}</span>` : ""}
         </div>
         <p class="hint">Leave hours empty if this is not work to quote (e.g. a claim): the reply will just point to the clause.</p>`
      : "";
    return `<article class="card ${r.verdict}">
      <div class="card-head"><p class="card-title">${esc(r.summary)}</p><span class="badge">${v.badge}</span></div>
      <p class="verdict-text">${v.text}</p>
      <blockquote class="quote">“${esc(r.message_quote)}”</blockquote>
      ${refList}${downgraded}${hours}
      <p class="reasoning"><strong>Model's reasoning:</strong> ${esc(r.reasoning)}</p>
    </article>`;
  }).join("");

  document.querySelectorAll("[data-field]").forEach((input) =>
    input.addEventListener("input", () => {
      const r = requests[input.dataset.i];
      r[input.dataset.field] = input.value;
      if (input.dataset.field === "rate") r.rateSource = null;
      renderDraft();
    }));
}

// First user: "no flat 'no's — make it more human". Every line stays neutral
// on the business decision; the freelancer edits before sending.
function renderDraft() {
  const lines = requests.map((r) => {
    const q = `“${r.message_quote}”`;
    if (r.verdict === "included") return `• ${q}: happy to take care of this, it's part of what we agreed.`;
    if (r.verdict === "extra") {
      const basis = r.evidence.excluding_lines.find((c) => c.valid);
      const h = parseFloat(r.hours);
      if (!(h > 0)) {
        const says = basis ? `our agreement says “${clause(basis.text)}”` : "this isn't covered by our agreement";
        return `• ${q}: on this point ${says}. Happy to talk it through if you'd like.`;
      }
      const why = basis ? ` (“${clause(basis.text)}”)` : "";
      const rate = rateOf(r);
      const cur = r.currency || defaultCurrency;
      const unit = h === 1 ? "hour" : "hours";
      return `• ${q}: happy to help with this. It's outside our original agreement${why}, so I'd quote it ` +
             `separately: about ${h} ${unit}, i.e. ${cur}${(h * rate).toLocaleString("en")} at ${cur}${rate}/hour. ` +
             `Shall I go ahead?`;
    }
    return `• ${q}: happy to look into this. Our agreement doesn't clearly cover it, so could we quickly ` +
           `agree on scope (and cost, if any) before I start?`;
  });
  $("draft").value = `Hi,\n\nThanks for your message! Here's where we stand on each point:\n\n` +
                     `${lines.join("\n\n")}\n\nLet me know what you think.\n\nBest regards,`;
  fitDraft();
}

// Show the whole reply without an inner scrollbar.
function fitDraft() {
  const draft = $("draft");
  draft.style.height = "auto";
  draft.style.height = `${draft.scrollHeight + 2}px`;
}

async function analyze() {
  const message = $("message").value.trim();
  const agreement = $("agreement").value.trim();
  if (!message || (!agreement && !agreementFile)) {
    $("error").textContent = "Add both the agreement and the client's message.";
    show("error");
    return;
  }

  const form = new FormData();
  form.append("message", message);
  form.append("agreement", agreement);
  if (agreementFile) form.append("agreement_file", agreementFile);

  show("working");
  $("analyze").disabled = true;
  const started = Date.now();
  $("elapsed").textContent = "0";
  const timer = setInterval(() => { $("elapsed").textContent = Math.round((Date.now() - started) / 1000); }, 1000);

  try {
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Error ${response.status}`);
    requests = data.requests;
    if (!requests.length) throw new Error("The model did not find any request in this message.");
    defaultCurrency = currencyOf(data.lines);
    $("currency").textContent = defaultCurrency;
    for (const r of requests) {
      const found = rateFromClauses(r);
      if (found) { r.rate = found.rate; r.currency = found.currency; r.rateSource = found.source; }
    }
    if (agreementFile) $("agreement").value = data.lines.join("\n");
    renderCards();
    show("output");
    renderDraft();
  } catch (err) {
    $("error").textContent = err.message;
    show("error");
  } finally {
    clearInterval(timer);
    $("analyze").disabled = false;
  }
}

$("agreement-file").addEventListener("change", (e) => {
  agreementFile = e.target.files[0] || null;
  $("file-name").textContent = agreementFile ? `Using ${agreementFile.name}` : "";
  if (agreementFile) $("agreement").value = "";
});
$("agreement").addEventListener("input", () => {
  if (agreementFile && $("agreement").value) {
    agreementFile = null;
    $("agreement-file").value = "";
    $("file-name").textContent = "";
  }
});
$("example").addEventListener("click", async () => {
  const data = await (await fetch("/api/example")).json();
  $("agreement").value = data.agreement;
  $("message").value = data.message;
});
$("analyze").addEventListener("click", analyze);
$("draft").addEventListener("input", fitDraft);
$("rate").addEventListener("input", () => { renderCards(); renderDraft(); });
$("copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("draft").value);
  $("copied").hidden = false;
  setTimeout(() => { $("copied").hidden = true; }, 1500);
});

checkStatus();
