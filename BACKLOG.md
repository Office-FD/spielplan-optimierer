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
**Status:** Offen

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
**Status:** Offen

---

### [intern] wizard.py Legacy-Status klären

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`wizard.py` ist in CLAUDE.md als "Legacy CLI-Wizard" markiert, aber ungeklärt ob noch genutzt. Prüfen ob `__main__.py` noch importiert → falls nicht: entweder löschen oder in CLAUDE.md als "nur für Notfall ohne Streamlit" dokumentieren.
**Status:** Offen

---

### [intern] CLAUDE.md Dateistruktur vervollständigen

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Folgende Dateien fehlen in der Dateistruktur (§2): `test_features.py`, `config_validator.py`. Je eine Zeile mit Kurzbeschreibung ergänzen.
**Status:** Offen
