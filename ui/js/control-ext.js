// Bedienfenster, Erweiterungen: Jahres-Kontextmenue, Demo-Modus, Regel-Show-Editor, Daten-Bereich (Siege, Preisnamen, Personen).
// Wird VOR control.js geladen und legt window.CTRL an; control.js ergaenzt call/toast/Dialoge zur Laufzeit.
(function () {
  const $ = (id) => document.getElementById(id);
  const CTRL = (window.CTRL = { AKTIONEN: {}, zeichner: {} });
  const A = CTRL.AKTIONEN;
  const Zn = () => CTRL.getZ();
  const norm = (s) => String(s || "").toLowerCase();

  // ------------------------------------------------------------------ Bild waehlen (Datei -> verkleinerte Data-URL)
  CTRL.bildWaehlen = function () {
    return new Promise((res) => {
      const inp = document.createElement("input");
      inp.type = "file";
      inp.accept = "image/jpeg,image/png";
      inp.addEventListener("change", async () => {
        const f = inp.files && inp.files[0];
        if (!f) { res(null); return; }
        try { res(await bildVerkleinern(f)); } catch (e) { CTRL.toast(e.message || "Das Bild konnte nicht gelesen werden.", true); res(null); }
      });
      inp.addEventListener("cancel", () => res(null));
      inp.click();
    });
  };

  // ------------------------------------------------------------------ Jahres-Kontextmenue
  // Rechtsklick auf die Jahreskachel oder Klick auf "..." oeffnet ein kleines Menue (Spiel oeffnen / Loeschen).
  const kx = { offen: false, jahr: null, ausloeser: null, zuEl: null, zuZeit: 0 };
  function kontextSchliessen(fokusZurueck) {
    const m = $("kontext");
    if (!kx.offen) return;
    kx.offen = false;
    m.classList.remove("offen");
    m.hidden = true;
    if (kx.ausloeser) kx.ausloeser.setAttribute("aria-expanded", "false");
    if (fokusZurueck && kx.ausloeser && document.contains(kx.ausloeser)) kx.ausloeser.focus();
  }
  function kontextOeffnen(jahr, ausloeser, x, y, ecke, mitFokus) {
    const m = $("kontext");
    kontextSchliessen(false);
    kx.offen = true; kx.jahr = jahr; kx.ausloeser = ausloeser;
    ausloeser.setAttribute("aria-expanded", "true");
    m.innerHTML = '<div class="kontext-titel">Spiel ' + esc(jahr) + "</div>" +
      '<button role="menuitem" class="kontext-punkt" data-act="kontext-oeffnen">Spiel öffnen</button>' +
      '<button role="menuitem" class="kontext-punkt gefahr" data-act="kontext-loeschen">Löschen</button>';
    m.hidden = false;
    const b = m.offsetWidth, h = m.offsetHeight;
    let l = ecke === "rechts" ? x - b : x, t = y + 4;
    l = Math.max(8, Math.min(l, window.innerWidth - b - 8));
    if (t + h > window.innerHeight - 8) t = Math.max(8, y - h - 4);
    m.style.left = l + "px"; m.style.top = t + "px";
    m.style.transformOrigin = Math.round(x - l) + "px " + (t > y ? "0" : "100%"); // wächst vom Auslöser aus
    void m.offsetWidth;
    m.classList.add("offen");
    if (mitFokus) { const first = m.querySelector(".kontext-punkt"); if (first) first.focus(); }
  }
  document.addEventListener("contextmenu", (e) => {
    const w = e.target.closest && e.target.closest(".jahr-wrap");
    if (!w) { if (kx.offen) kontextSchliessen(false); return; }
    e.preventDefault();
    const tastatur = e.clientX === 0 && e.clientY === 0;
    const r = w.getBoundingClientRect();
    kontextOeffnen(+w.dataset.jahr, w.querySelector(".jahr-mehr"), tastatur ? r.left + 16 : e.clientX, tastatur ? r.top + r.height / 2 : e.clientY, "links", tastatur);
  });
  document.addEventListener("pointerdown", (e) => {
    if (!kx.offen) return;
    if ($("kontext").contains(e.target)) return;
    const t = e.target.closest && e.target.closest(".jahr-mehr");
    kontextSchliessen(false);
    if (t) { kx.zuEl = t; kx.zuZeit = Date.now(); } // gleicher Klick soll nicht gleich wieder oeffnen
  }, true);
  document.addEventListener("keydown", (e) => {
    if (!kx.offen) return;
    const m = $("kontext");
    const punkte = Array.from(m.querySelectorAll(".kontext-punkt"));
    const i = punkte.indexOf(document.activeElement);
    if (e.key === "Escape") { e.preventDefault(); kontextSchliessen(true); }
    else if (e.key === "ArrowDown") { e.preventDefault(); punkte[(i + 1) % punkte.length].focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); punkte[(i - 1 + punkte.length) % punkte.length].focus(); }
    else if (e.key === "Home") { e.preventDefault(); punkte[0].focus(); }
    else if (e.key === "End") { e.preventDefault(); punkte[punkte.length - 1].focus(); }
    else if (e.key === "Tab") kontextSchliessen(false);
  });
  window.addEventListener("resize", () => kontextSchliessen(false));
  window.addEventListener("blur", () => kontextSchliessen(false));

  A["jahr-menue"] = (el, e) => {
    if (kx.zuEl === el && Date.now() - kx.zuZeit < 500) return;
    const r = el.getBoundingClientRect();
    kontextOeffnen(+el.dataset.jahr, el, r.right, r.bottom, "rechts", e && e.detail === 0);
  };
  A["kontext-oeffnen"] = async () => {
    const j = kx.jahr;
    kontextSchliessen(false);
    const r = await CTRL.call("jahr_waehlen", j);
    if (r) CTRL.setAnsicht("vorbereitung");
  };
  A["kontext-loeschen"] = async () => {
    const j = kx.jahr;
    kontextSchliessen(false);
    const ja = await CTRL.bestaetigen("Spiel " + j + " löschen?", "Spiel " + j + " wirklich löschen? Eine Sicherung wird angelegt.", "Ja", "Nein");
    if (!ja) return;
    const r = await CTRL.call("spiel_loeschen", j);
    if (r) CTRL.toast("Spiel " + j + " gelöscht. Eine Sicherung wurde angelegt.");
  };

  // ------------------------------------------------------------------ Demo-Modus
  A["demo-dialog"] = () => {
    CTRL.openModal(
      "<h2>Demo-Modus starten</h2>" +
      "<p>Zum gefahrlosen Ausprobieren und Vorführen. Bedienfenster und Beamer zeigen deutlich „Demo“.</p>" +
      '<div class="wahl" role="radiogroup" aria-label="Art der Demo-Daten">' +
      '<label class="wahl-karte"><input type="radio" name="demo-art" value="erfunden" checked><span><b>Erfundene Daten</b><small>Neu erfundene Teilnehmer, Preise und Siege.</small></span></label>' +
      '<label class="wahl-karte"><input type="radio" name="demo-art" value="kopie"><span><b>Kopie meiner Daten</b><small>Eine Kopie deiner Spiele und Bilder zum Ausprobieren.</small></span></label></div>' +
      '<p class="demo-sicher"><b>Deine echten Daten bleiben unverändert.</b></p>' +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Demo starten</button></div>');
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const art = ($("modal-karte").querySelector("input[name=demo-art]:checked") || {}).value || "erfunden";
      const r = await CTRL.call("demo_starten", art);
      if (r) { $("modal-karte").onclick = null; CTRL.closeModal(); CTRL.setAnsicht(CTRL.startAnsicht()); CTRL.toast("Demo-Modus gestartet"); }
    };
  };
  A["demo-beenden"] = async () => {
    const ja = await CTRL.bestaetigen("Demo beenden?", "Du kehrst zu deinen echten Daten zurück.", "Demo beenden");
    if (!ja) return;
    const r = await CTRL.call("demo_beenden");
    if (r) { CTRL.setAnsicht(CTRL.startAnsicht()); CTRL.toast("Demo beendet. Das sind wieder deine echten Daten."); }
  };
  A["demo-zuruecksetzen"] = async () => {
    const ja = await CTRL.bestaetigen("Testdaten zurücksetzen?", "Alle Änderungen im Demo-Modus gehen verloren, die Testdaten beginnen von vorn. Deine echten Daten sind nicht betroffen.", "Zurücksetzen");
    if (!ja) return;
    const r = await CTRL.call("demo_zuruecksetzen");
    if (r) { CTRL.setAnsicht(CTRL.startAnsicht()); CTRL.toast("Testdaten zurückgesetzt"); }
  };

  // ------------------------------------------------------------------ Regel-Show
  CTRL.zeichner.regeln = function () {
    const Z = Zn();
    const L = Z.regeln || [];
    const idx = Math.min(Z.regel_index || 0, Math.max(0, L.length - 1));
    $("rg-liste").innerHTML = L.length ? L.map((r, i) =>
      '<div class="rg-zeile' + (i === idx ? " aktiv" : "") + '">' +
      '<button class="rg-titel" data-act="regel-waehlen" data-index="' + i + '" title="Diese Folie anzeigen"><span class="nr">' + (i + 1) + '.</span><span class="t">' + esc(r.titel) + "</span>" +
      (r.wuerfel ? '<span class="tag">Würfel</span>' : "") + "</button>" +
      '<button class="knopf klein symbol" data-act="regel-hoch" data-id="' + r.id + '"' + (i === 0 ? " disabled" : "") + ' title="Nach vorn" aria-label="Nach vorn">' + uiIcon("hoch") + "</button>" +
      '<button class="knopf klein symbol" data-act="regel-runter" data-id="' + r.id + '"' + (i === L.length - 1 ? " disabled" : "") + ' title="Nach hinten" aria-label="Nach hinten">' + uiIcon("runter") + "</button>" +
      '<button class="knopf klein" data-act="regel-bearbeiten" data-id="' + r.id + '">Bearbeiten</button>' +
      '<button class="knopf klein gefahr" data-act="regel-loeschen" data-id="' + r.id + '">Löschen</button></div>').join("")
      : '<p class="leer-text">Noch keine Folien. Lege die erste mit „Folie hinzufügen“ an.</p>';
    const inp = $("rg-intervall");
    if (document.activeElement !== inp) inp.value = Z.regeln_intervall_s || 12;
    const r = L[idx];
    $("rg-vorschau-nr").textContent = L.length ? "· Folie " + (idx + 1) + " von " + L.length : "";
    $("rg-vorschau").innerHTML = r
      ? '<div class="rg-folie"><h3>' + esc(r.titel) + "</h3>" + (r.text ? "<p>" + esc(r.text) + "</p>" : "") + (r.wuerfel ? wuerfelBlock(r.wuerfel, true) : "") + "</div>"
      : '<p class="leer-text">Keine Folie vorhanden. Auf dem Beamer erscheint ein freundlicher Hinweis.</p>';
  };
  $("rg-intervall").addEventListener("change", async (e) => {
    const r = await CTRL.call("regeln_intervall_setzen", parseInt(e.target.value, 10));
    if (!r) CTRL.alleZeichnen();
  });

  function regelDialog(r) {
    const neu = !r;
    const w = (r && r.wuerfel) || [4, 4, 4];
    const sel = (i) => '<select id="rd-w' + i + '" aria-label="Würfel ' + (i + 1) + '">' + [1, 2, 3, 4, 5, 6].map((n) => '<option value="' + n + '"' + (n === w[i] ? " selected" : "") + ">" + n + "</option>").join("") + "</select>";
    CTRL.openModal(
      "<h2>" + (neu ? "Folie hinzufügen" : "Folie bearbeiten") + "</h2>" +
      '<label class="feld"><span>Titel</span><input type="text" id="rd-titel" value="' + esc(r ? r.titel : "") + '" autocomplete="off"></label>' +
      '<label class="feld"><span>Text (optional)</span><textarea id="rd-text" rows="5">' + esc(r ? r.text : "") + "</textarea></label>" +
      '<label class="haken"><input type="checkbox" id="rd-w-an"' + (r && r.wuerfel ? " checked" : "") + "> Würfel-Animation zeigen (Becher und drei Würfel)</label>" +
      '<div class="feld-wuerfel"><span class="leise">Beispielwurf:</span>' + sel(0) + sel(1) + sel(2) + "</div>" +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Speichern</button></div>');
    const umschalten = () => { [0, 1, 2].forEach((i) => ($("rd-w" + i).disabled = !$("rd-w-an").checked)); };
    $("rd-w-an").addEventListener("change", umschalten); umschalten();
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const wuerfel = $("rd-w-an").checked ? [0, 1, 2].map((i) => parseInt($("rd-w" + i).value, 10)) : null;
      const res = neu ? await CTRL.call("regel_hinzufuegen", $("rd-titel").value, $("rd-text").value, wuerfel)
        : await CTRL.call("regel_bearbeiten", r.id, $("rd-titel").value, $("rd-text").value, wuerfel);
      if (res) { $("modal-karte").onclick = null; CTRL.closeModal(); }
    };
  }
  A["regel-neu"] = () => regelDialog(null);
  A["regel-bearbeiten"] = (el) => regelDialog((Zn().regeln || []).find((x) => x.id === el.dataset.id));
  A["regel-loeschen"] = async (el) => {
    const r = (Zn().regeln || []).find((x) => x.id === el.dataset.id);
    if (!r) return;
    const ja = await CTRL.bestaetigen("Folie löschen?", "Die Folie „" + r.titel + "“ wird entfernt. Das gilt für alle Jahre.", "Löschen");
    if (ja) await CTRL.call("regel_loeschen", r.id);
  };
  A["regel-hoch"] = (el) => CTRL.call("regel_verschieben", el.dataset.id, -1);
  A["regel-runter"] = (el) => CTRL.call("regel_verschieben", el.dataset.id, 1);
  A["regel-waehlen"] = (el) => CTRL.call("regel_folie", parseInt(el.dataset.index, 10));
  A["regel-vor"] = () => CTRL.call("regel_folie", "vor");
  A["regel-zurueck"] = () => CTRL.call("regel_folie", "zurueck");
  A["regeln-zeigen"] = async () => {
    if ((Zn().regeln || []).length) { const f = await CTRL.call("regel_folie", 0); if (!f) return; }
    const r = await CTRL.call("beamer_ansicht_setzen", "regeln");
    if (r) CTRL.toast("Der Beamer zeigt die Regeln");
  };
  A["spiel-starten"] = async () => {
    const r = await CTRL.call("beamer_ansicht_setzen", "spiel");
    if (r) CTRL.toast("Der Beamer zeigt wieder das Spiel");
  };

  // ------------------------------------------------------------------ Daten
  const da = { reiter: "siege", jahr: null, siege: null, zaehler: 0, aufgebaut: null, auswahl: new Set(), psuche: "", pnZaehler: 0 };

  // Personenauswahl mit Suchfeld (fuer Dialoge). Liefert HTML; bindPerson() verdrahtet es und gibt einen Getter zurueck.
  function personHtml(pfx) {
    return '<input type="search" id="' + pfx + '-such" class="suche" placeholder="Person suchen" autocomplete="off"><select id="' + pfx + '-sel" size="8" class="wahl-liste" aria-label="Person"></select>';
  }
  function bindPerson(pfx, ausschluss, vorwahl) {
    let gew = vorwahl || null;
    const fuelle = () => {
      const such = $(pfx + "-such").value;
      const pe = Zn().personen.filter((p) => p.id !== ausschluss && (p.id === gew || CTRL.passt(p.name, such)));
      $(pfx + "-sel").innerHTML = pe.map((p) => '<option value="' + esc(p.id) + '"' + (p.id === gew ? " selected" : "") + ">" + esc(p.name) + (p.ist_team ? " (Team)" : "") + "</option>").join("");
      if (gew) { const o = $(pfx + "-sel").querySelector("option[selected]"); if (o) o.scrollIntoView({ block: "nearest" }); }
    };
    $(pfx + "-such").addEventListener("input", fuelle);
    $(pfx + "-sel").addEventListener("change", (e) => { gew = e.target.value; });
    fuelle();
    return () => gew;
  }
  const zeitText = (t) => {
    if (!t) return "–";
    const d = new Date(t);
    return isNaN(d) ? "–" : d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  };

  CTRL.zeichner.daten = function () {
    const Z = Zn();
    document.querySelectorAll("#da-reiter [data-reiter]").forEach((b) => { b.classList.toggle("aktiv", b.dataset.reiter === da.reiter); b.setAttribute("aria-selected", b.dataset.reiter === da.reiter ? "true" : "false"); });
    const box = $("da-inhalt");
    if (da.aufgebaut !== da.reiter) {
      da.aufgebaut = da.reiter;
      if (da.reiter === "siege") {
        box.innerHTML = '<div class="da-kopf"><label class="feld-inline">Jahr <select id="da-jahr"></select></label><span class="klein leise" id="da-info"></span></div><div id="da-liste" class="scroll da-scroll"></div>';
        $("da-jahr").addEventListener("change", (e) => { da.jahr = parseInt(e.target.value, 10); da.siege = null; siegeLaden(); });
      } else if (da.reiter === "preisnamen") {
        box.innerHTML = '<div class="da-kopf"><button class="knopf primaer" data-act="pn-merge" id="pn-merge-knopf" disabled>Zusammenführen zu …</button><span class="klein leise">Namen links ankreuzen (mindestens zwei), dann zusammenführen. Umbenennen gilt für alle Jahre.</span></div><div id="da-liste" class="scroll da-scroll"></div>';
      } else {
        box.innerHTML = '<div class="da-kopf"><input type="search" id="da-psuche" class="suche" placeholder="Person suchen" autocomplete="off"><span class="klein leise" id="da-info"></span></div><div id="da-liste" class="scroll da-scroll"></div>';
        $("da-psuche").value = da.psuche;
        $("da-psuche").addEventListener("input", (e) => { da.psuche = e.target.value; personenListe(); });
      }
    }
    if (da.reiter === "siege") {
      if (!da.jahr || !Z.jahre.includes(da.jahr)) da.jahr = Z.jahr || (Z.jahre.length ? Z.jahre[Z.jahre.length - 1] : null);
      $("da-jahr").innerHTML = Z.jahre.map((j) => '<option value="' + j + '"' + (j === da.jahr ? " selected" : "") + ">" + j + "</option>").join("");
      siegeLaden();
    } else if (da.reiter === "preisnamen") preisnamenLaden();
    else personenListe();
  };

  A["daten-reiter"] = (el) => { da.reiter = el.dataset.reiter; CTRL.zeichner.daten(); };

  // ---- Siege
  async function siegeLaden() {
    if (!da.jahr) { $("da-liste").innerHTML = '<p class="leer-text">Noch kein Spiel vorhanden</p>'; $("da-info").textContent = ""; return; }
    const mein = ++da.zaehler;
    const r = await CTRL.lies("siege_liste", da.jahr);
    if (mein !== da.zaehler || da.reiter !== "siege") return;
    da.siege = Array.isArray(r) ? r : [];
    $("da-info").textContent = anzahl(da.siege.length, "Sieg", "Siege");
    $("da-liste").innerHTML = da.siege.length
      ? '<table class="daten da-tabelle"><thead><tr><th>Runde</th><th>Zeit</th><th>Gewinner</th><th>Preis</th><th>Tisch</th><th>Kennzeichen</th><th></th></tr></thead><tbody>' +
        da.siege.map((s) => "<tr><td>" + (s.nr ? zahl(s.nr) : "–") + "</td><td>" + zeitText(s.zeit) + '</td><td class="umbruch">' + kurzHtml(s.name) + '</td><td class="umbruch">' + kurzHtml(s.preis_name) + "</td><td>" + (s.tisch ? zahl(s.tisch) : "–") + "</td><td>" +
          (s.sonderrunde ? '<span class="tag">Sonderrunde</span> ' : "") + (s.importiert ? '<span class="tag">importiert</span>' : "") + '</td><td class="aktionen">' +
          '<button class="knopf klein" data-act="sieg-bearbeiten" data-id="' + esc(s.id) + '">Bearbeiten</button> <button class="knopf klein gefahr" data-act="sieg-loeschen" data-id="' + esc(s.id) + '">Löschen</button></td></tr>').join("") + "</tbody></table>"
      : '<p class="leer-text">In diesem Jahr gibt es noch keine Siege</p>';
  }
  // Bezeichnung eines Siegs: importierte Siege haben keine Rundennummer
  const siegBezeichnung = (x) => (x.nr ? "Runde " + zahl(x.nr) : "Importierter Sieg");
  async function siegDialog(sieg) {
    if (!sieg) return;
    // Preise und Bestand des gewählten Jahres kommen lesend aus der Api; das aktive Spiel bleibt unverändert
    const preise = await CTRL.lies("preise_liste", da.jahr);
    if (!Array.isArray(preise)) return;
    // Tischanzahl des Jahres: aus der Jahresliste, sonst aus dem aktiven Spiel, sonst 1 bis 12 anbieten
    const Zx = Zn();
    const jInfo = (Zx.jahre_info || []).find((j) => j.jahr === da.jahr);
    let tn = jInfo && jInfo.tische ? jInfo.tische : Zx.spiel && Zx.jahr === da.jahr && Zx.spiel.tische ? Zx.spiel.tische : 12;
    const tischWeg = !!sieg.tisch && sieg.tisch > tn;   // Tischanzahl wurde verringert: alten Tisch nicht vorwaehlen
    const tischFeld = tn > 1 || !!sieg.tisch;
    let tischOpt = '<option value="">–</option>';
    for (let n = 1; n <= tn; n++) tischOpt += '<option value="' + n + '"' + (sieg.tisch === n ? " selected" : "") + ">Tisch " + n + "</option>";
    CTRL.openModal(
      "<h2>Sieg bearbeiten</h2><p class=\"leise\">" + siegBezeichnung(sieg) + " im Spiel " + da.jahr + "</p>" +
      '<div class="feld"><span>Gewinner</span>' + personHtml("sd") + "</div>" +
      '<label class="feld"><span>Preis</span><select id="sd-preis">' + preise.map((p) => {
        const aktuell = p.id === sieg.preis_id;
        const frei = aktuell || p.rest > 0;
        return '<option value="' + esc(p.id) + '"' + (aktuell ? " selected" : "") + (frei ? "" : " disabled") + ">" + esc(p.name) + " (" + (aktuell ? "aktuell, " : "") + "noch " + zahl(p.rest) + " von " + zahl(p.menge) + " übrig)" + "</option>";
      }).join("") + "</select></label>" +
      (tischFeld ? '<label class="feld"><span>Tisch</span><select id="sd-tisch">' + tischOpt + "</select>" + (tischWeg ? '<span class="hinweis-box">Tisch ' + sieg.tisch + " gibt es nicht mehr. Bitte einen Tisch wählen oder leer lassen.</span>" : "") + "</label>" : "") +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Speichern</button></div>');
    const person = bindPerson("sd", null, sieg.person_id);
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const tw = $("sd-tisch") ? $("sd-tisch").value : "";
      const r = await CTRL.call("sieg_bearbeiten", da.jahr, sieg.id, person(), $("sd-preis").value, tw ? parseInt(tw, 10) : (tischFeld ? null : sieg.tisch || null));
      if (r) { $("modal-karte").onclick = null; CTRL.closeModal(); CTRL.toast("Sieg geändert"); }
    };
  }
  A["sieg-bearbeiten"] = (el) => siegDialog((da.siege || []).find((x) => x.id === el.dataset.id));
  A["sieg-loeschen"] = async (el) => {
    const s = (da.siege || []).find((x) => x.id === el.dataset.id);
    if (!s) return;
    const ja = await CTRL.bestaetigen("Sieg löschen?", siegBezeichnung(s) + ": " + s.name + " – " + s.preis_name + " wird gelöscht. Der Preis steht danach wieder zur Verfügung.", "Löschen");
    if (!ja) return;
    const r = await CTRL.call("sieg_loeschen", da.jahr, s.id);
    if (r) CTRL.toast("Sieg gelöscht");
  };

  // ---- Preisnamen
  let pnListe = [];
  async function preisnamenLaden() {
    const mein = ++da.pnZaehler;
    const r = await CTRL.lies("preisnamen");
    if (mein !== da.pnZaehler || da.reiter !== "preisnamen") return;
    pnListe = Array.isArray(r) ? r : [];
    const vorhanden = new Set(pnListe.map((n) => n.name));
    Array.from(da.auswahl).forEach((n) => { if (!vorhanden.has(n)) da.auswahl.delete(n); });
    $("da-liste").innerHTML = pnListe.length
      ? '<table class="daten da-tabelle"><thead><tr><th></th><th>Bild</th><th>Name</th><th>Jahre</th><th>Anzahl</th><th>Vergeben</th><th></th></tr></thead><tbody>' +
        pnListe.map((n, i) => {
          const u = window.BILDER[normName(n.name)];
          return '<tr><td><input type="checkbox" data-act="pn-wahl" data-i="' + i + '"' + (da.auswahl.has(n.name) ? " checked" : "") + ' aria-label="' + esc(n.name) + ' auswählen"></td><td>' +
            (u ? bildIcon(normName(n.name), "geschenk").replace('class="bild"', 'class="bild mini"') : (n.hat_bild ? '<span class="tag">Bild</span>' : "–")) +
            '</td><td class="umbruch">' + kurzHtml(n.name) + "</td><td class=\"umbruch\">" + esc(jahreText(n.jahre)) + "</td><td>" + zahl(n.anzahl) + "</td><td>" + zahl(n.vergeben) + '</td><td class="aktionen">' +
            '<button class="knopf klein" data-act="pn-umbenennen" data-i="' + i + '">Umbenennen</button> <button class="knopf klein" data-act="pn-bild" data-i="' + i + '">Bild wählen …</button>' +
            (n.hat_bild ? ' <button class="knopf klein" data-act="pn-bild-weg" data-i="' + i + '">Bild entfernen</button>' : "") + "</td></tr>";
        }).join("") + "</tbody></table>"
      : '<p class="leer-text">Noch keine Preise vorhanden</p>';
    $("pn-merge-knopf").disabled = da.auswahl.size < 2;
  }
  const jahreText = (j) => (j || []).slice().sort().join(", ");
  A["pn-wahl"] = (el) => {
    const n = pnListe[+el.dataset.i];
    if (!n) return;
    if (el.checked) da.auswahl.add(n.name); else da.auswahl.delete(n.name);
    $("pn-merge-knopf").disabled = da.auswahl.size < 2;
  };
  function umbenennenDialog(n) {
    CTRL.openModal(
      "<h2>Preis umbenennen</h2><p class=\"leise\">Gilt für alle Jahre, in denen „" + esc(n.name) + "“ vorkommt.</p>" +
      '<label class="feld"><span>Neuer Name</span><input type="text" id="un-name" value="' + esc(n.name) + '" autocomplete="off"></label>' +
      '<p class="hinweis-box" id="un-hinweis" hidden></p>' +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Umbenennen</button></div>');
    const hinweis = () => {
      const k = normName($("un-name").value);
      const ex = k && k !== normName(n.name) ? pnListe.find((x) => normName(x.name) === k) : null;
      $("un-hinweis").hidden = !ex;
      if (ex) $("un-hinweis").textContent = "„" + n.name + "“ wird mit „" + ex.name + "“ zusammengeführt. Im selben Jahr werden die Preise zu einem zusammengelegt (Mengen addiert, Siege umgehängt).";
    };
    $("un-name").addEventListener("input", hinweis);
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const r = await CTRL.call("preisname_umbenennen", n.name, $("un-name").value);
      if (r) { $("modal-karte").onclick = null; CTRL.closeModal(); CTRL.toast("Preisname geändert"); }
    };
  }
  A["pn-umbenennen"] = (el) => { const n = pnListe[+el.dataset.i]; if (n) umbenennenDialog(n); };
  A["pn-merge"] = () => {
    const namen = Array.from(da.auswahl);
    if (namen.length < 2) return;
    CTRL.openModal(
      "<h2>Preisnamen zusammenführen</h2><p>Ausgewählt: " + namen.map((n) => "„" + esc(n) + "“").join(", ") + "</p>" +
      '<label class="feld"><span>Zusammenführen zu</span><input type="text" id="zm-name" value="' + esc(namen[0]) + '" autocomplete="off"></label>' +
      '<div class="menge-schnell">' + namen.map((n, i) => '<button class="knopf klein" data-ziel="' + i + '">' + esc(n) + "</button>").join("") + "</div>" +
      '<p class="klein leise">Im selben Jahr werden Preise mit gleichem Namen zu einem zusammengelegt (Mengen addiert, Siege umgehängt). Bilder ziehen mit.</p>' +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Zusammenführen</button></div>');
    $("modal-karte").onclick = async (e) => {
      const z = e.target.closest("[data-ziel]");
      if (z) { $("zm-name").value = namen[+z.dataset.ziel]; return; }
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const ziel = $("zm-name").value.trim();
      if (!ziel) { CTRL.toast("Bitte einen Namen eingeben", true); return; }
      for (const alt of namen) {
        if (alt === ziel) continue;
        const r = await CTRL.call("preisname_umbenennen", alt, ziel);
        if (!r) return;
      }
      da.auswahl.clear();
      $("modal-karte").onclick = null; CTRL.closeModal(); CTRL.toast("Preisnamen zusammengeführt");
    };
  };
  A["pn-bild"] = async (el) => {
    const n = pnListe[+el.dataset.i];
    if (!n) return;
    const u = await CTRL.bildWaehlen();
    if (u) { const r = await CTRL.call("preis_bild_setzen", n.name, u); if (r) CTRL.toast("Bild gespeichert"); }
  };
  A["pn-bild-weg"] = async (el) => {
    const n = pnListe[+el.dataset.i];
    if (!n) return;
    const r = await CTRL.call("preis_bild_entfernen", n.name);
    if (r) CTRL.toast("Bild entfernt");
  };

  // ---- Personen
  function personenListe() {
    const Z = Zn();
    const such = da.psuche;
    const alle = Z.personen.filter((p) => CTRL.passt(p.name, such));
    const MAX = 200;
    $("da-info").textContent = anzahl(Z.personen.length, "Person", "Personen") + (alle.length < Z.personen.length ? " · " + zahl(alle.length) + " gefunden" : "");
    $("da-liste").innerHTML = alle.length
      ? '<table class="daten da-tabelle"><thead><tr><th>Name</th><th>Vorname</th><th>Nachname</th><th></th><th></th></tr></thead><tbody>' +
        alle.slice(0, MAX).map((p) => '<tr><td class="umbruch">' + kurzHtml(p.name) + "</td><td class=\"umbruch\">" + esc(p.vorname) + '</td><td class="umbruch">' + esc(p.nachname) + "</td><td>" + (p.ist_team ? '<span class="tag">Team</span>' : "") +
          '</td><td class="aktionen"><button class="knopf klein" data-act="pe-bearbeiten" data-id="' + esc(p.id) + '">Bearbeiten</button> <button class="knopf klein" data-act="pe-merge" data-id="' + esc(p.id) + '">Zusammenführen</button></td></tr>').join("") +
        "</tbody></table>" + (alle.length > MAX ? '<p class="leer-text">Es werden die ersten ' + MAX + " angezeigt. Bitte die Suche verfeinern.</p>" : "")
      : '<p class="leer-text">Keine Person gefunden</p>';
  }
  A["pe-bearbeiten"] = (el) => {
    const p = Zn().personen.find((x) => x.id === el.dataset.id);
    if (!p) return;
    CTRL.openModal(
      "<h2>Person bearbeiten</h2>" +
      '<div class="feld-zeile"><label class="feld"><span>Vorname</span><input type="text" id="pb-vor" value="' + esc(p.vorname) + '" autocomplete="off"></label>' +
      '<label class="feld"><span>Nachname</span><input type="text" id="pb-nach" value="' + esc(p.nachname) + '" autocomplete="off"></label></div>' +
      '<label class="haken"><input type="checkbox" id="pb-team"' + (p.ist_team ? " checked" : "") + "> Team („A / B“)</label>" +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Speichern</button></div>');
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      if (CTRL.istLaufend()) return;
      const r = await CTRL.call("person_bearbeiten", p.id, $("pb-vor").value, $("pb-nach").value, $("pb-team").checked);
      if (r) { $("modal-karte").onclick = null; CTRL.closeModal(); CTRL.toast("Person geändert"); }
    };
  };
  function mergeDialog(q) {
    CTRL.openModal(
      "<h2>Personen zusammenführen</h2><p><b>" + esc(q.name) + "</b> wird in die Person übernommen, die du hier wählst.</p>" +
      '<div class="feld"><span>Ziel</span>' + personHtml("zf") + "</div>" +
      '<div class="modal-aktionen"><button class="knopf" data-m="abbruch">Abbrechen</button><button class="knopf primaer" data-m="ok">Weiter</button></div>');
    const ziel = bindPerson("zf", q.id, null);
    $("modal-karte").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "abbruch") { $("modal-karte").onclick = null; CTRL.closeModal(); return; }
      const zid = ziel();
      const z = Zn().personen.find((x) => x.id === zid);
      if (!z) { CTRL.toast("Bitte die Zielperson auswählen", true); return; }
      $("modal-karte").onclick = null;
      const ja = await CTRL.bestaetigen("Wirklich zusammenführen?", q.name + " wird in " + z.name + " übernommen, " + q.name + " wird gelöscht. Alle Siege und Anwesenheiten werden umgehängt.", "Zusammenführen");
      if (!ja) { mergeDialog(q); return; }
      const r = await CTRL.call("personen_zusammenfuehren", q.id, z.id);
      if (r) CTRL.toast("Personen zusammengeführt");
    };
  }
  A["pe-merge"] = (el) => { const q = Zn().personen.find((x) => x.id === el.dataset.id); if (q) mergeDialog(q); };
})();
