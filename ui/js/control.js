// Bedienfenster. Zustand kommt von Python (window.pywebview.api) oder aus der Demo-Attrappe (mock.js).
(function () {
  const $ = (id) => document.getElementById(id);
  let Z = null;           // letzter Zustand
  let demo = false;
  let ansicht = null;     // aktuelle Ansicht
  let gewaehlt = null;    // angeklickte Person im Spiel
  let XL = null;          // Excel-Vorschau {pfad, vorschau}
  let XLjahre = new Set();
  let XLueber = false;
  let XLfertig = null;
  let modalRefresh = null;
  let laufend = 0;        // Doppelklick-Schutz: Anzahl laufender Api-Aufrufe

  // ------------------------------------------------------------------ Aufruf der Api
  const AN = ["start", "vorbereitung", "spiel", "statistik", "regeln", "daten", "excel"];
  let bilderVer = null;   // bilder_version, zu der der Bild-Cache passt
  async function bilderPruefen() {
    if (!Z || Z.bilder_version === undefined || Z.bilder_version === bilderVer) return;
    const api = demo ? window.MockApi : (window.pywebview && window.pywebview.api);
    if (!api || typeof api.bilder !== "function") return;
    try { const m = await api.bilder(); if (m && !m.fehler) { window.BILDER = m; bilderVer = Z.bilder_version; } } catch (e) { /* ohne Bilder weiter */ }
  }
  // Nur lesen (Listen): kein Doppelklick-Schutz noetig, aendert den Zustand nicht
  async function lies(name, ...args) {
    const api = demo ? window.MockApi : (window.pywebview && window.pywebview.api);
    if (!api) return null;
    try { const r = await api[name](...args); if (r && r.fehler) { toast(r.fehler, true); return null; } return r; }
    catch (e) { toast("Fehler: " + (e && e.message ? e.message : e), true); return null; }
  }
  async function call(name, ...args) {
    const api = demo ? window.MockApi : (window.pywebview && window.pywebview.api);
    if (!api) { toast("Keine Verbindung zur Anwendung", true); return null; }
    let r;
    laufend++;
    try { r = await api[name](...args); }
    catch (e) { toast("Fehler: " + (e && e.message ? e.message : e), true); return null; }
    finally { laufend--; }
    if (r && r.fehler) { toast(r.fehler, true); return null; }
    if (r && r.personen !== undefined && r.statistik !== undefined) { Z = r; await bilderPruefen(); alleZeichnen(); }
    return r === undefined ? true : r;
  }

  let toastTimer = null;
  let toastAusTimer = null;
  const ausMs = () => dauerMs("--dauer-aus", 140) + 20; // etwas laenger als --dauer-aus, dann erst display:none
  // text: String oder Liste von Zeilen; opts.rueckgaengig: Button "Rueckgaengig" anzeigen
  function toast(text, fehler, opts) {
    const t = $("toast");
    const zeilen = Array.isArray(text) ? text : [text];
    const lang = (opts && opts.rueckgaengig) || zeilen.length > 1;
    t.innerHTML = zeilen.map((z, i) => "<div" + (i > 0 ? ' class="hinweis-zeile"' : "") + ">" + esc(z) + "</div>").join("") +
      (opts && opts.rueckgaengig ? '<button class="knopf toast-knopf" data-act="rueckgaengig">Rückgängig</button>' : "");
    clearTimeout(toastTimer); clearTimeout(toastAusTimer);
    t.className = "toast" + (fehler ? " fehler" : "") + " sichtbar";
    if (t.hidden) {
      // Einblenden: erst im Ausgangszustand zeichnen lassen, dann Klasse setzen (Transition)
      t.classList.remove("sichtbar");
      t.hidden = false;
      void t.offsetWidth;
      t.classList.add("sichtbar");
    }
    toastTimer = setTimeout(() => {
      t.classList.remove("sichtbar");
      toastAusTimer = setTimeout(() => (t.hidden = true), ausMs());
    }, fehler ? 6000 : lang ? 9000 : 3500);
  }

  // Hinweis nach einem Eintrag: Runde/Name/Preis, ggf. Phasenwechsel oder Spielende, plus "Rueckgaengig"
  function eintragHinweis(e) {
    const zeilen = ["Runde " + zahl(e.nr) + ": " + e.name + " – " + e.preis_name];
    const f = e.folge;
    if (f && f.typ === "phasenwechsel") {
      zeilen.push((f.von_name ? "Phase „" + f.von_name + "“" : "Phase") + " beendet – " +
        (f.nach_name ? "weiter mit „" + f.nach_name + "“" : "alle Phasen durch – Sonderrunde(n) offen"));
    } else if (f && f.typ === "ende") {
      zeilen.push("Spiel beendet");
    }
    toast(zeilen, false, { rueckgaengig: true });
  }

  // ------------------------------------------------------------------ Dialoge
  let modalAusTimer = null;
  function openModal(html) {
    const m = $("modal");
    clearTimeout(modalAusTimer);
    $("modal-karte").innerHTML = html;
    m.classList.remove("sofort");
    if (m.hidden) {
      m.hidden = false;
      void m.offsetWidth; // Ausgangszustand zeichnen, dann Klasse setzen
    }
    m.classList.add("offen");
    const f = $("modal-karte").querySelector("input[type=text],input[type=search],input[type=number]");
    if (f) setTimeout(() => f.focus(), 30);
  }
  // Schliessen: per Klick schnell ausblenden (--dauer-aus); per Tastatur (Escape) sofort, ohne Animation
  function closeModal(sofort) {
    const m = $("modal");
    modalRefresh = null;
    clearTimeout(modalAusTimer);
    if (sofort) m.classList.add("sofort");
    m.classList.remove("offen");
    const fertig = () => { m.hidden = true; m.classList.remove("sofort"); $("modal-karte").innerHTML = ""; };
    if (sofort) fertig(); else modalAusTimer = setTimeout(fertig, ausMs());
  }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("modal").hidden) closeModal(true); });

  function bestaetigen(titel, text, knopf, abbruch) {
    return new Promise((res) => {
      openModal("<h2>" + esc(titel) + "</h2><p>" + esc(text) + '</p><div class="modal-aktionen"><button class="knopf" data-m="nein">' + esc(abbruch || "Abbrechen") + '</button><button class="knopf gefahr" data-m="ja">' + esc(knopf || "OK") + "</button></div>");
      $("modal-karte").onclick = (e) => {
        const b = e.target.closest("[data-m]");
        if (!b) return;
        $("modal-karte").onclick = null;
        closeModal();
        res(b.dataset.m === "ja");
      };
    });
  }

  // ------------------------------------------------------------------ Hilfen
  const norm = (s) => String(s || "").toLowerCase();
  const passt = (name, such) => !such || norm(name).includes(norm(such.trim()));
  const spiel = () => (Z && Z.spiel) || null;

  function wechsleAnsicht(name) {
    if (name === "vorbereitung" || name === "spiel") { if (!spiel()) name = "start"; }
    if (name !== "start" && name !== "vorbereitung" && name !== "spiel" && !(Z && Z.datenordner)) name = "start";
    ansicht = name;
    AN.forEach((n) => { $("ansicht-" + n).hidden = n !== name; });
    alleZeichnen();
  }

  // ------------------------------------------------------------------ Zeichnen
  function alleZeichnen() {
    if (!Z) return;
    if (!ansicht) ansicht = startAnsicht();
    zeichneNav();
    wechselSichtbar();
    if (ansicht === "start") zeichneStart();
    if (ansicht === "vorbereitung") zeichneVorbereitung();
    if (ansicht === "spiel") zeichneSpiel();
    if (ansicht === "statistik") zeichneStatistik();
    if (ansicht === "regeln" && CTRL.zeichner.regeln) CTRL.zeichner.regeln();
    if (ansicht === "daten" && CTRL.zeichner.daten) CTRL.zeichner.daten();
    if (ansicht === "excel") zeichneExcel();
    zeichneBanner();
    if (modalRefresh) modalRefresh();
  }
  function startAnsicht() {
    if (!Z.datenordner || !spiel()) return "start";
    return Z.spiel.runden_gespielt > 0 ? "spiel" : "vorbereitung";
  }
  function wechselSichtbar() {
    // falls Ansicht nicht mehr moeglich ist (z. B. Spiel geloescht)
    if ((ansicht === "vorbereitung" || ansicht === "spiel") && !spiel()) ansicht = "start";
    AN.forEach((n) => { $("ansicht-" + n).hidden = n !== ansicht; });
  }

  function zeichneNav() {
    document.querySelectorAll(".nav-knopf").forEach((b) => {
      const a = b.dataset.ansicht;
      b.classList.toggle("aktiv", a === ansicht);
      b.disabled = ((a === "vorbereitung" || a === "spiel") && !spiel()) || ((a === "statistik" || a === "excel" || a === "regeln" || a === "daten") && !Z.datenordner);
    });
    $("nav-jahr").textContent = Z.jahr || "";
    document.querySelectorAll("[data-act=beamer-ansicht]").forEach((b) => b.classList.toggle("aktiv", b.dataset.wert === Z.beamer_ansicht));
    document.querySelectorAll("[data-act=beamer-design]").forEach((b) => b.classList.toggle("aktiv", b.dataset.wert === Z.beamer_design));
    const dAktiv = !!(Z.demo && Z.demo.aktiv);
    $("demo-hinweis").hidden = !demo || dAktiv;
    $("demo-schalter").hidden = dAktiv;
  }
  // Banner im Demo-Modus (echte Anwendung mit Demo-Daten)
  function zeichneBanner() {
    const b = $("demo-banner");
    const an = !!(Z.demo && Z.demo.aktiv);
    b.hidden = !an;
    if (!an) { b.innerHTML = ""; b._art = null; return; }
    if (b._art === Z.demo.art && b.innerHTML) return;
    b._art = Z.demo.art;
    b.innerHTML = "<strong>Demo</strong><span>Testdaten (" + (Z.demo.art === "kopie" ? "Kopie" : "erfunden") + "). Deine echten Daten bleiben unverändert.</span>" +
      '<button class="knopf klein" data-act="demo-zuruecksetzen">Zurücksetzen</button><button class="knopf klein" data-act="demo-beenden">Demo beenden</button>';
  }

  // ---- Start
  function zeichneStart() {
    $("start-ordner-text").textContent = Z.datenordner
      ? Z.datenordner
      : "Wähle einen Ordner, in dem Paschen die Spieldaten speichert (z. B. auf dem Laptop oder einem Vereinslaufwerk).";
    $("start-ordner-knopf").textContent = Z.datenordner ? "Ordner ändern …" : "Ordner wählen …";
    // Im Demo-Modus bleibt der Datenordner unangetastet: kein Knopf zum Ändern
    $("start-ordner-knopf").hidden = !!Z.datenordner && (demo || !!(Z.demo && Z.demo.aktiv));
    $("start-spiele-karte").hidden = !Z.datenordner;
    $("start-jahre").innerHTML = Z.jahre_info.length
      ? Z.jahre_info.map((j) =>
          '<div class="jahr-wrap" data-jahr="' + j.jahr + '"><button class="jahr-kachel' + (j.jahr === Z.jahr ? " aktiv" : "") + '" data-act="jahr" data-jahr="' + j.jahr + '"><b>' + j.jahr + "</b><span>" +
          anzahl(j.preise, "Preis", "Preise") + " · " + zahl(j.teilnehmer) + " angemeldet<br>" + (j.beendet ? "beendet" : anzahl(j.siege, "Sieg", "Siege")) + "</span></button>" +
          '<button class="jahr-mehr" data-act="jahr-menue" data-jahr="' + j.jahr + '" aria-haspopup="menu" aria-label="Menü für Spiel ' + j.jahr + '" title="Spiel ' + j.jahr + ': öffnen oder löschen">' + uiIcon("mehr") + "</button></div>").join("")
      : '<p class="leer-text">Noch kein Spiel vorhanden. Lege unten das erste an oder importiere eine Excel-Datei.</p>';
    const el = $("neu-jahr");
    const vorschlag = Z.jahre.length ? Math.max(...Z.jahre) + 1 : new Date().getFullYear();
    if (!el.value || el.dataset.auto !== "0") { el.value = vorschlag; el.dataset.auto = "1"; }
  }

  // ---- Vorbereitung
  function zeichneVorbereitung() {
    const s = spiel();
    $("vb-jahr").textContent = Z.jahr || "";
    // Phasen
    $("vb-phasen").innerHTML = s.phasen.length ? s.phasen.map((p, i) =>
      '<div class="phasen-zeile"><input type="text" class="phase-name" data-id="' + p.id + '" value="' + esc(p.name) + '">' +
      '<span class="rest">' + anzahl(p.gesamt, "Preis", "Preise") + "</span>" +
      '<button class="knopf symbol" data-act="phase-hoch" data-id="' + p.id + '"' + (i === 0 ? " disabled" : "") + ' title="Nach vorn" aria-label="Nach vorn">' + uiIcon("hoch") + "</button>" +
      '<button class="knopf symbol" data-act="phase-runter" data-id="' + p.id + '"' + (i === s.phasen.length - 1 ? " disabled" : "") + ' title="Nach hinten" aria-label="Nach hinten">' + uiIcon("runter") + "</button>" +
      '<button class="knopf symbol gefahr" data-act="phase-loeschen" data-id="' + p.id + '" title="Phase löschen" aria-label="Phase löschen">' + uiIcon("schliessen") + "</button></div>").join("")
      : '<p class="leer-text">Noch keine Phase. Lege zuerst mindestens eine Phase an.</p>';
    // Preise nach Phasen
    let h = "";
    s.phasen.forEach((ph) => {
      const ps = s.preise.filter((p) => p.phase_id === ph.id && !p.spezial);
      h += '<div class="preis-gruppe"><h3>' + esc(ph.name) + "</h3>" + (ps.length ? ps.map(preisZeile).join("") : '<p class="leer-text">Keine Preise in dieser Phase</p>') + "</div>";
    });
    const sp = s.preise.filter((p) => p.spezial);
    h += '<div class="preis-gruppe"><h3 class="sonder">Spezialpreise (Sonderrunde)</h3>' + (sp.length ? sp.map(preisZeile).join("") : '<p class="leer-text">Keine Spezialpreise</p>') + "</div>";
    $("vb-preise").innerHTML = h;
    // Teilnehmer
    const such = $("vb-suche").value;
    $("vb-zaehler").textContent = s.anwesende.length + " angemeldet";
    const pe = Z.personen.filter((p) => passt(p.name, such));
    $("vb-personen").innerHTML = pe.length ? pe.map((p) =>
      '<button class="name-kachel' + (p.anwesend ? " angemeldet" : "") + '" data-act="toggle-person" data-id="' + p.id + '">' + kurzHtml(p.name, "n") +
      (p.ist_team ? '<span class="zusatz">Team</span>' : "") + (p.anwesend ? '<span class="haken-zeichen">' + uiIcon("haken") + "</span>" : "") + "</button>").join("")
      : '<p class="leer-text">Keine Person gefunden</p>';
  }
  function preisZeile(p) {
    return '<button class="preis-zeile' + (p.spezial ? " spezial" : "") + '" data-act="preis-bearbeiten" data-id="' + p.id + '">' + bildIcon(p.bild, p.icon) +
      "<span>" + esc(p.name) + '</span><span class="menge">' + (p.vergeben ? zahl(p.rest) + " von " + zahl(p.menge) + " übrig" : zahl(p.menge) + " Stück") + "</span><span class='leise'>bearbeiten</span></button>";
  }

  // ---- Spiel
  function zeichneSpiel() {
    const s = spiel();
    const sr = Z.sonderrunde;
    if (gewaehlt && !s.anwesende.some((a) => a.id === gewaehlt)) gewaehlt = null;

    // Namen
    const such = $("sp-suche").value;
    const liste = s.anwesende.filter((a) => passt(a.name, such));
    $("sp-titel-wer").textContent = sr ? "Wer gewinnt " + sr.name + "?" : "1 · Wer hat gewonnen?";
    $("sp-titel-wer").title = sr ? $("sp-titel-wer").textContent : "";
    $("sp-namen").innerHTML = liste.length ? liste.map((a) =>
      '<button class="name-kachel' + (a.id === gewaehlt && !sr ? " gewaehlt" : "") + '" data-act="person" data-id="' + a.id + '">' + kurzHtml(a.name, "n") +
      (a.ist_team ? '<span class="zusatz">Team</span>' : "") + (a.siege ? '<span class="stille-zahl">' + zahl(a.siege) + "</span>" : "") + "</button>").join("")
      : '<p class="leer-text">' + (s.anwesende.length ? "Niemand gefunden." : "Noch niemand angemeldet. Unter „Werkzeuge“ Teilnehmer nachtragen.") + "</p>";

    // Preise
    const banner = $("sp-sonder-banner");
    banner.hidden = !sr;
    $("sp-titel-preis").textContent = sr ? "Sonderrunde" : "2 · Welcher Preis?";
    if (sr) {
      banner.innerHTML = '<div class="gross-text">' + bildIcon(sr.bild, sr.icon) + " Sonderrunde: " + esc(sr.name) + "</div><p>Auf dem Beamer läuft die Sonderrunde. Klicke links auf den Gewinner.</p>" +
        '<button class="knopf" data-act="sonder-abbrechen">Sonderrunde abbrechen</button>';
    }
    let hinweis = "";
    if (s.beendet) hinweis = "";
    else if (s.aktive_phase_name) hinweis = "Aktive Phase: " + s.aktive_phase_name + " (Phase " + s.phase_nr + " von " + s.phasen_anzahl + ")";
    else hinweis = s.spezialpreise_offen.length ? "Alle Phasen sind beendet – es fehlt nur noch die Sonderrunde." : "Keine Preise vorhanden. In der Vorbereitung Preise anlegen.";
    // Die aktive Phase traegt das Wuerfelauge
    $("sp-phasenhinweis").innerHTML = sr || !hinweis ? "" : (s.aktive_phase_name ? '<span class="aug" aria-hidden="true"></span>' : "") + "<span>" + esc(hinweis) + "</span>";
    const wb = s.preise.filter((p) => p.waehlbar);
    $("sp-preise").hidden = !!sr;
    $("sp-preise").innerHTML = wb.map((p) =>
      '<button class="preis-kachel' + (gewaehlt ? " bereit" : "") + '" data-act="preis" data-id="' + p.id + '">' + bildIcon(p.bild, p.icon) +
      kurzHtml(p.name, "name drei") + '<span class="rest"><b>' + zahl(p.rest) + "</b> von " + zahl(p.menge) + "</span></button>").join("");
    $("sp-spezial").hidden = !!sr;
    $("sp-spezial").innerHTML = s.beendet
      ? '<div class="ende-banner">Alle Preise sind vergeben. Das Spiel ist beendet.</div>'
      : s.spezialpreise_offen.map((p) =>
          '<button class="spezial-knopf" data-act="sonder-start" data-id="' + p.id + '">' + bildIcon(p.bild, p.icon) + "<span><small>Spezialpreis</small>Sonderrunde: " + esc(p.name) + "</span></button>").join("");

    // Status
    const l = s.letzter_sieg;
    const fortschritt = s.beendet ? "Beendet nach " + anzahl(s.runden_gespielt, "Runde", "Runden")
      : "Runde " + zahl(s.runde) + " · noch " + anzahl(s.rest_gesamt, "Preis", "Preise") + (s.phase_nr ? " · Phase " + s.phase_nr + "/" + s.phasen_anzahl : "");
    $("sp-status").innerHTML = '<h2>Stand</h2><div class="fortschritt">' + esc(fortschritt) + "</div>" +
      (l ? '<div class="letzter"><div class="zeile' + (l.sonderrunde ? " sonder" : "") + '">Runde ' + zahl(l.nr) + ": " + esc(l.name) + " – " + esc(l.preis_name) + "</div></div>"
        : '<div class="letzter leise">Noch keine Eintragung.</div>') +
      '<button class="knopf" data-act="rueckgaengig"' + (l ? "" : " disabled") + ">Rückgängig</button>";
    $("sp-siege").innerHTML = s.letzte_siege.length ? s.letzte_siege.map((x) =>
      '<li class="' + (x.sonderrunde ? "sonder" : "") + '"><span class="nr">' + zahl(x.nr) + '.</span><span>' + esc(x.name) + ' <span class="was">– ' + esc(x.preis_name) + "</span></span></li>").join("")
      : '<li class="leise">Noch keine Siege.</li>';
  }

  // ---- Statistik
  function zeichneStatistik() {
    const st = Z.statistik;
    $("st-liste").innerHTML = bestenlisteHtml(st, 200);
    $("st-jahre").innerHTML = jahresvergleichHtml(st);
    const r = rekordeHtml(st);
    $("st-nachmittag").innerHTML = r.nachmittag;
    $("st-teiln").innerHTML = r.teilnahmen;
    $("st-pech").innerHTML = r.pechvogel;
  }

  // ---- Excel
  function zeichneExcel() {
    const box = $("xl-vorschau");
    if (XLfertig) { box.innerHTML = "<p>" + esc(XLfertig) + "</p>"; return; }
    if (!XL) { box.innerHTML = ""; return; }
    const jahre = XL.vorschau.jahre;
    const bestand = new Set(Z.jahre);
    let h = '<p class="leise">Datei: ' + esc(XL.pfad) + "</p>";
    if (!jahre.length) h += '<p class="leer-text">In der Datei wurden keine Jahresblätter gefunden</p>';
    jahre.forEach((j) => {
      const existiert = j.existiert || bestand.has(j.jahr);
      h += '<label class="xl-jahr"><input type="checkbox" data-act="xl-jahr" data-jahr="' + j.jahr + '"' + (XLjahre.has(j.jahr) ? " checked" : "") + "><div><h3>" + j.jahr + "</h3>" +
        '<div class="details">' + anzahl(j.personen, "Person", "Personen") + " · " + anzahl(j.siege, "Sieg", "Siege") + " · " + anzahl(j.menge_gesamt, "Preis", "Preise") + " insgesamt<br>" +
        j.preise.map((p) => esc(p.name) + " " + p.vergeben + "/" + p.menge).join(" · ") + "</div>" +
        (existiert ? '<div class="existiert">Dieses Jahr gibt es schon in der App.</div>' : "") +
        ((j.live_siege || 0) > 0 ? '<div class="warn live">In der App wurden für dieses Jahr ' + anzahl(j.live_siege, "Sieg", "Siege") + " live eingetragen (nicht aus Excel). Beim Überschreiben gehen sie verloren.</div>" : "") +
        (j.warnungen || []).map((w) => '<div class="warn">Hinweis: ' + esc(w) + "</div>").join("") + "</div></label>";
    });
    const braucht = jahre.some((j) => XLjahre.has(j.jahr) && (j.existiert || bestand.has(j.jahr)));
    h += '<div class="xl-aktion">';
    if (braucht) h += '<label class="haken"><input type="checkbox" data-act="xl-ueber"' + (XLueber ? " checked" : "") + "> Vorhandene Daten dieser Jahre überschreiben</label>";
    h += '<button class="knopf primaer" data-act="xl-import"' + (XLjahre.size && (!braucht || XLueber) ? "" : " disabled") + ">Ausgewählte Jahre importieren</button></div>";
    box.innerHTML = h;
  }

  // ------------------------------------------------------------------ Dialoge: Preis, Nachlegen, Nachtragen
  function preisDialog(preis) {
    const s = spiel();
    const neu = !preis;
    const p = preis || { name: "", icon: "geschenk", menge: 1, phase_id: s.aktive_phase_id || (s.phasen[0] && s.phasen[0].id) || "", spezial: false, vergeben: 0 };
    let ic = p.icon || "geschenk";
    let manuell = !neu;
    let bildNeu = null, bildWeg = false;   // neu gewaehltes Bild (Data-URL) bzw. "Bild entfernen"
    openModal(
      "<h2>" + (neu ? "Preis hinzufügen" : "Preis bearbeiten") + "</h2>" +
      '<label class="feld"><span>Name</span><input type="text" id="pd-name" value="' + esc(p.name) + '" autocomplete="off"></label>' +
      '<div class="feld"><span>Icon</span><div class="icon-wahl" id="pd-icons"></div></div>' +
      '<div class="feld"><span>Bild (optional)</span><div class="bild-feld"><div id="pd-bild" class="bild-vorschau"></div><div class="bild-knoepfe"><button type="button" class="knopf klein" data-bild="waehlen">Bild wählen …</button><button type="button" class="knopf klein" data-bild="entfernen" id="pd-bild-weg">Bild entfernen</button><span class="klein leise">JPG oder PNG, wird verkleinert gespeichert und beim Preisnamen gemerkt.</span></div></div></div>' +
      '<div class="feld-zeile"><label class="feld"><span>Menge' + (p.vergeben ? " (mindestens " + p.vergeben + " schon vergeben)" : "") + '</span><input type="number" id="pd-menge" min="' + Math.max(1, p.vergeben || 0) + '" value="' + p.menge + '"></label>' +
      '<label class="feld"><span>Phase</span><select id="pd-phase">' + s.phasen.map((ph) => '<option value="' + ph.id + '"' + (ph.id === p.phase_id ? " selected" : "") + ">" + esc(ph.name) + "</option>").join("") + "</select></label></div>" +
      '<label class="haken"><input type="checkbox" id="pd-spezial"' + (p.spezial ? " checked" : "") + "> Spezialpreis (nur per Sonderrunde, in keiner Phase)</label>" +
      '<div class="modal-aktionen">' + (neu ? "" : '<button class="knopf gefahr links" data-m="loeschen">Löschen</button>') +
      '<button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Speichern</button></div>');
    const zeichneIcons = () => {
      $("pd-icons").innerHTML = ICON_NAMEN.map((n) => '<button type="button" data-icon="' + n + '" class="' + (n === ic ? "aktiv" : "") + '" title="' + n + '">' + icon(n) + "</button>").join("");
    };
    const phaseToggle = () => { $("pd-phase").disabled = $("pd-spezial").checked; };
    const zeichneBild = () => {
      const key = normName($("pd-name").value);
      const url = bildNeu || (!bildWeg && window.BILDER[key]) || null;
      if (url && /^data:image\/(jpeg|png);base64,[A-Za-z0-9+\/=]+$/.test(url)) $("pd-bild").innerHTML = '<span class="bild"><img alt="" src="' + url + '"></span>';
      else $("pd-bild").innerHTML = icon(ic);
      $("pd-bild-weg").disabled = !url;
    };
    zeichneIcons(); phaseToggle(); zeichneBild();
    let timer = null;
    $("pd-name").addEventListener("input", zeichneBild);
    $("pd-name").addEventListener("input", () => {
      if (manuell) return;
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const r = await call("icon_raten", $("pd-name").value);
        if (typeof r === "string" && !manuell) { ic = r; zeichneIcons(); zeichneBild(); }
      }, 200);
    });
    $("pd-spezial").addEventListener("change", phaseToggle);
    $("modal-karte").onclick = async (e) => {
      const ib = e.target.closest("[data-icon]");
      if (ib) { ic = ib.dataset.icon; manuell = true; zeichneIcons(); zeichneBild(); return; }
      const bb = e.target.closest("[data-bild]");
      if (bb) {
        if (bb.dataset.bild === "entfernen") { bildNeu = null; bildWeg = true; zeichneBild(); return; }
        const u = await CTRL.bildWaehlen();
        if (u) { bildNeu = u; bildWeg = false; zeichneBild(); }
        return;
      }
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; closeModal(); return; }
      if (b.dataset.m === "loeschen") {
        const ja = await bestaetigen("Preis löschen?", "„" + p.name + "“ wird entfernt.", "Löschen");
        if (ja) { const r = await call("preis_loeschen", p.id); if (r) toast("Preis gelöscht"); } else { preisDialog(preis); }
        return;
      }
      if (b.dataset.m === "ok") {
        if (laufend) return;
        const name = $("pd-name").value, menge = parseInt($("pd-menge").value, 10) || 0;
        const spezial = $("pd-spezial").checked, phase = spezial ? null : $("pd-phase").value || null;
        const r = neu ? await call("preis_hinzufuegen", name, ic, menge, phase, spezial) : await call("preis_bearbeiten", p.id, name, ic, menge, phase, spezial);
        if (r) {
          if (bildNeu) await call("preis_bild_setzen", name.trim(), bildNeu);
          else if (bildWeg && window.BILDER[normName(name)]) await call("preis_bild_entfernen", name.trim());
          $("modal-karte").onclick = null; closeModal();
        }
      }
    };
  }

  function nachlegenDialog() {
    const s = spiel();
    if (!s.preise.length) { toast("Es gibt noch keine Preise", true); return; }
    const vorwahl = (s.preise.find((p) => p.waehlbar) || s.preise[0]).id;
    openModal(
      "<h2>Preis nachlegen</h2>" +
      '<label class="feld"><span>Preis</span><select id="nl-preis">' + s.preise.map((p) => '<option value="' + p.id + '"' + (p.id === vorwahl ? " selected" : "") + ">" + esc(p.name) + " (" + zahl(p.rest) + " von " + zahl(p.menge) + ")</option>").join("") + "</select></label>" +
      '<label class="feld"><span>Anzahl, die dazukommt</span><input type="number" id="nl-anzahl" min="1" value="1"></label>' +
      '<div class="menge-schnell"><button class="knopf" data-plus="1">+1</button><button class="knopf" data-plus="5">+5</button><button class="knopf" data-plus="10">+10</button></div>' +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Nachlegen</button></div>');
    $("modal-karte").onclick = async (e) => {
      const pl = e.target.closest("[data-plus]");
      if (pl) { $("nl-anzahl").value = pl.dataset.plus; return; }
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; closeModal(); return; }
      if (laufend) return;
      const r = await call("preis_nachlegen", $("nl-preis").value, parseInt($("nl-anzahl").value, 10) || 0);
      if (r) { $("modal-karte").onclick = null; closeModal(); toast("Preis nachgelegt"); }
    };
  }

  function nachtragenDialog() {
    openModal(
      "<h2>Teilnehmer nachtragen</h2>" +
      '<input type="search" id="nt-suche" class="suche" placeholder="Name suchen" autocomplete="off">' +
      '<div id="nt-liste" class="namen liste-klein"></div>' +
      '<h2 class="zwischen">Neue Person</h2>' +
      '<form id="nt-form" class="form-person"><div class="feld-zeile"><input type="text" id="nt-vor" placeholder="Vorname" autocomplete="off"><input type="text" id="nt-nach" placeholder="Nachname" autocomplete="off"></div>' +
      '<label class="haken"><input type="checkbox" id="nt-team"> Team („A / B“)</label><button class="knopf primaer" type="submit">Anlegen und anmelden</button></form>' +
      '<div class="modal-aktionen"><button class="knopf" data-m="fertig">Fertig</button></div>');
    const liste = () => {
      const such = $("nt-suche") ? $("nt-suche").value : "";
      const pe = Z.personen.filter((p) => !p.anwesend && passt(p.name, such));
      $("nt-liste").innerHTML = pe.length ? pe.map((p) => '<button class="name-kachel" data-id="' + p.id + '">' + kurzHtml(p.name, "n") + (p.ist_team ? '<span class="zusatz">Team</span>' : "") + "</button>").join("")
        : '<p class="leer-text">Niemand mehr zum Nachtragen</p>';
    };
    modalRefresh = liste;
    liste();
    $("nt-suche").addEventListener("input", liste);
    $("nt-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const r = await call("person_anlegen", $("nt-vor").value, $("nt-nach").value, $("nt-team").checked, true);
      if (r) { $("nt-vor").value = ""; $("nt-nach").value = ""; $("nt-team").checked = false; toast("Person angelegt und angemeldet"); }
    });
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (b) { $("modal-karte").onclick = null; closeModal(); return; }
      const k = e.target.closest(".name-kachel[data-id]");
      if (k && !laufend) { const r = await call("anmelden", k.dataset.id); if (r) toast("Angemeldet"); }
    };
  }

  // ------------------------------------------------------------------ Aktionen (Klicks)
  const AKTIONEN = Object.assign(CTRL.AKTIONEN, {
    ansicht: (el) => wechsleAnsicht(el.dataset.ansicht),
    "ordner-waehlen": async () => {
      const r = await call("datenordner_waehlen");
      if (r) { ansicht = startAnsicht(); alleZeichnen(); }
    },
    jahr: async (el) => {
      const r = await call("jahr_waehlen", parseInt(el.dataset.jahr, 10));
      if (r) { ansicht = startAnsicht(); alleZeichnen(); }
    },
    "neues-spiel": async () => {
      const jahr = parseInt($("neu-jahr").value, 10);
      if (!jahr) { toast("Bitte ein Jahr eingeben", true); return; }
      const r = await call("neues_spiel", jahr);
      if (r) { $("neu-jahr").dataset.auto = "1"; ansicht = "vorbereitung"; alleZeichnen(); toast("Spiel " + jahr + " angelegt."); }
    },
    "phase-hoch": (el) => call("phase_verschieben", el.dataset.id, -1),
    "phase-runter": (el) => call("phase_verschieben", el.dataset.id, 1),
    "phase-loeschen": async (el) => {
      const ph = spiel().phasen.find((p) => p.id === el.dataset.id);
      const ja = await bestaetigen("Phase löschen?", "Die Phase „" + ph.name + "“ wird " + (ph.preise.length ? "samt " + (ph.preise.length === 1 ? "ihrem Preis" : "ihren " + ph.preise.length + " Preisen") : "ohne Preise") + " entfernt.", "Löschen");
      if (ja) await call("phase_loeschen", el.dataset.id);
    },
    "preis-neu": () => {
      if (!spiel().phasen.length) { toast("Lege zuerst eine Phase an (oder nutze einen Spezialpreis)", false); }
      preisDialog(null);
    },
    "preis-bearbeiten": (el) => preisDialog(spiel().preise.find((p) => p.id === el.dataset.id)),
    "toggle-person": async (el) => {
      const p = Z.personen.find((x) => x.id === el.dataset.id);
      await call(p.anwesend ? "abmelden" : "anmelden", p.id);
    },
    person: async (el) => {
      if (Z.sonderrunde) {
        const r = await call("sonderrunde_sieg", el.dataset.id);
        if (r && r.ereignis) eintragHinweis(r.ereignis);
        return;
      }
      gewaehlt = gewaehlt === el.dataset.id ? null : el.dataset.id;
      zeichneSpiel();
    },
    preis: async (el) => {
      if (!gewaehlt) { toast("Bitte zuerst links den Gewinner anklicken", true); return; }
      const wer = gewaehlt;
      gewaehlt = null; // sofort leeren: ein zweiter Klick kann nichts mehr eintragen
      const r = await call("sieg", wer, el.dataset.id);
      if (r) {
        if (r.ereignis) eintragHinweis(r.ereignis);
        zeichneSpiel();
      } else if (spiel() && spiel().anwesende.some((a) => a.id === wer)) {
        gewaehlt = wer; // Fehler: Auswahl behalten
        zeichneSpiel();
      }
    },
    rueckgaengig: async () => { const r = await call("rueckgaengig"); if (r) toast("Letzte Eintragung rückgängig gemacht"); },
    "sonder-start": (el) => call("sonderrunde_starten", el.dataset.id),
    "sonder-abbrechen": () => call("sonderrunde_abbrechen"),
    nachlegen: nachlegenDialog,
    nachtragen: nachtragenDialog,
    "beamer-ansicht": (el) => call("beamer_ansicht_setzen", el.dataset.wert),
    "beamer-design": (el) => call("beamer_design_setzen", el.dataset.wert),
    "beamer-wechseln": async () => { const r = await call("beamer_bildschirm_wechseln"); if (r) toast("Beamer verschoben"); },
    "beamer-oeffnen": async () => {
      const r = await call("beamer_oeffnen");
      if (r) toast(r.beamer_neu ? "Beamer-Fenster geöffnet." : "Das Beamer-Fenster ist bereits offen.");
    },
    "excel-waehlen": async () => {
      const r = await call("excel_vorschau_waehlen");
      if (!r || r.abgebrochen) return;
      XL = r; XLfertig = null; XLueber = false;
      XLjahre = new Set(r.vorschau.jahre.map((j) => j.jahr));
      zeichneExcel();
    },
    "xl-jahr": (el) => {
      const j = parseInt(el.dataset.jahr, 10);
      if (el.checked) XLjahre.add(j); else XLjahre.delete(j);
      zeichneExcel();
    },
    "xl-ueber": (el) => { XLueber = el.checked; zeichneExcel(); },
    "xl-import": async () => {
      const jahre = [...XLjahre].sort();
      const live = XL.vorschau.jahre.filter((j) => XLjahre.has(j.jahr) && XLueber && (j.live_siege || 0) > 0);
      if (live.length) {
        const ja = await bestaetigen("Live eingetragene Siege gehen verloren",
          live.map((j) => j.jahr + ": " + anzahl(j.live_siege, "Sieg", "Siege")).join(", ") + " – diese wurden in der App live eingetragen und werden durch den Import überschrieben. Wirklich überschreiben?", "Ja, überschreiben");
        if (!ja) return;
      }
      const r = await call("excel_importieren", XL.pfad, jahre, XLueber);
      if (r) { XLfertig = "Import abgeschlossen: " + jahre.join(", "); XL = null; zeichneExcel(); toast(XLfertig); }
    },
    "excel-export": async () => {
      const r = await call("excel_exportieren");
      if (r && r.gespeichert) toast("Gespeichert: " + r.gespeichert);
    },
  });
  Object.assign(CTRL, { call, lies, toast, openModal, closeModal, bestaetigen, getZ: () => Z, spiel, passt, alleZeichnen,
    istLaufend: () => laufend > 0, setModalRefresh: (f) => { modalRefresh = f; }, setAnsicht: (a) => { ansicht = a; alleZeichnen(); }, startAnsicht });

  document.addEventListener("click", async (e) => {
    const el = e.target.closest("[data-act]");
    if (!el || el.disabled) return;
    if (el.tagName === "INPUT") return; // Checkboxen laufen ueber "change"
    if (laufend) return; // Doppelklick-Schutz: waehrend eines Api-Aufrufs werden Klicks ignoriert
    const h = AKTIONEN[el.dataset.act];
    if (h) await h(el, e);
  });
  document.addEventListener("change", async (e) => {
    const el = e.target;
    if (el.tagName === "INPUT" && el.type === "checkbox" && el.dataset.act) { await AKTIONEN[el.dataset.act](el, e); return; }
    if (el.classList && el.classList.contains("phase-name")) {
      const r = await call("phase_umbenennen", el.dataset.id, el.value);
      if (!r) alleZeichnen(); // alten Namen wiederherstellen
    }
  });

  // ------------------------------------------------------------------ Formulare und Suchfelder
  $("form-phase").addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await call("phase_hinzufuegen", $("phase-neu").value);
    if (r) $("phase-neu").value = "";
  });
  $("form-person").addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await call("person_anlegen", $("np-vorname").value, $("np-nachname").value, $("np-team").checked, true);
    if (r) { $("np-vorname").value = ""; $("np-nachname").value = ""; $("np-team").checked = false; $("np-vorname").focus(); toast("Person angelegt und angemeldet"); }
  });
  $("vb-suche").addEventListener("input", () => zeichneVorbereitung());
  $("sp-suche").addEventListener("input", () => zeichneSpiel());
  $("neu-jahr").addEventListener("input", (e) => { e.target.dataset.auto = "0"; });

  // ------------------------------------------------------------------ Start
  starteMitApi(async function (echt) {
    demo = !echt;
    const r = await call("zustand");
    if (!r || !Z) {
      document.body.insertAdjacentHTML("beforeend", '<p style="padding:2rem">Die Anwendung konnte den Zustand nicht laden.</p>');
      return;
    }
    await bilderPruefen();
    ansicht = startAnsicht();
    alleZeichnen();
  }, true);
})();
