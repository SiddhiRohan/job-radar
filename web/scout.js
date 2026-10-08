/* Company scout card on the Agents view: employers the radar does not follow yet, each checked live at its careers
   system, with open roles, the roles matching your titles and its H-1B record. Follow adds it to companies.json and
   the next run reads it; nothing is added without that. Text only, never innerHTML. Uses el, api, waitJob and toast
   from app.js and loadAgents from agents.js. */
const SYSTEMS = { workday: "Workday", greenhouse: "Greenhouse", lever: "Lever", ashby: "Ashby" };

function scoutCard(r) {
  const s = r.scout, n = s.counts || {};
  const card = el("section", { class: "card wide" }, el("h3", {}, "Company scout"),
    el("p", { class: "sub" }, "Employers worth adding to the daily search, from where you applied, the H-1B sponsor lists and the model's weekly suggestions. Each is checked at its careers site before it shows here, a few each morning."));
  const run = el("button", { type: "button", onclick: async () => {
    run.disabled = true; run.textContent = "Checking";
    try { const found = await waitJob((await api("/api/scout/run", {})).job_id); toast(found.length ? `Found ${found.join(", ")}` : "Nothing new this time"); loadAgents(); }
    catch (e) { toast(`Scout: ${e.message}`); run.disabled = false; run.textContent = "Check more now"; }
  } }, "Check more now");
  const how = `${n.found || 0} found, ${n.followed || 0} followed, ${n.none || 0} not on a system the radar reads, ${n.new || 0} still to check`;
  card.append(el("div", { class: "mailacts" }, run, el("span", { class: "sub" }, how)));
  if (!s.found.length) card.append(el("p", { class: "kempty" }, "Nothing found yet. Leads are checked a few each morning."));
  for (const f of s.found) card.append(scoutItem(f));
  return card;
}

function scoutItem(f) {
  const act = (how, label) => {
    const b = el("button", { type: "button", ...(how === "follow" ? { class: "primary" } : {}), onclick: async () => {
      b.disabled = true;
      try { const res = await api("/api/scout/decide", { name: f.name, how }); toast(res.message); loadAgents(); }
      catch (e) { toast(`Could not ${how}: ${e.message}`); b.disabled = false; }
    } }, label);
    return b;
  };
  const sponsor = f.sponsors === true ? "sponsors H-1B" : f.sponsors === false ? "rarely sponsors" : "sponsorship unknown";
  return el("div", { class: "mailitem" },
    el("div", { class: "mailmeta" }, el("b", {}, f.name), el("span", {}, `${SYSTEMS[f.ats] || f.ats}, ${f.roles} open, ${f.matching} matching your titles`),
      el("span", { class: f.sponsors ? "tag yes" : "tag unknown" }, sponsor), el("a", { href: f.url, target: "_blank", rel: "noopener" }, "Careers site")),
    el("p", { class: "mailsnip" }, f.why || f.source),
    el("div", { class: "mailacts" }, act("follow", "Follow"), act("skip", "Skip")));
}
