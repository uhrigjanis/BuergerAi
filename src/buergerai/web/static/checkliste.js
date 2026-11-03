// Checkliste (#86): kompakte Zeilen, gruppiert nach Zeit, Stelle oder Ergebnis.
// Details öffnen sich in detail.js; "Jetzt klären" springt zur entscheidenden Frage.
import {
  $, ERGEBNIS_TEXT, anfrage, anzahl, aufzaehlung, ausloesen, datumText, download, einblenden, el, ergebnisMarke, fuellen, meldung,
  sitzung, speichern, zustand,
} from "./gemeinsam.js";
import { detailOeffnen } from "./detail.js";

const ERGEBNIS_GRUPPEN = [
  ["ja", "Steht Ihnen voraussichtlich zu oder ist zu erledigen"],
  ["unklar", "Noch unklar"],
];

// Datenstand als kleines Kennzeichen je Zeile (ADR 0004)
export function datenstand(l) {
  if (l.abdeckung === "allgemein") return { text: "nur allgemeine Angabe", art: "schwach" };
  const geaendert = l.quellen.some((q) => q.seit_pruefung_geaendert);
  if (geaendert) return { text: "Quelle seit Prüfung geändert", art: "warnung" };
  return {
    verifiziert: { text: "Quellen geprüft", art: "gut" },
    teilweise: { text: "teilweise geprüft", art: "mittel" },
    ungeprueft: { text: "ungeprüft", art: "schwach" },
    widerspruechlich: { text: "Quellen widersprüchlich", art: "warnung" },
  }[l.pruefstatus] || { text: l.pruef_text, art: "mittel" };
}

// Wichtigste Angabe der Zeile: dringendste Frist, sonst der Betrag
export function fristKurz(fr) {
  if (!fr.datum) return fr.text;
  const art = { spaetestens: "bis", empfohlen: "am besten bis", fruehestens: "ab" }[fr.art] || fr.art_text;
  let wann = "";
  if (fr.abgelaufen) wann = ` – vor ${anzahl(-fr.tage_bis, "Tag", "Tagen")} abgelaufen`;
  else if (fr.tage_bis === 0) wann = " (heute)";
  else if (fr.tage_bis > 0 && fr.tage_bis <= 30) wann = ` (in ${anzahl(fr.tage_bis, "Tag", "Tagen")})`;
  return `${art} ${datumText(fr.datum)}${fr.voraussichtlich ? ", voraussichtlich" : ""}${wann}`;
}

function kerninfo(l) {
  if (l.ergebnis !== "nein" && l.leitfrist !== null) {
    const fr = l.fristen[l.leitfrist];
    return el("span", { class: `frist ${fr.abgelaufen ? "abgelaufen" : (fr.bald ? "bald" : "")}`.trim() }, fristKurz(fr));
  }
  return l.betrag ? el("span", {}, l.betrag) : null;
}

function jetztKlaeren(l) {
  zustand.fokusFrage = l.klaeren_mit;
  zustand.pausiert = false;
  zustand.bearbeiten = null;
  ausloesen("neu-zeichnen", { fokus: true });
}

function zeile(l) {
  const b = sitzung.bericht;
  const relevant = l.ergebnis !== "nein";
  const erledigt = !!zustand.erledigt[l.id];
  const ds = datenstand(l);
  const offen = l.ergebnis === "unklar" && l.klaeren_mit && b.fragen.some((f) => f.id === l.klaeren_mit);
  return el("li", { class: `zeile-leistung ${l.ergebnis}${erledigt ? " erledigt" : ""}`, id: `leistung-${l.id}` },
    relevant
      ? el("input", {
        type: "checkbox", checked: erledigt, "aria-label": `${l.name} erledigt`,
        onchange: (ev) => {
          if (ev.target.checked) zustand.erledigt[l.id] = true; else delete zustand.erledigt[l.id];
          speichern();
          zeichneListe();
        },
      })
      : el("span", { class: "platz", "aria-hidden": "true" }),
    el("div", { class: "zeile-text" },
      el("button", { type: "button", class: "zeile-name", "aria-haspopup": "dialog", onclick: () => detailOeffnen(l.id) }, l.name),
      el("p", { class: "zeile-meta" },
        kerninfo(l),
        zustand.ansicht !== "stelle" ? el("span", {}, l.zustaendigkeit.name) : null,
        el("span", { class: `datenstand ${ds.art}` }, ds.text)),
      offen ? el("button", { type: "button", class: "klaeren", onclick: () => jetztKlaeren(l) },
        "Jetzt klären", el("span", { class: "leise" }, ` (${anzahl(l.offene_fragen, "Angabe fehlt", "Angaben fehlen")})`)) : null),
    ergebnisMarke(l.ergebnis));
}

function gefiltert() {
  const b = sitzung.bericht;
  if (zustand.fuer === "alle") return b.leistungen;
  return b.leistungen.filter((l) => l.personen.some((p) => p.person === zustand.fuer));
}

function gruppen(leistungen) {
  const b = sitzung.bericht;
  if (zustand.ansicht === "stelle") {
    const nachStelle = new Map();
    for (const l of leistungen) {
      const name = l.zustaendigkeit.name;
      if (!nachStelle.has(name)) nachStelle.set(name, []);
      nachStelle.get(name).push(l);
    }
    return [...nachStelle.entries()]
      .sort((a, c) => c[1].length - a[1].length || a[0].localeCompare(c[0], "de"))
      .map(([name, liste]) => ({ titel: name, liste }));
  }
  if (zustand.ansicht === "ergebnis") {
    return ERGEBNIS_GRUPPEN.map(([w, titel]) => ({ titel, liste: leistungen.filter((l) => l.ergebnis === w) }));
  }
  return b.zeitgruppen.map((g) => ({ titel: g.text, liste: leistungen.filter((l) => l.zeitgruppe === g.id) }));
}

export function zeichneListe(optionen = {}) {
  const b = sitzung.bericht;
  const alle = gefiltert();
  const relevant = alle.filter((l) => l.ergebnis !== "nein");
  const box = $("#liste");
  const sichtbar = gruppen(relevant).filter((g) => g.liste.length);
  fuellen(box, sichtbar.length
    ? sichtbar.map((g) => el("section", { class: "gruppe" },
      el("h3", {}, g.titel, el("span", { class: "anzahl" }, ` ${g.liste.length}`)),
      el("ul", { class: "zeilen" }, g.liste.map(zeile))))
    : el("p", { class: "leer" }, "Für diese Auswahl ist nichts zu erledigen."));

  const nein = alle.filter((l) => l.ergebnis === "nein");
  $("#nein-box").hidden = !nein.length;
  $("#nein-titel").textContent = `Voraussichtlich nicht für Sie (${nein.length})`;
  fuellen($("#nein-liste"), el("ul", { class: "zeilen" }, nein.map(zeile)));

  for (const k of document.querySelectorAll("[data-ansicht]")) k.setAttribute("aria-pressed", String(k.dataset.ansicht === zustand.ansicht));
  // Kalender nur, wenn es datierte Fristen gibt (kontextuelles Einblenden, #99)
  $("#kalender").hidden = !relevant.some((l) => l.fristen.some((fr) => fr.datum));
  if (optionen.einblenden) einblenden(box);
}

function zeichneFilter() {
  const b = sitzung.bericht;
  const personen = new Map();
  for (const l of b.leistungen) for (const p of l.personen) if (p.person) personen.set(p.person, p.name);
  const box = $("#fuer-filter");
  box.hidden = personen.size < 2;
  if (box.hidden) { zustand.fuer = "alle"; return; }
  if (zustand.fuer !== "alle" && !personen.has(zustand.fuer)) zustand.fuer = "alle";
  fuellen(box, el("span", { class: "leise" }, "Für"), [["alle", "Alle"], ...personen.entries()].map(([id, name]) =>
    el("button", { type: "button", "aria-pressed": String(zustand.fuer === id), onclick: () => { zustand.fuer = id; zeichneFilter(); zeichneListe(); } }, name)));
}

export function zeichneCheckliste() {
  const b = sitzung.bericht;
  const lagen = aufzaehlung(b.lebenslagen.map((l) => l.name));
  const ort = b.ort.hierarchie.length ? b.ort.hierarchie[0].name : "";
  $("#liste-kontext").textContent = `${lagen}, ${ort}`;
  $("#kind-text").textContent = b.kind ? `Kind: ${b.kind}` : "";
  $("#kind-text").hidden = !b.kind;
  fuellen($("#warnungen"), b.warnungen.map((w) => el("li", {}, w)));

  const andere = b.nur_andere_laender;
  $("#andere-box").hidden = !andere.length;
  $("#andere-titel").textContent = `Nur in anderen Bundesländern (${andere.length})`;
  fuellen($("#andere-liste"), andere.map((a) => el("li", {}, el("strong", {}, a.name), ` – ${a.laender.join(", ")}`)));
  const fehlt = b.nicht_erfasst;
  $("#nicht-erfasst-box").hidden = !fehlt.length;
  $("#nicht-erfasst-titel").textContent = `Noch nicht erfasst (${fehlt.length})`;
  fuellen($("#nicht-erfasst"), fehlt.map((n) => el("li", {}, el("strong", {}, n.name),
    b.lebenslagen.length > 1 ? ` (${n.lebenslage})` : "", " – ", n.grund)));
  zeichneFilter();
  zeichneListe({ einblenden: true });
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
  const b = sitzung.bericht;
  const daten = { name: "Eigene Angaben", beschreibung: `Gespeichert am ${datumText(new Date().toISOString().slice(0, 10))}` };
  for (const k of ["plz", "gemeinde", "land"]) if (zustand.ort[k]) daten[k] = zustand.ort[k];
  daten.stichtag = b.stichtag;
  daten.lebenslagen = b.lebenslagen.map((l) => l.id);
  daten.fakten = zustand.fakten;
  download("buergerai-angaben.json", JSON.stringify(daten, null, 2) + "\n", "application/json");
}

// Druck als Behördenmappe: je Stelle, was zu tun ist und was man mitnehmen muss (#86)
function druckAufbauen() {
  const b = sitzung.bericht;
  const relevant = b.leistungen.filter((l) => l.ergebnis !== "nein");
  const nachStelle = new Map();
  for (const l of relevant) {
    const k = l.zustaendigkeit.name;
    if (!nachStelle.has(k)) nachStelle.set(k, { stelle: l.zustaendigkeit, liste: [] });
    nachStelle.get(k).liste.push(l);
  }
  fuellen($("#druck"),
    el("h1", {}, "Ihre Behördenmappe"),
    el("p", {}, `${aufzaehlung(b.lebenslagen.map((l) => l.name))}, ${b.ort.text}. Stand: ${datumText(b.stichtag)}`),
    [...nachStelle.values()].map(({ stelle, liste }) => {
      const unterlagen = [...new Set(liste.flatMap((l) => l.verfahren.unterlagen))];
      return el("section", { class: "mappe" },
        el("h2", {}, stelle.name),
        stelle.beschreibung ? el("p", {}, stelle.beschreibung) : null,
        stelle.url ? el("p", {}, stelle.url) : null,
        el("ul", {}, liste.map((l) => el("li", {},
          `☐ ${l.name} – ${ERGEBNIS_TEXT[l.ergebnis]}`,
          l.leitfrist !== null ? `, ${fristKurz(l.fristen[l.leitfrist])}` : "",
          l.betrag ? `, ${l.betrag}` : ""))),
        unterlagen.length ? [el("h3", {}, "Mitnehmen"), el("ul", {}, unterlagen.map((u) => el("li", {}, `☐ ${u}`)))] : null);
    }),
    el("p", {}, "Unverbindliche Orientierung, keine Rechtsberatung. Verbindlich entscheidet die zuständige Stelle."));
}

export function checklisteEinrichten() {
  $("#kalender").addEventListener("click", kalender);
  $("#speichern").addEventListener("click", angabenSpeichern);
  $("#drucken").addEventListener("click", () => {
    druckAufbauen();
    window.print();
  });
  for (const k of document.querySelectorAll("[data-ansicht]")) {
    k.addEventListener("click", () => { zustand.ansicht = k.dataset.ansicht; speichern(); zeichneListe({ einblenden: true }); });
  }
}
