/* Insight cards on Applied. patternsCard: where the rejections cluster, counts only. Uses el, api and hoverable. */
function patternsCard() {
  const card = el("section", { class: "card wide" }, el("h3", {}, "What the rejections say"), el("p", { class: "sub" }, "Loading"));
  api("/api/patterns").then(r => fillPatterns(card, r)).catch(e => card.replaceChildren(el("h3", {}, "What the rejections say"), el("p", { class: "error" }, e.message)));
  return card;
}

function fillPatterns(card, r) {
  const pct = x => `${Math.round(100 * x)}%`;
  const head = [el("h3", {}, "What the rejections say")];
  if (!r.enough_data) {
    card.replaceChildren(...head, el("p", { class: "sub" }, `${r.rejected} rejection${r.rejected === 1 ? "" : "s"} so far. Patterns need at least three; this fills in as replies arrive.`));
    return;
  }
  head.push(el("p", { class: "sub" }, `${r.rejected} of ${r.total} rejected (${pct(r.overall_rate)}), ${r.responded} with a reply. Buckets with three or more rejections, against your overall rate.`));
  const rows = r.findings.slice(0, 8).map(f => {
    const row = el("div", { class: "prow" + (f.lift > 0.1 ? " hot" : "") },
      el("span", { class: "pl" }, el("b", {}, f.bucket), el("span", { class: "pd" }, f.dimension)),
      el("span", { class: "track" }, el("span", { class: "fill" + (f.lift > 0.1 ? "" : " rest"), style: `width:${100 * f.rate}%` })),
      el("span", { class: "pv" }, `${f.rejected} of ${f.applied}`),
      el("span", { class: "pr" }, (f.lift >= 0 ? "+" : "") + Math.round(100 * f.lift) + " pts"));
    return hoverable(row, `${pct(f.rate)} rejected`, `${f.dimension}: ${f.bucket}, ${f.responded} replied`);
  });
  card.replaceChildren(...head, el("div", { class: "hbars" }, ...rows),
    el("p", { class: "sub" }, "Bars show the rejection rate of each bucket; the last column is the gap to your overall rate. Small counts move a lot, read them as hints."));
}

/* watchCard: postings behind open applications that closed or changed since applying. */
function watchCard() {
  const card = el("section", { class: "card wide" }, el("h3", {}, "Postings since you applied"), el("p", { class: "sub" }, "Loading"));
  api("/api/watch").then(r => fillWatch(card, r)).catch(e => card.replaceChildren(el("h3", {}, "Postings since you applied"), el("p", { class: "error" }, e.message)));
  return card;
}

function fillWatch(card, r) {
  const check = el("button", { type: "button", onclick: async () => {
    check.disabled = true; check.textContent = "Checking";
    try { await waitJob((await api("/api/watch/run", {})).job_id); loadApplied(); }
    catch (e) { toast(`Could not check postings: ${e.message}`); check.disabled = false; check.textContent = "Check postings"; }
  } }, "Check postings");
  const head = el("div", { class: "mailhead" }, el("div", {}, el("h3", {}, "Postings since you applied"),
    el("p", { class: "sub" }, r.last_run ? `${r.open} still open, ${r.closed.length} closed, ${r.changed.length} changed. Last checked ${r.last_run}.` : "Not checked yet; runs with the morning radar.")), check);
  const days = d => Math.max(0, Math.round((Date.now() - new Date(d + "T12:00")) / 864e5));
  const item = (p, note) => el("li", {}, el("b", {}, p.company), `, ${p.title}: `, note);
  const closed = r.closed.length ? [el("h4", {}, "Closed with no reply", el("span", { class: "n" }, String(r.closed.length))),
    el("ul", { class: "mailevents" }, ...r.closed.map(p => item(p, `posting gone since ${p.closed_since}, ${days(p.applied)} days after you applied`)))] : [];
  const changed = r.changed.length ? [el("h4", {}, "Changed", el("span", { class: "n" }, String(r.changed.length))),
    el("ul", { class: "mailevents" }, ...r.changed.map(p => item(p, p.changes.map(c => `${c.what} (${c.date})`).join("; "))))] : [];
  card.replaceChildren(head, ...closed, ...changed, (!closed.length && !changed.length && r.last_run) ? el("p", { class: "kempty" }, "Every open application's posting is still up and unchanged.") : null);
}
