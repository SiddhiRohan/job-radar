/* What the rejections say, in plain words: how every application turned out, the clearest pattern as one sentence, and
   a tab per way of grouping them (role, level, resume, fit score, years asked, sponsorship, company). Each group shows
   how its applications turned out and whether it was rejected more or less often than your average; click a group to
   see the applications in it. Counts only, from /api/patterns. Uses el and api from app.js. */
const RJ = { tab: null, open: null };
const MIN_GROUP = 3;  /* a group smaller than this is never compared with the average */
const RJ_DIMS = [
  ["Title family", "Role", b => (b === "Other" ? "Other roles" : `${b} roles`)],
  ["Seniority in title", "Level", b => ({ Senior: "Senior titles", "Level II": "Level II titles", Entry: "Entry-level titles", Unmarked: "Titles with no level" })[b] || b],
  ["Resume base", "Resume", b => (b === "unknown" ? "Applications with no resume recorded" : `Applications with the ${b} resume`)],
  ["Fit score", "Fit score", b => (b === "unscored" ? "Unscored postings" : `Postings scored ${b.replace("score ", "")} of 5`)],
  ["Years asked", "Years asked", b => (b === "not stated" ? "Postings not stating years" : `Postings asking ${b} years`)],
  ["Sponsorship default", "Sponsorship", b => ({ yes: "Postings that say they sponsor", likely: "Employers that often sponsor", unlikely: "Employers that rarely sponsor",
    unknown: "Postings silent on sponsorship", no: "Postings that say they won't sponsor", perm_ad: "Green card style ads" })[b] || b],
  ["Company", "Company", b => b],
];
const rjPhrase = (dim, b) => (RJ_DIMS.find(d => d[0] === dim) || [, , x => x])[2](b);
const rjCount = (n, one, many) => `${n} ${n === 1 ? one : many}`;

function patternsCard() {
  const card = el("section", { class: "card wide rj" }, el("h3", {}, "What the rejections say"), el("p", { class: "sub" }, "Loading"));
  api("/api/patterns").then(r => fillPatterns(card, r)).catch(e => card.replaceChildren(el("h3", {}, "What the rejections say"), el("p", { class: "error" }, e.message)));
  return card;
}

/* One bar split into good replies, rejections and still waiting, widths by count. */
function outcomeBar(good, rejected, waiting) {
  const total = good + rejected + waiting || 1;
  const seg = (n, cls, what) => (n ? el("span", { class: `seg ${cls}`, style: `width:${(100 * n) / total}%`, title: `${n} ${what}` }) : null);
  return el("span", { class: "obar", role: "img", "aria-label": `${good} good replies, ${rejected} rejected, ${waiting} waiting` },
    seg(good, "good", "good replies"), seg(rejected, "rej", "rejected"), seg(waiting, "wait", "still waiting"));
}

function fillPatterns(card, r) {
  const waiting = r.total - r.rejected - r.responded, avg = Math.round(100 * r.overall_rate);
  const legend = el("span", { class: "legend" }, el("i", { class: "good" }), "good reply", el("i", { class: "rej" }), "rejected", el("i", { class: "wait" }), "still waiting");
  const head = [el("h3", {}, "What the rejections say"),
    el("p", { class: "rj-lead" }, `You've heard back on ${r.rejected + r.responded} of ${rjCount(r.total, "application", "applications")}: `,
      el("b", { class: "good" }, rjCount(r.responded, "good reply", "good replies")), " (a screen, interview or offer), ",
      el("b", { class: "rej" }, rjCount(r.rejected, "rejection", "rejections")), `, and ${waiting} still waiting.`),
    el("div", { class: "rj-total" }, outcomeBar(r.responded, r.rejected, waiting), legend)];
  if (!r.enough_data) {
    card.replaceChildren(...head, el("p", { class: "sub" },
      `Patterns show up once there are 3 rejections to compare. You have ${r.rejected} so far; this fills in as replies arrive.`));
    return;
  }
  const top = r.findings.find(f => f.lift >= 0.15);
  const insight = top
    ? el("p", { class: "rj-insight" }, "Clearest pattern: ", el("b", {}, top.dimension === "Company" ? `Applications to ${top.bucket}` : rjPhrase(top.dimension, top.bucket)),
      ` were rejected ${top.rejected} of ${top.applied} times (${Math.round(100 * top.rate)}%), against ${avg}% across all your applications.`)
    : el("p", { class: "rj-insight calm" }, `No group stands out yet: rejections are spread fairly evenly around your ${avg}% average.`);
  if (!RJ.tab || !r.tallies[RJ.tab]) RJ.tab = top ? top.dimension : RJ_DIMS[0][0];
  const redraw = () => fillPatterns(card, r);
  const tabs = el("div", { class: "chips rj-tabs", role: "tablist", "aria-label": "Group applications by" },
    el("span", { class: "sub" }, "Group by"),
    ...RJ_DIMS.filter(([d]) => r.tallies[d]).map(([d, label]) => el("button", { type: "button", role: "tab", class: "chip" + (d === RJ.tab ? " on" : ""),
      "aria-selected": String(d === RJ.tab), onclick: () => { RJ.tab = d; RJ.open = null; redraw(); } }, label)));
  card.replaceChildren(...head, insight, tabs, rjGroups(r, RJ.tab, redraw),
    el("p", { class: "sub" }, `Your average is ${avg}% rejected. A group is compared with it once it has ${MIN_GROUP} applications; small groups swing a lot, so read these as hints. Click a group to see its applications.`));
}

function rjGroups(r, dim, redraw) {
  const buckets = Object.entries(r.tallies[dim]).sort((a, b) => b[1].applied - a[1].applied || a[0].localeCompare(b[0]));
  return el("div", { class: "rj-groups" }, ...buckets.map(([b, t]) => {
    const n = t.applied, rej = t.rejected || 0, good = t.responded || 0, gap = rej / n - r.overall_rate;
    const [cls, verdict] = n < MIN_GROUP ? ["few", "Too few to tell"]
      : gap >= 0.15 ? ["hot", "Rejected more than usual"] : gap <= -0.15 ? ["cool", "Rejected less than usual"] : ["even", "About your average"];
    const key = `${dim}|${b}`, open = RJ.open === key;
    const row = el("button", { type: "button", class: `rj-row ${cls}`, "aria-expanded": String(open), onclick: () => { RJ.open = open ? null : key; redraw(); } },
      el("span", { class: "rl" }, rjPhrase(dim, b)), outcomeBar(good, rej, n - rej - good),
      el("span", { class: "rn" }, `${rej} of ${n} rejected`), el("span", { class: `rt ${cls}` }, verdict));
    const order = { rejected: 0, offer: 1, interview: 2, screen: 3, applied: 4 };  /* the rejections first, then the replies */
    const apps = open ? el("ul", { class: "rj-apps" }, ...r.apps.filter(a => a.dims[dim] === b).sort((x, y) => (order[x.status] ?? 5) - (order[y.status] ?? 5)).map(a =>
      el("li", {}, el("b", {}, a.company), el("span", {}, a.title), el("span", { class: `stag s-${a.status}` }, a.status)))) : null;
    return el("div", { class: "rj-group" + (open ? " open" : "") }, row, apps);
  }));
}
