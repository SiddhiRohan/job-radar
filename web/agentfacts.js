/* The two agents that only count, for the Agents view: skill gaps across a month of verdicts, and what each employer's
   own postings say about sponsorship. No model, no request beyond /api/agents. Uses el from app.js. */

/* One bar in up to three parts, widths against `of` (the longest bar), each part named for screen readers. */
function partsBar(parts, of, label) {
  const bar = el("span", { class: "obar", role: "img", "aria-label": label });
  for (const [n, cls, what] of parts) if (n) bar.append(el("span", { class: `seg ${cls}`, style: `width:${(100 * n) / (of || 1)}%`, title: `${n} ${what}` }));
  return bar;
}
const swatch = (cls, text) => el("span", { class: "legend" }, el("span", { class: `seg ${cls} key` }), text);

function gapsCard(g) {
  const card = el("section", { class: "card" }, el("h3", {}, "Skill gaps"),
    el("p", { class: "sub" }, `What ${g.postings} postings scored since ${g.since} found missing. Each bar is the postings missing that skill; the green part scored 3, one point below Apply.`));
  const learn = g.skills.filter(s => !s.confirmed).slice(0, 10);
  if (!learn.length) return card.append(el("p", { class: "kempty" }, "No skill is missing from two or more postings yet.")), card;
  const top = Math.max(...learn.map(s => s.postings));
  card.append(el("div", { class: "legend-row" }, swatch("good", "scored 3"), swatch("wait", "scored lower or higher")),
    el("div", { class: "hbars gapbars" }, ...learn.map(s => el("div", { class: "hrow", title: s.examples.map(x => `${x.company}: ${x.title}`).join("\n") },
      el("span", { class: "hl" }, s.skill, s.not_have ? el("span", { class: "tag unknown" }, "not-have list") : null),
      partsBar([[s.scored_3, "good", "scored 3"], [s.postings - s.scored_3, "wait", "other scores"]], top, `${s.skill}: missing in ${s.postings} postings, ${s.scored_3} of them scored 3`),
      el("span", { class: "hv" }, String(s.postings))))));
  if (g.confirmed.length) card.append(el("h4", { class: "minor" }, "On your resume, but not where postings look"),
    el("p", { class: "sub" }, "You confirmed these skills, yet postings read them as missing. Put them in a bullet or the skills line: ",
      g.confirmed.slice(0, 8).map(s => `${s.skill} (${s.postings})`).join(", "), "."));
  return card;
}

function sponsorCard(s) {
  const card = el("section", { class: "card" }, el("h3", {}, "Sponsor map"),
    el("p", { class: "sub" }, `What each employer's postings since ${s.since} say about sponsorship, next to its default in companies.json.`));
  if (!s.employers.length) return card.append(el("p", { class: "kempty" }, "No postings to read yet; the map fills in after a run.")), card;
  const n = s.counts;
  card.append(el("p", { class: "rj-lead" }, `${s.employers.length} employers posted: `, el("b", { class: "good" }, `${n.sponsors} say they sponsor`), `, ${n.mixed} decide per posting, `,
    el("b", { class: "rej" }, `${n.rules_out} mostly rule it out`), `, and ${n.silent} never say.`));
  const yes = s.employers.filter(e => e.yes).sort((a, b) => b.yes - a.yes || a.company.localeCompare(b.company)).slice(0, 8);
  const top = Math.max(1, ...yes.map(e => e.postings));
  if (yes.length) card.append(el("h4", { class: "minor" }, "Most postings that say they sponsor"),
    el("div", { class: "legend-row" }, swatch("good", "says yes"), swatch("rej", "says no"), swatch("wait", "says nothing")),
    el("div", { class: "hbars wideval" }, ...yes.map(e => el("div", { class: "hrow" }, el("span", { class: "hl" }, e.company),
      partsBar([[e.yes, "good", "say yes"], [e.no, "rej", "say no"], [e.silent, "wait", "say nothing"]], top, `${e.company}: ${e.yes} yes, ${e.no} no, ${e.silent} silent`),
      el("span", { class: "hv" }, `${e.yes}/${e.postings}`)))));
  if (s.flags.length) card.append(el("h4", { class: "minor" }, "Defaults to check"),
    el("ul", { class: "mailevents" }, ...s.flags.slice(0, 8).map(e => el("li", {}, el("b", {}, e.company), `: ${e.flag}`))),
    el("p", { class: "sub" }, "If you agree, change its sponsors_h1b in companies.json; posting wording always wins over the default."));
  const label = d => ({ true: "likely", false: "unlikely" })[String(d)] || "unknown";
  card.append(el("details", { class: "tableview" }, el("summary", {}, `Every employer (${s.employers.length})`),
    el("table", {}, el("thead", {}, el("tr", {}, ...["Employer", "Yes", "No", "Silent", "Default", "Filings"].map(h => el("th", {}, h)))),
      el("tbody", {}, ...s.employers.map(e => el("tr", {}, el("td", {}, e.company), el("td", {}, String(e.yes)), el("td", {}, String(e.no)),
        el("td", {}, String(e.silent)), el("td", {}, label(e.default)), el("td", {}, e.filings || "")))))));
  return card;
}
