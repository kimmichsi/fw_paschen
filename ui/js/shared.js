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

  // Linien-Icons der Oberflaeche (eigener Satz, gleicher Stil wie die Preis-Icons: 24er Raster, Linie, runde Enden)
  const UI = {
    zurueck: '<path d="M15 5l-7 7 7 7"/>',
    weiter: '<path d="M9 5l7 7-7 7"/>',
    hoch: '<path d="M5 15l7-7 7 7"/>',
    runter: '<path d="M5 9l7 7 7-7"/>',
    schliessen: '<path d="M6 6l12 12M18 6L6 18"/>',
    haken: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    mehr: '<circle cx="5.5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18.5" cy="12" r="1.2"/>',
  };
  window.uiIcon = function (name) {
    return '<span class="icon" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">' + (UI[name] || "") + "</svg></span>";
  };

  // Dauer einer Variablen aus basis.css in Millisekunden (z. B. "--dauer-aus"); so steht keine feste Dauer im Skript
  window.dauerMs = function (name, standard) {
    const roh = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    const w = parseFloat(roh);
    if (!isFinite(w)) return standard || 0;
    return /ms$/.test(roh) ? w : /s$/.test(roh) ? w * 1000 : w;
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
    if (!(stat.jahresvergleich || []).length) return '<p class="leer-text">Noch keine Daten</p>';
    let h = '<table class="daten' + ((stat.jahresvergleich || []).length > 8 ? " eng" : "") + '"><thead><tr><th>Jahr</th><th>Teilnehmer</th><th>Preise</th><th>Runden</th></tr></thead><tbody>';
    (stat.jahresvergleich || []).forEach((r) => {
      h += "<tr><td>" + r.jahr + "</td><td>" + zahl(r.teilnehmer) + "</td><td>" + zahl(r.preise_gesamt) + "</td><td>" + zahl(r.runden) + "</td></tr>";
    });
    return h + "</tbody></table>";
  };

  // Rekorde als drei Bloecke (Listen). Gibt {nachmittag, teilnahmen, pechvogel} als HTML zurueck.
  window.rekordeHtml = function (stat) {
    const r = stat.rekorde || {};
    const ma = r.meiste_siege_nachmittag || { ewig: [], je_jahr: [] };
    const liste = (arr, fmt) =>
      arr && arr.length ? "<ol>" + arr.map((x) => "<li>" + fmt(x) + "</li>").join("") + "</ol>" : '<p class="leise">Noch keine Daten</p>';
    const nachmittag =
      (ma.ewig.length
        ? "<p class='rekord-gross'>" + anzahl(ma.ewig[0].siege, "Sieg", "Siege") + "</p><p>" +
          ma.ewig.map((e) => esc(e.name) + " (" + e.jahr + ")").join(", ") + "</p>"
        : '<p class="leise">Noch keine Daten</p>') +
      (ma.je_jahr.length
        ? "<ul class='je-jahr" + (ma.je_jahr.length > 6 ? " viele" : "") + "'>" + ma.je_jahr.map((e) => "<li><b>" + e.jahr + "</b>" + kurzHtml(e.name) + "<span class='anz'>· " + zahl(e.siege) + "</span></li>").join("") + "</ul>"
        : "");
    return {
      nachmittag: nachmittag,
      teilnahmen: liste((r.teilnahmen || []).slice(0, 5), (x) => kurzHtml(x.name) + "<b>" + zahl(x.teilnahmen) + "×</b>"),
      pechvogel: '<p class="unterzeile">Teilnehmer ohne Sieg</p>' + liste((r.pechvogel || []).slice(0, 5), (x) => kurzHtml(x.name) + "<b>" + zahl(x.teilnahmen) + "× dabei</b>"),
    };
  };


  // ------------------------------------------------------------------ Preisbilder
  // BILDER: {name_norm: data_url}. Bedienfenster holt sie ueber api.bilder(), der Beamer bekommt sie per window.bilderSetzen(map).
  window.BILDER = {};
  window.normName = function (s) { return String(s || "").trim().toLowerCase().replace(/\s+/g, " "); };
  const DATA_OK = /^data:image\/(jpeg|png);base64,[A-Za-z0-9+\/=]+$/;
  // Bild (abgerundet, feste Quadratgroesse wie das Icon) oder Icon, wenn kein Bild vorhanden ist
  window.bildIcon = function (bild, name) {
    const u = bild && window.BILDER[bild];
    if (u && DATA_OK.test(u)) return '<span class="bild" aria-hidden="true"><img alt="" src="' + u + '"></span>';
    return icon(name);
  };
  // Datei -> JPEG-Data-URL, laengste Kante hoechstens 800 px, hoechstens ca. 300 KB
  window.bildVerkleinern = function (datei) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(datei);
      const img = new Image();
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error("Das Bild konnte nicht gelesen werden.")); };
      img.onload = () => {
        URL.revokeObjectURL(url);
        let w = img.naturalWidth, h = img.naturalHeight;
        if (!w || !h) { rej(new Error("Das Bild konnte nicht gelesen werden.")); return; }
        const f = Math.min(1, 800 / Math.max(w, h));
        w = Math.max(1, Math.round(w * f)); h = Math.max(1, Math.round(h * f));
        let q = 0.88, ergebnis = "";
        for (let versuch = 0; versuch < 12; versuch++) {
          const c = document.createElement("canvas");
          c.width = w; c.height = h;
          const g = c.getContext("2d");
          g.fillStyle = "#fff"; g.fillRect(0, 0, w, h); // PNG mit Transparenz: weisser Grund
          g.drawImage(img, 0, 0, w, h);
          ergebnis = c.toDataURL("image/jpeg", q);
          if (ergebnis.length * 0.75 <= 300 * 1024) break;
          if (q > 0.5) q -= 0.1; else { w = Math.max(1, Math.round(w * 0.8)); h = Math.max(1, Math.round(h * 0.8)); }
        }
        res(ergebnis);
      };
      img.src = url;
    });
  };

  // ------------------------------------------------------------------ Wuerfel-Grafiken (Regel-Show)
  const AUGEN = { 1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8] };
  window.wuerfelSvg = function (v) {
    let h = '<svg viewBox="0 0 100 100" aria-hidden="true"><rect class="w-koerper" x="6" y="6" width="88" height="88" rx="18"/>';
    (AUGEN[v] || AUGEN[1]).forEach((k) => { h += '<circle class="w-auge" cx="' + (28 + (k % 3) * 22) + '" cy="' + (28 + Math.floor(k / 3) * 22) + '" r="9"/>'; });
    return h + "</svg>";
  };
  window.becherSvg = function () {
    return '<svg viewBox="0 0 120 150" aria-hidden="true"><path class="b-koerper" d="M22 14 L98 14 L88 138 Q87 144 80 144 L40 144 Q33 144 32 138 Z"/>' +
      '<path class="b-band" d="M25.2 50 L94.8 50 L93.2 72 L26.8 72 Z"/><ellipse class="b-mund" cx="60" cy="14" rx="38" ry="8"/></svg>';
  };
  // still = true: ohne Animation (Vorschau)
  window.wuerfelBlock = function (w, still) {
    return '<div class="wurf' + (still ? " still" : "") + '" aria-hidden="true"><div class="becher">' + becherSvg() + '</div><div class="wuerfel-reihe">' +
      w.map((v, i) => '<div class="wuerfel-wurf" style="--i:' + i + ";--rot:" + [-6, 4, -3][i % 3] + 'deg">' + wuerfelSvg(v) + "</div>").join("") + "</div></div>";
  };

  // Nur die drei Wuerfel (ohne Becher), z. B. fuer die Sieg-Einblendung
  window.wuerfelReihe = function (w) {
    return '<div class="wurf" aria-hidden="true"><div class="wuerfel-reihe">' +
      w.map((v, i) => '<div class="wuerfel-wurf" style="--i:' + i + ";--rot:" + [-6, 4, -3][i % 3] + 'deg">' + wuerfelSvg(v) + "</div>").join("") + "</div></div>";
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
