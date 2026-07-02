/* Erdős Frontier · shared helpers. Requires nothing; pages own their logic. */
"use strict";

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/* Fetch JSON with an optional fallback URL (used by finding.html when a
   per-problem shard 404s during a feed/page deploy skew). */
async function fetchJSON(url, fallback) {
  const r = await fetch(url);
  if (r.ok) return r.json();
  if (fallback) {
    const f = await fetch(fallback);
    if (f.ok) return f.json();
  }
  throw new Error(`fetch failed: ${url} (${r.status})`);
}

/* Fold entrance — reveal .motion-fade-in-up sections as they enter. */
function armFadeInUp() {
  const els = document.querySelectorAll(".motion-fade-in-up");
  if (!els.length || !("IntersectionObserver" in window)) {
    els.forEach(el => el.classList.add("is-visible"));
    return;
  }
  const io = new IntersectionObserver(entries => {
    for (const e of entries) if (e.isIntersecting) {
      e.target.classList.add("is-visible");
      io.unobserve(e.target);
    }
  }, { rootMargin: "0px 0px -8% 0px" });
  els.forEach(el => io.observe(el));
}

/* Human labels for the gpt-erdos review categories. */
const GPT_LABEL = {
  new_proof: "new proof", literature: "literature", partial_literature: "partial lit.",
  typo: "typo", hidden_constraints: "hidden constraints", non_improving: "non-improving",
  conditional_conjecture: "conditional on conjecture", subtle_error: "subtle error",
};

/* Last segment of "name : Type" assumption strings. */
function condName(a) { return String(a).split(" : ").pop(); }
