// Gemeinsame Helfer und Zustand der Oberfläche. Kein Framework, keine externen Dateien (ADR 0006).

export const SPEICHER = "buergerai.v1";
export const ERGEBNIS_TEXT = { ja: "Ja", unklar: "Unklar", nein: "Nein" };
export const SYMBOL = { ja: "✓", unklar: "?", nein: "✗" };

// Alles, was der Browser sich merkt. Freitexte gehören bewusst nicht dazu.
export const zustand = {
  ort: null,            // {plz, gemeinde, land}
  stichtag: null,       // "JJJJ-MM-TT" oder null = heute
  lebenslagen: null,    // Liste von IDs
  fakten: {},           // id -> Wert (true/false, Zahl, "JJJJ-MM-TT", Auswahlwert, "unbekannt")
  erledigt: {},         // leistung_id -> true
  ansicht: "zeit",      // zeit | stelle | ergebnis
  bearbeiten: null,     // Fakt-ID, die gerade geändert wird
  fokusFrage: null,     // Frage, die "Jetzt klären" nach vorn holt
  pausiert: false,      // Fragen ausgeblendet ("nur Ergebnis")
  fuer: "alle",         // Personenfilter der Checkliste
};

// Nicht gespeichert: Server-Infos und der aktuelle Bericht
export const sitzung = { meta: null, bericht: null, vorher: null, einwilligung: false };

export const $ = (sel) => document.querySelector(sel);

export function el(tag, attrs = {}, ...kinder) {
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
export function fuellen(ziel, ...kinder) {
  ziel.replaceChildren(...kinder.flat(Infinity).filter((k) => k !== null && k !== undefined && k !== false));
}

export function datumText(iso) {
  if (!iso) return "";
  const [j, m, t] = iso.split("-");
  return `${t}.${m}.${j}`;
}

export function sicherLink(url, text) {
  // Nur http(s)-Links aus der Wissensbasis anzeigen
  if (!/^https?:\/\//i.test(url || "")) return document.createTextNode(text || url || "");
  return el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text || url);
}

// Links zu Antrag, Portal, Vorab-Check und Infoseite (#36), in der Reihenfolge des Servers.
// Nur https; jeder Link nennt seine Ebene und seinen Prüfstatus. Ohne Antrags-Link: ehrlicher Hinweis.
const LINK_KLASSE = { formular: "link-knopf haupt", portal: "link-knopf", rechner: "link-knopf", info: "link-text" };
export function linkLeiste(l) {
  const links = l.links.filter((x) => /^https:\/\//i.test(x.url));
  if (!links.length && !l.link_hinweise.length) return null;
  return el("div", { class: "links" },
    links.length ? el("ul", { class: "link-liste" }, links.map((x) => el("li", {},
      el("a", { href: x.url, target: "_blank", rel: "noopener noreferrer", class: LINK_KLASSE[x.art] || "link-text", title: x.titel },
        x.text, el("span", { class: "unsichtbar" }, " (öffnet in neuem Tab)")),
      el("span", { class: "leise link-meta" }, `${x.herkunft} · ${x.pruef_text}`)))) : null,
    l.link_hinweise.map((h) => el("p", { class: "link-hinweis" }, h)));
}

export function speichern() {
  try {
    const { ort, stichtag, lebenslagen, fakten, erledigt, ansicht } = zustand;
    localStorage.setItem(SPEICHER, JSON.stringify({ ort, stichtag, lebenslagen, fakten, erledigt, ansicht }));
  } catch (_) { /* privater Modus: dann eben ohne Speichern */ }
}

export function speicherLoeschen() {
  try { localStorage.removeItem(SPEICHER); } catch (_) { /* ignorieren */ }
}

export function ladenAusSpeicher() {
  try {
    const roh = JSON.parse(localStorage.getItem(SPEICHER) || "null");
    if (roh && roh.ort) Object.assign(zustand, roh);
  } catch (_) { /* ignorieren */ }
}

export function meldung(text) {
  const m = $("#meldung");
  m.textContent = text || "";
  m.hidden = !text;
  if (text) m.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

export async function api(pfad, daten) {
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

// Die Anfrage an /api/bericht: enthält nur bestätigte Angaben aus zustand.fakten
export function anfrage() {
  const daten = { ...zustand.ort, stichtag: zustand.stichtag, fakten: zustand.fakten };
  if (zustand.lebenslagen && zustand.lebenslagen.length) daten.lebenslagen = zustand.lebenslagen;
  return daten;
}

export function download(name, inhalt, typ) {
  const url = URL.createObjectURL(new Blob([inhalt], { type: typ }));
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// "Geburt, Umzug und Pflege"
const LISTE = new Intl.ListFormat("de", { type: "conjunction" });
export const aufzaehlung = (namen) => LISTE.format(namen);

export function anzahl(n, eins, mehr) {
  return `${n} ${n === 1 ? eins : mehr}`;
}

export function ergebnisMarke(wert) {
  return el("span", { class: `ergebnis ${wert}` }, el("span", { "aria-hidden": "true" }, SYMBOL[wert]), " ", ERGEBNIS_TEXT[wert]);
}

// Ein Ereignis-Bus zwischen den Modulen: "neu-zeichnen", "aktualisieren"
export const bus = new EventTarget();
export const ausloesen = (name, detail) => bus.dispatchEvent(new CustomEvent(name, { detail }));
