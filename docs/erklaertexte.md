# Erklärtexte und Glossar (#113)

Erklärtexte sagen verständlich, **was eine Leistung ist** und **was nach dem Antrag passiert**. Sie kommen aus geprüften Texten in der Wissensbasis, nicht aus dem Modellwissen eines LLM. Die Web-Oberfläche zeigt sie unter „Was ist das?“, das Terminal mit `--details`, und der Antworttext (LLM oder Vorlage) baut auf ihnen auf.

## Ablage

| Was | Wo |
|---|---|
| Erklärtext je Leistung | `data/fachmodule/<id>/erklaerungen.json`, in einem Modul, zu dem die Leistung gehört |
| Fachbegriffe | `data/kern/glossar.json`, jeder Begriff einmal |

Ein Eintrag in `erklaerungen.json`:

```json
{
  "leistung_id": "kindergeld",
  "was": "Was die Leistung ist und für wen (zwei bis vier Sätze).",
  "danach": "Was nach dem Antrag passiert (optional).",
  "achtung": "Typische Stolpersteine (optional).",
  "begriffe": ["familienkasse", "steuer_id"],
  "quellen": ["estg_62", "ba_kindergeld"],
  "pruefstatus": "ungeprueft"
}
```

Beide Dateien sind maschinell formatiert (zwei Leerzeichen Einrückung, Umlaute unverändert). Nach Änderungen von Hand: `./bai erklaerungen --formatieren`.

## Regeln für die Texte

`./bai daten` prüft sie beim Laden. Ein Verstoß ist ein Fehler.

- **Keine Zahlen.** Keine Ziffern, keine Mengen wie „drei Wochen“ oder „ersten Lebensjahr“, keine Beträge („Euro“, „Prozent“). Beträge, Fristen und Grenzen stehen strukturiert in Leistung und Variante und ändern sich dort. So veraltet kein Erklärtext unbemerkt. Statt „innerhalb von drei Wochen“ also „Die Frist ist kurz“; die genaue Frist zeigt der Bericht.
- **Keine Paragraphen und Links.** Die Rechtsgrundlage steht in den Quellen, Links setzt das Programm.
- **Keine Zusagen.** Nicht „sicher“, nicht „Sie bekommen …“, „Sie haben Anspruch“ oder „steht Ihnen zu“. Ob ein Anspruch besteht, sagt allein die Engine. Neutral formulieren: „Kindergeld gibt es für …“, „Wer …, kann …“. Die Regel unterscheidet nicht zwischen Groß- und Kleinschreibung, genau wie die Nachprüfung der Antworttexte.
- **Allgemein für alle Länder.** Der Text gilt für die Leistung, nicht für eine Variante. Was in einem Land anders ist, gehört in die `hinweise` der Variante.
- **Kurz und klar.** `was` 40–450 Zeichen, `danach` bis 400, `achtung` bis 350, Glossar 40–320. Kurze Sätze; Fachbegriffe über das Glossar erklären statt im Text.
- **Mit Quelle.** Mindestens eine Quelle je Text. Fehlt eine geeignete Quelle, bleibt die Leistung lieber ohne Erklärtext (`./bai daten` warnt).

## Prüfen und abnehmen

Der Prüfstatus gilt für den **Text**, nicht für die Quellen: Eine verifizierte Quelle macht einen ungeprüften Erklärtext nicht richtig.

1. Offene Texte anzeigen: `./bai erklaerungen --offen` (mit Texten und Quellen: `--text`, einzelne: `./bai erklaerungen elterngeld bescheid`).
2. Jeden Satz mit den Quellen vergleichen. Stimmt etwas nicht: in der JSON-Datei korrigieren, `./bai daten` laufen lassen.
3. Abnehmen: `./bai erklaerungen --abnehmen elterngeld --von "Vorname Nachname"` (Datum: `--am TT.MM.JJJJ`, Standard heute). Das setzt `verifiziert` mit Name und Datum.
4. Zurücknehmen, z. B. nach einer Gesetzesänderung: `./bai erklaerungen --zuruecksetzen elterngeld` (Status `ungeprueft`, oder `--status teilweise`).

`verifiziert` setzt nur ein Mensch (ANF-QS-02). Claude legt Entwürfe höchstens als `teilweise` an.

Erklärtexte und Glossarbegriffe erscheinen in `./bai quellen --verwendung ID` und damit auch in neu angelegten Prüfprotokollen. Wer eine Quelle prüft, sieht also auch die Texte, die sich auf sie stützen.

## Stand

Alle 101 Leistungen haben einen Erklärtext, dazu 59 Glossarbegriffe. Alle sind `ungeprueft`: Sie wurden aus den vorhandenen Daten der Wissensbasis (Kurztext, Schritte, Hinweise, Quellen) und allgemeinem Wissen entworfen. Die amtlichen Seiten waren aus der Entwicklungsumgebung nicht abrufbar. Vor dem Betrieb (#6) sollte jeder Text abgenommen sein, zuerst die der Lebenslagen mit den meisten Nutzern.
