const $ = (id) => document.getElementById(id);

const VERDICTS = {
  included: { badge: "Included", text: "This request appears to be covered by your agreement." },
  extra: { badge: "Potentially extra", text: "This request may require an additional quote. Review the cited clauses before responding." },
  ambiguous: { badge: "Needs clarification", text: "The agreement does not provide enough evidence for a definitive classification." },
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
    const downgraded = r.evidence.downgraded
      ? `<p class="downgraded">The model suggested “${esc(r.model_verdict)}” but did not cite a clause of the right kind, so ScopeLeak asks you to check.</p>`
      : "";
    const hours = r.verdict === "extra"
      ? `<label class="hours">Your estimate <input type="number" min="0" step="0.5" data-hours="${i}" value="${r.hours ?? ""}"> hours</label>`
      : "";
    return `<article class="card ${r.verdict}">
      <div class="card-head"><p class="card-title">${esc(r.summary)}</p><span class="badge">${v.badge}</span></div>
      <p class="verdict-text">${v.text}</p>
      <blockquote class="quote">“${esc(r.message_quote)}”</blockquote>
      ${refList}${downgraded}${hours}
      <p class="reasoning"><strong>Model's reasoning:</strong> ${esc(r.reasoning)}</p>
    </article>`;
  }).join("");

  document.querySelectorAll("[data-hours]").forEach((input) =>
    input.addEventListener("input", () => {
      requests[input.dataset.hours].hours = input.value;
      renderDraft();
    }));
}

function renderDraft() {
  const rate = parseFloat($("rate").value) || 0;
  const lines = requests.map((r) => {
    const q = `“${r.message_quote}”`;
    if (r.verdict === "included") return `• ${q}: this is covered by our agreement, I'll take care of it.`;
    if (r.verdict === "extra") {
      const basis = r.evidence.excluding_lines.find((c) => c.valid);
      const why = basis ? ` (“${clause(basis.text)}”)` : "";
      const h = parseFloat(r.hours);
      const estimate = h > 0 ? ` I estimate about ${h} hours, i.e. €${(h * rate).toLocaleString("en")} at €${rate}/hour.` : "";
      return `• ${q}: this appears to fall outside our original agreement${why}.${estimate} Shall we discuss an additional quote?`;
    }
    return `• ${q}: could we quickly clarify whether this is part of the original scope before I start?`;
  });
  $("draft").value = `Hi,\n\nThanks for your message.\n\n${lines.join("\n\n")}\n\nBest regards,`;
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
    if (agreementFile) $("agreement").value = data.lines.join("\n");
    renderCards();
    renderDraft();
    show("output");
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
$("rate").addEventListener("input", renderDraft);
$("copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("draft").value);
  $("copied").hidden = false;
  setTimeout(() => { $("copied").hidden = true; }, 1500);
});

checkStatus();
