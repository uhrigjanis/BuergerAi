// Fragen (#86): Begründung je Frage ("Entscheidet über"), Fortschritt als Anteil geklärter
// Leistungen, Änderungen nach einer Antwort. Mit LLM auch Antworten in eigenen Worten (#79).
import {
  $, ERGEBNIS_TEXT, anfrage, anzahl, api, ausloesen, el, fuellen, meldung, sitzung, zustand,
} from "./gemeinsam.js";
import { markierterText, vorschlagsliste } from "./vorschlaege.js";

function frageAktuell() {
  const b = sitzung.bericht;
  if (zustand.bearbeiten) {
    const a = b.angaben.find((x) => x.id === zustand.bearbeiten);
    if (a) return a;
    zustand.bearbeiten = null;
  }
  if (zustand.fokusFrage) {
    const f = b.fragen.find((x) => x.id === zustand.fokusFrage);
    if (f) return f;
    zustand.fokusFrage = null;
  }
  if (zustand.pausiert) return null;
  return b.fragen[0] || null;
}

export function antworten(fid, wert) {
  zustand.fakten[fid] = wert;
  if (zustand.bearbeiten === fid) zustand.bearbeiten = null;
  if (zustand.fokusFrage === fid) zustand.fokusFrage = null;
  ausloesen("aktualisieren", { fokus: true, vergleich: true });
}

export function uebernehmen(werte) {
  Object.assign(zustand.fakten, werte);
  zustand.bearbeiten = null;
  zustand.fokusFrage = null;
  ausloesen("aktualisieren", { fokus: true, vergleich: true });
}

// Wie viele Leistungen sind schon entschieden (Ja oder Nein)?
export function fortschritt(b) {
  const gesamt = b.leistungen.length;
  const geklaert = b.leistungen.filter((l) => l.ergebnis !== "unklar").length;
  return { gesamt, geklaert, unklar: gesamt - geklaert };
}

function fortschrittElement() {
  const { gesamt, geklaert, unklar } = fortschritt(sitzung.bericht);
  if (!gesamt) return null;
  return el("div", { class: "fortschritt-box" },
    el("label", { for: "fortschritt-balken" },
      `${geklaert} von ${anzahl(gesamt, "Leistung", "Leistungen")} geklärt`,
      unklar ? el("span", { class: "leise" }, `, ${unklar} noch unklar`) : null),
    el("progress", { id: "fortschritt-balken", max: String(gesamt), value: String(geklaert) }));
}

function betrifftElement(f) {
  if (!f.betrifft || !f.betrifft.length) return null;
  const anspruch = f.betrifft.filter((x) => x.art === "anspruch");
  const frist = f.betrifft.filter((x) => x.art === "frist");
  const namen = (liste) => {
    const n = liste.slice(0, 4).map((x) => x.name);
    return liste.length > 4 ? `${n.join(", ")} und ${liste.length - 4} weitere` : n.join(", ");
  };
  return el("div", { class: "betrifft" },
    anspruch.length ? el("p", {}, el("span", { class: "leise" }, "Entscheidet über "), namen(anspruch)) : null,
    frist.length ? el("p", {}, el("span", { class: "leise" }, "Legt Fristen fest für "), namen(frist)) : null);
}

export function zeichneFrage() {
  const karte = $("#frage-karte");
  const b = sitzung.bericht;
  const f = frageAktuell();
  const offen = b.fragen.length;
  if (!f) {
    fuellen(karte,
      offen && zustand.pausiert
        ? [el("h2", { id: "frage-titel" }, `${anzahl(offen, "Frage", "Fragen")} offen`),
          el("p", {}, "Mit diesen Angaben werden unklare Punkte der Checkliste genauer."),
          el("button", { type: "button", class: "primaer", onclick: () => { zustand.pausiert = false; ausloesen("neu-zeichnen"); } }, "Fragen fortsetzen")]
        : [el("h2", { id: "frage-titel", class: "fertig" }, "Alle nötigen Angaben sind gemacht"),
          el("p", { class: "leise" }, "Was jetzt noch unklar ist, kann nur die zuständige Stelle entscheiden. Ihre Angaben können Sie unten jederzeit ändern.")],
      fortschrittElement());
    return;
  }
  const bearbeiten = zustand.bearbeiten === f.id;
  const fuss = el("div", { class: "frage-fuss" },
    el("button", { type: "button", onclick: () => antworten(f.id, "unbekannt") }, "Weiß nicht"),
    bearbeiten
      ? el("button", { type: "button", class: "link", onclick: () => { zustand.bearbeiten = null; ausloesen("neu-zeichnen"); } }, "Abbrechen")
      : el("button", { type: "button", class: "link", onclick: () => { zustand.pausiert = true; zustand.fokusFrage = null; ausloesen("neu-zeichnen"); } }, "Fragen beenden"),
  );
  fuellen(karte,
    el("p", { class: "frage-kopf" },
      bearbeiten ? "Angabe ändern" : (zustand.fokusFrage === f.id ? "Diese Angabe fehlt" : "Nächste Frage"),
      f.person_name ? el("span", { class: "person" }, f.person_name) : null),
    el("h2", { id: "frage-titel" }, f.typ === "datum" ? f.frage.replace(/\s*\(TT\.MM\.JJJJ\)/, "") : f.frage),
    f.hilfe ? el("p", { class: "leise" }, f.hilfe) : null,
    eingabe(f, bearbeiten ? f.wert : undefined),
    fuss,
    !bearbeiten && sitzung.meta.freitext && f.typ !== "ort" ? eigeneWorte(f) : null,
    bearbeiten ? null : betrifftElement(f),
    fortschrittElement(),
  );
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
  const form = el("form", { class: "zeile", novalidate: true }, feld,
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

// Freie Antwort (#79): Vorschläge werden angezeigt und erst mit "Übernehmen" zu Angaben
function eigeneWorte(f) {
  const textId = "eigene-antwort";
  const feld = el("textarea", { id: textId, rows: "2", maxlength: "500", placeholder: "z. B. „Ja, ich arbeite seit 2019 in Teilzeit.“" });
  const einwilligung = sitzung.einwilligung ? null
    : el("label", { class: "haken" }, el("input", { type: "checkbox", id: "einwilligung-antwort" }),
      " Einverstanden, meine Antwort von einem KI-Dienst auswerten zu lassen. Sie wird nicht gespeichert.");
  const ergebnis = el("div", { class: "eigene-ergebnis", "aria-live": "polite" });
  const knopf = el("button", { type: "button" }, "Antwort auswerten");
  knopf.addEventListener("click", async () => {
    const text = feld.value.trim();
    if (!text) { meldung("Bitte schreiben Sie Ihre Antwort in das Feld."); feld.focus(); return; }
    if (!sitzung.einwilligung) {
      const haken = $("#einwilligung-antwort");
      if (!haken || !haken.checked) { meldung("Bitte bestätigen Sie, dass Ihre Antwort ausgewertet werden darf."); if (haken) haken.focus(); return; }
      sitzung.einwilligung = true;
    }
    meldung("");
    knopf.disabled = true;
    knopf.textContent = "Wird ausgewertet …";
    try {
      const r = await api("/api/antwort", { ...anfrage(), frage: f.id, text });
      vorschlaegeZeigen(ergebnis, text, r);
    } catch (e) {
      meldung(e.message);
    } finally {
      knopf.disabled = false;
      knopf.textContent = "Antwort auswerten";
    }
  });
  return el("details", { class: "eigene" },
    el("summary", {}, "In eigenen Worten antworten"),
    el("label", { for: textId, class: "unsichtbar" }, "Ihre Antwort"),
    feld, einwilligung, el("div", { class: "zeile" }, knopf), ergebnis);
}

function vorschlaegeZeigen(ziel, text, r) {
  if (!r.vorschlaege.length) {
    fuellen(ziel, r.hinweise.map((h) => el("p", { class: "hinweis" }, h)));
    return;
  }
  const zitat = el("blockquote", { class: "eigene-worte" }, markierterText(text, r.vorschlaege));
  const liste = vorschlagsliste(r.vorschlaege, zitat);
  fuellen(ziel,
    el("p", { class: "klein-titel" }, "Das haben wir verstanden – stimmt das?"),
    zitat, liste.element,
    el("div", { class: "zeile" },
      el("button", { type: "button", class: "primaer", onclick: () => {
        try { uebernehmen(liste.werte()); } catch (e) { meldung(e.message); }
      } }, "Übernehmen"),
      el("button", { type: "button", class: "link", onclick: () => fuellen(ziel) }, "Verwerfen")));
}

// Was hat sich durch die letzte Antwort geändert? (#86)
export function zeichneAenderung() {
  const ziel = $("#aenderung");
  const vorher = sitzung.vorher;
  if (!vorher) { ziel.textContent = ""; return; }
  const alt = Object.fromEntries(vorher.leistungen.map((l) => [l.id, l.ergebnis]));
  const neu = sitzung.bericht.leistungen.filter((l) => alt[l.id] && alt[l.id] !== l.ergebnis);
  if (!neu.length) { ziel.textContent = ""; return; }
  const teile = neu.slice(0, 3).map((l) => `${l.name}: ${ERGEBNIS_TEXT[alt[l.id]]} → ${ERGEBNIS_TEXT[l.ergebnis]}`);
  if (neu.length > 3) teile.push(`und ${neu.length - 3} weitere`);
  fuellen(ziel, el("span", { class: "leise" }, "Geändert: "), teile.join("; "));
}

export function zeichneAngaben() {
  const liste = $("#angaben");
  const b = sitzung.bericht;
  if (!b.angaben.length) {
    fuellen(liste, el("li", { class: "leise" }, "Noch keine Angaben."));
    return;
  }
  fuellen(liste, ...b.angaben.map((a) => el("li", { class: a.aktiv ? null : "inaktiv" },
    el("span", {}, a.frage, a.aktiv ? null : el("span", { class: "leise" }, " (nicht mehr relevant)")),
    el("span", { class: "rechts" },
      el("span", { class: "wert" }, a.wert === "unbekannt" ? "weiß nicht" : a.anzeige),
      el("button", {
        type: "button", class: "link", "aria-label": `Ändern: ${a.frage}`,
        onclick: () => { zustand.bearbeiten = a.id; ausloesen("neu-zeichnen", { fokus: true }); },
      }, "ändern"),
    ),
  )));
}
