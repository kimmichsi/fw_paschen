// Beamer-Fenster: bekommt den Zustand per window.render(z) von Python (oder aus mock.js im Demo-Modus).
(function () {
  const $ = (id) => document.getElementById(id);
  const ANSICHTEN = ["warten", "spiel", "sonderrunde", "ende", "statistik", "regeln"];
  let aktuelleAnsicht = null;
  let letzteEreignisId = 0;
  let overlayWarteschlange = [];
  let overlayLaeuft = false;
  let overlayAusTimer = null;
  let bilderVersion = 0;   // zaehlt hoch, wenn neue Bilder gesetzt wurden (Kachel-Cache)
  let letztesZ = null;
  const weniger = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  // Gestaffelter Ansichtswechsel: jede Ansicht bekommt ihre Elemente als .stufe mit Index --i (CSS: 40 ms Abstand)
  const STUFEN = {
    warten: "> *", sonderrunde: "> *", ende: "> *",
    spiel: ".links > *, .rechts > *", statistik: ".liste, .stat-rechts > *",
  };
  function stufenVergeben() {
    Object.keys(STUFEN).forEach((n) => {
      const wurzel = $("ansicht-" + n);
      const ziele = STUFEN[n] === "> *" ? Array.from(wurzel.children) : Array.from(wurzel.querySelectorAll(STUFEN[n]));
      ziele.forEach((el, i) => { el.classList.add("stufe"); el.style.setProperty("--i", String(i)); });
    });
  }

  // Restmenge wechselt: kurzer Zahlen-Tick (Einblenden + kleiner Versatz), nur wenn sich die Zahl aendert
  function zahlTick(el) {
    if (!el || !el.animate) return;
    const von = weniger() ? { opacity: 0 } : { opacity: 0, transform: "translateY(.35rem)" };
    // Dauer und Kurve aus den Variablen in basis.css (--dauer-tick, --ease-out)
    const dauer = dauerMs("--dauer-tick", 220);
    const kurve = getComputedStyle(document.documentElement).getPropertyValue("--ease-out").trim() || "ease-out";
    // Hinweis: Laeuft gerade ein Overlay, ist der Tick dahinter unsichtbar. Das ist gewollt: Das Overlay ist der Moment, die Zahl ist danach schon ruhig.
    el.animate([von, { opacity: 1, transform: "none" }], { duration: dauer, easing: kurve });
  }

  function setze(el, html) {
    if (el._h !== html) { el.innerHTML = html; el._h = html; }
  }

  function zeigeAnsicht(name) {
    if (name === aktuelleAnsicht) return;
    if (aktuelleAnsicht === "regeln") rgStop();
    ANSICHTEN.forEach((n) => { $("ansicht-" + n).hidden = n !== name; });
    aktuelleAnsicht = name;
  }

  // Eine laufende Sonderrunde hat Vorrang vor Regeln und Statistik
  function waehleAnsicht(z) {
    if (!z) return "warten";
    if (z.spiel && z.sonderrunde) return "sonderrunde";
    if (z.beamer_ansicht === "regeln") return "regeln";
    if (!z.spiel) return "warten";
    if (z.beamer_ansicht === "statistik") return "statistik";
    if (z.spiel.beendet) return "ende";
    return "spiel";
  }

  // ------------------------------------------------------------------ Kacheln (an Ort und Stelle aktualisiert)
  function kachelnAktualisieren(preise, phasen) {
    const box = $("kacheln");
    const ids = preise.map((p) => p.id);
    box.classList.toggle("viele", preise.length >= 10);
    Array.from(box.children).forEach((c) => { if (!ids.includes(c.dataset.id)) c.remove(); });
    preise.forEach((p, i) => {
      let el = box.querySelector('[data-id="' + p.id + '"]');
      if (!el) {
        el = document.createElement("div");
        el.className = "kachel";
        el.dataset.id = p.id;
        el.innerHTML = '<span class="ik"></span><div class="name"></div><div class="rest"></div><div class="herkunft"></div><div class="balken"><i></i></div>';
        box.appendChild(el);
      }
      if (box.children[i] !== el) box.insertBefore(el, box.children[i] || null);
      const ikKey = (p.bild || "") + "|" + bilderVersion + "|" + p.icon;
      if (el._icon !== ikKey) {
        const ik = el.querySelector(".ik");
        ik.innerHTML = bildIcon(p.bild, p.icon);
        ik.classList.toggle("mit-bild", !!(p.bild && BILDER[p.bild]));
        el._icon = ikKey;
      }
      const nm = el.querySelector(".name");
      nm.textContent = p.name;
      // Groesse nach Laenge des Namens und des laengsten Wortes (ein langes Wort darf nie mitten im Wort brechen)
      const wort = Math.max(...p.name.split(/\s+/).map((w) => w.length));
      nm.classList.toggle("lang", p.name.length > 14 || wort > 9);
      nm.classList.toggle("sehr-lang", p.name.length > 22 || wort > 12);
      const restHtml = p.rest > 0 ? "<b>" + zahl(p.rest) + "</b> von " + zahl(p.menge) : "Vergeben";
      if (el._rest !== restHtml) {
        const war = el._rest !== undefined;
        const re = el.querySelector(".rest");
        re.innerHTML = restHtml;
        el._rest = restHtml;
        if (war) zahlTick(re.querySelector("b") || re);
      }
      // Uebertragene Preise stehen in der letzten Phase normal da, nur mit einem ruhigen Vermerk
      const von = p.uebertragen ? (phasen || []).findIndex((ph) => ph.id === p.phase_id) + 1 : 0;
      el.classList.toggle("uebertragen", von > 0);
      setze(el.querySelector(".herkunft"), von > 0 ? "aus Phase " + von : "");
      el.querySelector(".balken i").style.transform = "scaleX(" + (p.menge ? Math.max(0, Math.min(1, p.rest / p.menge)) : 0) + ")";
      el.classList.toggle("leer", p.rest === 0);
      el.classList.toggle("wenig", p.rest > 0 && p.rest <= Math.max(1, Math.round(p.menge * 0.2)));
    });
  }

  // ------------------------------------------------------------------ Zeichnen
  function zeichne(z) {
    // Design: "hell" (Standard) oder "dunkel"
    const design = z && z.beamer_design === "dunkel" ? "dunkel" : "hell";
    if (document.body.dataset.design !== design) document.body.dataset.design = design;
    const ansicht = waehleAnsicht(z);
    zeigeAnsicht(ansicht);
    $("jahr").textContent = z && z.jahr ? z.jahr : "";
    demoBand(z);
    if (ansicht === "regeln") { setze($("fortschritt"), ""); zeichneRegeln(z); return; }
    if (ansicht === "warten") { setze($("fortschritt"), ""); return; }
    const s = z.spiel;

    // Fortschritt
    let f;
    if (s.beendet) f = "Beendet nach <b>" + anzahl(s.runden_gespielt, "Runde", "Runden") + "</b>";
    else {
      f = "Runde <b>" + zahl(s.runde) + "</b> · noch <b>" + anzahl(s.rest_gesamt, "Preis", "Preise") + "</b>";
      f += s.phase_nr ? " · Phase <b>" + s.phase_nr + "/" + s.phasen_anzahl + "</b>" : (s.spezialpreise_offen.length ? " · Sonderrunde folgt" : "");
    }
    setze($("fortschritt"), f);

    if (ansicht === "spiel") zeichneSpiel(z);
    else if (ansicht === "sonderrunde") {
      setze($("sonder-icon"), bildIcon(z.sonderrunde.bild, z.sonderrunde.icon));
      $("sonder-name").textContent = z.sonderrunde.name;
      $("sonder-name").className = laenge(z.sonderrunde.name).trim();
    } else if (ansicht === "ende") zeichneEnde(z);
    else if (ansicht === "statistik") zeichneStatistik(z);
  }

  // Runden je Tisch der aktiven Phase (nur bei mehr als 1 Tisch). Kein Wuerfelauge: alle Tische spielen gleichzeitig,
  // "aktiv" ist hier die Phase (traegt das Auge im Phasenkopf); ein Auge je Tisch waere 4 bis 12 gleichzeitige Markierungen.
  function tischeHtml(s, aktiv) {
    const T = s.tische || 1;
    if (T < 2) return "";
    const stand = s.tisch_stand || null;
    const eins = (t) => "<div class='tische-eins'><span class='etikett'>Runden je Tisch</span><span class='tische-frei'>" + t + "</span></div>";
    if (s.tisch_frei) return eins("Alle Kontingente gespielt · Rest frei ausgespielt");
    if (!stand || !stand.length) return aktiv.letzte && s.letzte_phase_modus === "frei" ? eins("Frei – wer zuerst kommt") : "";
    // Bis 6 Tische: "Tisch 3" und "noch 5"; ab 7 kompakt in EINER Zeile: "T3" und die Zahl (fertig = Haken), damit bis 12 Tische alle Kacheln sichtbar bleiben
    const dicht = stand.length > 6;
    const zellen = stand.map((e) => "<div class='tisch" + (e.fertig ? " fertig" : "") + "'><span class='t-name'>" + (dicht ? "T" : "Tisch ") + e.tisch + "</span>" +
      (e.fertig ? "<span class='t-wert'>" + uiIcon("haken") + (dicht ? "" : "fertig") + "</span>" : "<span class='t-wert'>" + (dicht ? "<b>" + zahl(e.noch) + "</b>" : "noch <b>" + zahl(e.noch) + "</b>") + "</span>") + "</div>");
    return "<div class='tische-raster" + (dicht ? " dicht" : "") + "' style='--sp:" + (zellen.length + 1) + ";--n:" + zellen.length + "'><span class='etikett'>Runden je Tisch</span>" + zellen.join("") + "</div>";
  }

  function zeichneSpiel(z) {
    const s = z.spiel;
    const aktiv = s.phasen.find((p) => p.aktiv);
    // Kopf der aktiven Phase
    if (aktiv) {
      setze($("phasenkopf"), "<span class='aug' aria-hidden='true'></span><h2" + (aktiv.name.length > 34 ? " class='lang'" : "") + ">" + esc(aktiv.name) + "</h2><span>Phase " + s.phase_nr + " von " + s.phasen_anzahl + "</span>");
      const preise = s.preise.filter((p) => !p.spezial && (p.phase_id === aktiv.id || (aktiv.letzte && p.uebertragen)));
      kachelnAktualisieren(preise, s.phasen);
    } else {
      setze($("phasenkopf"), s.spezialpreise_offen.length ? "<h2>Alle Phasen beendet</h2>"
        : s.preise.length ? "<h2>Alle Preise sind vergeben</h2>"
        : "<h2>Noch keine Preise angelegt</h2>");
      kachelnAktualisieren([], s.phasen);
      if (!s.preise.length && !$("kacheln").querySelector(".leer-text")) {
        const h = document.createElement("p");
        h.className = "leer-text";
        h.dataset.id = "__leer";
        h.textContent = "Die Preise legt die Spielleitung in der Vorbereitung an.";
        $("kacheln").appendChild(h);
      }
    }
    setze($("tische"), aktiv ? tischeHtml(s, aktiv) : "");
    // Spezialpreise
    setze($("spezial"), s.spezialpreise_offen.map((p) =>
      '<div class="spezial">' + bildIcon(p.bild, p.icon) + "<div><div class='hinweis'>Sonderrunde folgt</div><div class='name'>" + esc(p.name) +
      (p.rest > 1 ? " ×" + p.rest : "") + "</div></div></div>").join(""));
    // Kommende Phasen
    const kommend = s.phasen.filter((p) => !p.aktiv && !p.abgeschlossen && p.gesamt > 0 && (!aktiv || p.reihenfolge > aktiv.reihenfolge));
    setze($("kommend"), kommend.length ? "<span>Danach:</span>" + kommend.map((p) => {
      const ics = [...new Set(s.preise.filter((x) => x.phase_id === p.id).map((x) => x.icon))].slice(0, 4).map(icon).join("");
      return '<span class="chip">' + ics + "<span><b>" + esc(p.name) + "</b> · " + anzahl(p.rest, "Preis", "Preise") + "</span></span>";
    }).join("") : "");

    // Letzter Gewinner
    const l = s.letzter_sieg;
    setze($("letzter"), "<p class='etikett'>Letzter Gewinner</p>" + (l
      ? kurzHtml(l.name, "wer drei" + (l.name.length > 24 ? " lang" : "")) + "<div class='was" + (l.sonderrunde ? " sonder" : "") + "'>" + bildIcon(l.bild, l.icon) + "<span>" + esc(l.preis_name) + "</span></div><div class='runde'>Runde " + zahl(l.nr) + (l.tisch ? " · Tisch " + l.tisch : "") + "</div>"
      : "<div class='keiner'>Noch kein Gewinner</div>"));

    // Top 10
    setze($("top10"), "<h2>Top 10 des Nachmittags</h2>" + (s.top10.length
      ? "<ol>" + s.top10.map((t, i) => "<li><span class='platz'>" + (i + 1) + ".</span>" + kurzHtml(t.name, "name eine") + "<span class='anz'>" + zahl(t.siege) + "</span></li>").join("") + "</ol>"
      : "<div class='leer'>Noch keine Siege.</div>"));
  }

  function zeichneEnde(z) {
    const s = z.spiel;
    setze($("ende-titel"), "Paschen " + z.jahr + " beendet");
    const teiln = s.anwesende.length;
    setze($("ende-info"), anzahl(s.runden_gespielt, "Runde", "Runden") + " · " + anzahl(teiln, "Teilnehmer", "Teilnehmer"));
    const rows = s.top10.map((t, i) => "<div class='zeile" + (i === 0 ? " erster" : "") + "'><span class='platz'>" + (i + 1) + ".</span>" + kurzHtml(t.name, "name" + (t.name.length > 24 ? " lang" : "")) + "<span class='anz'>" + zahl(t.siege) + "</span></div>");
    const half = Math.ceil(rows.length / 2);
    setze($("ende-top"), rows.length
      ? "<div>" + rows.slice(0, half).join("") + "</div><div>" + rows.slice(half).join("") + "</div>"
      : "<p class='leer-text'>Es wurden keine Siege eingetragen.</p>");
  }

  function zeichneStatistik(z) {
    const st = z.statistik;
    $("ansicht-statistik").classList.toggle("eng", (st.jahre || []).length > 8); // viele Jahre: enger setzen
    setze($("stat-liste"), bestenlisteHtml(st, 15));
    setze($("stat-jahre"), jahresvergleichHtml(st));
    const r = rekordeHtml(st);
    setze($("rek-nachmittag"), r.nachmittag);
    setze($("rek-teilnahmen"), r.teilnahmen);
    setze($("rek-pech"), r.pechvogel);
  }

  // ------------------------------------------------------------------ Ereignisse (Overlay)
  // Groessenklasse nach Textlaenge: lange Namen werden kleiner gesetzt statt abgeschnitten
  const laenge = (t) => (t.length > 40 ? " sehr-lang" : t.length > 22 ? " lang" : "");
  function overlayKarte(e) {
    if (e.typ === "sieg") {
      // Drei Einsen schlagen alles: drei rote Wuerfel als Moment des Siegs
      return { html: wuerfelReihe([1, 1, 1]) + "<div class='klein'>" + (e.nr ? "Runde " + zahl(e.nr) : "Sieg") + (e.tisch ? " · Tisch " + e.tisch : "") + "</div><div class='wer" + laenge(e.name) + "'>" + esc(e.name) + "</div><div class='was" + (e.sonderrunde ? " sonder" : "") + (e.preis_name.length > 28 ? " lang" : "") + "'>" +
        bildIcon(e.bild, e.icon) + "<span>" + (e.sonderrunde ? "gewinnt " : "wählt ") + esc(e.preis_name) + "</span></div>", ms: 4000, klasse: "" };
    }
    if (e.typ === "phasenwechsel") {
      const weiter = e.nach_name ? "weiter mit <b>" + esc(e.nach_name) + "</b>" : "Sonderrunde folgt";
      return { html: "<div class='klein'>Phasenwechsel</div><div class='wer" + laenge(e.von_name || "") + "'>" + (e.von_name ? esc(e.von_name) + " beendet" : "Phase beendet") + "</div><div class='weiter" + ((e.nach_name || "").length > 28 ? " lang" : "") + "'>" + weiter + "</div>" +
        (e.uebertrag > 0 ? "<div class='uebertrag'>" + zahl(e.uebertrag) + " " + plural(e.uebertrag, "Preis wandert", "Preise wandern") + " in die letzte Phase</div>" : ""), ms: 5000, klasse: "wechsel" };
    }
    return null;
  }

  function einreihen(e) {
    const k = overlayKarte(e);
    if (k) overlayWarteschlange.push(k);
    if (e.folge) einreihen(e.folge);
  }

  // Overlay: ein (Karte scale .95 -> 1, ease-out), aus 180 ms (schneller als ein). Folgt direkt ein weiteres, wird nur getauscht.
  function naechstesOverlay() {
    const k = overlayWarteschlange.shift();
    const ov = $("overlay");
    clearTimeout(overlayAusTimer);
    if (!k) {
      overlayLaeuft = false;
      ov.classList.remove("an");
      overlayAusTimer = setTimeout(() => { if (!overlayLaeuft) ov.hidden = true; }, dauerMs("--dauer-overlay-aus", 140) + 40);
      return;
    }
    overlayLaeuft = true;
    const karte = $("overlay-karte");
    const sichtbar = !ov.hidden && ov.classList.contains("an");
    ov.className = "overlay " + k.klasse + (sichtbar ? " an" : "");
    karte.className = "overlay-karte " + k.klasse;
    karte.innerHTML = k.html;
    if (!sichtbar) {
      ov.hidden = false;
      void ov.offsetWidth; // Ausgangszustand zeichnen, dann einblenden
      ov.classList.add("an");
    } else {
      // Inhalt getauscht: Karten-Animation neu starten
      karte.style.animation = "none"; void karte.offsetWidth; karte.style.animation = "";
    }
    setTimeout(naechstesOverlay, k.ms);
  }

  function ereignis(e) {
    if (!e || (e.id && e.id <= letzteEreignisId)) return;
    if (e.id) letzteEreignisId = e.id;
    einreihen(e);
    if (!overlayLaeuft) naechstesOverlay();
  }

  // ------------------------------------------------------------------ DEMO-Band
  function demoBand(z) {
    const an = !!(z && z.demo && z.demo.aktiv);
    const b = $("demo-band");
    document.body.classList.toggle("ist-demo", an);
    b.hidden = !an;
    if (an) setze(b, "<b>Demo</b><span>Testdaten (" + (z.demo.art === "kopie" ? "Kopie" : "erfunden") + "), keine echten Spieldaten</span>");
  }

  // ------------------------------------------------------------------ Regel-Show
  // Der Beamer steuert den Folien-Timer selbst. Neues regel_nonce = auf regel_index springen und Timer neu starten.
  const rg = { nonce: undefined, index: 0, sig: null, timer: null, intervall: 12, n: 0, nPlan: -1, aktiv: false, liste: [] };
  function rgStop() { clearTimeout(rg.timer); rg.timer = null; rg.aktiv = false; rg.nPlan = -1; }
  function rgPlane() {
    clearTimeout(rg.timer); rg.timer = null; rg.nPlan = rg.n;
    if (rg.n > 1) rg.timer = setTimeout(() => { rg.index = (rg.index + 1) % rg.n; rgZeige(); rgPlane(); }, rg.intervall * 1000);
  }
  function rgPunkte() {
    setze($("regel-punkte"), rg.n > 1 ? rg.liste.map((_, i) => '<span class="punkt' + (i === rg.index ? " an" : "") + '"></span>').join("") : "");
  }
  function rgZeige() {
    const box = $("regel-buehne");
    const r = rg.liste[rg.index];
    rg.sig = r ? JSON.stringify(r) : "leer";
    // Alte Folie blendet aus (--dauer-folie-aus) und wird danach entfernt: per animationend, mit Zeitpolster als Absicherung
    Array.from(box.children).forEach((c) => {
      if (c.classList.contains("geht")) return;
      c.classList.add("geht");
      const weg = () => c.remove();
      c.addEventListener("animationend", (e) => { if (e.target === c) weg(); });
      setTimeout(weg, dauerMs("--dauer-folie-aus", 220) + 100);
    });
    const el = document.createElement("div");
    el.className = "folie";
    if (!r) {
      el.innerHTML = '<div class="regel-leer"><h1>Noch keine Regeln</h1><p>Die Spielleitung kann die Regel-Folien im Bedienfenster unter „Regeln“ anlegen.</p></div>';
    } else {
      const t = r.text || "";
      el.innerHTML = '<h1 class="regel-titel' + (r.titel.length > 40 ? " lang" : "") + '">' + esc(r.titel) + "</h1>" +
        (t ? '<p class="regel-text' + (t.length > 260 ? " lang" : "") + '">' + esc(t) + "</p>" : "") +
        (r.wuerfel ? wuerfelBlock(r.wuerfel, false) : "");
    }
    box.appendChild(el);
    rgPunkte();
  }
  function zeichneRegeln(z) {
    const neuAktiv = !rg.aktiv;
    rg.aktiv = true;
    rg.liste = z.regeln || [];
    rg.n = rg.liste.length;
    const neuNonce = z.regel_nonce !== rg.nonce;
    const iv = Math.max(5, Math.min(120, z.regeln_intervall_s || 12));
    const ivNeu = iv !== rg.intervall;
    rg.intervall = iv;
    if (neuNonce) { rg.nonce = z.regel_nonce; rg.index = z.regel_index || 0; }
    if (rg.index >= rg.n) rg.index = 0;
    const sig = rg.n ? JSON.stringify(rg.liste[rg.index]) : "leer";
    if (neuNonce || neuAktiv || sig !== rg.sig) rgZeige(); else rgPunkte();
    if (neuNonce || neuAktiv || ivNeu || rg.nPlan !== rg.n) rgPlane();
  }

  // ------------------------------------------------------------------ Bilder
  window.bilderSetzen = function (map) {
    window.BILDER = map && typeof map === "object" ? map : {};
    bilderVersion++;
    if (letztesZ) window.render(letztesZ);
  };

  // ------------------------------------------------------------------ Einstieg
  window.render = function (z) {
    letztesZ = z;
    try { zeichne(z); } catch (err) { console.error(err); }
    if (z && z.ereignis) ereignis(z.ereignis);
  };

  stufenVergeben();
  zeigeAnsicht("warten");

  starteMitApi(function (echt) {
    if (echt) return; // (nie im Beamer-Fenster) Python schickt den Zustand per window.render
    const param = new URLSearchParams(location.search).get("ansicht");
    const api = window.MockApi;
    if (param) {
      window.BILDER = api._bilder();
      window.render(api._vorfuehren(param));
    } else {
      window.BILDER = api._bilder();
      api.zustand().then((z) => window.render(z));
      if (api._kanal) api._kanal.onmessage = (m) => {
        const d = m.data;
        if (d && d._bilder) { window.BILDER = d._bilder; bilderVersion++; }
        window.render(d);
      };
    }
  }, false);
})();
