// BürgerAI Web-Oberfläche (Phase 2, ohne LLM). Kein Framework, keine externen Dateien.
"use strict";

// Muss zu buergerai.__version__ passen (Test: tests/test_web.py); sonst warnt die Seite
const VERSION = "0.6.0";
const SPEICHER = "buergerai.v1";
const ERGEBNIS_TEXT = { ja: "Ja", unklar: "Unklar", nein: "Nein" };
const SYMBOL = { ja: "✓", unklar: "?", nein: "✗" };
const GRUPPEN = [
  ["ja", "Das steht Ihnen voraussichtlich zu / ist zu erledigen"],
  ["unklar", "Unklar – fehlende Angaben oder Prüfung nötig"],
  ["nein", "Voraussichtlich kein Anspruch / nicht nötig"],
];

const zustand = {
  ort: null,            // {plz, gemeinde, land}
  stichtag: null,       // "JJJJ-MM-TT" oder null = heute
  lebenslagen: null,    // Liste von IDs oder null = Standard des Servers (Geburt)
  fakten: {},           // id -> Wert (true/false, Zahl, "JJJJ-MM-TT", Auswahlwert, "unbekannt")
  erledigt: {},         // leistung_id -> true
  bearbeiten: null,     // Fakt-ID, die gerade geändert wird
  pausiert: false,      // Fragen ausgeblendet ("nur Ergebnis")
};
let bericht = null;
let meta = null;
let anfrageNr = 0;  // nur die Antwort auf die jüngste Anfrage wird angezeigt

// ------------------------------------------------------------------ Helfer
const $ = (sel) => document.querySelector(sel);

function el(tag, attrs = {}, ...kinder) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kinder.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return e;
}

// Setzt den Inhalt eines Elements. Leere Teile (null, undefined, false) werden
// entfernt, sonst würde replaceChildren sie als Text "null" anzeigen.
function fuellen(ziel, ...kinder) {
  ziel.replaceChildren(...kinder.flat(Infinity).filter((k) => k !== null && k !== undefined && k !== false));
}

function datumText(iso) {
  if (!iso) return "";
  const [j, m, t] = iso.split("-");
  return `${t}.${m}.${j}`;
}

function sicherLink(url, text) {
  // Nur http(s)-Links aus der Wissensbasis anzeigen
  if (!/^https?:\/\//i.test(url || "")) return document.createTextNode(text || url || "");
  return el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text || url);
}

function speichern() {
  try {
    localStorage.setItem(SPEICHER, JSON.stringify({
      ort: zustand.ort, stichtag: zustand.stichtag, lebenslagen: zustand.lebenslagen,
      fakten: zustand.fakten, erledigt: zustand.erledigt,
    }));
  } catch (_) { /* privater Modus: dann eben ohne Speichern */ }
}

function speicherLoeschen() {
  try { localStorage.removeItem(SPEICHER); } catch (_) { /* ignorieren */ }
}

function ladenAusSpeicher() {
  try {
    const roh = JSON.parse(localStorage.getItem(SPEICHER) || "null");
    if (roh && roh.ort) Object.assign(zustand, roh);
  } catch (_) { /* ignorieren */ }
}

function meldung(text) {
  const m = $("#meldung");
  m.textContent = text || "";
  m.hidden = !text;
  if (text) m.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function api(pfad, daten) {
  const opt = daten === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(daten),
  };
  const antwort = await fetch(pfad, opt);
  const typ = antwort.headers.get("Content-Type") || "";
  const inhalt = typ.includes("json") ? await antwort.json() : await antwort.text();
  if (!antwort.ok) {
    const fehler = new Error((inhalt && inhalt.fehler) || `Fehler ${antwort.status}`);
    fehler.status = antwort.status;
    fehler.daten = inhalt;
    throw fehler;
  }
  return inhalt;
}

// ------------------------------------------------------------------ Lebenslagen
function lebenslagenAuswahl(ziel, gewaehlt, beiAenderung) {
  const legende = ziel.querySelector("legend");
  fuellen(ziel, legende, ...meta.lebenslagen.map((l) => el("label", {},
    el("input", {
      type: "checkbox", name: "lebenslage", value: l.id, checked: gewaehlt.includes(l.id),
      onchange: beiAenderung || null,
    }),
    el("span", {}, el("strong", {}, l.name), el("br"), el("span", { class: "leise" }, l.beschreibung)),
  )));
}

function gewaehlteLebenslagen(ziel) {
  return [...ziel.querySelectorAll("input[name=lebenslage]:checked")].map((e) => e.value);
}

function anfrage() {
  const daten = { ...zustand.ort, stichtag: zustand.stichtag, fakten: zustand.fakten };
  if (zustand.lebenslagen && zustand.lebenslagen.length) daten.lebenslagen = zustand.lebenslagen;
  return daten;
}

function download(name, inhalt, typ) {
  const url = URL.createObjectURL(new Blob([inhalt], { type: typ }));
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ------------------------------------------------------------------ Schritt 1: Wohnort
async function ortAbsenden(ev) {
  if (ev) ev.preventDefault();
  meldung("");
  const plz = $("#plz").value.trim();
  const daten = { plz };
  if (!$("#gemeinde-wahl").hidden && $("#gemeinde").value) daten.gemeinde = $("#gemeinde").value;
  if (!$("#land-wahl").hidden && $("#land").value) daten.land = $("#land").value;
  const lagen = gewaehlteLebenslagen($("#lebenslagen-wahl"));
  if (!lagen.length) {
    meldung("Bitte mindestens eine Lebenslage wählen.");
    return;
  }
  if (!/^\d{5}$/.test(plz)) {
    meldung("Bitte eine fünfstellige Postleitzahl eingeben.");
    $("#plz").focus();
    return;
  }
  try {
    await api("/api/ort", daten);
    zustand.ort = { plz, gemeinde: daten.gemeinde || null, land: daten.land || null };
    zustand.lebenslagen = lagen;
    zustand.fakten = {};
    zustand.erledigt = {};
    zustand.bearbeiten = null;
    zustand.pausiert = false;
    await aktualisieren();
  } catch (e) {
    if (e.daten && e.daten.status === "mehrdeutig") {
      const s = $("#gemeinde");
      fuellen(s,
        el("option", { value: "" }, `Bitte wählen (${e.daten.gemeinden.length} Gemeinden) …`),
        ...e.daten.gemeinden.map((g) => el("option", { value: g.id }, g.kreis ? `${g.name} – ${g.kreis}` : g.name)),
      );
      $("#gemeinde-wahl").hidden = false;
      s.focus();
    } else if (e.daten && e.daten.status === "unbekannt") {
      $("#land-text").textContent = e.daten.fehler;
      const s = $("#land");
      fuellen(s,
        el("option", { value: "" }, "Bitte wählen …"),
        ...e.daten.laender.map((l) => el("option", { value: l.kuerzel }, l.name)),
      );
      $("#land-wahl").hidden = false;
      s.focus();
    } else {
      meldung(e.message);
    }
  }
}

function startZuruecksetzen() {
  $("#gemeinde-wahl").hidden = true;
  $("#land-wahl").hidden = true;
}

async function szenarioLaden() {
  const id = $("#szenario").value;
  if (!id) return;
  meldung("");
  try {
    const s = await api(`/api/szenario/${encodeURIComponent(id)}`);
    angabenUebernehmen(s);
  } catch (e) {
    meldung(e.message);
  }
}

function angabenUebernehmen(s) {
  if (!s || typeof s !== "object" || !(s.plz || s.gemeinde || s.land)) {
    meldung("Die Datei enthält keinen Wohnort (plz, gemeinde oder land).");
    return;
  }
  zustand.ort = { plz: s.plz || null, gemeinde: s.gemeinde || null, land: s.land || null };
  zustand.stichtag = s.stichtag || null;
  zustand.lebenslagen = Array.isArray(s.lebenslagen) && s.lebenslagen.length ? s.lebenslagen : null;
  zustand.fakten = (s.fakten && typeof s.fakten === "object") ? s.fakten : {};
  zustand.erledigt = {};
  zustand.bearbeiten = null;
  zustand.pausiert = false;
  aktualisieren();
}

function dateiLaden(ev) {
  const datei = ev.target.files && ev.target.files[0];
  ev.target.value = "";
  if (!datei) return;
  datei.text().then((t) => {
    try {
      angabenUebernehmen(JSON.parse(t));
    } catch (_) {
      meldung("Die Datei ist kein gültiges JSON.");
    }
  });
}

// ------------------------------------------------------------------ Bericht holen
async function aktualisieren() {
  if (!zustand.ort) {
    $("#start").hidden = false;
    $("#arbeit").hidden = true;
    return;
  }
  const nr = ++anfrageNr;
  let neu;
  try {
    neu = await api("/api/bericht", anfrage());
  } catch (e) {
    if (nr !== anfrageNr) return;  // veraltete Antwort verwerfen
    meldung(e.message);
    if (!bericht) {
      // Ungültiger gespeicherter Zustand: zurück zum Start
      zustand.ort = null;
      speicherLoeschen();
      $("#start").hidden = false;
      $("#arbeit").hidden = true;
    }
    return;
  }
  if (nr !== anfrageNr) return;  // inzwischen wurde neu gefragt: veraltete Antwort verwerfen
  bericht = neu;
  meldung("");
  speichern();
  $("#start").hidden = true;
  $("#arbeit").hidden = false;
  zeichnen();
}

function antworten(fid, wert) {
  zustand.fakten[fid] = wert;
  if (zustand.bearbeiten === fid) zustand.bearbeiten = null;
  aktualisieren().then(() => {
    const karte = $("#frage-karte");
    const ziel = karte.querySelector("button, input, select");
    if (ziel && window.matchMedia("(min-width: 861px)").matches) ziel.focus({ preventScroll: true });
  });
}

// ------------------------------------------------------------------ Zeichnen
function zeichnen() {
  $("#ort-text").textContent = bericht.ort.text;
  $("#stichtag-zeile").textContent = zustand.stichtag
    ? `Simuliertes Datum: ${datumText(zustand.stichtag)}`
    : `Stand: heute, ${datumText(bericht.stichtag)}`;
  $("#stichtag").value = bericht.stichtag;
  const namen = bericht.lebenslagen.map((l) => l.name).join(", ");
  $("#lebenslage-text").textContent = namen;
  $("#titel").textContent = (bericht.lebenslagen.length > 1 ? "Lebenslagen " : "Lebenslage ") + namen;
  lebenslagenAuswahl($("#lebenslagen-wahl-arbeit"), bericht.lebenslagen.map((l) => l.id), () => {
    const lagen = gewaehlteLebenslagen($("#lebenslagen-wahl-arbeit"));
    if (!lagen.length) {
      meldung("Bitte mindestens eine Lebenslage wählen.");
      return;
    }
    zustand.lebenslagen = lagen;
    aktualisieren();
  });
  $("#kind-text").textContent = bericht.kind ? `Kind: ${bericht.kind}` : "";
  $("#kind-text").hidden = !bericht.kind;
  zeichneFrage();
  zeichneAngaben();
  zeichneErgebnis();
}

function frageAktuell() {
  if (zustand.bearbeiten) {
    const a = bericht.angaben.find((x) => x.id === zustand.bearbeiten);
    if (a) return a;
    zustand.bearbeiten = null;
  }
  if (zustand.pausiert) return null;
  return bericht.fragen[0] || null;
}

function zeichneFrage() {
  const karte = $("#frage-karte");
  const f = frageAktuell();
  const offen = bericht.fragen.length;
  if (!f) {
    if (offen && zustand.pausiert) {
      fuellen(karte,
        el("p", {}, `Noch ${offen} Frage${offen === 1 ? "" : "n"} offen. Mit diesen Angaben werden unklare Punkte genauer.`),
        el("button", { type: "button", class: "primaer", onclick: () => { zustand.pausiert = false; zeichnen(); } }, "Fragen fortsetzen"),
      );
    } else {
      fuellen(karte,
        el("p", { class: "fertig-box" }, "✓ Alle nötigen Angaben sind gemacht."),
        el("p", { class: "leise" }, "Was jetzt noch unklar ist, kann nur die zuständige Stelle entscheiden. Angaben lassen sich unten jederzeit ändern."),
      );
    }
    return;
  }
  const bearbeiten = zustand.bearbeiten === f.id;
  const kopf = [
    el("p", { class: "fortschritt" }, bearbeiten ? "Angabe ändern" : `Noch ${offen} offene Frage${offen === 1 ? "" : "n"} – die Liste passt sich Ihren Antworten an`),
    f.person_name ? el("span", { class: "person" }, f.person_name) : null,
    el("h2", { id: "frage-titel" }, f.typ === "datum" ? f.frage.replace(/\s*\(TT\.MM\.JJJJ\)/, "") : f.frage),
    f.hilfe ? el("p", { class: "leise" }, f.hilfe) : null,
  ];
  const aktuell = bearbeiten ? f.wert : undefined;
  const fuss = el("div", { class: "frage-fuss" },
    el("button", { type: "button", onclick: () => antworten(f.id, "unbekannt") }, "Weiß nicht"),
    bearbeiten
      ? el("button", { type: "button", class: "link", onclick: () => { zustand.bearbeiten = null; zeichnen(); } }, "Abbrechen")
      : el("button", { type: "button", class: "link", onclick: () => { zustand.pausiert = true; zeichnen(); } }, "Fragen beenden, nur Ergebnis"),
  );
  fuellen(karte, kopf, eingabe(f, aktuell), fuss);
}

function eingabe(f, aktuell) {
  if (f.typ === "ja_nein") {
    return el("div", { class: "optionen zwei" },
      el("button", { type: "button", "aria-pressed": String(aktuell === true), onclick: () => antworten(f.id, true) }, "Ja"),
      el("button", { type: "button", "aria-pressed": String(aktuell === false), onclick: () => antworten(f.id, false) }, "Nein"),
    );
  }
  if (f.typ === "auswahl") {
    return el("div", { class: "optionen", role: "group", "aria-label": f.frage },
      f.optionen.map((o) => el("button", {
        type: "button", "aria-pressed": String(aktuell === o.wert), onclick: () => antworten(f.id, o.wert),
      }, o.text)),
    );
  }
  const istDatum = f.typ === "datum";
  const feld = el("input", {
    id: "frage-eingabe",
    type: istDatum ? "date" : (f.typ === "zahl" ? "number" : "text"),
    inputmode: f.typ === "zahl" ? "decimal" : (f.typ === "ort" ? "numeric" : null),
    maxlength: f.typ === "ort" ? "8" : null,
    placeholder: f.typ === "ort" ? "z. B. 80331" : null,
    min: f.typ === "zahl" ? "0" : null,
    step: f.typ === "zahl" ? "any" : null,
    "aria-labelledby": "frage-titel",
    required: true,
  });
  if (aktuell !== undefined && aktuell !== "unbekannt") feld.value = String(aktuell);
  const form = el("form", { class: "zeile optionen-form", novalidate: true }, feld,
    el("button", { type: "submit", class: "primaer" }, "Weiter"));
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const roh = feld.value.trim();
    if (!roh) { meldung("Bitte einen Wert eingeben oder „Weiß nicht“ wählen."); feld.focus(); return; }
    if (f.typ === "zahl") {
      const zahl = Number(roh);
      if (!Number.isFinite(zahl) || zahl < 0) { meldung("Bitte eine Zahl ab 0 eingeben."); feld.focus(); return; }
      antworten(f.id, zahl);
    } else if (f.typ === "ort") {
      if (!/^(\d{5}|\d{8})$/.test(roh)) { meldung("Bitte eine fünfstellige Postleitzahl eingeben."); feld.focus(); return; }
      antworten(f.id, roh);
    } else if (istDatum) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(roh)) { meldung("Bitte ein gültiges Datum wählen."); feld.focus(); return; }
      antworten(f.id, roh);
    } else {
      antworten(f.id, roh);
    }
  });
  return el("div", { class: "optionen" }, form);
}

function zeichneAngaben() {
  const liste = $("#angaben");
  if (!bericht.angaben.length) {
    fuellen(liste, el("li", { class: "leise" }, "Noch keine Angaben."));
    return;
  }
  fuellen(liste, ...bericht.angaben.map((a) => el("li", { class: a.aktiv ? null : "inaktiv" },
    el("span", {}, a.frage, a.aktiv ? null : el("span", { class: "leise" }, " (nicht mehr relevant)")),
    el("span", { class: "rechts" },
      el("span", { class: "wert" }, a.wert === "unbekannt" ? "weiß nicht" : a.anzeige),
      el("button", {
        type: "button", class: "link", "aria-label": `Ändern: ${a.frage}`,
        onclick: () => { zustand.bearbeiten = a.id; zeichnen(); $("#frage-karte").scrollIntoView({ behavior: "smooth", block: "nearest" }); },
      }, "ändern"),
    ),
  )));
}

function zeichneErgebnis() {
  fuellen($("#warnungen"), ...bericht.warnungen.map((w) => el("li", {}, "⚠ ", w)));
  const fehlt = bericht.nicht_erfasst;
  $("#nicht-erfasst-box").hidden = fehlt.length === 0;
  fuellen($("#nicht-erfasst"), ...fehlt.map((n) => el("li", {}, el("strong", {}, n.name),
    bericht.lebenslagen.length > 1 ? ` (${n.lebenslage})` : "", " – ", n.grund)));
  const andere = bericht.nur_andere_laender;
  $("#andere-laender").hidden = andere.length === 0;
  $("#andere-laender").textContent = andere.length
    ? "Nur in anderen Ländern (hier nicht verfügbar): " + andere.map((a) => `${a.name} (${a.laender.join(", ")})`).join("; ")
    : "";
  fuellen($("#zaehler"), ...GRUPPEN.map(([w]) =>
    el("span", { class: `chip ${w}` }, `${bericht.zaehler[w]} × ${ERGEBNIS_TEXT[w]}`)));

  const plan = bericht.zeitplan;
  $("#zeitplan-box").hidden = plan.length === 0;
  fuellen($("#zeitplan"), ...plan.map((t) => el("li", {
    class: [t.abgelaufen ? "abgelaufen" : "", t.bald ? "bald" : "", zustand.erledigt[t.leistung_id] ? "erledigt" : ""].join(" ").trim() || null,
  },
  el("span", { class: "datum" }, datumText(t.datum)),
  el("span", {}, el("strong", {}, t.leistung), ` – ${t.art_text}`, t.voraussichtlich ? " (voraussichtlich)" : "",
    t.abgelaufen ? " – abgelaufen" : "", t.ergebnis === "unklar" ? " · Anspruch unklar" : "",
    el("br"), el("span", { class: "leise" }, t.text)),
  )));

  const box = $("#leistungen");
  fuellen(box);
  for (const [wert, titel] of GRUPPEN) {
    const eintraege = bericht.leistungen.filter((l) => l.ergebnis === wert);
    if (!eintraege.length) continue;
    const karten = eintraege.map(leistungKarte);
    if (wert === "nein") {
      box.append(el("section", { class: "gruppe" },
        el("details", {}, el("summary", {}, `${titel} (${eintraege.length})`), karten)));
    } else {
      box.append(el("section", { class: "gruppe" }, el("h3", {}, `${titel} (${eintraege.length})`), karten));
    }
  }
}

function fristZeile(fr) {
  if (!fr.datum) {
    return el("li", {}, fr.text, fr.braucht_datum ? el("span", { class: "leise" }, " (Datum fehlt für die Berechnung)") : null);
  }
  const zusatz = [];
  if (fr.voraussichtlich) zusatz.push("voraussichtlich");
  if (fr.tage_bis < 0) zusatz.push(`vor ${-fr.tage_bis} Tagen`);
  else if (fr.tage_bis === 0) zusatz.push("heute");
  else zusatz.push(`in ${fr.tage_bis} Tagen`);
  return el("li", { class: fr.abgelaufen ? "abgelaufen" : (fr.bald ? "bald" : null) },
    el("strong", {}, `${fr.art_text} ${datumText(fr.datum)}`), ` (${zusatz.join(", ")})`,
    fr.abgelaufen ? " – ABGELAUFEN" : "", `: ${fr.text}`);
}

function gruendeListe(gruende) {
  if (!gruende.length) return el("ul", { class: "gruende" }, el("li", { class: "ja" }, el("span", { class: "sym" }, "✓"), "Keine besonderen Voraussetzungen"));
  return el("ul", { class: "gruende" }, gruende.map((g) => el("li", { class: g.ergebnis },
    el("span", { class: "sym", "aria-label": ERGEBNIS_TEXT[g.ergebnis] }, g.art === "pruefung_noetig" ? "!" : SYMBOL[g.ergebnis]),
    g.art === "pruefung_noetig" ? `Prüfung nötig: ${g.text}` : g.text,
    g.fehlt ? el("span", { class: "angabe" }, ` – Angabe fehlt: ${g.fehlt}`) : null,
    g.angabe ? el("span", { class: "angabe" }, ` – Ihre Angabe: ${g.angabe === "unbekannt" ? "weiß nicht" : g.angabe}`) : null,
  )));
}

function leistungKarte(l) {
  const relevant = l.ergebnis !== "nein";
  const erledigt = !!zustand.erledigt[l.id];
  const cbId = `erledigt-${l.id}`;
  const fakten = [];
  const zeile = (dt, ...dd) => fakten.push(el("dt", {}, dt), el("dd", {}, ...dd));
  const mehrPersonen = l.personen.length > 1 || l.personen[0].person !== null;
  if (bericht.lebenslagen.length > 1 && l.lebenslagen.length) {
    zeile("Lebenslage", l.lebenslagen.map((id) => (bericht.lebenslagen.find((x) => x.id === id) || { name: id }).name).join(", "));
  }
  if (mehrPersonen) {
    zeile("Für", l.personen.map((p, i) => [i ? ", " : "", `${p.name}: `, el("span", { class: `badge ${p.ergebnis}` }, ERGEBNIS_TEXT[p.ergebnis])]));
  }
  if (l.beantragt_hinweis) zeile("Wer beantragt", l.beantragt_hinweis);
  zeile("Zuständig", l.zustaendigkeit.url ? sicherLink(l.zustaendigkeit.url, l.zustaendigkeit.name) : l.zustaendigkeit.name,
    l.zustaendigkeit.beschreibung ? el("div", { class: "leise" }, l.zustaendigkeit.beschreibung) : null);
  if (l.betrag && relevant) zeile("Betrag", l.betrag);
  if (relevant && l.fristen.length) zeile(l.fristen.length > 1 ? "Fristen" : "Frist", el("ul", {}, l.fristen.map(fristZeile)));
  if (relevant && l.voraussetzungen.length) zeile("Vorher erledigen", l.voraussetzungen.join(", "));

  const titel = { ja: "Warum?", unklar: "Warum unklar?", nein: "Warum nicht?" }[l.ergebnis];
  const warum = el("details", { open: l.ergebnis === "unklar" },
    el("summary", {}, titel),
    l.personen.map((p) => [mehrPersonen && l.personen.length > 1 ? el("p", { class: "person-titel" }, p.name) : null, gruendeListe(p.gruende)]));

  const v = l.verfahren;
  const teile = [];
  if (relevant && v.unterlagen.length) {
    teile.push(el("details", {}, el("summary", {}, `Unterlagen (${v.unterlagen.length})`), el("ul", {}, v.unterlagen.map((u) => el("li", {}, u)))));
  }
  if (relevant && (v.schritte.length || v.kosten || v.online_url || v.hinweise.length)) {
    teile.push(el("details", {}, el("summary", {}, "So geht's"),
      v.schritte.length ? el("ol", {}, v.schritte.map((s) => el("li", {}, s))) : null,
      v.kosten ? el("p", {}, el("strong", {}, "Kosten: "), v.kosten) : null,
      v.online_url ? el("p", {}, el("strong", {}, "Online: "), sicherLink(v.online_url)) : null,
      v.hinweise.map((h) => el("p", { class: "hinweis" }, h)),
    ));
  }
  teile.push(el("details", {}, el("summary", {}, "Quellen und Datenstand"),
    el("p", { class: "status" }, `Daten: ${l.gebiet.ebene_text} ${l.gebiet.name} · ${l.abdeckung_text} · ${l.pruef_text}`),
    el("ul", { class: "quellen" }, l.quellen.map((q) => el("li", {},
      q.url ? sicherLink(q.url, q.titel) : q.titel, el("span", { class: "status" }, ` [${q.pruefstatus}]`),
      q.seit_pruefung_geaendert
        ? el("span", { class: "status geaendert" }, ` seit Prüfung geändert (festgestellt am ${datumText(q.seit_pruefung_geaendert)})`)
        : null))),
  ));

  return el("article", { class: `karte leistung ${l.ergebnis}${erledigt ? " erledigt" : ""}`, id: `leistung-${l.id}` },
    el("div", { class: "leistung-kopf" },
      relevant ? el("input", {
        type: "checkbox", id: cbId, checked: erledigt, "aria-label": `${l.name} erledigt`,
        onchange: (ev) => {
          if (ev.target.checked) zustand.erledigt[l.id] = true; else delete zustand.erledigt[l.id];
          speichern();
          zeichneErgebnis();
        },
      }) : null,
      el("h4", {}, relevant ? el("label", { for: cbId }, l.name) : l.name),
      el("span", { class: `badge ${l.ergebnis}` }, ERGEBNIS_TEXT[l.ergebnis]),
    ),
    el("p", { class: "kurz" }, l.kurz),
    l.anspruch_hinweis ? el("p", { class: "hinweis" }, el("strong", {}, "Hinweis: "), l.anspruch_hinweis) : null,
    el("dl", { class: "fakten-liste" }, fakten),
    l.hinweise.map((h) => el("p", { class: "hinweis" }, el("strong", {}, "Hinweis: "), h)),
    warum,
    teile,
  );
}

// ------------------------------------------------------------------ Werkzeuge
async function kalender() {
  try {
    const antwort = await fetch("/api/kalender", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(anfrage()),
    });
    if (!antwort.ok) {
      const istJson = (antwort.headers.get("Content-Type") || "").includes("json");
      throw new Error((istJson && (await antwort.json()).fehler) || `Fehler ${antwort.status}`);
    }
    download("buergerai-fristen.ics", await antwort.text(), "text/calendar");
  } catch (e) {
    meldung(e.message);
  }
}

function angabenSpeichern() {
  // Gleiches Format wie szenarien/*.json: im Terminal mit ./bai pruefen -s datei.json nutzbar
  const daten = { name: "Eigene Angaben", beschreibung: `Gespeichert am ${datumText(new Date().toISOString().slice(0, 10))}` };
  for (const k of ["plz", "gemeinde", "land"]) if (zustand.ort[k]) daten[k] = zustand.ort[k];
  daten.stichtag = bericht.stichtag;
  daten.lebenslagen = bericht.lebenslagen.map((l) => l.id);
  daten.fakten = zustand.fakten;
  download("buergerai-angaben.json", JSON.stringify(daten, null, 2) + "\n", "application/json");
}

function drucken() {
  const zu = [...document.querySelectorAll("#leistungen details:not([open])")];
  zu.forEach((d) => { d.open = true; });
  window.print();
  zu.forEach((d) => { d.open = false; });
}

function neuBeginnen() {
  if (!confirm("Alle Angaben löschen und neu beginnen?")) return;
  zustand.ort = null;
  zustand.fakten = {};
  zustand.erledigt = {};
  zustand.stichtag = null;
  zustand.lebenslagen = null;
  zustand.bearbeiten = null;
  zustand.pausiert = false;
  bericht = null;
  speicherLoeschen();
  startZuruecksetzen();
  $("#plz").value = "";
  aktualisieren();
  $("#plz").focus();
}

// ------------------------------------------------------------------ Start
async function init() {
  $("#ort-form").addEventListener("submit", ortAbsenden);
  $("#plz").addEventListener("input", startZuruecksetzen);
  $("#gemeinde").addEventListener("change", () => { if ($("#gemeinde").value) ortAbsenden(); });
  $("#land").addEventListener("change", () => { if ($("#land").value) ortAbsenden(); });
  $("#szenario-laden").addEventListener("click", szenarioLaden);
  $("#szenario").addEventListener("change", () => {
    const s = meta && meta.szenarien.find((x) => x.id === $("#szenario").value);
    $("#szenario-text").textContent = s ? s.beschreibung : "";
  });
  $("#datei-laden").addEventListener("change", dateiLaden);
  $("#datei-laden-start").addEventListener("change", dateiLaden);
  $("#kalender").addEventListener("click", kalender);
  $("#drucken").addEventListener("click", drucken);
  $("#speichern").addEventListener("click", angabenSpeichern);
  $("#neu").addEventListener("click", neuBeginnen);
  $("#stichtag").addEventListener("change", () => {
    const v = $("#stichtag").value;
    zustand.stichtag = v && v !== (meta && meta.heute) ? v : null;
    aktualisieren();
  });
  $("#stichtag-heute").addEventListener("click", () => { zustand.stichtag = null; aktualisieren(); });

  try {
    meta = await api("/api/meta");
    $("#version").textContent = `Version ${VERSION}`;
    if (meta.version !== VERSION) {
      meldung(`Diese Seite (Version ${VERSION}) passt nicht zum Server (Version ${meta.version}). Bitte neu laden: Strg+Umschalt+R bzw. Cmd+Umschalt+R.`);
    }
    lebenslagenAuswahl($("#lebenslagen-wahl"), []);
    fuellen($("#szenario"), el("option", { value: "" }, "Beispiel wählen …"),
      ...meta.szenarien.map((s) => el("option", { value: s.id }, s.name)));
  } catch (e) {
    meldung("Server nicht erreichbar. Läuft „./bai web“?");
    return;
  }
  ladenAusSpeicher();
  aktualisieren();
}

document.addEventListener("DOMContentLoaded", init);
