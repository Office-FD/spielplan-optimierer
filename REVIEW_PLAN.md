# Code-Review Plan – Spielplan-Optimierer

> **Status:** Vorbereitet Mai 2026 – nächste vollständige Review-Runde noch nicht gestartet.
> Erstellt nach Abschluss Code-Review Runde 5 (Mai 2026, alle Blöcke erledigt).
> Diese Datei beschreibt einen sinnvoll aufgeteilten Review-Plan für die nächste Runde, sodass jeder Block eigenständig (in einer Session) durchführbar ist.

---

## Prinzip der Aufteilung

Statt das gesamte Projekt in einem Marathon zu reviewen, ist es in **7 Blöcke** geteilt – nach Komponente/Verantwortlichkeit, nicht nach Datei-Größe. Jeder Block:

- Hat einen klaren thematischen Fokus
- Ist in einer Session (~30-60 min) abschließbar
- Hat eine eigene Checkliste mit konkreten Fragestellungen
- Mündet in einen Backlog-Eintrag mit Befunden

Reihenfolge ist nicht zwingend, aber **Block A → B → C → D/E → F → G** ist sinnvoll: erst die Pipeline-Korrektheit prüfen, dann die UI, dann das Drumherum.

---

## Block A: Solver-Modell (Constraints & Performance)

**Dateien:**
- `spielplan_multi/solver.py`
- `spielplan_multi/multi_solver.py`
- `spielplan_multi/sa_refine.py`
- `spielplan_multi/tt_scheduler.py`

**Fokus:** Korrektheit der CP-SAT-Constraints, Edge-Cases im Solver-Modell, Performance/Modellgröße.

**Checkliste:**
- [ ] DST-Constraints: Was passiert bei DST-Block am Saisonende? DST + Sperrtag-Kombinationen?
- [ ] Ungerade Teamzahl (`needs_bye`): Sind alle Sliding-Window-Constraints konsistent?
- [ ] `n_rounds=3` (Dreifachrunde): Hin-/Rück-/Dritt-Phasen-Trennung korrekt?
- [ ] `gpd > 1` (Turniertag): Werden alle Stats-Funktionen geguarded?
- [ ] Phase-2-Modell: ist das KW-Mapping wirklich gemeinsam optimiert oder gibt es stille Entkopplungen?
- [ ] SA-Phase: Akzeptanzkriterium, Cooling-Schedule, Reset-Verhalten — alles deterministisch?
- [ ] Symmetry-Level: noch der richtige Wert nach OOM-Fix?
- [ ] `bool_core`-Verhalten: tritt die Klausel-Kaskade unter neuen Parametern wieder auf?
- [ ] Logging: Werden `[FEHLER]`-Pfade in allen Subprocess-/Thread-Pfaden abgefangen?

---

## Block B: Datenmodell & Eingabe-Validierung

**Dateien:**
- `spielplan_multi/league_types.py`
- `spielplan_multi/config.py`
- `spielplan_multi/config_validator.py`
- `spielplan_multi/calendar_parser.py`
- `spielplan_multi/distances.py`

**Fokus:** Type-Konsistenz, Validierungs-Coverage, Defaults, NaN/Edge-Cases.

**Checkliste:**
- [ ] `LeagueConfig`: alle computed properties korrekt für ungerade n + gpd>1?
- [ ] `validate_cfgs()`: deckt alle hart-INFEASIBLE-machenden Eingaben ab?
- [ ] Pflichtspiel-Validierung: doppelte Paare bei n_rounds>1 möglich, aber nicht beliebig oft?
- [ ] Distanzmatrix-Loader: Symmetrie geprüft? Diagonale = 0 erzwungen?
- [ ] Kalender-Parser: Was bei lückenhaftem Excel? Gemischten Datumsformaten?
- [ ] `clubs_db.csv`-Format: Was bei Sonderzeichen, BOM, Umlauten?
- [ ] Default-Werte: gibt es noch `defaultdict`-Fallen wie in CR4-D2?

---

## Block C: Spielplan-Nachbearbeitung & Export

**Dateien:**
- `spielplan_multi/schedule_utils.py`
- `spielplan_multi/excel_output.py`

**Fokus:** Konsistenz von Mutationen (move/cancel/reschedule/swap), Excel-Layout, iCal/HTML-Export.

**Checkliste:**
- [ ] `recompute_result_stats()`: Transitions-Modell für alle Liga-Formate korrekt?
- [ ] `move_game` / `cancel_game` / `reschedule_game`: hinterlassen sie konsistente `home_vals`?
- [ ] `swap_home_away`: DST-Block-Partner wirklich immer mitgetauscht?
- [ ] Excel-Spaltenbreiten für n_rounds>2 (Dreifachrunde): alle Sheets korrekt?
- [ ] Heatmap: zeigt sie nach Mutationen aktuelle Werte?
- [ ] Co-Home-Excel: korrekt bei Mehrspartenvereinen die nur in 1 Liga aktiv sind?
- [ ] Übersichts-Excel: Sortierung jahresübergreifender Saisons?
- [ ] iCal: alle Pflichtfelder (DTSTAMP, UID-Eindeutigkeit) für jeden Eintrag?
- [ ] HTML-Druck: korrekte Darstellung bei sehr großen Ligen (>20 Teams)?

---

## Block D: UI – Wizard-Schritte 0-7

**Dateien:**
- `app.py` Zeilen 0 – ca. 2600 (Schritte 0-7)
- `spielplan_multi/_worker.py` (Subprocess-Aufruf)

**Fokus:** Session-State-Konsistenz, Validierungsflow, Datei-Upload, Konfigurations-Persistenz.

**Checkliste:**
- [ ] Session-State-Reset: alle `S.*`-Schlüssel beim „Neuen Spielplan erstellen" korrekt zurückgesetzt?
- [ ] Konfigurations-Upload: deckt Excel + JSON gleichermaßen alle Felder ab?
- [ ] Konfigurations-Download/Upload-Round-Trip: bleiben alle Werte erhalten?
- [ ] Distanzmatrix-Editor: synchron mit `S.dist_matrices` nach Upload?
- [ ] Pflichtspiele/Sperrtage: Validierung gegen aktuelle Teamliste konsistent?
- [ ] Co-Home-Auto-Erkennung: korrekt bei Vereinsnamen mit Sonderzeichen?
- [ ] Solver-Konfiguration: alle Presets (90 min / 3h / 8h) konsistent in Phase 1/2/SA?
- [ ] Streamlit-Deprecation-Warnings: gibt es weitere `use_container_width`-Reste?

---

## Block E: UI – Ergebnisansicht & Aktionen (Schritt 8)

**Dateien:**
- `app.py` Zeilen ca. 2600 – Ende (Schritt 8, Result-View, Mutations, Downloads, Vergleich)

**Fokus:** Result-Konsistenz nach manuellen Aktionen, Download-Korrektheit, Recovery-Flow.

**Checkliste:**
- [ ] Session-Recovery (`.cache/last_result.pkl`): funktioniert nach Browser-Refresh?
- [ ] Spiel verschieben/absagen/nachholen: Stats werden überall mit-aktualisiert?
- [ ] Heatmap-Aktualisierung nach manuellen Änderungen
- [ ] Download-Dateinamen: alle Suffixe (Gewichte, Laufzeit) konsistent?
- [ ] Spielplan-Vergleich: Delta-Berechnung korrekt bei unterschiedlicher Tagesreihenfolge?
- [ ] Druckansicht (HTML): in allen gängigen Browsern korrekt?
- [ ] Warnings-Banner: `[FEHLER]` UND `[!!]`-Zeilen sichtbar gemacht?
- [ ] Hallenbelegungs-Sheet: korrekt für Turniertag mit/ohne Gruppen?

---

## Block F: Distribution & Lifecycle

**Dateien:**
- `launcher.py`
- `build_release.py`
- `installer/` (alle Dateien)
- `.github/workflows/release.yml`
- `VERSION`
- `_worker.py` (Subprocess-Side)

**Fokus:** Update-Pfad, Versionierung, Path-Traversal, Atomarität.

**Checkliste:**
- [ ] Auto-Updater: was bei abgebrochenem Download nach erfolgreichem Tag-Read?
- [ ] Versionsvergleich: ist `tuple(int(x) for x in v.split('.'))` ausreichend (z.B. für 1.2.10)?
- [ ] ZIP-Path-Traversal-Guard: deckt symbolische Links ab?
- [ ] `build_release.py`: ignoriert `.venv`, `.cache`, `Spielplaene/`, Logs?
- [ ] GitHub Actions: erzeugt der Workflow korrekte `app-files.zip` ohne Build-Artefakte?
- [ ] Bootstrap-Installer: Embedded Python noch aktuell (3.13 → ggf. 3.14)?
- [ ] Launcher-Browser: korrekte Anzeige bei mehrfacher gleichzeitiger Instanz?
- [ ] `_worker.py`: alle Streamlit-Warnungen unterdrückt? stderr-Redirect noch nötig?

---

## Block G: CLI-Wizard & Tests

**Dateien:**
- `spielplan_multi/wizard.py`
- `spielplan_multi/main.py`
- `spielplan_multi/ui.py`
- `spielplan_multi/__main__.py`, `__init__.py`
- `test_all.py`, `test_smoke.py`, `test_distances.py`, `test_features.py`

**Fokus:** CLI-Pfad-Korrektheit, Test-Coverage-Audit.

**Checkliste:**
- [ ] CLI-Wizard: läuft `python -m spielplan_multi` noch ohne Fehler durch?
- [ ] CLI-Formel-Synchronität mit `app.py` (siehe B5-H1)?
- [ ] Tests: laufen alle test_*.py durch? `pytest`-Output sauber?
- [ ] Test-Coverage: welche Module sind ungetestet? (`tt_scheduler.py`, `sa_refine.py`?)
- [ ] Smoke-Test deckt die wichtigsten Pipeline-Stationen ab?
- [ ] Test für Spielfrei-Modus (ungerade Teamzahl) vorhanden?
- [ ] Test für Turniertag (gpd > 1) vorhanden?

---

## Nach jedem Block

1. Befunde als neuen Eintrag in `BACKLOG.md` anhängen: `### [intern] Code-Review Runde 6 – Block X: <Thema>` mit Liste aller Befunde.
2. Severity je Befund: Kritisch / Hoch / Mittel / Niedrig.
3. Fixes nicht im Review-Block selbst — getrennte Aufgabe, nach Backlog-Eintrag.
4. CLAUDE.md am Ende der Runde updaten (neue „Code-Review Runde 6"-Sektion).

---

## Historische Reviews (zur Kontext-Erhaltung)

- **Runde 1** (vor Mai 2026): erste systematische Durchsicht, ~10 Hauptbugs
- **Runde 2** (Mai 2026): ~15 weitere Fixes, Heatmap-Spaltenindex, DST-Routing
- **Runde 3** (Mai 2026): ~25 Fixes, Launcher-Sicherheit, defaultdict-Fix
- **Runde 4** (Mai 2026): ~20 Fixes, Sys.stdout-Race, ZIP-Path-Traversal, Crashes
- **Runde 5** (Mai 2026, abgeschlossen): 8 Blöcke, ~15 Fixes, recompute_result_stats Transitions-Modell, Sliding-Window für DST-Lücken

**Nach Runde 5:** Optimierungslücke-Verringerung als großes Feature in BACKLOG.md (siehe Eintrag „Optimierungslücke (Optimality Gap) verringern"), nicht Teil dieser Review-Runde.
