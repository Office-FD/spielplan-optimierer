# Backlog – Spielplan-Optimierer

Funktionswünsche und Fehlerberichte für den Spielplan-Optimierer von FD.
Einträge werden über die App eingereicht und hier gesammelt.

---

## Felder je Eintrag

| Feld | Bedeutung |
|---|---|
| **Typ** | Neue Funktion / Verbesserung / Fehler/Bug |
| **Bereich** | Welcher Teil der App ist betroffen |
| **Wichtigkeit** | Kleiner Wunsch / Wichtig für Alltag / Blocker |
| **Titel** | Kurze Zusammenfassung (1 Satz) |
| **Beschreibung** | Was soll passieren? Was ist das Problem? Welcher Schritt? |
| **Kontakt** | Optional: E-Mail für Rückfragen |
| **Status** | Offen / In Bearbeitung / Erledigt / Zurueckgestellt |

---

## Einträge

<!-- Neue Einträge werden hier automatisch von der App angehängt -->

---

### [intern]Druckansicht Liga: Fehlende Phase-Spalte in „Alle Spiele"-Tabelle verschiebt Spaltenausrichtung

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
In der HTML-Druckansicht (z. B. `Spielplan_LIGA_1_druckbar.html`) enthält der `<thead>` der „Alle Spiele"-Tabelle acht Spalten: ST, KW, Datum, Phase, Uhrzeit, Heimteam, Gastteam, Ausrichter. In den Datenzeilen (`<tbody>`) werden ST, KW und Datum per `rowspan` zusammengefasst, die Spalte **Phase** wird jedoch nicht als `<td>` ausgegeben. Dadurch verschiebt sich jede nachfolgende Zelle (Uhrzeit, Heimteam, Gastteam, Ausrichter) um eine Position nach links und steht unter der falschen Überschrift. Fix: In jeder Spielzeile ein `<td>` für die Phase einfügen (z. B. „Hinrunde" / „Rückrunde"), analog zur Umsetzung in den teamspezifischen Tabellen weiter unten im Dokument, wo die Phase-Spalte korrekt befüllt wird.
**Status:** Erledigt

---

### [intern] iCal-Export pro Team

**Typ:** Neue Funktion  
**Bereich:** Excel-Export  
**Wichtigkeit:** Wichtig für Alltag  
**Aufwand:** Klein  
**Beschreibung:**  
Jedes Team bekommt nach der Optimierung eine `.ics`-Datei zum Download, die direkt in Google Calendar, Outlook oder Apple Calendar importiert werden kann. Das Grundgerüst ist bereits in `schedule_utils.py` vorhanden (PRODID, VCALENDAR-Struktur). Erweiterung: pro Liga/Team eine separate Datei generieren, alle in einer ZIP bündeln.  
**Status:** Erledigt

---

### [intern] Spielplan-Druckansicht (HTML/PDF)

**Typ:** Neue Funktion  
**Bereich:** Excel-Export  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Klein  
**Beschreibung:**  
Vereinfachte Druckansicht pro Liga als HTML oder PDF – ohne Solver-Metadaten, nur Spieltag/Datum/Heim/Gast. Direkt aus der App herunterzuladen. Zielgruppe: Vereinsverantwortliche die keinen Excel-Viewer haben.  
**Status:** Erledigt

---

### [intern] Warnungen bei unausgewogenen Plänen im Excel

**Typ:** Verbesserung  
**Bereich:** Excel-Export  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Klein  
**Beschreibung:**  
Nach der Optimierung werden auffällige Konstellationen farbig markiert oder als Hinweis-Sheet ausgegeben: z. B. „Team X hat 4× Auswärts in Folge", „Team Y hat 0 Heimspiele in den letzten 5 Spieltagen". Hilft beim schnellen Qualitätscheck ohne manuelles Durchsuchen.  
**Status:** Erledigt

---

### [intern] DST-Blöcke aus Kalender-Excel automatisch vorschlagen

**Typ:** Verbesserung  
**Bereich:** Kalender / Termine  
**Wichtigkeit:** Wichtig für Alltag  
**Aufwand:** Klein  
**Beschreibung:**  
Aktuell müssen DST-Blöcke (Doppelspieltage) manuell eingetragen werden. Der Rahmenterminplan-Parser in `calendar_parser.py` kann bereits Spieltage einlesen. Erweiterung: direkt aufeinanderfolgende Wochenend-Spieltage (Sa+So) automatisch als DST-Vorschlag markieren, den der Nutzer bestätigen oder ablehnen kann.  
**Status:** Erledigt

---

### [intern] Manuelle Nachbearbeitung des Spielplans

**Typ:** Neue Funktion  
**Bereich:** Spielplan-Optimierung  
**Wichtigkeit:** Wichtig für Alltag  
**Aufwand:** Mittel  
**Beschreibung:**  
Nach der Optimierung sollen einzelne Spiele manuell auf einen anderen Spieltag verschoben werden können (Dropdown oder Drag-and-drop in der App). Die App prüft dabei ob die wichtigsten Constraints (jedes Team max. 1 Spiel/Tag, DST-Konsistenz) noch eingehalten werden und zeigt Konflikte an. Ergebnis wird in den Download übernommen.  
**Status:** Erledigt

---

### [intern] Spielplan-Vergleich zweier Konfigurationen

**Typ:** Neue Funktion  
**Bereich:** Spielplan-Optimierung  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Mittel  
**Beschreibung:**  
Zwei zuvor gespeicherte Konfiguration-Excels hochladen. App zeigt die Kennzahlen beider Läufe nebeneinander: Gesamtkilometer, Heimrechtswechsel, Fairness-Score, Laufzeit. Erleichtert die Entscheidung welche Variante übernommen wird.  
**Status:** Erledigt

---

### [intern] Spielabsagen und Nachholspiele

**Typ:** Neue Funktion  
**Bereich:** Spielplan-Optimierung  
**Wichtigkeit:** Wichtig für Alltag  
**Aufwand:** Mittel  
**Beschreibung:**  
Bestehenden Spielplan laden, ein ausgefallenes Spiel markieren. Die App sucht aus den verbleibenden freien Slots (Spieltage an denen eines der beiden Teams noch kein Spiel hat) einen geeigneten Nachholtermin und schlägt diesen vor. Export als aktualisierter Spielplan.  
**Status:** Erledigt

---

### [intern] Interaktive Kalenderansicht im Browser

**Typ:** Neue Funktion  
**Bereich:** Excel-Export  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Groß  
**Beschreibung:**  
Spielplan nach der Optimierung als klickbaren Monatskalender direkt in der App anzeigen (z. B. mit der Streamlit-Komponente `streamlit-calendar`). Spiele sind farblich nach Liga/Team kodiert, Klick zeigt Details (Heim/Gast/Ort). Ersetzt den Excel-Export nicht, bietet aber schnellen Überblick.  
**Status:** Offen

---

### [intern] Karten-Visualisierung der Reiserouten

**Typ:** Neue Funktion  
**Bereich:** Distanzen / Karte  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Groß  
**Beschreibung:**  
Reiserouten pro Spieltag auf einer interaktiven Karte einblenden (Folium oder Leaflet via streamlit-folium). Standorte der Teams als Pins, Verbindungen zeigen welches Team wohin reist. Kann helfen Ausreißer-Spieltage mit ungewöhnlich langen Wegen zu identifizieren.  
**Status:** Offen

---

### [intern] Multi-Saison-Planung

**Typ:** Neue Funktion  
**Bereich:** Spielplan-Optimierung  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Groß  
**Beschreibung:**  
Hin- und Rückrunde als separate Konfigurationen planen, die sich eine Distanzmatrix teilen. Heimrechts-Wechsel werden über beide Saisons hinweg konsistent gehalten (Team das Saison 1 viel Heimrecht hatte, bekommt Saison 2 mehr Auswärtsspiele). Erfordert Erweiterung der LeagueConfig und des Solver-Modells.  
**Status:** Offen

---

### [intern] REST-API für externe Integration

**Typ:** Neue Funktion  
**Bereich:** Sonstiges  
**Wichtigkeit:** Kleiner Wunsch  
**Aufwand:** Groß  
**Beschreibung:**  
Konfiguration per JSON-Request übergeben, optimierten Spielplan per JSON zurückbekommen. Ermöglicht Integration in Vereinsverwaltungssoftware oder andere FD-interne Systeme ohne Streamlit-UI. Technische Basis: FastAPI neben der bestehenden Streamlit-App, teilt sich die `spielplan_multi`-Pipeline.  
**Status:** Offen

---

### [2026-04-29 12:44] Verbesserung – Kontrolle Heimrechtswechsel Turniertag

**Typ:** Verbesserung  
**Bereich:** Spielplan-Optimierung  
**Wichtigkeit:** Kleiner Wunsch  
**Beschreibung:**  
Beim Modus Turniertag ist der alternierende Wechsel von Heimrechten nicht so wichtig, da sowieso mehrere Teams zu einem Ausrichter fahren und das Heimrecht da nur auf dem Papier existiert. Wichtig sind da nur, dass am Ende der Saison alle Teams gleiche Anzahl an Heim- wie Auswärtsbegegnungen habe und im besten fall der Ausrichter eines Spieltages an diesem immer Heimrecht hat.

**Status:** Erledigt

---

### [intern] Tests für _balance_home_away() in tt_scheduler.py

**Typ:** Verbesserung
**Bereich:** Tests
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Die neue Funktion `_balance_home_away()` (tt_scheduler.py, Zeile 23-63) hat keine Tests. Folgende Fälle abdecken: (1) Nach Aufruf ist max(home_count) - min(home_count) <= 1, (2) Ausrichter-Spiele werden nicht angetastet, (3) Edge-Case: kein Ausrichter definiert.
**Status:** Erledigt

---

### [intern] Tests für build_print_html() Phase-Spalten-Fix

**Typ:** Verbesserung
**Bereich:** Tests
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`build_print_html()` (schedule_utils.py) hat keinen Test der die korrekte Spaltenanzahl in der „Alle Spiele"-Tabelle prüft. Regressionsschutz für den Phase-Spalten-Bug: Header-Count == td-Count je Zeile, Phase-Spalte vorhanden, Tabelle mit/ohne DST/Datum/Uhrzeiten korrekt.
**Status:** Erledigt

---

### [intern] Excel-Upload Fehlerbehandlung robuster machen

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`pd.read_excel()` in app.py (Zeilen ~125, ~565, ~892) kann bei beschädigten XLSX-Dateien die Streamlit-Session crashen ohne User-Feedback. Spezifische Exceptions abfangen: `zipfile.BadZipFile` (korrupte Datei), `ValueError` (Sheet nicht gefunden), Out-of-Memory via `nrows`-Limit. Nutzer soll klare Fehlermeldung sehen.
**Status:** Erledigt

---

### [intern] .gitattributes hinzufügen (CRLF-Konsistenz)

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Bei jedem Commit auf Windows erscheinen CRLF-Warnungen. `.gitattributes` mit `*.py text eol=lf`, `*.bat text eol=crlf`, `*.xlsx binary` etc. beseitigt das dauerhaft.
**Status:** Offen

---

### [intern] Code-Duplikation in Excel-Ladefunktionen

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Mittel
**Beschreibung:**
`_parse_club_upload()`, `_load_teams_excel()` und `_load_full_config_excel()` in app.py haben alle dasselbe Pattern (pd.read_excel + fillna + strip columns + Exception-Handling). In eine gemeinsame Hilfsfunktion `_load_excel_safe()` zusammenführen.
**Status:** Erledigt – _load_excel_safe() extrahiert; _parse_club_upload und _load_teams_excel nutzen sie. _load_full_config_excel verwendet pd.ExcelFile (anderes Muster, nicht refactored).

---

### [intern] Google Maps API: KeyError bei malformed Response

**Typ:** Fehler/Bug
**Bereich:** Distanzen / Karte
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
In `distances.py` kann `el['distance']['value']` einen KeyError werfen wenn die API eine unvollständige Response liefert (z.B. Status != OK). Pro Element try/except mit Fallback auf UNREACHABLE_KM einbauen.
**Status:** Erledigt

---

### [intern] create_overview_doc.py dokumentieren oder einordnen

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`create_overview_doc.py` (434 Zeilen, generiert DOCX) ist nicht in CLAUDE.md erwähnt und `python-docx` fehlt in requirements.txt. Klären: produktionsrelevant → dokumentieren + requirements ergänzen; oder Wegwerfcode → in BACKLOG archivieren.
**Status:** Erledigt – Standalone-Skript (kein Teil der App-Pipeline), in CLAUDE.md §2 dokumentiert. python-docx bleibt bewusst außerhalb von requirements.txt.

---

### [intern] wizard.py Legacy-Status klären

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`wizard.py` ist in CLAUDE.md als "Legacy CLI-Wizard" markiert, aber ungeklärt ob noch genutzt. Prüfen ob `__main__.py` noch importiert → falls nicht: entweder löschen oder in CLAUDE.md als "nur für Notfall ohne Streamlit" dokumentieren.
**Status:** Erledigt – wizard.py ist aktiv: main.py importiert run_wizard(), Einstieg via python -m spielplan_multi. In CLAUDE.md §2 als CLI-Alternative korrekt dokumentiert.

---

### [intern] CLAUDE.md Dateistruktur vervollständigen

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Folgende Dateien fehlen in der Dateistruktur (§2): `test_features.py`, `config_validator.py`. Je eine Zeile mit Kurzbeschreibung ergänzen.
**Status:** Erledigt – test_features.py, config_validator.py, main.py, __main__.py, create_overview_doc.py alle in §2 ergänzt.

---

### [intern] Style-Cleanup: _clubs_excel_bytes und io-Import (app.py)

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Zwei Style-Punkte aus PR #7-Review:
1. `_clubs_excel_bytes()` ist aktuell innerhalb von `_sidebar()` definiert (wird bei jedem Render neu erstellt). Sollte wie `_parse_club_upload` und `_load_excel_safe` auf Modulebene liegen.
2. `import io as _io` steht innerhalb der Funktion – `io` ist stdlib und immer verfügbar, Import auf Modulebene verschieben, `_io`-Alias entfernen.
**Status:** Offen

---

## Code-Review-Befunde Mai 2026 (8-teiliger vollständiger Review)

> Alle kritischen (9), hohen (8), mittleren (7) und niedrigen (7) Bugs wurden behoben.
> Stand: 2026-05-04

---

### [intern] M1 – config_validator: DST-Routing-Prüfung bei gesperrten DST-Tagen zu grob

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`config_validator.py` Z.155–185: Die Prüfung ob DST-Routing-Constraints erfüllbar sind, schaut nur ob *irgendein* DST-Tag gesperrt ist, unterscheidet aber nicht ob Tag 1 oder Tag 2 des DST-Blocks gesperrt ist. Das erzeugt Falsch-Positive: eine Warnung erscheint obwohl der Solver die Situation korrekt lösen kann (Routing-Constraint gilt nur für Tag 1 → Tag 2, nicht umgekehrt). Fix: Prüfung auf den konkret betroffenen Tag eingrenzen.
**Status:** Erledigt

---

### [intern] M2 – multi_solver: Co-Home nimmt immer ersten Spieltag einer KW

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`multi_solver.py` `_add_cohome_constraints()`: Bei KWs mit mehreren Spieltagen einer Liga wird immer `sts[0]` (der erste Spieltag) als Referenz für die Co-Home-Variable verwendet. Wenn die Liga an dieser KW zwei Spieltage hat (z.B. DST), kann der zweite Spieltag heimrechtlich anders belegt sein. Fix: alle Spieltage der KW berücksichtigen oder die Logik explizit auf den relevanten Spieltag fokussieren.
**Status:** Erledigt

---

### [intern] M3 – config: TEAM_COLORS KeyError ab 20 Teams

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`config.py` `get_team_color()`: Das Farb-Dictionary hat Einträge für Index 0–19. Bei Ligen mit ≥ 20 Teams wirft `TEAM_COLORS[idx]` einen `KeyError`. Fix: `.get(idx % len(TEAM_COLORS), '#CCCCCC')` oder die Farbpalette per Modulo-Wrap zirkulieren.
**Status:** Erledigt

---

### [intern] M4 – distances: Meter→km per Truncation statt Rounding

**Typ:** Fehler/Bug
**Bereich:** Distanzen / Karte
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`distances.py`: Die Umrechnung von Metern (Google Maps API) in km verwendet ganzzahlige Division (`// 1000`), was systematisch abrundet. Bei Distanzen nahe einem km-Schwellwert (z.B. 999 m → 0 km) kann das zu 0 km führen. Fix: `round(meters / 1000)` oder `math.ceil` je nach gewünschtem Verhalten.
**Status:** Erledigt

---

### [intern] M5 – calendar_parser: week_start/week_end ohne Jahreszahl

**Typ:** Fehler/Bug
**Bereich:** Kalender / Termine
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`calendar_parser.py`: `week_start` und `week_end` werden als Strings ohne Jahr gespeichert (z.B. "14.01." statt "14.01.2026"). Im Excel-Export und in der Co-Home-Übersicht werden diese Werte direkt angezeigt – bei Jahreswechsel (Spieltag im Dezember/Januar) fehlt der Jahreskontext vollständig. Fix: Jahr aus dem Kalender-Context mitführen und im Format "14.01.2026" speichern.
**Status:** Erledigt

---

### [intern] M6 – app.py: Log-Parsing per Substring → Falsch-Positive bei ähnlichen Liga-IDs

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`app.py` `_diagnose_infeasible_league()` und verwandte Stellen: Log-Zeilen werden per `lid in log_line` (Substring-Suche) einer Liga zugeordnet. Liga-IDs wie "BL" und "BL2" führen dazu, dass BL2-Logs auch BL zugeordnet werden. Fix: Regex-Wortgrenze (`r'\b' + re.escape(lid) + r'\b'`) oder eindeutiges Präfix-/Suffix-Format in den Log-Ausgaben verwenden.
**Status:** Erledigt

---

### [intern] M7 – app.py: _clubs_excel_bytes crasht bei leerer Vereinsdatenbank

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
`app.py` Z.476: `_clubs_excel_bytes()` ruft `max()` auf einem Openpyxl-Worksheet auf, das leer ist (keine Zeilen außer Header). Wenn `clubs_db.csv` leer oder nicht geladen ist, wirft das einen `ValueError: max() arg is an empty sequence`. Fix: Guard vor dem `max()`-Aufruf oder Early-Return bei leerem Worksheet.
**Status:** Erledigt

---

### [intern] N1 – config_validator: Kalender-Duplikate werden mehrfach gezählt

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`config_validator.py` Z.117–124: Wenn `cfg.calendar` mehrere identische Spieltag-Einträge enthält (z.B. durch Doppel-Import), werden diese mehrfach in die Spieltag-Zählung einbezogen. Die Warnung "zu viele Spieltage" erscheint dann nicht, obwohl sie sollte (Falsch-Negativ). Fix: `set()` über die Kalender-Keys vor der Längen-Prüfung.
**Status:** Erledigt

---

### [intern] N2 – multi_solver: privates Attribut _t0 und redundante Sets

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`multi_solver.py`: (1) `_p2_cb._t0 = t0` setzt ein privates Attribut der Callback-Klasse von außen – besser `t0` als Konstruktor-Parameter übergeben. (2) Mehrere Set-Definitionen werden in Schleifen mehrfach neu berechnet statt einmalig vorberechnet. Kein Absturz-Risiko, aber unnötige CPU-Last bei großen Modellen.
**Status:** Erledigt

---

### [intern] N3 – wizard: import math im Bedingungsblock

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`wizard.py` Z.182: `import math` steht innerhalb eines `if`-Blocks statt am Dateianfang. Kein funktionaler Fehler, aber verletzt PEP 8. Fix: Import auf Modulebene verschieben.
**Status:** Erledigt

---

### [intern] N4 – app.py: Toter Code und Style-Probleme

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`app.py`:
1. Z.495: `n_extra`-Variable wird berechnet aber nicht verwendet (toter Code).
2. Z.589: `fmt_list`-Funktion ist definiert aber wird nirgends aufgerufen (toter Code).
3. Z.917: Backslash-Zeilenfortsetzung im Hinweise-Sheet statt Klammern (Style).
Fix: toten Code entfernen, Backslash durch Klammern ersetzen.
**Status:** Erledigt

---

### [intern] N5 – solver: AddMaxEquality auf leerer Liste bei n=0

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`solver.py`: Bei einer Liga mit 0 Teams (`n=0`, z.B. durch Konfigurationsfehler der vom Validator nicht abgefangen wird) wird `model.AddMaxEquality([], [])` aufgerufen, was in CP-SAT undefiniertes Verhalten hat. Der Validator schließt `n < 4` aus, aber die Solver-Funktion selbst hat keinen Guard. Fix: Early-Return in `build_league_vars()` wenn `n < 2`.
**Status:** Erledigt

---

### [intern] N6 – wizard: DST-Limit und n_active-Eingabe Randfälle

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`wizard.py`:
1. Z.477: Das Limit für die Anzahl der DST-Blöcke ist `n_teams - 1` (= maximale Spieltagzahl einer Einfachrunde), aber korrekt wäre `n_md // 2` (halbe Spieltagzahl), da DST-Blöcke je zwei Spieltage verbrauchen. Bei Hin-Rückrunde akzeptiert der Wizard zu viele DST-Blöcke.
2. Z.192: Wenn nur genau 1 gültiger `n_active`-Wert existiert (z.B. nur 6 von 6 Teams aktiv möglich), wird keine Eingabe angeboten und der Wert bleibt auf dem Default – stille Lücke ohne Feedback an den Nutzer.
**Status:** Erledigt

---

### [intern] N7 – app.py: kein UI-Widerspruchs-Check blocked vs. forced_home

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`app.py` Schritt 5: Wenn ein Nutzer denselben Spieltag gleichzeitig als Sperrtag (`blocked`) und als Heimspiel-Pflichttag (`forced_home`) für dasselbe Team einträgt, gibt es in der UI keine sofortige Warnung. Der `config_validator` fängt das zwar ab, aber erst beim Starten der Optimierung. Fix: direkten Widerspruchs-Hinweis beim Eintragen anzeigen.
**Status:** Erledigt

---

## Code-Review-Befunde Mai 2026 – Vollständiger Review (Runde 2)

> 8-teiliger Code-Review vom 2026-05-04.
> Kritisch (8) · Hoch (18) · Mittel (19) · Niedrig (7)
> Stand 2026-05-04: Kritisch + Hoch vollständig bearbeitet.

---

### [intern] R2-K1 – sa_refine: t_idx KeyError nach manuellen Spielplanänderungen

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Blocker
**Beschreibung:**
`sa_refine.py` Z.82–86: `_recompute_team_km()` greift per `t_idx[ht]`/`t_idx[at]` auf den Team-Index zu. Nach manuellen Bearbeitungen (Spielverschiebung, Nachholspiel) können Teamnamen im Schedule auftreten, die nicht im ursprünglichen `t_idx`-Dict vorhanden sind. Dann wirft SA-Phase 3 einen unkontrollierten `KeyError`. Fix: `t_idx.get(ht)` mit Fallback oder Guard-Check vor SA-Start.
**Status:** Erledigt

---

### [intern] R2-K2 – schedule_utils: travels[ti] IndexError in find_schedule_warnings

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Blocker
**Beschreibung:**
`schedule_utils.py` Z.394–396: `find_schedule_warnings()` greift per `travels[ti]` auf die Kilometerliste zu ohne Längen-Guard. Wenn `result.travels` kürzer als `n_teams` ist (z.B. nach Turniertag-Phase-3 oder bei leerem Feld), entsteht `IndexError`. Fix: `result.travels[ti] if ti < len(result.travels) else 0`.
**Status:** Erledigt

---

### [intern] R2-K3 – tt_scheduler: pool.pop() bei mehreren Slots verliert Spiele

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Blocker
**Beschreibung:**
`tt_scheduler.py` Z.196–209: Bei der Ausrichter-Zuweisung entfernt `pool.pop()` Spiele aus dem Pool; nachfolgende Zuweisungen finden nichts mehr und Matches werden still verworfen – kein Fehler, aber fehlende Spiele im Excel. Fix: Kopie des Pools verwenden oder Zuweisung umstrukturieren.
**Status:** Kein Problem – Code-Analyse zeigt: pool wird korrekt iteriert, alle Spiele enden in slots[] oder pool für _backtrack. False positive.

---

### [intern] R2-K4 – excel_output: Heatmap-Spaltenindex falsch bei nicht-sequenziellen Spieltagen

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Blocker
**Beschreibung:**
`excel_output.py` Z.288–292: Die Heimrecht-Heatmap verwendet den Spieltag-Integer direkt als Spaltenoffset. Nach manuellen Spiellöschungen (z.B. nur noch Spieltage 1, 3, 5) schreibt der Code in die falsche Spalte und korrumpiert die Heatmap. Fix: Mapping-Dict `{day: col_idx}` für die Spaltenzuordnung verwenden.
**Status:** Erledigt

---

### [intern] R2-K5 – excel_output/main: min/max auf leerer travels-Liste

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Blocker
**Beschreibung:**
`excel_output.py` Z.91–92 bzw. `main.py`: Wenn `result.travels` eine leere Liste ist (z.B. bei Turniertag mit 0 km), wirft `min(result.travels)` / `max(result.travels)` `ValueError: min() arg is an empty sequence`. Fix: `min(result.travels or [0])` bzw. Guard.
**Status:** Erledigt (main.py gefixt; excel_output.py hatte kein direktes min/max auf travels)

---

### [intern] R2-K6 – wizard: build_configs() verliert hier_weight durch Neuberechnung

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Blocker
**Beschreibung:**
`wizard.py` Z.850–852: `build_configs()` berechnet `w_scaled` aus Rohgewichten neu statt das gespeicherte `w_scaled_per_liga`-Dict zu verwenden. Der `'hier'`-Schlüssel geht dabei verloren, da er getrennt in `ld['hier_weight']` liegt. In der CLI-Pipeline hat `cfg.hier_weight` immer Default-Wert. Fix: `hier_weight=ld.get('hier_weight', 1.0)` explizit übernehmen.
**Status:** Kein Problem – `hier_weight=hw` wird bereits aus `league_def[3]` korrekt extrahiert (Z.871). False positive.

---

### [intern] R2-K7 – app.py: S.sol vs S.solver Key-Mismatch beim Sitzungs-Speichern/Laden

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Blocker
**Beschreibung:**
`app.py` Z.2925 und Z.2974: `_session_to_json()` serialisiert Solver-Einstellungen unter Key `'sol'` (`S.sol`), der in `_DEFAULTS` nicht existiert (korrekt: `S.solver`). Klicken auf „💾 Sitzung speichern" wirft immer `AttributeError`. `_session_from_json()` schreibt geladene Werte nach `S.sol` statt `S.solver` – Solver-Einstellungen fallen nach dem Laden auf Default zurück. Fix: `S.sol` → `S.solver` an beiden Stellen.
**Status:** Erledigt

---

### [intern] R2-K8 – app.py: st.image(width='stretch') wirft StreamlitAPIException

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Blocker
**Beschreibung:**
`app.py` Z.379: `st.image(_LOGO_PATH, width='stretch')` – `st.image()` akzeptiert nur `int` oder `None` als `width`, nicht den String `'stretch'`. In Streamlit ≥1.32 wirft das bei jedem Render der Sidebar eine `StreamlitAPIException` und bricht die gesamte App. Fix: `width=None` oder `width=200`.
**Status:** Erledigt

---

### [intern] R2-H1 – sa_refine: round_len=0 → ZeroDivisionError in _recompute_team_km

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`sa_refine.py` Z.97–111: `round_len = n_matchdays // n_rounds` kann 0 sein wenn `n_matchdays < n_rounds`. Die folgende Division `(day - 1) // round_len` wirft `ZeroDivisionError`. Fix: `round_len = max(1, n_matchdays // n_rounds)`.
**Status:** Kein Problem – `round_len` existiert nicht in sa_refine.py; Phasen-Splitting nutzt `hinrunde_end`. False positive.

---

### [intern] R2-H2 – league_types: games_per_team_per_day=0 → ZeroDivisionError in n_matchdays

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`league_types.py` Z.56–58: Die `n_matchdays`-Property teilt durch `games_per_team_per_day`. Bei `games_per_team_per_day=0` durch Konfigurationsfehler entsteht `ZeroDivisionError`. Fix: `max(1, self.games_per_team_per_day)` im Nenner.
**Status:** Kein Problem – `gpd = max(1, self.games_per_team_per_day)` war bereits im Code. False positive.

---

### [intern] R2-H3 – config_validator: NaN in Distanzmatrix macht Leer-Check stumm

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`config_validator.py` Z.63: `if dist is None or dist.size == 0` erkennt nicht wenn die Matrix NaN-Werte enthält (z.B. durch fehlerhaften CSV-Import). NaN propagiert sich durch alle Solver-Berechnungen ohne Fehlermeldung. Fix: `np.isnan(dist).any()` zusätzlich prüfen.
**Status:** Erledigt

---

### [intern] R2-H4 – solver: DST-Routing referenziert d1+1 statt d2

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`solver.py` Z.323–332: Die DST-Routing-Constraint verwendet `loc[ti, d1+1, j]` (arithmetischer +1-Offset) statt `d2` aus dem DST-Block-Tupel. Wenn ein DST-Block nicht-konsekutive Spieltage hat (z.B. `(3, 7)`), verweist `d1+1=4` auf einen ggf. nicht im `loc`-Dict vorhandenen Tag → `KeyError`. Fix: `for d1, d2 in cfg.dst_blocks: ... loc[ti, d2, j]`.
**Status:** Erledigt

---

### [intern] R2-H5 – multi_solver: fehlender Guard für leeres cfgs in run_phase2

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`multi_solver.py` `run_phase2()`: Wenn `cfgs` leer übergeben wird, baut das Modell keine Variablen auf, der Solver findet trivial OPTIMAL, und es erscheint keinerlei Warnung. Fix: `if not cfgs: warn('Keine Ligen übergeben.'); return {}` am Anfang.
**Status:** Erledigt

---

### [intern] R2-H6 – tt_scheduler: kein globales Node-Budget in Ausrichter-Fallback-Schleifen

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`tt_scheduler.py` Z.147–184: Die Ausrichter-Zuweisung iteriert in Fallback-Schleifen ohne Abbruchkriterium. Bei degenerierten Konfigurationen (viele Sperrtage + viele Teams) kann die Suche exponentiell lange dauern. Fix: Maximale Iterationszahl einführen.
**Status:** Erledigt

---

### [intern] R2-H7 – schedule_utils: DTSTAMP fehlt in iCal-VEVENTs (RFC 5545)

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`schedule_utils.py` Z.298–303: `build_ics_bytes()` erzeugt VEVENTs ohne RFC-5545-Pflichtkomponente `DTSTAMP`. Strenge iCal-Clients (z.B. Outlook) lehnen solche Dateien ab. Fix: `DTSTAMP:YYYYMMDDTHHMMSSZ` (aktuelle UTC-Zeit) in jeden VEVENT einfügen.
**Status:** Erledigt

---

### [intern] R2-H8 – schedule_utils: leere Weekend-Subliste → IndexError auf wknd[0]

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`schedule_utils.py` Z.52–54: `wknd[0]` wird aufgerufen ohne zu prüfen ob die Sub-Liste leer ist. Wenn `cfg.weekends` einen leeren Eintrag `[]` enthält (Kalender-Parsing-Fehler), entsteht `IndexError`. Fix: `if not wknd: continue`.
**Status:** Erledigt

---

### [intern] R2-H9 – schedule_utils: ncols=5 statt 6 in HTML-Druckansicht

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`schedule_utils.py` Z.428–430: In `build_print_html()` ist `ncols=5` hartcodiert für `colspan`-Berechnungen, obwohl die Haupttabelle 6 Spalten hat. Trennzeilen werden zu schmal und verzerren die Tabellenbreite. Fix: `ncols=6`.
**Status:** Kein Problem – ncols wird bereits dynamisch berechnet: `5 + bool(season_year) + bool(cfg.dst_blocks) + bool(is_tt) + bool(has_times)`. False positive.

---

### [intern] R2-H10 – excel_output: falsche Spaltenbreiten für n_rounds > 2

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`excel_output.py` Z.583: Die Spaltenbreiten-Berechnung verwendet einen festen Offset, der für `n_rounds <= 2` korrekt ist. Bei Dreifachrunden ist der Offset zu klein, die letzte Datenspalte wird zu schmal. Fix: Offset auf `n_rounds` anpassen.
**Status:** Erledigt

---

### [intern] R2-H11 – excel_output: n_bcols off-by-one im Co-Home-Excel

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`excel_output.py` Z.492: `n_bcols` (Anzahl Block-Spalten im Co-Home-Excel) ist um 1 zu groß (off-by-one). Eine leere Spalte erscheint rechts, Hintergrundfarbe der letzten Datenspalte fehlt. Fix: `n_bcols` um 1 reduzieren.
**Status:** Erledigt (tatsächlich war n_bcols 1 zu klein – von 3+2n auf 4+2n korrigiert; Bewertung-Spalte fehlte im Merge)

---

### [intern] R2-H12 – calendar_parser: Jahreswechsel-Bug im Datums-Parsing

**Typ:** Fehler/Bug
**Bereich:** Kalender / Termine
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`calendar_parser.py`: Bei KWs über den Jahreswechsel (Dez./Jan.) wird das Jahr für `week_start`/`week_end` falsch zugeordnet. `week_start` im Dezember erhält fälschlich das Folgejahr. Fix: Jahr für `week_start` separat anhand des Monats ableiten.
**Status:** Erledigt

---

### [intern] R2-H13 – wizard: k_group-Config bei einzelnem gültigem K übersprungen

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`wizard.py` Z.223: Wenn für Turniertag Stufe 2 exakt ein gültiger `K`-Wert existiert, überspringt der Wizard die Konfigurationsanzeige ohne Rückmeldung. Fix: Informationszeile ausgeben auch bei einzelnem K.
**Status:** Erledigt

---

### [intern] R2-H14 – wizard: min_gap ask_int mit Range 0…0 bei 1 Spieltag

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`wizard.py` Z.258–265: `ask_int()` für `min_gap` wird mit `min=0, max=0` aufgerufen wenn die Liga nur 1 Spieltag hat – ungültige Range. Fix: Guard `if max_gap == 0: min_gap = 0` ohne Eingabeaufforderung.
**Status:** Erledigt

---

### [intern] R2-H15 – wizard: n_md falsch für Stufe-2-Turniertag in Schritt 5/6/6b

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`wizard.py` Z.580–581: In Schritten 5, 6, 6b wird `n_md = n_rounds * (n_t - 1)` berechnet statt `_calc_n_matchdays()`. Bei Turniertag Stufe 2 mit Gruppen ergibt die Formel zu viele Spieltage. Fix: `n_md = _calc_n_matchdays(ld)`.
**Status:** Erledigt

---

### [intern] R2-H16 – app.py: Liga-ID-Umbenennung ohne Guard für leeren Namen

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.1803: `if new_lid != lid and new_lid not in S.league_order` fehlt der Guard `and new_lid`. Leert der Nutzer das Feld, wird die Liga zu leerem Schlüssel `''` umbenannt und korrumpiert `S.leagues`/`S.league_order`. Fix: `if new_lid and new_lid != lid and new_lid not in S.league_order`.
**Status:** Erledigt

---

### [intern] R2-H17 – app.py: Liga-Löschen bereinigt S.clubs nicht

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.1374–1379: Beim Löschen einer Liga wird `S.clubs` nicht bereinigt. Stale `lid`-Einträge in Club-Dicts führen in Schritt 6 zu falschen Co-Home-Zuordnungen und im Excel-Export zu `KeyError`. Fix: In der Cleanup-Schleife pro Club-Dict den entfernten `lid`-Key löschen.
**Status:** Erledigt

---

### [intern] R2-H18 – app.py: Excel-Erzeugung nach Solver-Abschluss ohne try/except

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.3477–3490: `build_league_excel()`, `build_cohome_summary()`, `build_hall_schedule()` im `done`-Handler ohne try/except. Ein Fehler verhindert `st.rerun()`, `S.excel_bytes` bleibt leer, Ergebnisanzeige inkonsistent. Fix: try/except-Block analog zu `_session_from_json()` Z.3046–3051.
**Status:** Erledigt

---

### [intern] R2-M1 – config_validator: pin_key str/int-Mismatch beim Pflichtspiel-Check

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`config_validator.py` Z.102–111: `pin_key = (teamA, teamB, day)` – wenn `day` als String gespeichert ist (JSON: `"3"` statt `3`), werden Duplikate nicht erkannt (`("A","B","3") != ("A","B",3)`). Widersprüchliche Pflichtspiele erscheinen nicht als Fehler. Fix: `int(day)` beim Aufbau des `pin_key` erzwingen.
**Status:** Offen

---

### [intern] R2-M2 – sa_refine: leere Kandidatenliste → IndexError in random.choice

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`sa_refine.py` Z.159–172: Wenn alle Paarungen fixes Heimrecht haben, ist die Kandidatenliste für Heim↔Auswärts-Tausch leer. `random.choice([])` wirft `IndexError`. Fix: `if not candidates: break` vor dem `random.choice()`.
**Status:** Offen

---

### [intern] R2-M3 – solver: Turniertag-Switch-Summation erzeugt unnötige CP-Terme

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`solver.py` Z.456: `sum(lv.switch[ti, d] ...)` in `add_league_objective()` summiert für Turniertag-Ligen immer 0 (alle Switches fixiert), erzeugt aber N-1 unnötige CP-Terme (Modell-Aufblähung). Fix: Turniertag-Branch überspringen.
**Status:** Offen

---

### [intern] R2-M4 – solver: Switch-Constraints iterieren range(1,N) statt cfg.days

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`solver.py` Z.127, 248–253: Switch-Constraints iterieren über `range(1, N)` statt `cfg.days[:-1]`. Falls `cfg.days` nicht lückenlos 1…N ist, stimmen Indizes nicht mehr überein. Fix: `for d in cfg.days[:-1]` verwenden.
**Status:** Offen

---

### [intern] R2-M5 – schedule_utils: move_game validiert new_day nicht gegen cfg.days

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`schedule_utils.py` `move_game()`: `new_day` wird nicht gegen `cfg.days` geprüft. Ein nicht-existierender Spieltag kann eingetragen werden und Export-Funktionen crashen lassen. Fix: `if new_day not in cfg.days: return 'Spieltag nicht im Kalender'`.
**Status:** Offen

---

### [intern] R2-M6 – schedule_utils: reschedule_game validiert Teamnamen nicht

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`schedule_utils.py` `reschedule_game()`: Teamnamen werden nicht gegen `cfg.teams` validiert. Tippfehler erzeugen stille Dateninkonsistenz. Fix: `if ht not in cfg.teams or at not in cfg.teams: return 'Unbekannte(s) Team(s)'`.
**Status:** Offen

---

### [intern] R2-M7 – schedule_utils: iCal-Text nicht RFC 5545-konform escaped

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`schedule_utils.py` `build_ics_bytes()`: Teamnamen/Ortsnamen werden ohne RFC-5545-Escaping in `SUMMARY`/`LOCATION` eingetragen. Sonderzeichen `,`, `;`, `\n` müssen escaped werden. Fix: Escape-Funktion einbauen.
**Status:** Offen

---

### [intern] R2-M8 – schedule_utils: iCal-Zeilen-Folding fehlt (RFC 5545)

**Typ:** Fehler/Bug
**Bereich:** Excel-Export
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`schedule_utils.py` `build_ics_bytes()`: RFC 5545 schreibt Line-Folding nach 75 Oktetts vor. Lange Zeilen mit langen Teamnamen werden von strict-Mode-Parsern abgelehnt. Fix: Line-Folding-Funktion anwenden.
**Status:** Offen

---

### [intern] R2-M9 – excel_output: t_idx-Dict redundant mehrfach aufgebaut

**Typ:** Verbesserung
**Bereich:** Excel-Export
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`excel_output.py`: `t_idx = {t: i for i, t in enumerate(cfg.teams)}` wird innerhalb derselben Funktion mehrfach neu aufgebaut. Fix: Einmalig am Funktionsanfang berechnen.
**Status:** Offen

---

### [intern] R2-M10 – main.py: n_per_round ZeroDivisionError bei wenigen Spieltagen

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`main.py`: `n_per_round = n_matchdays // n_rounds` kann 0 ergeben wenn `n_matchdays < n_rounds` (z.B. nach manuellen Spiellöschungen). Folgeoperationen mit `n_per_round` als Divisor werfen `ZeroDivisionError`. Fix: `max(1, ...)`.
**Status:** Offen

---

### [intern] R2-M11 – app.py: mat uninitialisiert vor try-Block in _step1

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.1938–1948: `mat` wird nicht mit `None` initialisiert vor dem `try`-Block der `calculate_distance_matrix()` aufruft. Bei unerwarteter Exception ist `mat` undefiniert → unkontrollierter `NameError`. Fix: `mat = None` vor dem `try`-Block.
**Status:** Offen

---

### [intern] R2-M12 – app.py: tt_rounds_val=0 führt zu index=-1 im Selectbox

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.1431–1433: Bei korruptem State kann `tt_rounds_val=0` sein. `index = 0-1 = -1` wählt im Selectbox das letzte Element (Python -1-Index). Fix: `index = max(0, min(tt_rounds_val - 1, 2))`.
**Status:** Offen

---

### [intern] R2-M13 – app.py: n_md in Schritt 2 als falsche Formel

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.2204: In `_step2()` wird `n_md = n_rounds * (n_t - 1)` berechnet statt `_calc_n_matchdays(ld)`. Bei Turniertag Stufe 2 oder Spielfrei-Modus liefert die Formel zu viele Spieltage als max-Wert für Eingabefelder. Fix: `n_md = _calc_n_matchdays(ld)`.
**Status:** Offen

---

### [intern] R2-M14 – app.py: kein Duplikat-Check beim Hinzufügen von Pflichtspielen

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.2405–2410: Beim Hinzufügen eines Pflichtspiels in Schritt 4 wird nicht geprüft ob dieselbe Paarung (teamA, teamB, day) bereits existiert. Doppelte Einträge zwingen den Solver in INFEASIBLE. Fix: Vor `pinned.append()` auf identischen Eintrag prüfen.
**Status:** Offen

---

### [intern] R2-M15 – app.py: Routing-Toleranz-Slider erlaubt 0% (→ INFEASIBLE)

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.2315: Routing-Toleranz-Slider hat `min_value=0`. Bei 0% wird die Constraint „Umweg ≤ Direktstrecke", was nahezu immer INFEASIBLE ergibt. Fix: `min_value=5` oder explizite Warnung bei 0%.
**Status:** Offen

---

### [intern] R2-M16 – app.py: _diagnose_infeasible_league Falsch-Positive bei ähnlichen Liga-IDs

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.3551–3553: `_diagnose_infeasible_league()` prüft ob „INFEASIBLE" UND `lid` im Gesamtlog vorkommen – als unabhängige Suchen. Liga „BL" wird fälschlich als INFEASIBLE diagnostiziert wenn Liga „BL2" diesen Status hatte. Fix: Zeilenweise prüfen ob `lid` und `INFEASIBLE` in **derselben** Zeile vorkommen.
**Status:** Offen

---

### [intern] R2-M17 – app.py: Neu berechnen löscht cohome_bytes/excel_bytes nicht

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.3219–3226: „Neu berechnen" setzt `S.results=None` und `S.hall_bytes=None`, aber nicht `S.cohome_bytes` und `S.excel_bytes`. Veraltete Bytes belegen Speicher. Fix: `S.cohome_bytes = None; S.excel_bytes = {}` ergänzen.
**Status:** Offen

---

### [intern] R2-M18 – app.py: cancel_game schlägt stumm fehl bei ungültigem match_idx

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.4136–4145: Wenn `_cancel_game()` `(None, None)` zurückgibt, ist `_ht_c` falsy und die Operation schlägt ohne Fehlermeldung fehl. Fix: `else: st.error('Spiel nicht gefunden – bitte Seite neu laden.')`.
**Status:** Offen

---

### [intern] R2-M19 – app.py: col_hdrs-Filterung schneidet Distanzmatrix bei leeren Spaltenköpfen ab

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Beschreibung:**
`app.py` Z.1024–1026: In `_load_full_config_excel()` werden leere/NaN-Spaltenköpfe der Distanzmatrix übersprungen. Ist ein Teamname-Header leer (Formatierungsartefakt), ist `n` zu klein und die Matrix wird still abgeschnitten. Fix: `n` aus der Anzahl der tatsächlich geladenen Teams ableiten.
**Status:** Offen

---

### [intern] R2-N1 – multi_solver: toter Import in _phase1_worker

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`multi_solver.py` Z.31–32: `from ortools.sat.python import cp_model as _cp` wird importiert aber nirgends verwendet. Fix: Import entfernen.
**Status:** Offen

---

### [intern] R2-N2 – solver: stdout-Interleaving bei parallelen Phase-1-Läufen

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`solver.py` Z.578–585: `_ProgressCallback` schreibt direkt auf `sys.stdout`. Bei parallelen Phase-1-Läufen können Ausgaben verschiedener Ligen interleaven wenn Streamlits `sys.stdout`-Ersatz nicht thread-safe ist. Fix: Ausgabe in `threading.Lock` kapseln.
**Status:** Offen

---

### [intern] R2-N3 – config: TEAM_COLORS-Dict nur für 20 Teams

**Typ:** Verbesserung
**Bereich:** Excel-Export
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`config.py` Z.33: `TEAM_COLORS = {i: get_team_color(i) for i in range(20)}` – externer Code der per `TEAM_COLORS[idx]` mit `idx >= 20` zugreift statt `get_team_color()` erhält `KeyError`. Fix: `defaultdict(get_team_color)` oder alle Aufrufer umstellen.
**Status:** Offen

---

### [intern] R2-N4 – app.py: Verein-Hinzufügen in Schritt 6 ohne Duplikat-Check

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.2692–2699: Beim manuellen Hinzufügen eines Vereins wird nicht geprüft ob der Name bereits in `S.clubs` existiert. Bestehender Eintrag wird stillschweigend überschrieben. Fix: Warnung wenn `new_club in S.clubs`.
**Status:** Offen

---

### [intern] R2-N5 – app.py: n_per_round ZeroDivisionError in Ergebnisanzeige

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.3747: `n_per_round = res.cfg.n_matchdays // n_rounds` kann 0 ergeben nach manuellen Spiellöschungen. `(d - 1) // n_per_round` wirft `ZeroDivisionError`. Fix: `max(1, res.cfg.n_matchdays // n_rounds)`.
**Status:** Offen

---

### [intern] R2-N6 – app.py: falsche Slot-Anzahl bei Spielfrei-Modus im Uhrzeiten-Editor

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.3873: `_gspd = _n_t * _gpd // 2` berücksichtigt nicht den Spielfrei-Modus (`n_active_per_day < n_t`). Der Default-Uhrzeiten-String hat zu viele Slots. Fix: `_n_active = ld.get('n_active_per_day') or _n_t; _gspd = _n_active * _gpd // 2`.
**Status:** Offen

---

### [intern] R2-N7 – app.py: falscher Sheet-Kommentar (Sheet 10 vs. 11)

**Typ:** Verbesserung
**Bereich:** Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`app.py` Z.900: Kommentar `# ── Sheet 10: Hinweise` ist falsch – das Hinweis-Sheet ist Sheet 11 (Sheet 10 ist das Co-Home-Sheet bei Z.884). Fix: Kommentar auf `Sheet 11` korrigieren.
**Status:** Offen
