# Code-Review Plan – Spielplan-Optimierer

> **Status:** Runde 8 in Vorbereitung 27.05.2026 — **Final-Review vor Produktiveinsatz**.
> **Vorherige Runden:**
> - Runde 6 (Mai 2026, v1.3.0 → v1.6.2): 67/73 Items + R1-R3-Refactors erledigt
> - Runde 7 (27.05.2026, v1.12.1 → v1.13.0): 16/29 Befunde gefixt, 13 zurückgestellt

---

## Ziel von Runde 8: Produktions-Freigabe

Runde 8 ist die **finale Verifikation vor dem echten Produktiveinsatz** der App für die FLVD-Saisonplanung. Im Gegensatz zu R7 (nur neue Module) wird hier **alles** geprüft, aber mit einem anderen Fokus:

| Aspekt | Bewertung |
|---|---|
| **Korrektheit** | Sind alle Constraints richtig? Edge-Cases abgedeckt? |
| **Robustheit** | Was passiert bei Fehler/Crash/leerer Eingabe? Pipeline-Kontinuität? |
| **Datenkonsistenz** | JSON/Excel/CSV-Outputs synchron mit App-State? |
| **UX-Korrektheit** | Wizard-Flow nachvollziehbar? Fehlermeldungen verständlich? |
| **Performance** | Lange Läufe? Große Datenmengen? Speicher? |
| **Security** | XSS in Tooltips, Path-Traversal, Subprocess-Sicherheit |
| **Distribution** | Installer + Auto-Updater + Endnutzer-Pfad |
| **Doku-Konsistenz** | Stimmen alle MD-Dateien mit dem Code? |

Befunde werden mit **Schweregrad + Produktions-Blocker-Flag** markiert:
- 🛑 **Show-Stopper:** muss vor Produktiv-Lauf gefixt werden
- 🔴 **Hoch:** sollte gefixt werden, aber kein Blocker
- 🟡 **Mittel:** nachher fixen, nicht zeitkritisch
- 🟢 **Niedrig:** Polishing, optional

---

## 8 Blöcke

Jeder Block ist eigenständig in ~45-60 Min reviewbar. **Reihenfolge ist sinnvoll, aber nicht zwingend** — bei Bedarf kannst Du auch nicht-aufeinanderfolgende Blöcke fahren.

### R8-A: Solver-Modell + Pipeline (~60 min)
**Dateien:** `solver.py`, `multi_solver.py`
**Fokus:** Korrektheit aller CP-SAT-Constraints, Pipeline-Übergaben Phase 1→2→3, Edge-Cases.
**Checkliste:**
- Alle Constraint-Familien einzeln (Heimrecht, DST, Sperrtage, Pflichtspiele, Pflichtheim, Sliding-Window, Co-Home, Round-Balance, Round-Bound)
- Spielfrei-Modus bei ungerader Teamzahl: alle Constraints konsistent geconditionalized?
- Turniertag-Pfade Stufe 1 + Stufe 2: alle Sub-Funktionen geguarded?
- `needs_bye` × DST × forced_home: 3-Wege-Interaktion sauber?
- Hint-Pass-Through Phase 1 → Phase 2 (set_hints): alle Variablen abgedeckt?
- Telemetrie-Persistenz durch alle Phasen
- Logging / `[FEHLER]`-Pfade in allen Subprocess-/Thread-Pfaden

### R8-B: Nachbearbeitung (~45 min)
**Dateien:** `sa_refine.py`, `tt_scheduler.py`, `schedule_utils.py`
**Fokus:** SA-Determinismus, Mutationsfunktionen (move/cancel/reschedule/swap), iCal/HTML-Export.
**Checkliste:**
- SA Akzeptanz-Kriterium / Cooling / Reset-Verhalten
- `apply_tournament_ordering` + `_balance_home_away` Edge-Cases
- Alle Mutationen mit Turniertag-Guard?
- `recompute_result_stats` synchron mit Solver-Modell?
- iCal: RFC 5545 Escaping + Line-Folding korrekt?
- Spielfrei + DST + Pinned in Mutationen

### R8-C: Datenmodell + Eingabe-Validierung (~45 min)
**Dateien:** `league_types.py`, `config.py`, `config_validator.py`, `calendar_parser.py`, `distances.py`
**Fokus:** Datenklassen-Konsistenz, Validator-Vollständigkeit, Parser-Robustheit.
**Checkliste:**
- `LeagueConfig`-Properties bei allen Konfig-Variationen (gpd/n_rounds/K/n_active)
- Validator: hat jeden Befund aus früheren Reviews abgedeckt?
- Calendar-Parser: alle Excel-Format-Varianten, Jahreswechsel, Doppel-Spieltage
- Distance-Loader: CSV-Matrix vs. Paarlisten, Excel, Google API, Cache
- Negative km, NaN, leere Zellen, Header-Erkennung

### R8-D: Export + Visualisierung (~60 min)
**Dateien:** `excel_output.py`, `map_output.py`, `calendar_output.py`, `geocode.py`
**Fokus:** Alle Output-Formate korrekt + visuell verständlich.
**Checkliste:**
- Excel: alle Sheets (Spielplan, Heatmap, km, Distanzmatrix, Fairness, Gruppen) bei allen Format-Varianten
- Co-Home-Excel + Hallenbelegungsplan + Gesamtübersicht
- Karten: leere/Single-Liga/Multi-Liga, fehlende Geocodes, HTML-Escape
- Kalender: KW-Fallback, allDay vs. Uhrzeit, Multi-Liga
- Geocode-Cache: Race-Condition, Umlaut-Norm, Rate-Limit

### R8-E: UI Wizard-Schritte 1-7 (~60 min)
**Dateien:** `app.py` Schritte 1-7 (Liga-Konfiguration bis Co-Home)
**Fokus:** Konfigurations-Eingabe, Fehlerbehandlung, Session-State-Konsistenz.
**Checkliste:**
- Liga-Add/Remove/Rename: alle State-Dicts synchron?
- Distance-Matrix-Editor: leere Zellen, Symmetrisierung, Validierung
- Calendar-Editor: cal_table-Roundtrip Excel-Save/Load
- Pflichttermine: Konflikt-Detektion in der UI
- Sperrtage + Pflichtheim: Validator-Live-Feedback
- Co-Home-Auto-Detection
- JSON-Save/Load v1.0 + v1.1 backward-compat

### R8-F: UI Wizard-Schritte 8-9 + Mutationen (~60 min)
**Dateien:** `app.py` Schritte 8-9 (Solver + Ergebnisansicht + Aktionen)
**Fokus:** Solver-Start, Live-Anzeige, Ergebnis-Section, Spielplan-Aktionen.
**Checkliste:**
- Solver-Subprocess: Crash-Handling, Cancel-Button, Queue-Sync
- Live-Log (`_translate_solver_log_cached`): Performance, Korrektheit
- Telemetrie-Section: Phase-2 vs. Phase-1-Fallback-Anzeige
- Karten-Section + Kalender-Section: Fallbacks, Performance
- Spielplan-Mutationen (move/cancel/reschedule/swap)
- Downloads (Excel, Co-Home, Hall, Overview, iCal, HTML, CSV)
- Spielplan-Vergleich-Feature

### R8-G: Distribution + CLI (~45 min)
**Dateien:** `launcher.py`, `installer/`, `wizard.py`, `main.py`, `build_release.py`, `.github/workflows/release.yml`
**Fokus:** Endnutzer-Auslieferung, Auto-Updater-Rollback, CLI-Pfad.
**Checkliste:**
- Launcher: Update-Pfad mit Backup/Rollback, Background-Check
- Installer: spielplan.iss, build_bootstrap.bat, Embedded-Python-SHA
- CLI-Wizard: alle Pfade durch, deckt UI-Funktionen ab?
- `build_release.py`: erstellt korrektes app-files.zip
- Release-Workflow: Tag-Validation, Test-Gate

### R8-H: Tests + CI + Doku (~60 min)
**Dateien:** `test_*.py`, `.github/workflows/`, Konfig-Files, MD-Dateien
**Fokus:** Test-Coverage-Lücken identifizieren, CI-Robustheit, Doku ↔ Code-Abgleich.
**Checkliste:**
- Test-Coverage-Lücken: was wird NICHT getestet? (calendar_parser-Excel-Parser?, launcher.py?, manuelle UI-Aktionen?)
- Alle 4 Workflows: korrekte Trigger, Berechtigungen, Timeouts
- Ruff-Config-Vollständigkeit
- `.coveragerc` Include/Omit-Konsistenz
- BENUTZERHANDBUCH ↔ aktuelle UI-Sections
- INSTALLATION ↔ Installer-Verhalten
- CLAUDE.md ↔ Code-Stand (alle Section-Referenzen aktuell?)
- README.md Feature-Liste vs. echte Features

---

## Befund-Sammlung

Pro Block werden Befunde gesammelt in `BACKLOG.md` unter `Code-Review Runde 8 – Block <X>` mit:
- ID: `R8-<Block>-<Schweregrad><Nummer>`, z. B. `R8-A-H1`, `R8-D-M3`
- Beschreibung + Code-Stelle (Datei:Zeile)
- Schweregrad-Emoji (🛑 / 🔴 / 🟡 / 🟢)
- Empfohlener Fix-Aufwand
- **Produktions-Blocker?** (Ja/Nein)

Am Ende: **Produktions-Bereitschafts-Bericht** als `PRODUCTION_READINESS.md` mit:
- Anzahl Befunde pro Schweregrad
- Liste der Show-Stopper (muss gefixt werden)
- Empfohlene Fix-Reihenfolge
- Verbleibende Risiken nach Fix

---

## Wann starten?

Empfehlung: **Block für Block**, mit ausreichend Pausen.
- Du sagst „R8 Block A starten" → ich review → Befunde dokumentiert
- Pause / nächste Session
- Du sagst „R8 Block B starten" → weiter

Falls Du keinen Block überspringen willst: **Reihenfolge A → H** ist optimal (jeder Block baut auf dem vorigen auf — Datenmodell vor Output etc.).

---

## Aktueller Code-Stand (Start R8)

- Version: **v1.13.0** (lokal committed, noch nicht gepusht)
- 16 Befunde aus R7 gefixt, 13 zurückgestellt (in BACKLOG.md)
- Tests: 67/67 features, 18/18 distances, smoke ✓, test_all noch im Hintergrund-Lauf (~14 min)
- Letzter realer 8h-Saison-Lauf: 26.05.2026 (post-F1) — Gap 15,35 %
