// Beamer-Fenster: bekommt den Zustand per window.render(z) von Python (oder aus mock.js im Demo-Modus).
(function () {
  const $ = (id) => document.getElementById(id);
  const ANSICHTEN = ["warten", "spiel", "sonderrunde", "ende", "statistik"];
  let aktuelleAnsicht = null;
  let letzteEreignisId = 0;
  let overlayWarteschlange = [];
  let overlayLaeuft = false;

  function setze(el, html) {
    if (el._h !== html) { el.innerHTML = html; el._h = html; }
  }

  function zeigeAnsicht(name) {
    if (name === aktuelleAnsicht) return;
    ANSICHTEN.forEach((n) => { $("ansicht-" + n).hidden = n !== name; });
    aktuelleAnsicht = name;
  }

  function waehleAnsicht(z) {
    if (!z || !z.spiel) return "warten";
    if (z.sonderrunde) return "sonderrunde";
    if (z.beamer_ansicht === "statistik") return "statistik";
    if (z.spiel.beendet) return "ende";
    return "spiel";
  }

  // ------------------------------------------------------------------ Kacheln (an Ort und Stelle aktualisiert)
  function kachelnAktualisieren(preise) {
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
        el.innerHTML = '<span class="ik"></span><div class="name"></div><div class="rest"></div><div class="balken"><i></i></div>';
        box.appendChild(el);
      }
      if (box.children[i] !== el) box.insertBefore(el, box.children[i] || null);
      const iconHtml = icon(p.icon);
      if (el._icon !== iconHtml) { el.querySelector(".ik").innerHTML = iconHtml; el._icon = iconHtml; }
      const nm = el.querySelector(".name");
      nm.textContent = p.name;
      nm.classList.toggle("lang", p.name.length > 14);
      el.querySelector(".rest").innerHTML = p.rest > 0 ? "<b>" + p.rest + "</b> von " + p.menge : "vergeben";
      el.querySelector(".balken i").style.width = (p.menge ? (100 * p.rest) / p.menge : 0) + "%";
      el.classList.toggle("leer", p.rest === 0);
      el.classList.toggle("wenig", p.rest > 0 && p.rest <= Math.max(1, Math.round(p.menge * 0.2)));
    });
  }

  // ------------------------------------------------------------------ Zeichnen
  function zeichne(z) {
    const ansicht = waehleAnsicht(z);
    zeigeAnsicht(ansicht);
    $("jahr").textContent = z && z.jahr ? z.jahr : "";
    if (ansicht === "warten") { setze($("fortschritt"), ""); return; }
    const s = z.spiel;

    // Fortschritt
    let f;
    if (s.beendet) f = "Beendet nach <b>" + s.runden_gespielt + " Runden</b>";
    else {
      f = "Runde <b>" + s.runde + "</b> · noch <b>" + s.rest_gesamt + " " + (s.rest_gesamt === 1 ? "Preis" : "Preise") + "</b>";
      f += s.phase_nr ? " · Phase <b>" + s.phase_nr + "/" + s.phasen_anzahl + "</b>" : (s.spezialpreise_offen.length ? " · Sonderrunde folgt" : "");
    }
    setze($("fortschritt"), f);

    if (ansicht === "spiel") zeichneSpiel(z);
    else if (ansicht === "sonderrunde") {
      setze($("sonder-icon"), icon(z.sonderrunde.icon));
      $("sonder-name").textContent = z.sonderrunde.name;
    } else if (ansicht === "ende") zeichneEnde(z);
    else if (ansicht === "statistik") zeichneStatistik(z);
  }

  function zeichneSpiel(z) {
    const s = z.spiel;
    const aktiv = s.phasen.find((p) => p.aktiv);
    // Kopf der aktiven Phase
    if (aktiv) {
      setze($("phasenkopf"), "<h2>" + esc(aktiv.name) + "</h2><span>Phase " + s.phase_nr + " von " + s.phasen_anzahl + "</span>");
      const preise = s.preise.filter((p) => p.phase_id === aktiv.id && !p.spezial);
      kachelnAktualisieren(preise);
    } else {
      setze($("phasenkopf"), "<h2>" + (s.spezialpreise_offen.length ? "Alle Phasen beendet" : "Keine Preise") + "</h2>");
      kachelnAktualisieren([]);
    }
    // Spezialpreise
    setze($("spezial"), s.spezialpreise_offen.map((p) =>
      '<div class="spezial">' + icon(p.icon) + "<div><div class='hinweis'>Sonderrunde folgt</div><div class='name'>" + esc(p.name) +
      (p.rest > 1 ? " ×" + p.rest : "") + "</div></div></div>").join(""));
    // Kommende Phasen
    const kommend = s.phasen.filter((p) => !p.aktiv && !p.abgeschlossen && p.gesamt > 0 && (!aktiv || p.reihenfolge > aktiv.reihenfolge));
    setze($("kommend"), kommend.length ? "<span>Danach:</span>" + kommend.map((p) => {
      const ics = [...new Set(s.preise.filter((x) => x.phase_id === p.id).map((x) => x.icon))].slice(0, 4).map(icon).join("");
      return '<span class="chip">' + ics + "<span><b>" + esc(p.name) + "</b> · " + p.rest + " Preise</span></span>";
    }).join("") : "");

    // Letzter Gewinner
    const l = s.letzter_sieg;
    setze($("letzter"), "<p class='etikett'>Letzter Gewinner</p>" + (l
      ? "<div class='wer'>" + esc(l.name) + "</div><div class='was" + (l.sonderrunde ? " sonder" : "") + "'>" + icon(l.icon) + "<span>" + esc(l.preis_name) + "</span></div><div class='runde'>Runde " + l.nr + "</div>"
      : "<div class='keiner'>Noch kein Gewinner</div>"));

    // Top 10
    setze($("top10"), "<h2>Top 10 des Abends</h2>" + (s.top10.length
      ? "<ol>" + s.top10.map((t, i) => "<li><span class='platz'>" + (i + 1) + ".</span><span class='name'>" + esc(t.name) + "</span><span class='anz'>" + t.siege + "</span></li>").join("") + "</ol>"
      : "<div class='leer'>Noch keine Siege.</div>"));
  }

  function zeichneEnde(z) {
    const s = z.spiel;
    setze($("ende-titel"), "Paschen " + z.jahr + " beendet");
    const teiln = s.anwesende.length;
    setze($("ende-info"), s.runden_gespielt + " Runden · " + teiln + " Teilnehmer");
    const rows = s.top10.map((t, i) => "<div class='zeile" + (i === 0 ? " erster" : "") + "'><span class='platz'>" + (i + 1) + ".</span><span class='name'>" + esc(t.name) + "</span><span class='anz'>" + t.siege + "</span></div>");
    const half = Math.ceil(rows.length / 2);
    setze($("ende-top"), "<div>" + rows.slice(0, half).join("") + "</div><div>" + rows.slice(half).join("") + "</div>");
  }

  function zeichneStatistik(z) {
    const st = z.statistik;
    setze($("stat-liste"), bestenlisteHtml(st, 15));
    setze($("stat-jahre"), jahresvergleichHtml(st));
    const r = rekordeHtml(st);
    setze($("rek-abend"), r.abend);
    setze($("rek-teilnahmen"), r.teilnahmen);
    setze($("rek-pech"), r.pechvogel);
  }

  // ------------------------------------------------------------------ Ereignisse (Overlay)
  function overlayKarte(e) {
    if (e.typ === "sieg") {
      return { html: "<div class='klein'>Runde " + e.nr + "</div><div class='wer'>" + esc(e.name) + "</div><div class='was" + (e.sonderrunde ? " sonder" : "") + "'>" +
        icon(e.icon) + "<span>" + (e.sonderrunde ? "gewinnt " : "wählt ") + esc(e.preis_name) + "</span></div>", ms: 4000, klasse: "" };
    }
    if (e.typ === "phasenwechsel") {
      const weiter = e.nach_name ? "weiter mit <b>" + esc(e.nach_name) + "</b>" : "Sonderrunde folgt";
      return { html: "<div class='klein'>Phasenwechsel</div><div class='wer'>" + (e.von_name ? esc(e.von_name) + " beendet" : "Phase beendet") + "</div><div class='weiter'>" + weiter + "</div>", ms: 5000, klasse: "wechsel" };
    }
    return null;
  }

  function einreihen(e) {
    const k = overlayKarte(e);
    if (k) overlayWarteschlange.push(k);
    if (e.folge) einreihen(e.folge);
  }

  function naechstesOverlay() {
    const k = overlayWarteschlange.shift();
    if (!k) { overlayLaeuft = false; $("overlay").hidden = true; return; }
    overlayLaeuft = true;
    const karte = $("overlay-karte");
    karte.className = "overlay-karte " + k.klasse;
    karte.innerHTML = k.html;
    // Animation neu starten
    karte.style.animation = "none"; void karte.offsetWidth; karte.style.animation = "";
    $("overlay").hidden = false;
    setTimeout(naechstesOverlay, k.ms);
  }

  function ereignis(e) {
    if (!e || (e.id && e.id <= letzteEreignisId)) return;
    if (e.id) letzteEreignisId = e.id;
    einreihen(e);
    if (!overlayLaeuft) naechstesOverlay();
  }

  // ------------------------------------------------------------------ Einstieg
  window.render = function (z) {
    try { zeichne(z); } catch (err) { console.error(err); }
    if (z && z.ereignis) ereignis(z.ereignis);
  };

  zeigeAnsicht("warten");

  starteMitApi(function (echt) {
    if (echt) return; // (nie im Beamer-Fenster) Python schickt den Zustand per window.render
    const param = new URLSearchParams(location.search).get("ansicht");
    const api = window.MockApi;
    if (param) {
      window.render(api._vorfuehren(param));
    } else {
      api.zustand().then((z) => window.render(z));
      if (api._kanal) api._kanal.onmessage = (m) => window.render(m.data);
    }
  }, false);
})();
