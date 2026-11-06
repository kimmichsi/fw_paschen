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

  // Einzahl/Mehrzahl nach deutscher Regel: plural(1, "Preis", "Preise") -> "Preis"
  const PR = (function () { try { return new Intl.PluralRules("de"); } catch (e) { return null; } })();
  window.plural = function (n, eins, mehr) {
    return (PR ? PR.select(n) === "one" : n === 1) ? eins : mehr;
  };
  // "3 Preise", "1 Preis"
  window.anzahl = function (n, eins, mehr) {
    return zahl(n) + " " + plural(n, eins, mehr);
  };
  // Zahl mit deutschem Tausendertrennzeichen (ab 1000): 2345 -> "2.345"
  window.zahl = function (n) {
    return typeof n === "number" ? n.toLocaleString("de-DE") : String(n == null ? "" : n);
  };
  // Name, der nie das Layout sprengt: nach 2 Zeilen gekuerzt, voller Name als title. klasse z. B. "n", "drei", "eine"
  window.kurzHtml = function (text, klasse) {
    return '<span class="kappe' + (klasse ? " " + klasse : "") + '" title="' + esc(text) + '">' + esc(text) + "</span>";
  };

  // "12 von 15"
  window.restText = function (p) {
    return zahl(p.rest) + " von " + zahl(p.menge);
  };

  // Tabelle der ewigen Bestenliste. opts: {limit, jahre}
  window.bestenlisteHtml = function (stat, limit) {
    const jahre = stat.jahre || [];
    const zeilen = (stat.bestenliste || []).slice(0, limit || 9999);
    if (!zeilen.length) return '<p class="leer-text">Noch keine Daten. Sobald Siege eingetragen sind, erscheint hier die Bestenliste.</p>';
    let h = '<table class="daten' + (jahre.length > 8 ? " eng" : "") + '"><thead><tr><th>Name</th>';
    jahre.forEach((j) => (h += "<th>" + j + "</th>"));
    h += '<th class="gesamt">Gesamt</th></tr></thead><tbody>';
    zeilen.forEach((z, i) => {
      h += '<tr><td class="name"><div class="name-zelle"><span class="nr leise">' + (i + 1) + ".</span>" + kurzHtml(z.name) + "</div></td>";
      jahre.forEach((j) => {
        const v = z.jahre[String(j)];
        h += v == null ? '<td class="null">–</td>' : "<td>" + zahl(v) + "</td>";
      });
      h += '<td class="gesamt">' + zahl(z.gesamt) + "</td></tr>";
    });
    return h + "</tbody></table>";
  };

  window.jahresvergleichHtml = function (stat) {
    if (!(stat.jahresvergleich || []).length) return '<p class="leer-text">Noch keine Daten.</p>';
    let h = '<table class="daten' + ((stat.jahresvergleich || []).length > 8 ? " eng" : "") + '"><thead><tr><th>Jahr</th><th>Teilnehmer</th><th>Preise</th><th>Runden</th></tr></thead><tbody>';
    (stat.jahresvergleich || []).forEach((r) => {
      h += "<tr><td>" + r.jahr + "</td><td>" + zahl(r.teilnehmer) + "</td><td>" + zahl(r.preise_gesamt) + "</td><td>" + zahl(r.runden) + "</td></tr>";
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
        ? "<p class='rekord-gross'>" + anzahl(ma.ewig[0].siege, "Sieg", "Siege") + "</p><p>" +
          ma.ewig.map((e) => esc(e.name) + " (" + e.jahr + ")").join(", ") + "</p>"
        : '<p class="leise">Noch keine Daten.</p>') +
      (ma.je_jahr.length
        ? "<ul class='je-jahr" + (ma.je_jahr.length > 6 ? " viele" : "") + "'>" + ma.je_jahr.map((e) => "<li><b>" + e.jahr + "</b>" + kurzHtml(e.name) + "<span class='anz'>· " + zahl(e.siege) + "</span></li>").join("") + "</ul>"
        : "");
    return {
      abend: abend,
      teilnahmen: liste((r.teilnahmen || []).slice(0, 5), (x) => kurzHtml(x.name) + "<b>" + zahl(x.teilnahmen) + "×</b>"),
      pechvogel: '<p class="unterzeile">Teilnahmen ohne Sieg</p>' + liste((r.pechvogel || []).slice(0, 5), (x) => kurzHtml(x.name) + "<b>" + zahl(x.teilnahmen) + "×</b>"),
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
