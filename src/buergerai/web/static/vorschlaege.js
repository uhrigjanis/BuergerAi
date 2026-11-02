// Erkannte Angaben zur Bestätigung (#79): eigener Text mit markierten Belegen und
// eine bearbeitbare Liste. Nichts hiervon geht an die Engine, bevor der Nutzer bestätigt.
import { el } from "./gemeinsam.js";

let zaehler = 0;

// Text der Person mit <mark> an den Stellen, aus denen eine Angabe stammt
export function markierterText(text, vorschlaege) {
  const stellen = vorschlaege
    .map((v, i) => (v.stelle ? { von: v.stelle[0], bis: v.stelle[1], i } : null))
    .filter(Boolean)
    .sort((a, b) => a.von - b.von);
  const teile = [];
  let pos = 0;
  for (const s of stellen) {
    if (s.von < pos) continue;  // überlappende Belege: nur der erste wird markiert
    teile.push(text.slice(pos, s.von), el("mark", { "data-nr": String(s.i) }, text.slice(s.von, s.bis)));
    pos = s.bis;
  }
  teile.push(text.slice(pos));
  return teile;
}

function editor(v, id) {
  const unbekannt = el("option", { value: "unbekannt" }, "weiß nicht");
  if (v.typ === "ja_nein" || v.typ === "auswahl") {
    const optionen = v.typ === "ja_nein"
      ? [["true", "Ja"], ["false", "Nein"]]
      : v.optionen.map((o) => [o.wert, o.text]);
    const s = el("select", { id },
      optionen.map(([w, t]) => el("option", { value: w }, t)), unbekannt);
    s.value = String(v.wert);
    return s;
  }
  const typ = { datum: "date", zahl: "number" }[v.typ] || "text";
  const feld = el("input", { id, type: typ, inputmode: v.typ === "zahl" ? "decimal" : (v.typ === "ort" ? "numeric" : null),
    min: v.typ === "zahl" ? "0" : null, step: v.typ === "zahl" ? "any" : null });
  feld.value = v.wert === "unbekannt" ? "" : String(v.wert);
  return feld;
}

function wertAus(v, feld) {
  const roh = feld.value.trim();
  if (roh === "unbekannt" || roh === "") return "unbekannt";
  if (v.typ === "ja_nein") return roh === "true";
  if (v.typ === "zahl") {
    const z = Number(roh);
    if (!Number.isFinite(z) || z < 0) throw new Error(`Bitte eine Zahl ab 0 eingeben: ${v.frage}`);
    return z;
  }
  if (v.typ === "datum" && !/^\d{4}-\d{2}-\d{2}$/.test(roh)) throw new Error(`Bitte ein gültiges Datum wählen: ${v.frage}`);
  if (v.typ === "ort" && !/^(\d{5}|\d{8})$/.test(roh)) throw new Error(`Bitte eine fünfstellige Postleitzahl eingeben: ${v.frage}`);
  return roh;
}

// Liefert {element, werte}. werte() gibt nur die angehakten Angaben zurück und wirft bei
// ungültigen Eingaben einen Fehler mit verständlicher Meldung.
export function vorschlagsliste(vorschlaege, textElement) {
  const nr = ++zaehler;
  const zeilen = vorschlaege.map((v, i) => {
    const feldId = `vs-${nr}-${i}`;
    const haken = el("input", { type: "checkbox", checked: true, "aria-label": `Übernehmen: ${v.frage}` });
    const feld = editor(v, feldId);
    const zeile = el("li", { class: "vorschlag", "data-nr": String(i) },
      haken,
      el("div", { class: "vorschlag-inhalt" },
        el("label", { for: feldId }, v.person_name ? `${v.person_name}: ` : "", v.frage),
        feld,
        el("p", { class: "beleg" }, el("span", { class: "leise" }, "Aus Ihrem Text: "), el("q", {}, v.beleg)),
      ),
    );
    haken.addEventListener("change", () => {
      zeile.classList.toggle("abgewaehlt", !haken.checked);
      feld.disabled = !haken.checked;
    });
    // Beim Zeigen auf eine Angabe leuchtet ihre Stelle im Text auf
    const mark = () => textElement && textElement.querySelector(`mark[data-nr="${i}"]`);
    const an = () => { const m = mark(); if (m) m.classList.add("aktiv"); };
    const aus = () => { const m = mark(); if (m) m.classList.remove("aktiv"); };
    zeile.addEventListener("mouseenter", an);
    zeile.addEventListener("mouseleave", aus);
    zeile.addEventListener("focusin", an);
    zeile.addEventListener("focusout", aus);
    return { v, haken, feld, zeile };
  });
  const element = el("ul", { class: "vorschlaege" }, zeilen.map((z) => z.zeile));
  function werte() {
    const ergebnis = {};
    for (const z of zeilen) if (z.haken.checked) ergebnis[z.v.id] = wertAus(z.v, z.feld);
    return ergebnis;
  }
  return { element, werte };
}
