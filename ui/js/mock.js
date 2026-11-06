// Demo-Modus: In-Memory-Attrappe der Python-Api mit ERFUNDENEN Daten.
// Wird nur benutzt, wenn window.pywebview fehlt (HTML direkt im Browser geoeffnet).
// Spiegelt paschen/api.py (Zustandsform und Regeln), ist aber bewusst klein gehalten.
(function () {
  function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
  let idz = 1;
  const nid = (p) => (p || "id") + (idz++);

  const VOR = "Fridolin Ottilie Kunigunde Balduin Hermine Eberhard Waltraud Leopold Gundula Theobald Rosalinde Adelbert Mechthild Wendelin Hildegunde Kasimir Brunhilde Ansgar Irmtraud Volkmar Gerlinde Radegund Isidor Walburga Humbert Thusnelda Lambert Sieglinde Quirin".split(" ");
  const NACH = "Musterfrau Beispiel Probe Testmann Demo Platzhalter Vorlage Exempel Schablone Attrappe Modell Stichprobe Fiktiv Erfunden Beleg Entwurf Skizze Dummy Zufall Rohling Prototyp Kopie Nachbau Probant Testfall Stellvertreter Mustermann Fallbeispiel Versuch Muster".split(" ");

  const D = { ordner: "C:\\Demo\\Paschen-Daten", personen: [], spiele: [], jahr: 2025, ansicht: "spiel", design: (/[?&]design=dunkel(&|$)/.test(location.search) ? "dunkel" : "hell"), sonderrunde: null, ereignis: null, ez: 0,
    demo: { aktiv: /[?&]demoband(&|=|$)/.test(location.search), art: "erfunden" }, bilder: {}, bilder_version: 1, bilder_gepostet: 0,
    regeln: [], regeln_intervall: 12, regel_index: 0, regel_nonce: 1 };
  D.regeln = [
    { id: "r1", titel: "Paschen", text: "Gespielt wird mit 3 Würfeln und einem Würfelbecher.\nJede Runde hat genau einen Gewinner.", wuerfel: [3, 5, 2] },
    { id: "r2", titel: "Der Startspieler legt vor", text: "Er würfelt mit allen drei Würfeln unter dem Becher, bis zu dreimal, und darf nach jedem Wurf ansagen.\nDie Zielvorgabe lautet zum Beispiel „Höher als 15!“ oder „Tiefer als 5!“.", wuerfel: [6, 5, 4] },
    { id: "r3", titel: "Die anderen würfeln reihum", text: "Mit allen drei Würfeln – höchstens so oft, wie der Startspieler vor seiner Ansage gewürfelt hat.\nWer möchte, darf früher aufhören.", wuerfel: null },
    { id: "r4", titel: "Gezählt wird die Augensumme", text: "Bei „Höher“ gewinnt das höchste Ergebnis über der Vorgabe, bei „Tiefer“ das niedrigste darunter.\nWer die Vorgabe nicht erfüllt, wird nicht gewertet.", wuerfel: [6, 6, 5] },
    { id: "r5", titel: "Auch der Startspieler kann gewinnen", text: "Nach seiner Ansage würfelt er nicht mehr.\nEr gewinnt, wenn niemand seine Vorgabe übertrifft beziehungsweise unterbietet.", wuerfel: null },
    { id: "r6", titel: "Drei Einsen schlagen alles", text: "3 × 1 ist immer die beste Kombination –\nsogar besser als 3 × 6 bei „Höher“.", wuerfel: [1, 1, 1] },
    { id: "r7", titel: "Gleichstand? Dann wird gestochen", text: "Nur die Spieler mit dem gleichen besten Ergebnis stechen. Wer die Gewinnerzahl zuerst erreicht hat, beginnt und gibt eine neue Vorgabe vor.\nGestochen wird, bis es einen eindeutigen Gewinner gibt.", wuerfel: null },
    { id: "r8", titel: "Wer fängt an?", text: "Die erste Runde beginnt der jüngste Spieler.\nDanach beginnt jeweils der Spieler rechts vom bisherigen Startspieler.", wuerfel: null },
    { id: "r9", titel: "Der Gewinner wählt", text: "Nach jeder Runde sucht sich der Gewinner einen der noch verfügbaren Preise aus – hier auf dem Beamer zu sehen.", wuerfel: null },
  ];
  { const m = /[?&]folie=(\d+)/.exec(location.search); if (m) D.regel_index = +m[1]; }

  function aufbauen() {
    for (let i = 0; i < 30; i++) {
      const team = i === 29;
      D.personen.push({
        id: "p" + i,
        vorname: team ? "Ulfried / Wiltrud" : VOR[i],
        nachname: team ? "Gemeinsam" : NACH[i],
        ist_team: team,
      });
    }
    const r = rng(42);
    [2022, 2023, 2024].forEach((jahr, k) => {
      const n = 20 + Math.floor(r() * 7);
      const ids = D.personen.map((p) => p.id).sort(() => r() - 0.5).slice(0, n);
      const menge = 60 + k * 8;
      const siege = [];
      for (let i = 0; i < menge; i++) {
        const pid = ids[Math.floor(Math.pow(r(), 1.6) * ids.length)];
        siege.push({ nr: null, person_id: pid, preis_id: "alt" + jahr, sonderrunde: false, importiert: true });
      }
      D.spiele.push({ jahr, datum: null, phasen: [], preise: [{ id: "alt" + jahr, name: "Preise", icon: "geschenk", menge, phase_id: null, spezial: false }], anwesende_ids: ids, siege });
    });
    const p1 = { id: "ph1", name: "Wurst & Teigwaren", reihenfolge: 1 };
    const p2 = { id: "ph2", name: "Werbegeschenke", reihenfolge: 2 };
    const preise = [
      { id: "w1", name: "Dose Bierschinken", icon: "dose", menge: 10, phase_id: "ph1", spezial: false },
      { id: "w2", name: "Ringwurst", icon: "ring", menge: 8, phase_id: "ph1", spezial: false },
      { id: "w3", name: "Geräucherte Wurst", icon: "wurst", menge: 12, phase_id: "ph1", spezial: false },
      { id: "w4", name: "Teigwaren", icon: "teig", menge: 15, phase_id: "ph1", spezial: false },
      { id: "w5", name: "Honig", icon: "glas", menge: 6, phase_id: "ph1", spezial: false },
      { id: "g1", name: "Tasse", icon: "geschenk", menge: 12, phase_id: "ph2", spezial: false },
      { id: "g2", name: "Kugelschreiber-Set", icon: "geschenk", menge: 10, phase_id: "ph2", spezial: false },
      { id: "g3", name: "Wanderpokal", icon: "pokal", menge: 2, phase_id: "ph2", spezial: false },
      { id: "sp1", name: "Gin", icon: "flasche", menge: 1, phase_id: null, spezial: true },
    ];
    // Vorfuehrung: ?demo&viele = zusaetzliche Preise in Phase 1 (15 Kacheln), ?demo&lang = ~20 Zeichen lange Namen
    const q = location.search;
    if (/[?&]viele(&|=|$)/.test(q)) {
      ["Kugelschreiber-Set", "Dose Leberwurst", "Flasche Apfelsaft", "Packung Kaffee", "Salamistange", "Kasseler Kotelett", "Nudeln mit Ei", "Senf im Glas", "Schinkenspeck", "Dosenbrot"].forEach((n, i) =>
        preise.splice(5 + i, 0, { id: "v" + i, name: n, icon: ["geschenk", "dose", "flasche", "glas", "wurst", "ring", "teig", "glas", "wurst", "dose"][i], menge: 3 + i, phase_id: "ph1", spezial: false }));
    }
    if (/[?&]lang(&|=|$)/.test(q)) {
      preise[0].name = "Dose Bierschinken groß";
      preise[2].name = "Geräucherte Dauerwurst";
      preise[3].name = "Hausgemachte Teigwaren";
    }
    const anw = D.personen.slice(0, 26).map((p) => p.id);
    const s25 = { jahr: 2025, datum: null, phasen: [p1, p2], preise, anwesende_ids: anw, siege: [] };
    D.spiele.push(s25);
    // einige Siege vorspielen (gewichtet)
    const pre = ["w1", "w1", "w3", "w4", "w4", "w2", "w3", "w5", "w4", "w1", "w2", "w3", "w4", "w4", "w1", "w3", "w2", "w4", "w5", "w3", "w1", "w4", "w2", "w3", "w4", "w1", "w3"];
    pre.forEach((pr, i) => {
      const pid = anw[Math.floor(Math.pow(r(), 1.5) * anw.length)];
      s25.siege.push({ nr: i + 1, person_id: pid, preis_id: pr, sonderrunde: false, importiert: false, zeit: "2025-11-06T19:" + String(10 + i).padStart(2, "0") + ":00" });
    });
  }
  // Worst-Case-Daten zum Ausprobieren der Oberflaeche (alles ERFUNDEN):
  //   ?demo&extrem        70 Anwesende, sehr lange Namen/Teams, Ein-Buchstaben-Namen, dreistellige Mengen,
  //                       140+ Runden, 12 Vorjahre, Preisname mit 30+ Zeichen, Phase ohne Preise, zwei Spezialpreise
  //   ?demo&extrem=leer   alles leer: keine Personen, Siege, Vorjahre, Preise
  function aufbauenExtrem(leer) {
    D.personen = []; D.spiele = [];
    if (leer) {
      D.spiele.push({ jahr: 2025, datum: null, phasen: [], preise: [], anwesende_ids: [], siege: [] });
      return;
    }
    const LANG_V = "Maximiliane-Theodora-Annabelle-Friederike-Gundelinde";
    const LANG_N = "Musterfrau-Beispielhausen-Platzhalter-Vorlagenstein";
    for (let i = 0; i < 70; i++) {
      let vor = VOR[i % VOR.length], nach = NACH[(i * 7 + 3 + Math.floor(i / VOR.length)) % NACH.length], team = false;
      if (i < 4) { vor = LANG_V.slice(0, 20 + i * 10); nach = LANG_N; }              // sehr lange Namen
      else if (i < 8) { vor = "XQZW"[i - 4]; nach = "YKJV"[i - 4]; }                  // Ein-Buchstaben-Namen
      else if (i < 14) {                                                              // lange Teams
        team = true;
        vor = VOR[i] + "-" + VOR[i + 1] + " / " + VOR[i + 2] + "-" + VOR[i + 3];
        nach = "Gemeinsam-" + NACH[i] + "-Gruppe";
      }
      D.personen.push({ id: "p" + i, vorname: vor, nachname: nach, ist_team: team });
    }
    const r = rng(7);
    // 12 Vorjahre
    for (let jahr = 2013; jahr <= 2024; jahr++) {
      const n = 25 + Math.floor(r() * 40);
      const ids = D.personen.map((p) => p.id).sort(() => r() - 0.5).slice(0, n);
      const menge = 90 + Math.floor(r() * 80);
      const siege = [];
      for (let i = 0; i < menge; i++) siege.push({ nr: null, person_id: ids[Math.floor(Math.pow(r(), 1.6) * ids.length)], preis_id: "alt" + jahr, sonderrunde: false, importiert: true });
      D.spiele.push({ jahr, datum: null, phasen: [], preise: [{ id: "alt" + jahr, name: "Preise", icon: "geschenk", menge, phase_id: null, spezial: false }], anwesende_ids: ids, siege });
    }
    const p1 = { id: "ph1", name: "Phase 1 – Wurst, Teigwaren und andere Dauerwaren aus dem Vereinsvorrat", reihenfolge: 1 };
    const p2 = { id: "ph2", name: "Phase 2 – Werbegeschenke", reihenfolge: 2 };
    const p3 = { id: "ph3", name: "Phase 3 – noch ohne Preise", reihenfolge: 3 };
    const p4 = { id: "ph4", name: "Phase 4 – Restposten", reihenfolge: 4 };
    const N1 = ["Dose Bierschinken", "Ringwurst", "Geräucherte Wurst", "Teigwaren", "Honig", "Handgefertigter Vereinspokal mit Gravur und Schleife", "Salamistange",
      "Dose Leberwurst", "Flasche Apfelsaft", "Packung Kaffee", "Kasseler Kotelett", "Senf im Glas", "Schinkenspeck", "Dosenbrot"];
    const IC = ["dose", "ring", "wurst", "teig", "glas", "pokal", "wurst", "dose", "flasche", "glas", "wurst", "glas", "wurst", "dose"];
    const MENGE = [180, 240, 150, 320, 110, 2, 95, 120, 100, 410, 260, 130, 999, 105];
    const preise = N1.map((n, i) => ({ id: "w" + i, name: n, icon: IC[i], menge: MENGE[i], phase_id: "ph1", spezial: false }));
    ["Tasse", "Kugelschreiber-Set", "Z"].forEach((n, i) => preise.push({ id: "g" + i, name: n, icon: "geschenk", menge: [12, 10, 1][i], phase_id: "ph2", spezial: false }));
    ["Gutschein", "Flaschenöffner", "Schlüsselband"].forEach((n, i) => preise.push({ id: "r" + i, name: n, icon: "geschenk", menge: [7, 6, 5][i], phase_id: "ph4", spezial: false }));
    preise.push({ id: "sp1", name: "Flasche Premium-Gin aus der Vereinsbrennerei (limitierte Sonderfüllung)", icon: "flasche", menge: 1, phase_id: null, spezial: true });
    preise.push({ id: "sp2", name: "Reisegutschein", icon: "geschenk", menge: 2, phase_id: null, spezial: true });
    const anw = D.personen.map((p) => p.id);
    const s25 = { jahr: 2025, datum: null, phasen: [p1, p2, p3, p4], preise, anwesende_ids: anw, siege: [] };
    D.spiele.push(s25);
    // 148 Runden vorspielen; der letzte Gewinner hat einen sehr langen Namen
    for (let i = 0; i < 148; i++) {
      const pid = i === 147 ? "p3" : anw[Math.floor(Math.pow(r(), 1.5) * anw.length)];
      let k = i % 14;
      if (k === 5 && s25.siege.filter((x) => x.preis_id === "w5").length >= 2) k = 3;
      s25.siege.push({ nr: i + 1, person_id: pid, preis_id: "w" + k, sonderrunde: false, importiert: false, zeit: "2025-11-06T19:" + String(10 + (i % 50)).padStart(2, "0") + ":00" });
    }
  }
  const EXTREM = /[?&]extrem(&|=|$)/.test(location.search);
  const EXTREM_LEER = /[?&]extrem=leer(&|$)/.test(location.search);

  aufbauen();
  if (EXTREM) aufbauenExtrem(EXTREM_LEER);

  // Beispielbilder (per Canvas erzeugte Farbflaechen und Muster, keine Fremdbilder)
  function bildErzeugen(art) {
    const c = document.createElement("canvas"); c.width = 240; c.height = 240;
    const g = c.getContext("2d");
    const farben = { ringwurst: ["#B5472E", "#F0C9A8"], honig: ["#E0A020", "#FFF0B8"], tasse: ["#2F6DB5", "#DCEBFA"], pokal: ["#3F8F5A", "#E2F3E8"] }[art];
    g.fillStyle = farben[1]; g.fillRect(0, 0, 240, 240);
    g.fillStyle = farben[0];
    if (art === "ringwurst") { for (let i = -240; i < 240; i += 44) { g.beginPath(); g.moveTo(i, 240); g.lineTo(i + 30, 240); g.lineTo(i + 270, 0); g.lineTo(i + 240, 0); g.fill(); } }
    if (art === "honig") { for (let y = 0; y < 5; y++) for (let x = 0; x < 5; x++) { g.beginPath(); g.arc(24 + x * 48 + (y % 2) * 24, 24 + y * 48, 17, 0, 7); g.fill(); } }
    if (art === "tasse") { g.fillRect(0, 150, 240, 90); g.beginPath(); g.arc(120, 100, 56, 0, 7); g.fill(); g.fillStyle = farben[1]; g.beginPath(); g.arc(120, 100, 28, 0, 7); g.fill(); }
    if (art === "pokal") { for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) { g.beginPath(); g.moveTo(30 + x * 60, y * 60 + 6); g.lineTo(54 + x * 60, y * 60 + 30); g.lineTo(30 + x * 60, y * 60 + 54); g.lineTo(6 + x * 60, y * 60 + 30); g.fill(); } }
    return c.toDataURL("image/jpeg", 0.8);
  }
  if (!/[?&]ohnebilder(&|=|$)/.test(location.search) && !EXTREM) {
    try {
      D.bilder[normName("Ringwurst")] = bildErzeugen("ringwurst");
      D.bilder[normName("Honig")] = bildErzeugen("honig");
      D.bilder[normName("Tasse")] = bildErzeugen("tasse");
      D.bilder[normName("Wanderpokal")] = bildErzeugen("pokal");
    } catch (e) { /* ohne Canvas keine Bilder */ }
  }
  D.spiele.forEach((sp) => sp.siege.forEach((x) => { if (!x.id) x.id = "s" + (idz++); }));

  // ---------------------------------------------------------------- Regeln (Spiegel von spiel.py)
  const spiel = (j) => D.spiele.find((s) => s.jahr === (j == null ? D.jahr : j));
  const person = (id) => D.personen.find((p) => p.id === id);
  const pname = (id) => { const p = person(id); return p ? (p.vorname + " " + p.nachname).trim() : "(unbekannt)"; };
  const vergeben = (s, id) => s.siege.filter((x) => x.preis_id === id).length;
  const rest = (s, id) => { const p = s.preise.find((x) => x.id === id); return Math.max(0, p.menge - vergeben(s, id)); };
  const phasen = (s) => s.phasen.slice().sort((a, b) => a.reihenfolge - b.reihenfolge);
  const aktive = (s) => phasen(s).find((ph) => s.preise.some((p) => p.phase_id === ph.id && !p.spezial && rest(s, p.id) > 0)) || null;
  const restGesamt = (s) => s.preise.reduce((a, p) => a + rest(s, p.id), 0);
  const beendet = (s) => s.preise.length > 0 && restGesamt(s) === 0;
  const sortName = (a, b) => (a.nachname + a.vorname).localeCompare(b.nachname + b.vorname, "de");
  const fehler = (t) => { throw new Error(t); };

  const bildKey = (p) => (p && D.bilder[normName(p.name)] ? normName(p.name) : null);
  function siegDict(s, x) {
    const p = s.preise.find((q) => q.id === x.preis_id);
    if (!x.id) x.id = nid("s");
    return { id: x.id, bild: bildKey(p), importiert: !!x.importiert, nr: x.nr, zeit: x.zeit || null, person_id: x.person_id, name: pname(x.person_id), preis_id: x.preis_id, preis_name: p ? p.name : "?", icon: p ? p.icon : "", sonderrunde: !!x.sonderrunde };
  }
  function teiln(s) { return new Set([...s.anwesende_ids, ...s.siege.map((x) => x.person_id)]); }
  function zaehle(s) { const m = {}; s.siege.forEach((x) => (m[x.person_id] = (m[x.person_id] || 0) + 1)); return m; }

  function statistik() {
    const jahre = D.spiele.map((s) => s.jahr).sort();
    const ids = new Set(); D.spiele.forEach((s) => teiln(s).forEach((i) => ids.add(i)));
    const zeilen = [...ids].map((pid) => {
      const o = {}; let g = 0;
      D.spiele.forEach((s) => { if (teiln(s).has(pid)) { const n = zaehle(s)[pid] || 0; o[s.jahr] = n; g += n; } else o[s.jahr] = null; });
      return { person_id: pid, name: pname(pid), jahre: o, gesamt: g };
    }).sort((a, b) => b.gesamt - a.gesamt || a.name.localeCompare(b.name, "de"));
    const jv = D.spiele.slice().sort((a, b) => a.jahr - b.jahr).map((s) => ({ jahr: s.jahr, teilnehmer: teiln(s).size, preise_gesamt: s.preise.reduce((a, p) => a + p.menge, 0), runden: s.siege.length }));
    const alle = [], jeJahr = [];
    D.spiele.slice().sort((a, b) => a.jahr - b.jahr).forEach((s) => {
      const z = zaehle(s);
      const e = Object.keys(z).map((pid) => ({ jahr: s.jahr, person_id: pid, name: pname(pid), siege: z[pid] })).sort((a, b) => b.siege - a.siege || a.name.localeCompare(b.name, "de"));
      alle.push(...e); if (e.length) jeJahr.push(e[0]);
    });
    const max = alle.length ? Math.max(...alle.map((e) => e.siege)) : 0;
    const ewig = alle.filter((e) => e.siege === max);
    const tn = {}, sg = {};
    D.spiele.forEach((s) => { teiln(s).forEach((i) => (tn[i] = (tn[i] || 0) + 1)); Object.entries(zaehle(s)).forEach(([i, n]) => (sg[i] = (sg[i] || 0) + n)); });
    const top = (arr) => arr.sort((a, b) => tn[b] - tn[a] || pname(a).localeCompare(pname(b), "de")).slice(0, 10).map((i) => ({ person_id: i, name: pname(i), teilnahmen: tn[i] }));
    return { jahre, bestenliste: zeilen, jahresvergleich: jv, rekorde: { meiste_siege_nachmittag: { ewig, je_jahr: jeJahr }, teilnahmen: top(Object.keys(tn)), pechvogel: top(Object.keys(tn).filter((i) => !sg[i])) } };
  }

  function zustand(mitEreignis) {
    const s = spiel();
    const z = {
      datenordner: D.ordner,
      jahre: D.spiele.map((x) => x.jahr).sort(),
      jahr: s ? s.jahr : null,
      jahre_info: D.spiele.slice().sort((a, b) => a.jahr - b.jahr).map((x) => ({ jahr: x.jahr, preise: x.preise.reduce((a, p) => a + p.menge, 0), teilnehmer: x.anwesende_ids.length, siege: x.siege.length, beendet: beendet(x) })),
      beamer_ansicht: D.ansicht,
      beamer_design: D.design,
      sonderrunde: null,
      spiel: null,
      personen: [],
      statistik: statistik(),
      ereignis: mitEreignis ? D.ereignis : null,
      demo: { aktiv: D.demo.aktiv, art: D.demo.aktiv ? D.demo.art : null },
      bilder_version: D.bilder_version,
      regeln: D.regeln.map((r) => ({ id: r.id, titel: r.titel, text: r.text, wuerfel: r.wuerfel ? r.wuerfel.slice() : null })),
      regeln_intervall_s: D.regeln_intervall,
      regel_index: D.regel_index,
      regel_nonce: D.regel_nonce,
    };
    const z0 = s ? zaehle(s) : {};
    z.personen = D.personen.slice().sort(sortName).map((p) => ({ id: p.id, vorname: p.vorname, nachname: p.nachname, ist_team: p.ist_team, name: (p.vorname + " " + p.nachname).trim(), anwesend: !!s && s.anwesende_ids.includes(p.id), siege: z0[p.id] || 0 }));
    if (!s) return z;
    const akt = aktive(s);
    const ph = phasen(s);
    const pd = (p) => { const r = rest(s, p.id); return { id: p.id, name: p.name, icon: p.icon, bild: bildKey(p), menge: p.menge, phase_id: p.phase_id, spezial: p.spezial, rest: r, vergeben: p.menge - r, waehlbar: !p.spezial && r > 0 && !!akt && p.phase_id === akt.id }; };
    const ni = s.siege.filter((x) => !x.importiert);
    if (D.sonderrunde) {
      const p = s.preise.find((x) => x.id === D.sonderrunde);
      if (p && p.spezial && rest(s, p.id) > 0) z.sonderrunde = { preis_id: p.id, name: p.name, icon: p.icon, bild: bildKey(p), rest: rest(s, p.id) };
    }
    z.spiel = {
      jahr: s.jahr, datum: s.datum,
      phasen: ph.map((p) => { const ps = s.preise.filter((x) => x.phase_id === p.id && !x.spezial); const r = ps.reduce((a, x) => a + rest(s, x.id), 0); const g = ps.reduce((a, x) => a + x.menge, 0); return { id: p.id, name: p.name, reihenfolge: p.reihenfolge, rest: r, gesamt: g, aktiv: !!akt && akt.id === p.id, abgeschlossen: g > 0 && r === 0, preise: ps.map((x) => x.id) }; }),
      phasen_anzahl: ph.length,
      aktive_phase_id: akt ? akt.id : null,
      aktive_phase_name: akt ? akt.name : null,
      phase_nr: akt ? ph.findIndex((p) => p.id === akt.id) + 1 : null,
      preise: s.preise.map(pd),
      anwesende: s.anwesende_ids.map(person).filter(Boolean).sort(sortName).map((p) => ({ id: p.id, name: (p.vorname + " " + p.nachname).trim(), ist_team: p.ist_team, siege: z0[p.id] || 0 })),
      letzte_siege: ni.slice(-12).reverse().map((x) => siegDict(s, x)),
      letzter_sieg: ni.length ? siegDict(s, ni[ni.length - 1]) : null,
      runde: s.siege.length + 1,
      runden_gespielt: s.siege.length,
      rest_gesamt: restGesamt(s),
      beendet: beendet(s),
      top10: Object.keys(z0).sort((a, b) => z0[b] - z0[a] || pname(a).localeCompare(pname(b), "de")).slice(0, 10).map((i) => ({ person_id: i, name: pname(i), siege: z0[i] })),
      spezialpreise_offen: s.preise.filter((p) => p.spezial && rest(s, p.id) > 0).map(pd),
    };
    return z;
  }

  let kanal = null;
  try { kanal = new BroadcastChannel("paschen-demo"); } catch (e) { /* egal */ }
  function fertig(ereignis) {
    if (ereignis) { D.ez++; ereignis.id = D.ez; }
    D.ereignis = ereignis || null;
    const z = zustand(true);
    try {
      if (kanal) {
        const m = Object.assign({}, z);
        if (D.bilder_gepostet !== D.bilder_version) { m._bilder = D.bilder; D.bilder_gepostet = D.bilder_version; }
        kanal.postMessage(m);
      }
    } catch (e) { /* egal */ }
    D.ereignis = null;
    return z;
  }
  function folge(s, vorher) {
    if (beendet(s)) return { typ: "ende" };
    const jetzt = aktive(s);
    if ((jetzt ? jetzt.id : null) !== (vorher ? vorher.id : null)) return { typ: "phasenwechsel", von_name: vorher ? vorher.name : null, nach_name: jetzt ? jetzt.name : null };
    return null;
  }
  function eintragen(pid, prid, sonder) {
    const s = spiel();
    if (!s) fehler("Bitte zuerst ein Spiel wählen.");
    if (!s.anwesende_ids.includes(pid)) fehler("Diese Person ist nicht als anwesend angemeldet.");
    const p = s.preise.find((x) => x.id === prid);
    if (!p) fehler("Dieser Preis existiert nicht.");
    if (rest(s, prid) <= 0) fehler('Der Preis "' + p.name + '" ist bereits vergeben.');
    if (sonder) { if (!p.spezial) fehler("Kein Spezialpreis."); }
    else {
      if (D.sonderrunde) fehler("Eine Sonderrunde läuft. Bitte erst abschließen oder abbrechen.");
      if (p.spezial) fehler('"' + p.name + '" ist ein Spezialpreis und nur in einer Sonderrunde vergebbar.');
      const a = aktive(s);
      if (!a || p.phase_id !== a.id) fehler('"' + p.name + '" gehört nicht zur aktuellen Phase.');
    }
    const vorher = aktive(s);
    const x = { nr: s.siege.length + 1, zeit: new Date().toISOString().slice(0, 19), person_id: pid, preis_id: prid, sonderrunde: !!sonder, importiert: false };
    s.siege.push(x);
    if (sonder) D.sonderrunde = null;
    return fertig(Object.assign(siegDict(s, x), { typ: "sieg", folge: folge(s, vorher) }));
  }

  const roh = {
    zustand: () => zustand(false),
    datenordner_waehlen: () => { D.ordner = "C:\\Demo\\Paschen-Daten"; return fertig(); },
    datenordner_setzen: (p) => { D.ordner = p; return fertig(); },
    jahr_waehlen: (j) => { if (!spiel(+j)) fehler("Für " + j + " gibt es kein Spiel."); D.jahr = +j; D.sonderrunde = null; return fertig(); },
    neues_spiel: (j) => {
      j = j ? +j : Math.max(...D.spiele.map((s) => s.jahr)) + 1;
      if (spiel(j)) fehler("Für " + j + " gibt es bereits ein Spiel.");
      const vor = D.spiele.filter((s) => s.jahr < j).sort((a, b) => b.jahr - a.jahr)[0];
      const n = { jahr: j, datum: null, phasen: [], preise: [], anwesende_ids: [], siege: [] };
      if (vor) {
        const m = {};
        vor.phasen.forEach((p) => { const q = { id: nid("ph"), name: p.name, reihenfolge: p.reihenfolge }; m[p.id] = q.id; n.phasen.push(q); });
        vor.preise.forEach((p) => n.preise.push(Object.assign({}, p, { id: nid("pr"), phase_id: p.phase_id ? m[p.phase_id] : null })));
        n.anwesende_ids = vor.anwesende_ids.slice();
      }
      D.spiele.push(n); D.jahr = j; D.sonderrunde = null; return fertig();
    },
    person_anlegen: (v, n, team, anm) => {
      v = (v || "").trim(); n = (n || "").trim();
      if (!v && !n) fehler("Bitte Vor- und Nachname eingeben.");
      if (!team && (!v || !n)) fehler("Bitte Vor- und Nachname eingeben.");
      if (D.personen.some((p) => p.vorname.toLowerCase() === v.toLowerCase() && p.nachname.toLowerCase() === n.toLowerCase())) fehler('"' + v + " " + n + '" gibt es schon.');
      const p = { id: nid("p"), vorname: v, nachname: n, ist_team: !!team };
      D.personen.push(p);
      const s = spiel();
      if (anm !== false && s) s.anwesende_ids.push(p.id);
      return fertig();
    },
    anmelden: (id) => { const s = spiel(); if (!s.anwesende_ids.includes(id)) s.anwesende_ids.push(id); return fertig(); },
    abmelden: (id) => {
      const s = spiel();
      if (s.siege.some((x) => x.person_id === id)) fehler("Diese Person hat schon gewonnen und kann nicht abgemeldet werden.");
      s.anwesende_ids = s.anwesende_ids.filter((i) => i !== id); return fertig();
    },
    phase_hinzufuegen: (name) => {
      const s = spiel(); name = (name || "").trim(); if (!name) fehler("Die Phase braucht einen Namen.");
      s.phasen.push({ id: nid("ph"), name, reihenfolge: Math.max(0, ...s.phasen.map((p) => p.reihenfolge)) + 1 }); return fertig();
    },
    phase_umbenennen: (id, name) => { name = (name || "").trim(); if (!name) fehler("Die Phase braucht einen Namen."); spiel().phasen.find((p) => p.id === id).name = name; return fertig(); },
    phase_verschieben: (id, r) => {
      const s = spiel(); const l = phasen(s); const i = l.findIndex((p) => p.id === id); const j = i + (r > 0 ? 1 : -1);
      if (j >= 0 && j < l.length) { [l[i], l[j]] = [l[j], l[i]]; l.forEach((p, n) => (p.reihenfolge = n + 1)); }
      return fertig();
    },
    phase_loeschen: (id) => {
      const s = spiel();
      if (s.preise.some((p) => p.phase_id === id && vergeben(s, p.id) > 0)) fehler("In dieser Phase wurden schon Preise vergeben. Sie kann nicht gelöscht werden.");
      s.preise = s.preise.filter((p) => p.phase_id !== id); s.phasen = s.phasen.filter((p) => p.id !== id); return fertig();
    },
    icon_raten: (name) => {
      const n = (name || "").toLowerCase();
      const t = [["dose", ["dose"]], ["ring", ["ring"]], ["teig", ["teig", "nudel"]], ["wurst", ["wurst", "schinken"]], ["flasche", ["gin", "wein", "schnaps", "bier"]], ["glas", ["honig", "glas"]], ["pokal", ["pokal"]]];
      for (const [i, w] of t) if (w.some((x) => n.includes(x))) return i;
      return "geschenk";
    },
    preis_hinzufuegen: (name, icon, menge, phase, spezial) => {
      const s = spiel(); name = (name || "").trim(); menge = +menge;
      if (!name) fehler("Der Preis braucht einen Namen.");
      if (!(menge > 0)) fehler("Die Menge muss größer als 0 sein.");
      if (!spezial && (!phase || !s.phasen.some((p) => p.id === phase))) fehler("Ein normaler Preis braucht eine existierende Phase.");
      s.preise.push({ id: nid("pr"), name, icon: icon || roh.icon_raten(name), menge, phase_id: spezial ? null : phase, spezial: !!spezial }); return fertig();
    },
    preis_bearbeiten: (id, name, icon, menge, phase, spezial) => {
      const s = spiel(); const p = s.preise.find((x) => x.id === id); menge = +menge; name = (name || "").trim();
      if (!name) fehler("Der Preis braucht einen Namen.");
      if (!(menge > 0)) fehler("Die Menge muss größer als 0 sein.");
      if (menge < vergeben(s, id)) fehler("Davon sind schon " + vergeben(s, id) + " vergeben. Die Menge kann nicht kleiner sein.");
      if (!spezial && (!phase || !s.phasen.some((q) => q.id === phase))) fehler("Ein normaler Preis braucht eine existierende Phase.");
      Object.assign(p, { name, icon, menge, spezial: !!spezial, phase_id: spezial ? null : phase }); return fertig();
    },
    preis_loeschen: (id) => {
      const s = spiel(); if (vergeben(s, id) > 0) fehler("Dieser Preis wurde schon vergeben und kann nicht gelöscht werden.");
      s.preise = s.preise.filter((p) => p.id !== id); return fertig();
    },
    preis_nachlegen: (id, n) => { n = +n; if (!(n > 0)) fehler("Die Anzahl zum Nachlegen muss größer als 0 sein."); spiel().preise.find((p) => p.id === id).menge += n; return fertig(); },
    sieg: (pid, prid) => eintragen(pid, prid, false),
    rueckgaengig: () => {
      const s = spiel(); const i = s.siege.map((x) => x.importiert).lastIndexOf(false);
      if (i < 0) fehler("Es gibt keine Eintragung, die rückgängig gemacht werden kann.");
      s.siege.splice(i, 1); D.sonderrunde = null; return fertig();
    },
    sonderrunde_starten: (id) => {
      const s = spiel(); const p = s.preise.find((x) => x.id === id);
      if (!p || !p.spezial) fehler("Das ist kein Spezialpreis.");
      if (rest(s, id) <= 0) fehler('Der Preis "' + p.name + '" ist bereits vergeben.');
      D.sonderrunde = id; return fertig();
    },
    sonderrunde_abbrechen: () => { D.sonderrunde = null; return fertig(); },
    sonderrunde_sieg: (pid) => { if (!D.sonderrunde) fehler("Es läuft keine Sonderrunde."); return eintragen(pid, D.sonderrunde, true); },
    // ---- Neu: Spiele, Siege, Preisnamen, Personen, Bilder, Regeln, Demo
    spiel_loeschen: (j) => {
      j = +j; if (!spiel(j)) fehler("Für " + j + " gibt es kein Spiel.");
      D.spiele = D.spiele.filter((s) => s.jahr !== j); D.sonderrunde = null;
      if (D.jahr === j) { const r = D.spiele.map((s) => s.jahr).sort(); D.jahr = r.length ? r[r.length - 1] : null; }
      return fertig();
    },
    siege_liste: (j) => {
      const s = spiel(+j); if (!s) fehler("Für " + j + " gibt es kein Spiel.");
      return s.siege.map((x) => { const d = siegDict(s, x); return { id: x.id, nr: x.nr, zeit: x.zeit || null, person_id: x.person_id, name: d.name, preis_id: x.preis_id, preis_name: d.preis_name, sonderrunde: !!x.sonderrunde, importiert: !!x.importiert }; });
    },
    // Preise eines Jahres, nur lesend (aendert das aktive Jahr nicht); Form wie paschen/verwaltung.py
    preise_liste: (j) => {
      const s = spiel(+j); if (!s) fehler("Für " + j + " gibt es kein Spiel.");
      return s.preise.map((p) => ({ id: p.id, name: p.name, menge: p.menge, rest: rest(s, p.id), vergeben: vergeben(s, p.id), spezial: !!p.spezial, phase_id: p.phase_id || null, bild: bildKey(p) }));
    },
    sieg_bearbeiten: (j, sid, pid, prid) => {
      const s = spiel(+j); if (!s) fehler("Für " + j + " gibt es kein Spiel.");
      const x = s.siege.find((q) => q.id === sid); if (!x) fehler("Dieser Sieg existiert nicht.");
      if (!person(pid)) fehler("Diese Person existiert nicht.");
      const p = s.preise.find((q) => q.id === prid); if (!p) fehler("Dieser Preis existiert nicht.");
      if (prid !== x.preis_id && rest(s, prid) <= 0) fehler("Der Preis \"" + p.name + "\" ist bereits vergeben.");
      x.person_id = pid; x.preis_id = prid;
      if (!s.anwesende_ids.includes(pid)) s.anwesende_ids.push(pid);
      return fertig();
    },
    sieg_loeschen: (j, sid) => {
      const s = spiel(+j); if (!s) fehler("Für " + j + " gibt es kein Spiel.");
      if (!s.siege.some((q) => q.id === sid)) fehler("Dieser Sieg existiert nicht.");
      s.siege = s.siege.filter((q) => q.id !== sid); s.siege.forEach((q, i) => { if (!q.importiert) q.nr = i + 1; }); D.sonderrunde = null;
      return fertig();
    },
    preisnamen: () => {
      const m = new Map();
      D.spiele.slice().sort((a, b) => a.jahr - b.jahr).forEach((s) => s.preise.forEach((p) => {
        const k = normName(p.name);
        if (!m.has(k)) m.set(k, { name: p.name, jahre: [], anzahl: 0, vergeben: 0, hat_bild: !!D.bilder[k] });
        const e = m.get(k); if (!e.jahre.includes(s.jahr)) e.jahre.push(s.jahr);
        e.anzahl += p.menge; e.vergeben += vergeben(s, p.id);
      }));
      return [...m.values()].sort((a, b) => a.name.localeCompare(b.name, "de"));
    },
    preisname_umbenennen: (alt, neu) => {
      neu = (neu || "").trim(); if (!neu) fehler("Der neue Name darf nicht leer sein.");
      const ka = normName(alt), kn = normName(neu);
      if (!D.spiele.some((s) => s.preise.some((p) => normName(p.name) === ka))) fehler("Diesen Preisnamen gibt es nicht.");
      D.spiele.forEach((s) => {
        s.preise.forEach((p) => { if (normName(p.name) === ka) p.name = neu; });
        const erste = {};
        s.preise = s.preise.filter((p) => {
          if (normName(p.name) !== kn) return true;
          const e = erste[kn];
          if (!e) { erste[kn] = p; return true; }
          e.menge += p.menge; s.siege.forEach((x) => { if (x.preis_id === p.id) x.preis_id = e.id; }); return false;
        });
      });
      if (ka !== kn && D.bilder[ka]) { if (!D.bilder[kn]) D.bilder[kn] = D.bilder[ka]; delete D.bilder[ka]; }
      D.bilder_version++;
      return fertig();
    },
    person_bearbeiten: (id, v, n, team) => {
      const p = person(id); if (!p) fehler("Diese Person existiert nicht.");
      v = (v || "").trim(); n = (n || "").trim();
      if (!v && !n) fehler("Bitte Vor- und Nachname eingeben.");
      if (!team && (!v || !n)) fehler("Bitte Vor- und Nachname eingeben.");
      if (D.personen.some((q) => q.id !== id && q.vorname.toLowerCase() === v.toLowerCase() && q.nachname.toLowerCase() === n.toLowerCase())) fehler("\"" + v + " " + n + "\" gibt es schon. Bitte stattdessen zusammenführen.");
      Object.assign(p, { vorname: v, nachname: n, ist_team: !!team }); return fertig();
    },
    personen_zusammenfuehren: (q, z) => {
      if (q === z) fehler("Quelle und Ziel sind dieselbe Person.");
      if (!person(q) || !person(z)) fehler("Person nicht gefunden.");
      D.spiele.forEach((s) => {
        s.siege.forEach((x) => { if (x.person_id === q) x.person_id = z; });
        if (s.anwesende_ids.includes(q) && !s.anwesende_ids.includes(z)) s.anwesende_ids.push(z);
        s.anwesende_ids = s.anwesende_ids.filter((i) => i !== q);
      });
      D.personen = D.personen.filter((p) => p.id !== q); return fertig();
    },
    preis_bild_setzen: (name, url) => {
      if (!/^data:image\/(jpeg|png);base64,/.test(url || "")) fehler("Das ist kein gültiges Bild.");
      if (!(name || "").trim()) fehler("Der Preisname fehlt.");
      D.bilder[normName(name)] = url; D.bilder_version++; return fertig();
    },
    preis_bild_entfernen: (name) => { delete D.bilder[normName(name)]; D.bilder_version++; return fertig(); },
    bilder: () => Object.assign({}, D.bilder),
    regel_hinzufuegen: (titel, text, w) => {
      titel = (titel || "").trim(); if (!titel) fehler("Die Folie braucht einen Titel.");
      D.regeln.push({ id: nid("r"), titel, text: (text || "").trim(), wuerfel: w || null }); return fertig();
    },
    regel_bearbeiten: (id, titel, text, w) => {
      const r = D.regeln.find((x) => x.id === id); if (!r) fehler("Diese Folie existiert nicht.");
      titel = (titel || "").trim(); if (!titel) fehler("Die Folie braucht einen Titel.");
      Object.assign(r, { titel, text: (text || "").trim(), wuerfel: w || null }); return fertig();
    },
    regel_loeschen: (id) => {
      D.regeln = D.regeln.filter((x) => x.id !== id);
      if (D.regel_index >= D.regeln.length) D.regel_index = 0;
      return fertig();
    },
    regel_verschieben: (id, richtung) => {
      const i = D.regeln.findIndex((x) => x.id === id), j = i + (richtung > 0 ? 1 : -1);
      if (i < 0) fehler("Diese Folie existiert nicht.");
      if (j >= 0 && j < D.regeln.length) [D.regeln[i], D.regeln[j]] = [D.regeln[j], D.regeln[i]];
      return fertig();
    },
    regeln_intervall_setzen: (sek) => {
      sek = +sek; if (!(sek >= 5 && sek <= 120)) fehler("Das Intervall muss zwischen 5 und 120 Sekunden liegen.");
      D.regeln_intervall = Math.round(sek); return fertig();
    },
    regel_folie: (ziel) => {
      const n = D.regeln.length; if (!n) fehler("Es gibt noch keine Regel-Folien.");
      if (ziel === "vor") D.regel_index = (D.regel_index + 1) % n;
      else if (ziel === "zurueck") D.regel_index = (D.regel_index - 1 + n) % n;
      else D.regel_index = Math.max(0, Math.min(n - 1, +ziel || 0));
      D.regel_nonce++; return fertig();
    },
    demo_starten: (art) => {
      if (art !== "erfunden" && art !== "kopie") fehler("Unbekannte Demo-Art.");
      D.demo = { aktiv: true, art }; return fertig();
    },
    demo_beenden: () => { D.demo = { aktiv: false, art: "erfunden" }; return fertig(); },
    demo_zuruecksetzen: () => {
      if (!D.demo.aktiv) fehler("Der Demo-Modus ist nicht aktiv.");
      const b = D.bilder, bv = D.bilder_version + 1, demo = D.demo;
      D.personen = []; D.spiele = []; D.sonderrunde = null; D.jahr = 2025;
      aufbauen(); D.spiele.forEach((sp) => sp.siege.forEach((x) => { if (!x.id) x.id = "s" + (idz++); }));
      D.bilder = b; D.bilder_version = bv; D.demo = demo; return fertig();
    },
    beamer_ansicht_setzen: (a) => { if (a !== "spiel" && a !== "statistik" && a !== "regeln") fehler("Unbekannte Beamer-Ansicht."); D.ansicht = a; return fertig(); },
    beamer_design_setzen: (d) => { if (d !== "hell" && d !== "dunkel") fehler("Unbekanntes Beamer-Design."); D.design = d; return fertig(); },
    beamer_bildschirm_wechseln: () => fehler("Demo-Modus: kein Beamer-Fenster."),
    beamer_oeffnen: () => fehler("Demo-Modus: kein Beamer-Fenster."),
    excel_vorschau_waehlen: () => ({
      pfad: "C:\\Demo\\Paschen-Alt.xlsx",
      vorschau: { jahre: [
        { jahr: 2025, personen: 26, siege: 63, preise: [{ name: "Wurst", menge: 30, vergeben: 30 }, { name: "Teig", menge: 15, vergeben: 15 }, { name: "Sachpreis", menge: 30, vergeben: 18 }], menge_gesamt: 75, existiert: true, live_siege: 3, warnungen: ["Menge für „Sachpreis“ fehlt in der Tabelle, es wurde die Summe der Siege genommen."] },
        { jahr: 2021, personen: 22, siege: 50, preise: [{ name: "Wurst", menge: 30, vergeben: 30 }, { name: "Teig", menge: 20, vergeben: 20 }], menge_gesamt: 50, existiert: false, warnungen: [] },
      ] },
    }),
    excel_vorschau: (p) => roh.excel_vorschau_waehlen(),
    excel_importieren: () => { const z = fertig(); z["import"] = { jahre: [2021], demo: true }; return z; },
    excel_exportieren: () => ({ gespeichert: "C:\\Demo\\Paschen-Auswertung.xlsx" }),
  };

  // Alle Methoden wie pywebview: asynchron, Fehler als {fehler}
  const api = {};
  Object.keys(roh).forEach((k) => {
    api[k] = async (...a) => {
      try { return roh[k](...a); } catch (e) { return { fehler: e.message }; }
    };
  });

  // Hilfen nur fuer die Vorfuehrung (beamer.html?ansicht=...)
  api._vorfuehren = function (modus) {
    const s = spiel();
    if (modus === "statistik") D.ansicht = "statistik";
    if (modus === "regeln") D.ansicht = "regeln";
    if (modus === "sonderrunde") {
      s.preise.filter((p) => !p.spezial).forEach((p) => { for (let i = rest(s, p.id); i > 0; i--) s.siege.push({ nr: s.siege.length + 1, person_id: s.anwesende_ids[i % 20], preis_id: p.id, sonderrunde: false, importiert: false }); });
      D.sonderrunde = "sp1";
    }
    if (modus === "ende") {
      s.preise.forEach((p) => { for (let i = rest(s, p.id); i > 0; i--) s.siege.push({ nr: s.siege.length + 1, person_id: s.anwesende_ids[Math.floor(Math.pow(Math.random(), 1.7) * 20)], preis_id: p.id, sonderrunde: p.spezial, importiert: false }); });
    }
    if (modus === "phasenwechsel") D.ereignis = { typ: "phasenwechsel", von_name: "Wurst & Teigwaren", nach_name: "Werbegeschenke", id: 1 };
    if (modus === "sieg") D.ereignis = Object.assign(siegDict(s, s.siege[s.siege.length - 1]), { typ: "sieg", folge: null, id: 1 });
    const z = zustand(true);
    D.ereignis = null;
    return z;
  };
  api._kanal = kanal;
  api._bilder = () => Object.assign({}, D.bilder);

  window.MockApi = api;
})();
