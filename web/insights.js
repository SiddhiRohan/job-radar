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
