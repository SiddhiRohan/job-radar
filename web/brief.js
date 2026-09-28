/* The morning brief card at the top of Today: the postings to apply to first, what changed, what went quiet, and
   one pattern. "Hide for today" is remembered per brief day, so tomorrow's brief shows again. Uses el and api. */
async function loadBrief() {
  const box = $("#brief");
  if (!box) return;
  let b;
  try { b = await api("/api/brief"); } catch (e) { box.replaceChildren(); return; }
  const hideKey = `radar-brief-hidden-${b.day}`;
  let hidden = false;
  try { hidden = localStorage.getItem(hideKey) === "1"; } catch (e) {}
  if (hidden || !b.day) { box.replaceChildren(); return; }
  const item = (lead, rest) => el("li", {}, el("b", {}, lead), rest ? ` ${rest}` : "");
  const picks = b.picks.length
    ? el("ol", { class: "brief-picks" }, ...b.picks.map(p => el("li", {},
        el("span", { class: "bp-head" }, el("b", {}, p.company), " ", postingTitle(p.title, p.url), el("span", { class: "meta" }, ` ${p.fit}${p.pay ? " · " + p.pay : ""}`)),
        p.reason ? el("span", { class: "bp-why" }, p.reason) : null)))
    : el("p", { class: "sub" }, "Nothing new scored 4 today, or 3 for an entry-level title.");
  const changes = [
    ...b.moved.map(x => item(x.company, `moved from ${x.from} to ${x.status}`)),
    ...b.closed.map(x => item(x.company, `closed: ${x.title}`)),
  ];
  const quiet = b.quiet.map(x => item(x.company, `${x.title}, applied ${x.applied}, posting ${x.posting}: a short follow-up may help`));
  const hide = el("button", { type: "button", class: "quiet", onclick: () => {
    try { localStorage.setItem(hideKey, "1"); } catch (e) {}
    box.replaceChildren();
  } }, "Hide for today");
  box.replaceChildren(el("details", { class: "card brief", open: "" },
    el("summary", {}, el("h3", {}, "Morning brief"), el("span", { class: "sub" }, b.day)),
    el("h4", {}, "Apply first"), picks,
    changes.length ? el("h4", {}, "Since the last brief") : null, changes.length ? el("ul", { class: "brief-list" }, ...changes) : null,
    quiet.length ? el("h4", {}, "Gone quiet") : null, quiet.length ? el("ul", { class: "brief-list" }, ...quiet) : null,
    b.suggestion ? el("p", { class: "brief-pattern" }, b.suggestion) : null,
    el("div", { class: "brief-foot" }, hide)));
}
