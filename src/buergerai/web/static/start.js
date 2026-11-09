// Einstieg (#86, #79): "Was ist bei Ihnen los?" – Freitext (mit LLM) oder Stichwortsuche,
// Kacheln nach Bereichen, Wohnort. Erkannte Angaben gehen erst nach Bestätigung weiter.
import { $, api, ausloesen, el, fuellen, meldung, sitzung, zustand } from "./gemeinsam.js";
import { markierterText, vorschlagsliste } from "./vorschlaege.js";

// Gruppierung der Kacheln. Unbekannte Lebenslagen landen unter "Weitere".
const BEREICHE = [
  ["Familie", ["geburt", "heirat", "schule"]],
  ["Arbeit und Ausbildung", ["jobverlust", "selbststaendig", "ausbildung_studium"]],
  ["Wohnen", ["umzug", "wohneigentum"]],
  ["Gesundheit", ["pflege", "behinderung"]],
  ["Geld und Alter", ["geringes_einkommen", "ruhestand"]],
  ["Abschied", ["todesfall"]],
];
const KURZ = {
  jobverlust: "Job verloren", selbststaendig: "Selbstständig", ausbildung_studium: "Ausbildung, Studium",
  schule: "Schulstart", wohneigentum: "Kaufen oder bauen", ruhestand: "Ruhestand", todesfall: "Todesfall",
};

const auswahl = new Set();
let bestaetigung = null;  // Vorschlagsliste aus dem Freitext, bis zur Bestätigung
let wohnortAusText = false;  // Gemeindefeld ist mit dem Wohnort aus dem Freitext vorbelegt (#115)
const GEMEINDE_FRAGE_PLZ = "Die Postleitzahl gehört zu mehreren Gemeinden. Welche ist es?";

function kachelnZeichnen() {
  const meta = sitzung.meta;
  const bekannt = new Set(meta.lebenslagen.map((l) => l.id));
  const vergeben = new Set(BEREICHE.flatMap(([, ids]) => ids));
  const bereiche = BEREICHE.map(([name, ids]) => [name, ids.filter((id) => bekannt.has(id))]);
  const rest = meta.lebenslagen.map((l) => l.id).filter((id) => !vergeben.has(id));
  if (rest.length) bereiche.push(["Weitere", rest]);
  const name = (id) => KURZ[id] || meta.lebenslagen.find((l) => l.id === id).name;
  const box = $("#lebenslagen-wahl");
  fuellen(box, box.querySelector("legend"), bereiche.filter(([, ids]) => ids.length).map(([bereich, ids]) =>
    el("div", { class: "bereich" },
      el("span", { class: "bereich-name", id: `bereich-${bereich.replace(/\W/g, "")}` }, bereich),
      el("div", { class: "bereich-kacheln", role: "group", "aria-labelledby": `bereich-${bereich.replace(/\W/g, "")}` },
        ids.map((id) => el("button", {
          type: "button", class: "kachel", "data-lebenslage": id, "aria-pressed": String(auswahl.has(id)),
          onclick: () => { if (auswahl.has(id)) auswahl.delete(id); else auswahl.add(id); auswahlZeigen(); },
        }, name(id)))))));
}

// Beschreibung erst bei Auswahl (#86)
function auswahlZeigen() {
  for (const k of document.querySelectorAll(".kachel")) k.setAttribute("aria-pressed", String(auswahl.has(k.dataset.lebenslage)));
  fuellen($("#auswahl-text"), [...auswahl].map((id) => {
    const l = sitzung.meta.lebenslagen.find((x) => x.id === id);
    return el("li", {}, el("strong", {}, l.name), " – ", l.beschreibung);
  }));
}

function bestaetigungZuruecksetzen() {
  bestaetigung = null;
  $("#verstanden").hidden = true;
  $("#ort-senden").textContent = "Checkliste erstellen";
  if (wohnortAusText) startZuruecksetzen();
}

// ------------------------------------------------------------------ Orte aus dem Freitext (#115)
// Der Server hat die Namen den Gemeinden zugeordnet. Übernommen wird erst mit "Stimmt so".
function ortZeile(o) {
  const name = `„${o.ortsname || o.plz}“`;
  if (o.rolle === "wohnort") {
    if (o.status === "eindeutig") {
      const plz = o.gemeinde.plz_text ? `, ${o.gemeinde.plz_text}` : "";
      return el("p", {}, el("strong", {}, "Wohnort: "), `${o.gemeinde.text}${plz} – stimmt das? Unten ist er schon eingetragen.`);
    }
    if (o.status === "mehrdeutig") {
      const text = o.art === "plz" ? `Die Postleitzahl ${o.plz} gehört zu mehreren Gemeinden.`
        : o.art === "tippfehler" ? `Meinten Sie ${o.kandidaten.map((k) => k.name).join(" oder ")}?`
        : `${name} passt zu ${o.kandidaten.length === 1 ? "dieser Gemeinde" : `${o.kandidaten.length} Gemeinden`}.`;
      return el("p", {}, el("strong", {}, "Wohnort: "), `${text} Bitte wählen Sie unten aus.`);
    }
    return el("p", { class: "hinweis" }, `Den Wohnort ${name} konnten wir keiner Gemeinde zuordnen. Bitte geben Sie unten die Postleitzahl ein.`);
  }
  if (o.status === "unbekannt" && !o.plz) {
    return el("p", { class: "leise" }, `${name} konnten wir keiner Gemeinde zuordnen. Wir fragen später nach der Postleitzahl.`);
  }
  return null;  // steht in der Vorschlagsliste
}

function wohnortVorbelegen(o) {
  if (!o) return;
  if (o.plz) $("#plz").value = o.plz;
  const gemeinden = o.gemeinde ? [o.gemeinde] : o.kandidaten;
  if (!gemeinden.length) return;
  if (!o.plz && o.gemeinde && o.gemeinde.plz.length === 1) $("#plz").value = o.gemeinde.plz[0];
  fuellen($("#gemeinde"),
    o.gemeinde ? null : el("option", { value: "" }, `Bitte wählen (${gemeinden.length}) …`),
    gemeinden.map((g) => el("option", { value: g.id }, g.text)));
  $("#gemeinde").value = o.gemeinde ? o.gemeinde.id : "";
  $("#gemeinde-label").textContent = "Wohnort aus Ihrem Text – bitte prüfen. Oder geben Sie oben eine Postleitzahl ein.";
  $("#gemeinde-wahl").hidden = false;
  wohnortAusText = true;
}

// ------------------------------------------------------------------ Freitext und Suche
async function textAbsenden(ev) {
  ev.preventDefault();
  meldung("");
  const text = $("#freitext").value.trim();
  if (!text) { meldung("Bitte beschreiben Sie kurz Ihre Lage oder wählen Sie unten aus."); $("#freitext").focus(); return; }
  if (sitzung.meta.freitext) {
    if (!$("#einwilligung-ja").checked) {
      meldung("Bitte bestätigen Sie, dass Ihr Text ausgewertet werden darf – oder wählen Sie unten ohne KI aus.");
      $("#einwilligung-ja").focus();
      return;
    }
    sitzung.einwilligung = true;
    await freitextAuswerten(text);
  } else {
    await suchen(text);
  }
}

async function suchen(text) {
  try {
    const r = await api("/api/suche", { text });
    bestaetigungZuruecksetzen();
    if (!r.lebenslagen.length) {
      meldung("Dazu haben wir keine passende Lebenslage gefunden. Bitte wählen Sie unten aus.");
      return;
    }
    auswahl.clear();
    r.lebenslagen.forEach((id) => auswahl.add(id));
    auswahlZeigen();
    $("#kacheln-titel").textContent = "Passend zu Ihrer Suche ausgewählt – bitte prüfen";
    $("#lebenslagen-wahl").querySelector(".kachel[aria-pressed=true]").focus();
  } catch (e) {
    meldung(e.message);
  }
}

async function freitextAuswerten(text) {
  const knopf = $("#text-senden");
  knopf.disabled = true;
  knopf.textContent = "Wird ausgewertet …";
  try {
    const r = await api("/api/intake", { text, stichtag: zustand.stichtag });
    verstandenZeigen(text, r);
  } catch (e) {
    meldung(e.status === 404
      ? "Die Auswertung von Freitext ist gerade nicht verfügbar. Bitte wählen Sie unten aus."
      : e.message);
  } finally {
    knopf.disabled = false;
    knopf.textContent = "Text auswerten";
  }
}

function verstandenZeigen(text, r) {
  const box = $("#verstanden");
  box.hidden = false;
  fuellen($("#verstanden-hinweise"), r.hinweise.map((h) => el("p", { class: r.kategorie === "notlage" ? "hinweis wichtig" : "hinweis" }, h)));
  const zitat = $("#verstanden-text");
  const orte = r.orte || [];
  const wohnort = orte.find((o) => o.rolle === "wohnort");
  // Markiert werden die Belege der Vorschläge und des Wohnorts (dieser ohne Zeile in der Liste)
  fuellen(zitat, markierterText(text, wohnort ? [...r.vorschlaege, wohnort] : r.vorschlaege));
  startZuruecksetzen();
  wohnortVorbelegen(wohnort);
  fuellen($("#verstanden-orte"), orte.map(ortZeile));
  auswahl.clear();
  r.lebenslagen.forEach((l) => auswahl.add(l.id));
  auswahlZeigen();
  $("#verstanden-lagen").textContent = r.lebenslagen.length
    ? `Erkannt: ${r.lebenslagen.map((l) => l.name).join(", ")}. Unten können Sie die Auswahl ändern.`
    : "Wir haben keine Lebenslage erkannt. Bitte wählen Sie unten aus.";
  $("#kacheln-titel").textContent = r.lebenslagen.length ? "Ihre Lebenslagen – bitte prüfen" : "Bitte wählen Sie aus – mehrere sind möglich";
  if (r.vorschlaege.length) {
    bestaetigung = vorschlagsliste(r.vorschlaege, zitat);
    fuellen($("#verstanden-liste"),
      el("p", {}, "Diese Angaben übernehmen wir, wenn Sie zustimmen. Korrigieren Sie, was nicht stimmt, oder nehmen Sie den Haken weg."),
      bestaetigung.element);
    $("#ort-senden").textContent = "Stimmt so – Checkliste erstellen";
  } else {
    bestaetigung = null;
    fuellen($("#verstanden-liste"));
    $("#ort-senden").textContent = "Checkliste erstellen";
  }
  box.focus();
}

// ------------------------------------------------------------------ Wohnort und Start
async function ortAbsenden(ev) {
  if (ev) ev.preventDefault();
  meldung("");
  const plz = $("#plz").value.trim();
  const daten = { plz };
  if (!$("#gemeinde-wahl").hidden && $("#gemeinde").value) daten.gemeinde = $("#gemeinde").value;
  if (!$("#land-wahl").hidden && $("#land").value) daten.land = $("#land").value;
  const lagen = [...auswahl];
  if (!lagen.length) {
    meldung("Bitte mindestens eine Lebenslage wählen.");
    return;
  }
  // Mit einer Gemeinde aus dem Freitext ist die PLZ nicht nötig (#115)
  if (wohnortAusText && !daten.gemeinde && !plz) {
    meldung("Bitte wählen Sie Ihren Wohnort aus oder geben Sie die Postleitzahl ein.");
    $("#gemeinde").focus();
    return;
  }
  if (!(daten.gemeinde && !plz) && !/^\d{5}$/.test(plz)) {
    meldung("Bitte eine fünfstellige Postleitzahl eingeben.");
    $("#plz").focus();
    return;
  }
  if (!plz) delete daten.plz;
  // Bestätigte Angaben: nur, was in der Liste angehakt ist (#79)
  let bestaetigt = {};
  try {
    bestaetigt = bestaetigung ? bestaetigung.werte() : {};
  } catch (e) {
    meldung(e.message);
    return;
  }
  try {
    await api("/api/ort", daten);
  } catch (e) {
    ortFehler(e);
    return;
  }
  Object.assign(zustand, {
    ort: { plz: plz || null, gemeinde: daten.gemeinde || null, land: daten.land || null },
    lebenslagen: lagen, fakten: bestaetigt, erledigt: {},
    bearbeiten: null, fokusFrage: null, pausiert: false, fuer: "alle",
  });
  ausloesen("aktualisieren");
}

function ortFehler(e) {
  if (e.daten && e.daten.status === "mehrdeutig") {
    wohnortAusText = false;
    $("#gemeinde-label").textContent = GEMEINDE_FRAGE_PLZ;
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

export function startZuruecksetzen() {
  $("#gemeinde-wahl").hidden = true;
  $("#land-wahl").hidden = true;
  $("#gemeinde-label").textContent = GEMEINDE_FRAGE_PLZ;
  wohnortAusText = false;
}

export function startLeeren() {
  auswahl.clear();
  auswahlZeigen();
  bestaetigungZuruecksetzen();
  startZuruecksetzen();
  $("#freitext").value = "";
  $("#plz").value = "";
  $("#kacheln-titel").textContent = sitzung.meta.freitext ? "Oder wählen Sie aus – mehrere sind möglich" : "Wählen Sie aus – mehrere sind möglich";
}

export function startEinrichten() {
  const meta = sitzung.meta;
  if (meta.freitext) {
    $("#einwilligung").hidden = false;
  } else {
    // Ohne LLM: dasselbe Feld als Stichwortsuche, gleiches Layout (#86)
    $("#text-label").textContent = "Suchen Sie nach einem Stichwort";
    $("#freitext").rows = 1;
    $("#freitext").maxLength = 200;
    $("#freitext").placeholder = "z. B. „Baby“, „Kündigung“ oder „Umzug“";
    $("#text-senden").textContent = "Suchen";
    $("#kacheln-titel").textContent = "Wählen Sie aus – mehrere sind möglich";
  }
  kachelnZeichnen();
  $("#text-form").addEventListener("submit", textAbsenden);
  // Enter im einzeiligen Suchfeld sucht; im Freitext macht es eine neue Zeile
  $("#freitext").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !meta.freitext) { ev.preventDefault(); $("#text-form").requestSubmit(); }
  });
  $("#ort-form").addEventListener("submit", ortAbsenden);
  $("#plz").addEventListener("input", startZuruecksetzen);
  // Bei der PLZ-Rückfrage startet die Wahl sofort; beim Wohnort aus dem Text erst "Stimmt so" (#115)
  $("#gemeinde").addEventListener("change", () => { if ($("#gemeinde").value && !wohnortAusText) ortAbsenden(); });
  $("#land").addEventListener("change", () => { if ($("#land").value) ortAbsenden(); });

  // "Beispiel laden" nur im Entwicklermodus (?dev)
  if (new URLSearchParams(location.search).has("dev")) {
    $("#beispiele").hidden = false;
    fuellen($("#szenario"), el("option", { value: "" }, "Beispiel wählen …"),
      ...meta.szenarien.map((s) => el("option", { value: s.id }, s.name)));
    $("#szenario").addEventListener("change", () => {
      const s = meta.szenarien.find((x) => x.id === $("#szenario").value);
      $("#szenario-text").textContent = s ? s.beschreibung : "";
    });
    $("#szenario-laden").addEventListener("click", async () => {
      const id = $("#szenario").value;
      if (!id) return;
      try {
        ausloesen("angaben-laden", await api(`/api/szenario/${encodeURIComponent(id)}`));
      } catch (e) {
        meldung(e.message);
      }
    });
  }
}
