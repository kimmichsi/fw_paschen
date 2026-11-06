// Gemeinsame Hilfen fuer Bedien- und Beamer-Fenster (keine externen Ressourcen).
(function () {
  const MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  window.esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => MAP[c]);
  };

  window.ICON_NAMEN = ["wurst", "ring", "dose", "teig", "flasche", "glas", "geschenk", "pokal"];

  // Inline-SVG-Icon als HTML (faellt auf "geschenk" zurueck)
  window.icon = function (name) {
    const svg = (window.ICON_SVG || {})[name] || (window.ICON_SVG || {}).geschenk || "";
    return '<span class="icon" aria-hidden="true">' + svg + "</span>";
  };

  // "12 von 15"
  window.restText = function (p) {
    return p.rest + " von " + p.menge;
  };

  // Tabelle der ewigen Bestenliste. opts: {limit, jahre}
  window.bestenlisteHtml = function (stat, limit) {
    const jahre = stat.jahre || [];
    const zeilen = (stat.bestenliste || []).slice(0, limit || 9999);
    let h = '<table class="daten"><thead><tr><th>Name</th>';
    jahre.forEach((j) => (h += "<th>" + j + "</th>"));
    h += '<th class="gesamt">Gesamt</th></tr></thead><tbody>';
    zeilen.forEach((z, i) => {
      h += '<tr><td class="name"><span class="leise">' + (i + 1) + ".</span> " + esc(z.name) + "</td>";
      jahre.forEach((j) => {
        const v = z.jahre[String(j)];
        h += v == null ? '<td class="null">–</td>' : "<td>" + v + "</td>";
      });
      h += '<td class="gesamt">' + z.gesamt + "</td></tr>";
    });
    return h + "</tbody></table>";
  };

  window.jahresvergleichHtml = function (stat) {
    let h = '<table class="daten"><thead><tr><th>Jahr</th><th>Teilnehmer</th><th>Preise</th><th>Runden</th></tr></thead><tbody>';
    (stat.jahresvergleich || []).forEach((r) => {
      h += "<tr><td>" + r.jahr + "</td><td>" + r.teilnehmer + "</td><td>" + r.preise_gesamt + "</td><td>" + r.runden + "</td></tr>";
    });
    return h + "</tbody></table>";
  };

  // Rekorde als drei Bloecke (Listen). Gibt {abend, teilnahmen, pechvogel} als HTML zurueck.
  window.rekordeHtml = function (stat) {
    const r = stat.rekorde || {};
    const ma = r.meiste_siege_abend || { ewig: [], je_jahr: [] };
    const liste = (arr, fmt) =>
      arr && arr.length ? "<ol>" + arr.map((x) => "<li>" + fmt(x) + "</li>").join("") + "</ol>" : '<p class="leise">Noch keine Daten.</p>';
    const abend =
      (ma.ewig.length
        ? "<p class='rekord-gross'>" + ma.ewig[0].siege + " Siege</p><p>" +
          ma.ewig.map((e) => esc(e.name) + " (" + e.jahr + ")").join(", ") + "</p>"
        : '<p class="leise">Noch keine Daten.</p>') +
      (ma.je_jahr.length
        ? "<ul class='je-jahr'>" + ma.je_jahr.map((e) => "<li><b>" + e.jahr + "</b> " + esc(e.name) + " · " + e.siege + "</li>").join("") + "</ul>"
        : "");
    return {
      abend: abend,
      teilnahmen: liste((r.teilnahmen || []).slice(0, 5), (x) => esc(x.name) + " <b>" + x.teilnahmen + "×</b>"),
      pechvogel: liste((r.pechvogel || []).slice(0, 5), (x) => esc(x.name) + " <b>" + x.teilnahmen + "× ohne Sieg</b>"),
    };
  };

  // Startet die Seite. cb(true) = echter Modus (pywebview-Api bereit), cb(false) = Demo-Modus.
  // Demo gibt es NUR mit dem URL-Parameter ?demo (oder &demo). Sonst wird ohne Zeitlimit auf
  // pywebview gewartet. Ohne mitApi (Beamer-Fenster) ruft nichts cb im echten Modus: Python schickt
  // den Zustand per window.render.
  window.istDemo = function () {
    return /[?&]demo(&|=|$)/.test(location.search);
  };
  window.starteMitApi = function (cb, mitApi) {
    if (window.istDemo()) { cb(false); return; }
    if (!mitApi) return;
    const bereit = () => !!(window.pywebview && window.pywebview.api && typeof window.pywebview.api.zustand === "function");
    let fertig = false;
    const los = () => { if (!fertig) { fertig = true; cb(true); } };
    if (bereit()) { los(); return; }
    window.addEventListener("pywebviewready", () => { if (bereit()) los(); else setTimeout(() => bereit() && los(), 100); });
  };
})();
