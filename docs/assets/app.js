/* HAMON site — interactive pages.
 *
 * INTEGRITY RULE (mirrors the on-page methodology note):
 *   • All HAMON data and loss numbers are TEXT, straight from hamonpy's round-trip
 *     report. They never pass through music21 or Verovio.
 *   • The engraved score is an ILLUSTRATIVE music21→Verovio realization, for visual
 *     reference only. If it can't render, we show text and say so — the data is intact.
 */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const el = (tag, attrs = {}, html = "") => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k === "dataset") Object.assign(e.dataset, v);
    else e.setAttribute(k, v);
  }
  if (html) e.innerHTML = html;
  return e;
};
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));

/** A scrollable code panel whose lines can be highlighted by substring.
 *  Tab-separated text (DCML .tsv) is drawn as a table: in a <pre> the tabs jump to
 *  8-column stops and the columns drift. Blank and `#` comment lines span the row. */
function codePanel(title, text, extraHead = "") {
  const lines = (text || "").replace(/\n$/, "").split("\n");
  const head = `<div class="panel"><div class="phead"><span>${esc(title)}</span><span>${extraHead}</span></div>`;
  if (lines.some((l) => l.includes("\t"))) {
    const width = Math.max(...lines.filter((l) => !l.startsWith("#")).map((l) => l.split("\t").length));
    const rows = lines.map((l, i) => {
      const attrs = `class="ln${i === 0 && !l.startsWith("#") ? " th" : ""}" data-i="${i}" data-text="${esc(l)}"`;
      if (!l.trim() || l.startsWith("#") || !l.includes("\t"))
        return `<tr ${attrs}><td colspan="${width}">${esc(l) || "&nbsp;"}</td></tr>`;
      return `<tr ${attrs}>${l.split("\t").map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`;
    }).join("");
    return head + `<pre><table class="tsv">${rows}</table></pre></div>`;
  }
  const body = lines.map((l, i) =>
    `<span class="ln" data-i="${i}">${esc(l) || "&nbsp;"}</span>`).join("");
  return head + `<pre>${body}</pre></div>`;
}

function highlightLines(panelPre, needles) {
  panelPre.querySelectorAll(".ln").forEach((ln) => {
    const t = ln.dataset.text ?? ln.textContent;
    ln.classList.toggle("hl", needles.some((n) => n && t.includes(n)));
  });
}

/** Illustrative-score block: renders MusicXML/MEI via Verovio, or a clear text fallback.
 *  scoreKind "overlay" = the real source score with HAMON harmony injected as positioned
 *  <harm>/<fb>; anything else = a music21 realization of the labels (display only). */
function scoreBlock(container, musicxml, scoreKind, note) {
  const LABEL = scoreKind === "overlay"
    ? "Real source score (Verovio) with the HAMON harmony overlaid as positioned "
      + "&lt;harm&gt;/&lt;fb&gt; — the labels come solely from the .hamon."
    : "Illustrative engraving — music21 realization → Verovio "
      + "(display only; not part of the HAMON pipeline).";
  if (!musicxml) {
    container.className = "score empty";
    container.innerHTML = note
      ? note + " The HAMON data below is complete and unaffected."
      : "No engraved preview for this example — the display realizer covers "
        + "chord symbols &amp; Roman numerals only. The HAMON data below is complete and unaffected.";
    return;
  }
  container.className = "score";
  container.innerHTML = `<div class="slabel">${LABEL}</div><div class="svg">rendering…</div>`;
  const slot = $(".svg", container);
  if (!window.HamonVerovio) { slot.textContent = "(Verovio unavailable)"; return; }
  const width = Math.max(700, (slot.clientWidth || container.clientWidth || 1100) - 4);
  window.HamonVerovio.render(musicxml, width)
    .then((svg) => { slot.innerHTML = svg; })
    .catch(() => {
      container.className = "score empty";
      container.innerHTML = "Score preview unavailable (Verovio could not render / load). "
        + "This is a display limitation only — the HAMON data below is intact.";
    });
}

async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

/* ── ICCCM'26 loss viewer ──────────────────────────────────────────────── */
async function initIcccm26() {
  const data = await loadJSON("assets/data/icccm26.json");
  const root = $("#viewer");
  let exi = 0, tgt = null, mode = "native";
  const isNat = () => mode === "native";
  const fmtName = (t) => esc(data.formatLabels[t] || t);

  const exTabs = el("div", { class: "tabs ex-tabs" });
  data.examples.forEach((ex, i) => {
    const b = el("button", i === 0 ? { class: "active" } : {}, esc(ex.label));
    b.onclick = () => { exi = i; tgt = null; render(); };
    exTabs.appendChild(b);
  });
  const header = el("div", { class: "ex-header" });
  const scoreRow = el("div", { class: "score-row" });
  const grid = el("div", { class: "ic-grid" });
  root.append(exTabs, header, scoreRow, grid);

  function lossPanelHtml(t) {
    const loss = isNat() ? t.nativeLoss : t.annotatedLoss;
    if (loss === 0) {
      return `<div class="loss-summary"><span class="chip ok">lossless ✓</span></div>`
        + (!isNat() && t.nativeLoss > 0
          ? `<p class="hint">The ${t.nativeLoss} aspect(s) lost natively ride in the `
            + `<b>out-of-band HAMON annotation</b> appended to the export.</p>` : "");
    }
    const items = t.lostAspects.map((a) =>
      `<li class="sem"><b>${esc(a.label)}</b> <span class="lp">×${a.count}</span></li>`).join("");
    return `<div class="loss-summary"><span class="chip sem">−${loss} aspect(s)</span></div>`
      + `<ul class="loss-list">${items}</ul>`;
  }

  function render() {
    const ex = data.examples[exi];
    [...exTabs.children].forEach((b, i) => b.classList.toggle("active", i === exi));

    const fits = ex.targets.filter((t) => t.fits && t.target !== "hamon");
    const noFits = ex.targets.filter((t) => !t.fits);
    if (!tgt || !ex.targets.some((t) => t.target === tgt)) {
      tgt = (fits[0] || ex.targets.find((t) => t.target !== "hamon") || ex.targets[0]).target;
    }
    const t = ex.targets.find((x) => x.target === tgt);

    header.innerHTML =
      `<h2>${esc(ex.title)}</h2>`
      + (ex.excerpt ? ` <span class="excerpt">${esc(ex.excerpt)}</span>` : "")
      + (ex.blurb ? `<p class="blurb">${esc(ex.blurb)}</p>` : "");

    // ── format chooser: the ones that fit (interactive) + the ones that don't
    const fitBtns = fits.map((x) => {
      const loss = isNat() ? x.nativeLoss : x.annotatedLoss;
      return `<button data-t="${x.target}" class="${x.target === tgt ? "active" : ""}">`
        + `${fmtName(x.target)}<small>${loss === 0 ? "✓" : "−" + loss}</small></button>`;
    }).join("");
    const noFitBtns = noFits.map((x) =>
      `<button data-t="${x.target}" class="chip-nofit ${x.target === tgt ? "active" : ""}">`
      + `${fmtName(x.target)}</button>`).join("");
    const chooser =
      `<div class="fmt-group"><span class="fmt-lead">Encodings that fit</span>`
      + `<div class="tabs fmt-tabs">${fitBtns || '<span class="hint">— only HAMON keeps this reading —</span>'}</div></div>`
      + (noFits.length
        ? `<div class="fmt-group"><span class="fmt-lead muted">Can't express this</span>`
          + `<div class="tabs fmt-tabs nofit">${noFitBtns}</div></div>` : "");

    // ── the selected format's panel
    let detail;
    if (t.fits) {
      const dl = `<a class="dl" href="${esc(isNat() ? t.nativePath : t.annotatedPath)}" download>download .${esc(t.ext)}</a>`;
      const modeTabs = `<div class="tabs mode-tabs">`
        + [["native", "Native"], ["annotated", "Native + HAMON"]].map(([m, l]) =>
          `<button data-mode="${m}" class="${m === mode ? "active" : ""}">${l}</button>`).join("")
        + `</div>`;
      detail = modeTabs
        + codePanel(`${isNat() ? "Native" : "Native + HAMON"} → ${fmtName(tgt)}`,
                    isNat() ? t.nativeText : t.annotatedText, dl)
        + lossPanelHtml(t);
    } else {
      const dl = `<a class="dl" href="${esc(t.annotatedPath)}" download>download .${esc(t.ext)}</a>`;
      detail = `<div class="nofit-explain"><p class="why">${esc(t.whyNot)}</p></div>`
        + (t.hasSlot
          ? codePanel(`Native + HAMON → ${fmtName(tgt)} (out-of-band)`, t.annotatedText, dl)
          : `<p class="hint">This encoding has no comment/annotation slot, so the HAMON reading can't travel here at all — only the interlingua keeps it.</p>`);
    }

    scoreRow.innerHTML = `<div class="score" id="ic-score"></div>`;

    grid.innerHTML =
      `<div class="col-left">`
      + codePanel(`HAMON source · @${esc(ex.systemHint || "auto")}`, ex.hamonText)
      + `<details class="jsonwrap" style="margin-top:10px">`
      + `<summary>HAMON canonical JSON <span class="hint">(the hub — <code>grammar/hamon-schema.json</code>)</span></summary>`
      + codePanel("hamon.json", ex.hamonJson)
      + `</details></div>`
      + `<div class="col-right">${chooser}${detail}</div>`;

    grid.querySelectorAll("[data-t]").forEach((b) =>
      b.onclick = () => { tgt = b.dataset.t; render(); });
    grid.querySelectorAll("[data-mode]").forEach((b) =>
      b.onclick = () => { mode = b.dataset.mode; render(); });
    scoreBlock($("#ic-score", scoreRow), ex.musicxml, ex.scoreKind, ex.scoreNote);
  }
  render();
}

/* ── Fixtures browser ──────────────────────────────────────────────────── */
async function initFixtures() {
  const data = await loadJSON("assets/data/fixtures.json");
  const list = $("#fx-list"), detail = $("#fx-detail");
  let active = data.cases[0]?.id;

  const filter = el("div", { class: "fx-filter" });
  const input = el("input", { type: "search", placeholder: `Filter ${data.cases.length} cases…` });
  filter.appendChild(input);
  const listBody = el("div");
  list.append(filter, listBody);

  function renderList(q = "") {
    listBody.innerHTML = "";
    q = q.toLowerCase();
    data.categories.forEach((cat) => {
      const cases = data.cases.filter((c) => c.category === cat &&
        (!q || c.id.toLowerCase().includes(q) || (c.description || "").toLowerCase().includes(q)));
      if (!cases.length) return;
      listBody.appendChild(el("div", { class: "cat" }, esc(cat)));
      cases.forEach((c) => {
        const item = el("div", { class: "item" + (c.id === active ? " active" : "") }, esc(c.id));
        item.title = c.description || "";
        item.onclick = () => { active = c.id; renderDetail(c); renderList(input.value); };
        listBody.appendChild(item);
      });
    });
  }

  function renderDetail(c) {
    const encTabs = Object.entries(c.encodings);
    let encKey = encTabs[0]?.[0];
    const expected = c.expected ? JSON.stringify(c.expected, null, 2) : "";
    detail.innerHTML =
      `<h2>${esc(c.id)}</h2>`
      + `<div class="meta-row">${esc(c.category)}${c.description ? " · " + esc(c.description) : ""}`
      + ` · <code>${esc(c.path)}</code></div>`
      + `<div class="score" id="fx-score"></div>`
      + `<div class="grid-2" style="margin-top:14px">`
      + `<div>` + codePanel("HAMON surface", c.hamonText) + `</div>`
      + `<div>` + codePanel("Expected semantics (fixture JSON)", expected) + `</div>`
      + `</div>`
      + `<h3 style="font-size:15px;margin:18px 0 6px">Source encodings (verbatim)</h3>`
      + `<div class="tabs" id="fx-enc-tabs"></div><div id="fx-enc-body"></div>`;

    scoreBlock($("#fx-score", detail), c.musicxml);

    const encTabsEl = $("#fx-enc-tabs", detail), encBody = $("#fx-enc-body", detail);
    function renderEnc() {
      encTabsEl.innerHTML = "";
      encTabs.forEach(([k]) => {
        const b = el("button", k === encKey ? { class: "active" } : {}, esc(k));
        b.onclick = () => { encKey = k; renderEnc(); };
        encTabsEl.appendChild(b);
      });
      const e = c.encodings[encKey];
      encBody.innerHTML = e ? codePanel(esc(e.file), e.text) : `<p class="hint">no encodings</p>`;
    }
    if (encTabs.length) renderEnc(); else encBody.innerHTML = `<p class="hint">no source encodings for this case.</p>`;
  }

  input.oninput = () => renderList(input.value);
  renderList();
  const first = data.cases.find((c) => c.id === active) || data.cases[0];
  if (first) renderDetail(first);
}

/* ── boot ──────────────────────────────────────────────────────────────── */
(async function () {
  try {
    if (window.__PAGE__ === "icccm26") await initIcccm26();
    else if (window.__PAGE__ === "fixtures") await initFixtures();
  } catch (e) {
    const m = document.querySelector("main");
    if (m) m.appendChild(el("p", { class: "method" }, "Failed to load page data: " + esc(e.message)
      + ". If you opened the file directly, serve it over HTTP: <code>python -m http.server -d docs</code>."));
  }
})();
