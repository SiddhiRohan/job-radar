/* Setup page: the doctor's checks, then resume, API key and profile, then the first run. It opens by itself while
   something needs fixing. Uses el, api, toast and runRadar from app.js, which loads after this file. */
const PROFILE_HINT = `Roles I want:
Level (new grad, 2 to 4 years, senior):
Where I can work:
Visa sponsorship needed (yes or no):
Pay floor:
Never show me:
My strongest experience:
Tools I have not used:`;

async function loadSetup() {
  const body = $("#setup-body");
  try {
    const s = await api("/api/setup");
    body.replaceChildren(checksCard(s.checks), resumeCard(s), keyCard(s), profileCard(s), dailyCard(s), nextCard(s.checks));
  } catch (e) { body.replaceChildren(el("p", { class: "error" }, e.message)); }
}

function checksCard(checks) {
  const label = { ok: "ok", info: "note", fix: "fix" };
  return el("section", { class: "card setup" }, el("h3", {}, "Checks"),
    el("ul", { class: "checks" }, ...checks.map(c => el("li", { class: `check ${c.level}` },
      el("span", { class: "badge" }, label[c.level]), el("span", {}, c.what), c.detail ? el("span", { class: "sub" }, ` ${c.detail}`) : null))));
}

function resumeCard(s) {
  if (s.original_layout) {
    return el("section", { class: "card setup" }, el("h3", {}, "1. Resume"),
      el("p", { class: "sub" }, "Using your Resume/ folder tree. Change those files directly."));
  }
  const input = el("input", { type: "file", accept: ".docx,.txt,.md", "aria-label": "Resume file" });
  input.addEventListener("change", () => {
    const f = input.files[0]; if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const r = await api("/api/setup/resume", { name: f.name, data: String(reader.result).split(",")[1] || "" });
        toast(`Saved ${r.saved}`); loadSetup();
      } catch (e) { toast(e.message); }
    };
    reader.readAsDataURL(f);
  });
  return el("section", { class: "card setup" }, el("h3", {}, "1. Resume"),
    el("p", { class: "sub" }, s.resume.length ? `Now using ${s.resume.join(", ")}. Choose a file to replace it.` : "A Word file (.docx) works best: it is also the template for tailored versions."),
    input);
}

function keyCard(s) {
  const input = el("input", { type: "password", autocomplete: "off", spellcheck: "false", placeholder: "sk-ant-...", "aria-label": "Anthropic API key" });
  const save = el("button", { type: "button", class: "primary", onclick: async () => {
    save.disabled = true;
    try {
      const r = await api("/api/setup/key", { key: input.value });
      input.value = ""; toast(r.checked === "ok" ? "Key saved and checked" : "Key saved; it could not be checked offline"); loadSetup();
    } catch (e) { toast(e.message); save.disabled = false; }
  } }, "Save key");
  return el("section", { class: "card setup" }, el("h3", {}, "2. Anthropic API key"),
    el("p", { class: "sub" }, s.key_set ? "A key is saved in .env. Paste a new one to replace it." : "Scoring and tailoring use your own key. Create one at console.anthropic.com; it is saved only in .env on this computer."),
    el("div", { class: "row-inline" }, input, save));
}

function profileCard(s) {
  const text = el("textarea", { rows: "9", "aria-label": "Profile", placeholder: PROFILE_HINT }, s.profile || "");
  const save = el("button", { type: "button", class: "primary", onclick: async () => {
    try { await api("/api/setup/profile", { text: text.value }); toast("Profile saved"); loadSetup(); }
    catch (e) { toast(e.message); }
  } }, "Save profile");
  return el("section", { class: "card setup" }, el("h3", {}, "3. What you are looking for"),
    el("p", { class: "sub" }, "A few plain lines make the scores sharper. Optional, and you can change it any time."),
    text, save);
}

function dailyCard(s) {
  const flip = el("button", { type: "button", onclick: async () => {
    flip.disabled = true;
    try {
      const r = await api("/api/schedule", { on: !s.scheduled });
      toast(r.ok ? (r.scheduled ? "It will run every morning, even with the app closed" : "System schedule removed") : (r.why || "Could not change the system schedule"));
      loadSetup();
    } catch (e) { toast(e.message); flip.disabled = false; }
  } }, s.scheduled ? "Stop the system schedule" : "Run every morning, even when the app is closed");
  return el("section", { class: "card setup" }, el("h3", {}, "4. Every morning"),
    el("p", { class: "sub" }, s.scheduled
      ? "Your computer's scheduler starts the run each morning, whether or not this app is open."
      : "While this app is open it runs every morning by itself. To run even when it is closed, let your computer's scheduler start it."),
    flip);
}

function nextCard(checks) {
  const ready = !checks.some(c => c.level === "fix");
  const run = el("button", { type: "button", class: "primary", disabled: ready ? null : "", onclick: () => { runRadar(1, false); location.hash = "today"; } }, "Run the radar now");
  return el("section", { class: "card setup" }, el("h3", {}, ready ? "Ready" : "Almost there"),
    el("p", { class: "sub" }, ready
      ? "From now on it runs every morning while this app is open, and catches up when you open it. The first run takes up to an hour."
      : "Fix the items marked fix above, then run it."),
    run,
    el("p", { class: "sub" }, "Optional: statuses from hiring emails (the Email section of docs/CONFIG.md). Using a coding assistant? Open this folder in it and type /radar-setup."));
}

/* First visit: open Setup while the doctor finds something to fix. */
async function setupFirst() {
  if (location.hash && location.hash !== "#today") return;
  try {
    const d = await api("/api/doctor");
    if (d.checks.some(c => c.level === "fix")) location.hash = "setup";
  } catch (e) { /* the app still works without this nudge */ }
}
