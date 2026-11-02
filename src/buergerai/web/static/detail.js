// Details einer Leistung (#86): auf großen Bildschirmen als Seitenpanel, am Handy als
// Vollbild. Ein <dialog> hält den Fokus und schließt mit Escape.
import { $, ERGEBNIS_TEXT, SYMBOL, datumText, el, ergebnisMarke, fuellen, sicherLink, sitzung } from "./gemeinsam.js";

let ausloeser = null;

function fristZeile(fr) {
  if (!fr.datum) {
    return el("li", {}, fr.text, fr.braucht_datum ? el("span", { class: "leise" }, " (Datum fehlt noch für die Berechnung)") : null);
  }
  const zusatz = [];
  if (fr.voraussichtlich) zusatz.push("voraussichtlich");
  if (fr.tage_bis < 0) zusatz.push(`vor ${-fr.tage_bis} Tagen`);
  else if (fr.tage_bis === 0) zusatz.push("heute");
  else zusatz.push(`in ${fr.tage_bis} Tagen`);
  return el("li", { class: fr.abgelaufen ? "abgelaufen" : (fr.bald ? "bald" : null) },
    el("strong", {}, `${fr.art_text} ${datumText(fr.datum)}`), ` (${zusatz.join(", ")})`,
    fr.abgelaufen ? ", abgelaufen" : "", `: ${fr.text}`);
}

function gruendeListe(gruende) {
  if (!gruende.length) return el("ul", { class: "gruende" }, el("li", { class: "ja" }, el("span", { class: "sym", "aria-hidden": "true" }, "✓"), "Keine besonderen Voraussetzungen"));
  return el("ul", { class: "gruende" }, gruende.map((g) => el("li", { class: g.ergebnis },
    el("span", { class: "sym", "aria-hidden": "true" }, g.art === "pruefung_noetig" ? "!" : SYMBOL[g.ergebnis]),
    el("span", { class: "unsichtbar" }, `${ERGEBNIS_TEXT[g.ergebnis]}: `),
    g.art === "pruefung_noetig" ? `Prüfung nötig: ${g.text}` : g.text,
    g.fehlt ? el("span", { class: "angabe" }, ` – Angabe fehlt: ${g.fehlt}`) : null,
    g.angabe ? el("span", { class: "angabe" }, ` – Ihre Angabe: ${g.angabe === "unbekannt" ? "weiß nicht" : g.angabe}`) : null,
  )));
}

function abschnitt(titel, ...inhalt) {
  return el("section", { class: "detail-abschnitt" }, el("h3", {}, titel), inhalt);
}

export function detailOeffnen(id) {
  const b = sitzung.bericht;
  const l = b.leistungen.find((x) => x.id === id);
  if (!l) return;
  ausloeser = document.activeElement;
  const relevant = l.ergebnis !== "nein";
  const v = l.verfahren;
  const mehrPersonen = l.personen.length > 1 || l.personen[0].person !== null;
  const warumTitel = { ja: "Warum Ja?", unklar: "Warum noch unklar?", nein: "Warum Nein?" }[l.ergebnis];

  const dialog = $("#detail");
  fuellen(dialog,
    el("div", { class: "detail-kopf" },
      el("h2", { id: "detail-titel" }, l.name),
      el("button", { type: "button", class: "schliessen", onclick: () => dialog.close() }, "Schließen")),
    el("div", { class: "detail-inhalt" },
      el("p", {}, ergebnisMarke(l.ergebnis), " ", l.kurz),
      l.anspruch_hinweis ? el("p", { class: "hinweis" }, l.anspruch_hinweis) : null,
      l.hinweise.map((h) => el("p", { class: "hinweis" }, h)),
      el("dl", { class: "fakten-liste" },
        mehrPersonen ? [el("dt", {}, "Für"), el("dd", {}, l.personen.map((p, i) => [i ? ", " : "", `${p.name}: `, ERGEBNIS_TEXT[p.ergebnis]]))] : null,
        l.beantragt_hinweis ? [el("dt", {}, "Wer beantragt"), el("dd", {}, l.beantragt_hinweis)] : null,
        [el("dt", {}, "Zuständig"), el("dd", {},
          l.zustaendigkeit.url ? sicherLink(l.zustaendigkeit.url, l.zustaendigkeit.name) : l.zustaendigkeit.name,
          l.zustaendigkeit.beschreibung ? el("div", { class: "leise" }, l.zustaendigkeit.beschreibung) : null)],
        relevant && l.betrag ? [el("dt", {}, "Betrag"), el("dd", {}, l.betrag)] : null,
        relevant && l.voraussetzungen.length ? [el("dt", {}, "Vorher erledigen"), el("dd", {}, l.voraussetzungen.join(", "))] : null,
      ),
      relevant && l.fristen.length ? abschnitt(l.fristen.length > 1 ? "Fristen" : "Frist", el("ul", { class: "fristen" }, l.fristen.map(fristZeile))) : null,
      relevant && (v.schritte.length || v.kosten || v.online_url || v.hinweise.length)
        ? abschnitt("So geht's",
          v.schritte.length ? el("ol", {}, v.schritte.map((s) => el("li", {}, s))) : null,
          v.kosten ? el("p", {}, el("strong", {}, "Kosten: "), v.kosten) : null,
          v.online_url ? el("p", {}, el("strong", {}, "Online: "), sicherLink(v.online_url)) : null,
          v.hinweise.map((h) => el("p", { class: "hinweis" }, h)))
        : null,
      relevant && v.unterlagen.length ? abschnitt("Unterlagen", el("ul", {}, v.unterlagen.map((u) => el("li", {}, u)))) : null,
      abschnitt(warumTitel, l.personen.map((p) => [
        mehrPersonen && l.personen.length > 1 ? el("p", { class: "person-titel" }, p.name) : null, gruendeListe(p.gruende)])),
      abschnitt("Quellen und Datenstand",
        el("p", { class: "leise" }, `${l.gebiet.ebene_text} ${l.gebiet.name}: ${l.abdeckung_text}, ${l.pruef_text}`),
        el("ul", { class: "quellen" }, l.quellen.map((q) => el("li", {},
          q.url ? sicherLink(q.url, q.titel) : q.titel, el("span", { class: "leise" }, ` (${q.pruefstatus})`),
          q.seit_pruefung_geaendert
            ? el("span", { class: "geaendert" }, ` – seit der Prüfung geändert (festgestellt am ${datumText(q.seit_pruefung_geaendert)})`)
            : null)))),
    ));
  dialog.showModal();
  dialog.querySelector(".detail-inhalt").scrollTop = 0;
}

export function detailEinrichten() {
  const dialog = $("#detail");
  dialog.addEventListener("close", () => { if (ausloeser && ausloeser.isConnected) ausloeser.focus(); });
  // Klick auf den abgedunkelten Hintergrund schließt
  dialog.addEventListener("click", (ev) => { if (ev.target === dialog) dialog.close(); });
}
