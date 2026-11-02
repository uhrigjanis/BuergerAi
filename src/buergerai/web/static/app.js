// BürgerAI Web-Oberfläche: Einstieg. Kein Framework, kein Build-Schritt (ADR 0006).
// Module: start.js (Einstieg), frage.js (Fragen), checkliste.js (Ergebnis), detail.js (Details),
// vorschlaege.js (Bestätigung erkannter Angaben, #79), gemeinsam.js (Helfer und Zustand).
import {
  $, anfrage, api, aufzaehlung, bus, datumText, el, fuellen, ladenAusSpeicher, meldung, sitzung, speicherLoeschen, speichern,
  zustand,
} from "./gemeinsam.js";
import { checklisteEinrichten, zeichneCheckliste } from "./checkliste.js";
import { detailEinrichten } from "./detail.js";
import { zeichneAenderung, zeichneAngaben, zeichneFrage } from "./frage.js";
import { startEinrichten, startLeeren } from "./start.js";

// Muss zu buergerai.__version__ passen (Test: tests/test_web.py); sonst warnt die Seite
const VERSION = "0.6.0";
const SCHMAL = window.matchMedia("(max-width: 860px)");
let anfrageNr = 0;  // nur die Antwort auf die jüngste Anfrage wird angezeigt

function ansichtZeigen(arbeit) {
  $("#start").hidden = arbeit;
  $("#arbeit").hidden = !arbeit;
  document.body.classList.toggle("mit-reitern", arbeit);
}

// ------------------------------------------------------------------ Bericht holen
async function aktualisieren(optionen = {}) {
  if (!zustand.ort) {
    ansichtZeigen(false);
    return;
  }
  const nr = ++anfrageNr;
  let neu;
  try {
    neu = await api("/api/bericht", anfrage());
  } catch (e) {
    if (nr !== anfrageNr) return;  // veraltete Antwort verwerfen
    meldung(e.message);
    if (!sitzung.bericht) {
      // Ungültiger gespeicherter Zustand: zurück zum Start
      zustand.ort = null;
      speicherLoeschen();
      ansichtZeigen(false);
    }
    return;
  }
  if (nr !== anfrageNr) return;  // inzwischen wurde neu gefragt: veraltete Antwort verwerfen
  // "Geändert: …" nur nach einer Antwort, nicht nach Wechsel der Lebenslagen oder des Datums
  sitzung.vorher = optionen.vergleich ? sitzung.bericht : null;
  sitzung.bericht = neu;
  meldung("");
  speichern();
  ansichtZeigen(true);
  zeichnen(optionen);
}

function zeichnen(optionen = {}) {
  const b = sitzung.bericht;
  $("#ort-text").textContent = b.ort.text;
  $("#stichtag-zeile").textContent = zustand.stichtag
    ? `Simuliertes Datum: ${datumText(zustand.stichtag)}`
    : `Stand: heute, ${datumText(b.stichtag)}`;
  $("#stichtag").value = b.stichtag;
  $("#titel").textContent = aufzaehlung(b.lebenslagen.map((l) => l.name));
  lagenListe();
  zeichneFrage();
  zeichneAenderung();
  zeichneAngaben();
  zeichneCheckliste();
  if (optionen.fokus) {
    const ziel = $("#frage-karte").querySelector("button, input, select");
    if (ziel) {
      ziel.focus({ preventScroll: true });
      $("#frage-karte").scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
}

// Lebenslagen nachträglich ändern; die Angaben bleiben erhalten (ANF-WEB-10)
function lagenListe() {
  const ziel = $("#lebenslagen-wahl-arbeit");
  const gewaehlt = sitzung.bericht.lebenslagen.map((l) => l.id);
  fuellen(ziel, ziel.querySelector("legend"), sitzung.meta.lebenslagen.map((l) => el("label", { class: "haken" },
    el("input", {
      type: "checkbox", name: "lebenslage", value: l.id, checked: gewaehlt.includes(l.id),
      onchange: () => {
        const lagen = [...ziel.querySelectorAll("input[name=lebenslage]:checked")].map((e) => e.value);
        if (!lagen.length) {
          meldung("Bitte mindestens eine Lebenslage wählen.");
          return;
        }
        zustand.lebenslagen = lagen;
        sitzung.vorher = null;
        aktualisieren();
      },
    }), l.name)));
}

// ------------------------------------------------------------------ Handy: Reiter
function reiterSetzen(name) {
  $("#arbeit").dataset.reiter = name;
  for (const k of document.querySelectorAll(".reiter [data-reiter]")) k.setAttribute("aria-pressed", String(k.dataset.reiter === name));
  if (SCHMAL.matches) window.scrollTo({ top: 0 });
}

// ------------------------------------------------------------------ Laden, neu beginnen
function angabenUebernehmen(s) {
  if (!s || typeof s !== "object" || !(s.plz || s.gemeinde || s.land)) {
    meldung("Die Datei enthält keinen Wohnort (plz, gemeinde oder land).");
    return;
  }
  Object.assign(zustand, {
    ort: { plz: s.plz || null, gemeinde: s.gemeinde || null, land: s.land || null },
    stichtag: s.stichtag || null,
    lebenslagen: Array.isArray(s.lebenslagen) && s.lebenslagen.length ? s.lebenslagen : null,
    fakten: (s.fakten && typeof s.fakten === "object") ? s.fakten : {},
    erledigt: {}, bearbeiten: null, fokusFrage: null, pausiert: false, fuer: "alle",
  });
  sitzung.bericht = null;
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

function neuBeginnen() {
  if (!confirm("Alle Angaben löschen und neu beginnen?")) return;
  Object.assign(zustand, {
    ort: null, fakten: {}, erledigt: {}, stichtag: null, lebenslagen: null,
    bearbeiten: null, fokusFrage: null, pausiert: false, fuer: "alle",
  });
  sitzung.bericht = null;
  sitzung.vorher = null;
  speicherLoeschen();
  startLeeren();
  ansichtZeigen(false);
  $("#freitext").focus();
}

// ------------------------------------------------------------------ Start
async function init() {
  try {
    sitzung.meta = await api("/api/meta");
  } catch (e) {
    meldung("Server nicht erreichbar. Läuft „./bai web“?");
    return;
  }
  $("#version").textContent = `Version ${VERSION}`;
  if (sitzung.meta.version !== VERSION) {
    meldung(`Diese Seite (Version ${VERSION}) passt nicht zum Server (Version ${sitzung.meta.version}). Bitte neu laden: Strg+Umschalt+R bzw. Cmd+Umschalt+R.`);
  }
  startEinrichten();
  checklisteEinrichten();
  detailEinrichten();

  bus.addEventListener("aktualisieren", (ev) => aktualisieren(ev.detail || {}));
  bus.addEventListener("neu-zeichnen", (ev) => { if (sitzung.bericht) { sitzung.vorher = null; zeichnen(ev.detail || {}); } });
  bus.addEventListener("reiter", (ev) => reiterSetzen(ev.detail));
  bus.addEventListener("angaben-laden", (ev) => angabenUebernehmen(ev.detail));
  for (const k of document.querySelectorAll(".reiter [data-reiter]")) k.addEventListener("click", () => reiterSetzen(k.dataset.reiter));

  $("#datei-laden").addEventListener("change", (ev) => { $("#menue").open = false; dateiLaden(ev); });
  $("#datei-laden-start").addEventListener("change", dateiLaden);
  $("#neu").addEventListener("click", neuBeginnen);
  $("#stichtag").addEventListener("change", () => {
    const v = $("#stichtag").value;
    zustand.stichtag = v && v !== sitzung.meta.heute ? v : null;
    sitzung.vorher = null;
    aktualisieren();
  });
  $("#stichtag-heute").addEventListener("click", () => { zustand.stichtag = null; sitzung.vorher = null; aktualisieren(); });

  ladenAusSpeicher();
  aktualisieren();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
