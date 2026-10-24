"""Fachregeln für das Lebensereignis Geburt (Bund + Pilotland Bayern)."""

from datetime import date

import pytest

from buergerai.regeln import Wert
from conftest import familie


def ergebnis(bericht, leistung, person=None):
    e = bericht.eintrag(leistung)
    if person is None:
        return e.ergebnis.value
    return next(p.schritt.wert.value for p in e.personen if p.person == person)


@pytest.mark.anforderung("ANF-GA-01")
def test_geburtsanzeige(plane):
    b = plane({"kind_geboren": "ja", "geburtsdatum": "2026-10-20"})
    e = b.eintrag("geburtsanzeige")
    assert e.ergebnis is Wert.JA
    assert e.fristen[0].datum == date(2026, 10, 27)


@pytest.mark.anforderung("ANF-VA-01")
@pytest.mark.parametrize("verheiratet,erwartet", [("ja", "nein"), ("nein", "ja")])
def test_vaterschaft_und_sorge(plane, verheiratet, erwartet):
    b = plane(familie(eltern_verheiratet=verheiratet))
    assert ergebnis(b, "vaterschaftsanerkennung") == erwartet
    assert ergebnis(b, "sorgeerklaerung") == erwartet


@pytest.mark.anforderung("ANF-MU-01")
@pytest.mark.parametrize(
    "kv,beschaeftigt,krankengeld,erwartet",
    [
        ("gesetzlich_mitglied", "ja", None, "ja"),
        ("gesetzlich_mitglied", "nein", "ja", "ja"),
        ("gesetzlich_mitglied", "nein", "nein", "nein"),
        ("gesetzlich_mitglied", "nein", None, "unklar"),
        ("privat", "ja", None, "nein"),
        ("gesetzlich_familienversichert", "ja", None, "nein"),
    ],
)
def test_mutterschaftsgeld_krankenkasse(plane, kv, beschaeftigt, krankengeld, erwartet):
    b = plane(familie(mutter__krankenversicherung=kv, mutter__beschaeftigt=beschaeftigt,
                      mutter__krankengeldanspruch=krankengeld))
    assert ergebnis(b, "mutterschaftsgeld_krankenkasse") == erwartet


@pytest.mark.anforderung("ANF-MU-02")
@pytest.mark.parametrize(
    "kv,beschaeftigt,erwartet",
    [("privat", "ja", "ja"), ("gesetzlich_familienversichert", "ja", "ja"),
     ("gesetzlich_mitglied", "ja", "nein"), ("privat", "nein", "nein")],
)
def test_mutterschaftsgeld_bas(plane, kv, beschaeftigt, erwartet):
    b = plane(familie(mutter__krankenversicherung=kv, mutter__beschaeftigt=beschaeftigt))
    assert ergebnis(b, "mutterschaftsgeld_bas") == erwartet


@pytest.mark.anforderung("ANF-MU-03")
@pytest.mark.parametrize("beschaeftigt,erwartet", [("ja", "ja"), ("nein", "nein")])
def test_arbeitgeberzuschuss(plane, beschaeftigt, erwartet):
    assert ergebnis(plane(familie(mutter__beschaeftigt=beschaeftigt)), "arbeitgeberzuschuss_mutterschaftsgeld") == erwartet


@pytest.mark.anforderung("ANF-EZ-01", "ANF-ENG-08")
def test_elternzeit_je_elternteil(plane):
    b = plane(familie(partner__beschaeftigt="nein"))
    assert ergebnis(b, "elternzeit", "mutter") == "ja"
    assert ergebnis(b, "elternzeit", "partner") == "nein"
    assert ergebnis(b, "elternzeit") == "ja"


@pytest.mark.anforderung("ANF-EG-01")
@pytest.mark.parametrize("zve,erwartet", [(175000, "ja"), (175001, "nein")])
def test_elterngeld_grenze_2025(plane, zve, erwartet):
    b = plane(familie(errechneter_termin="2026-12-15", zve_eltern=zve))
    assert ergebnis(b, "elterngeld") == erwartet


@pytest.mark.anforderung("ANF-EG-02", "ANF-ENG-07")
@pytest.mark.parametrize(
    "geburt,zve,erwartet",
    [("2025-03-31", 190000, "ja"), ("2025-04-01", 190000, "nein"), ("2024-04-01", 200000, "ja"),
     ("2024-04-01", 200001, "nein"), ("2024-03-31", 100000, "unklar")],
)
def test_elterngeld_grenze_2024(plane, geburt, zve, erwartet):
    b = plane(familie(kind_geboren="ja", errechneter_termin=None, geburtsdatum=geburt, zve_eltern=zve),
              stichtag=date(2025, 6, 1))
    assert ergebnis(b, "elterngeld") == erwartet


@pytest.mark.anforderung("ANF-EG-03")
@pytest.mark.parametrize("stunden,erwartet", [(32, "ja"), (32.5, "nein"), (0, "ja")])
def test_elterngeld_stunden(plane, stunden, erwartet):
    b = plane(familie(partner__erwerbsstunden_nach_geburt=stunden))
    assert ergebnis(b, "elterngeld", "partner") == erwartet


@pytest.mark.anforderung("ANF-EG-04")
def test_elterngeld_drittstaat_unklar(plane):
    b = plane(familie(partner__staatsangehoerigkeit="andere"))
    assert ergebnis(b, "elterngeld", "partner") == "unklar"
    assert ergebnis(b, "elterngeld", "mutter") == "ja"


@pytest.mark.anforderung("ANF-EG-05")
def test_elterngeld_alleinerziehend(plane):
    b = plane(familie(partner_im_haushalt="nein"))
    assert [p.person for p in b.eintrag("elterngeld").personen] == ["mutter"]
    assert [p.person for p in plane(familie()).eintrag("elterngeld").personen] == ["mutter", "partner"]


@pytest.mark.anforderung("ANF-EG-06")
def test_elterngeld_frist(plane):
    b = plane(familie(kind_geboren="ja", geburtsdatum="2026-10-15", errechneter_termin=None))
    assert b.eintrag("elterngeld").fristen[0].datum == date(2027, 1, 14)


@pytest.mark.anforderung("ANF-KG-01")
def test_kindergeld_betrag(plane):
    assert "259 €" in plane(familie()).eintrag("kindergeld").betrag.text


@pytest.mark.anforderung("ANF-KG-02")
@pytest.mark.parametrize(
    "mutter,partner,im_haushalt,erwartet",
    [("deutsch", "andere", "ja", "ja"), ("andere", "eu_ewr_ch", "ja", "ja"),
     ("andere", "andere", "ja", "unklar"), ("andere", None, "nein", "unklar")],
)
def test_kindergeld_staatsangehoerigkeit(plane, mutter, partner, im_haushalt, erwartet):
    b = plane(familie(mutter__staatsangehoerigkeit=mutter, partner__staatsangehoerigkeit=partner,
                      partner_im_haushalt=im_haushalt))
    assert ergebnis(b, "kindergeld") == erwartet


@pytest.mark.anforderung("ANF-KG-03")
def test_kindergeld_frist(plane):
    b = plane(familie(kind_geboren="ja", geburtsdatum="2026-08-31", errechneter_termin=None))
    assert b.eintrag("kindergeld").fristen[0].datum == date(2027, 2, 28)


@pytest.mark.anforderung("ANF-KV-01")
@pytest.mark.parametrize(
    "mutter,partner,verheiratet,erwartet",
    [
        ("gesetzlich_mitglied", "gesetzlich_mitglied", "ja", "ja"),
        ("gesetzlich_mitglied", "privat", "ja", "unklar"),
        ("privat", "gesetzlich_mitglied", "ja", "unklar"),
        ("privat", "gesetzlich_mitglied", "nein", "ja"),
        ("privat", "privat", "ja", "nein"),
        ("privat", "privat", "nein", "nein"),
    ],
)
def test_familienversicherung(plane, mutter, partner, verheiratet, erwartet):
    b = plane(familie(mutter__krankenversicherung=mutter, partner__krankenversicherung=partner,
                      eltern_verheiratet=verheiratet))
    assert ergebnis(b, "familienversicherung_kind") == erwartet


@pytest.mark.anforderung("ANF-KZ-01", "ANF-ENG-05")
@pytest.mark.parametrize(
    "brutto,partner,erwartet",
    [(899, "ja", "nein"), (900, "ja", "unklar"), (599, "nein", "nein"), (600, "nein", "unklar")],
)
def test_kinderzuschlag(plane, brutto, partner, erwartet):
    b = plane(familie(brutto_haushalt_monat=brutto, partner_im_haushalt=partner))
    assert ergebnis(b, "kinderzuschlag") == erwartet


@pytest.mark.anforderung("ANF-BY-01")
def test_elterngeld_bayern_zbfs(plane):
    assert "ZBFS" in plane(familie()).eintrag("elterngeld").zustaendigkeit.name
    assert "Bundeslandes" in plane(familie(), plz=None, land="HE").eintrag("elterngeld").zustaendigkeit.name


@pytest.mark.anforderung("ANF-BY-02")
@pytest.mark.parametrize(
    "geburt,erwartet",
    [("2024-12-31", "ja"), ("2025-01-01", "unklar"), ("2026-08-31", "unklar"), ("2026-09-01", "nein")],
)
def test_familiengeld(plane, geburt, erwartet):
    b = plane({"kind_geboren": "ja", "geburtsdatum": geburt})
    assert ergebnis(b, "bayerisches_familiengeld") == erwartet


@pytest.mark.anforderung("ANF-BY-03")
def test_standesamt_muenchen_und_freising(plane):
    assert plane(familie()).eintrag("geburtsanzeige").zustaendigkeit.id == "standesamt_muenchen"
    freising = plane(familie(), plz="85356").eintrag("geburtsanzeige")
    assert freising.zustaendigkeit.id == "standesamt_geburtsort"
    assert freising.variante.hinweise
