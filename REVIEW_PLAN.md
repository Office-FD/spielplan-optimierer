# Code-Review Plan – Spielplan-Optimierer

> **Status:** Runde 7 vorbereitet 27.05.2026 — Fokus auf alles, was seit v1.6.2 dazugekommen ist.
> **Vorheriger Stand:** Runde 6 (Mai 2026) komplett abgeschlossen — 67/73 Items + R1-R3-Refactors.
> **Aktuelle App-Version:** v1.12.1 (lokal). 9 Tag-Pushes seit Runde 6: v1.7.0 → v1.12.1.

---

## Prinzip der Aufteilung

Statt das gesamte Projekt nochmal von vorne zu reviewen (alte Module wurden in Runde 6 gründlich geprüft + R1-R3-Refactor), fokussiert Runde 7 auf die **neuen / stark veränderten Module**. 5 Blöcke, jeder eigenständig in ~30-60 min reviewbar.

Reihenfolge-Empfehlung: **A → B → C → D → E**, weil jede Stufe auf der vorigen aufbaut.

---

## Block A: Solver-Erweiterungen (F1 + Telemetrie)

**Dateien:**
- `spielplan_multi/solver.py` (H3 Switch-Bound, H1 symmetry_level, Telemetrie in `_ProgressCallback` + `solve_league_phase1`)
- `spielplan_multi/multi_solver.py` (H1 symmetry_level, set_hints-Erweiterung H2, Phase-2-Telemetrie)
- `spielplan_multi/sa_refine.py` (v1.12.1-Hotfix: Telemetrie durchreichen)
- `spielplan_multi/league_types.py` (`gap_history`, `best_bound`, `final_gap`)

**Fokus:** Korrektheit der F1-Hebel + Telemetrie-Persistenz durch alle 3 Phasen.

**Checkliste:**
- [ ] H3-Bound `_max_sw_per_team = n_transitions - consecutive_dst`: ist die Berechnung für n_rounds=3 oder Turniertag korrekt? Was bei `dst_blocks[(d1, d2)]` wo `d2 > d1+1`?
- [ ] symmetry_level=2: bool_core-OOM-Risiko bei seltsamen Configs noch denkbar? `max_memory_in_mb=4096` als Schutz ausreichend?
- [ ] set_hints H2: werden die abgeleiteten `switch`-Werte korrekt aus `home_vals` berechnet, auch bei Turniertag (`gpd > 1`)?
- [ ] sa_refine Telemetrie-Pass-Through: was, wenn Input-`gap_history` None ist statt `[]`? Defaults sauber?
- [ ] `final_gap`-Berechnung bei `best_bound = 0` oder negativ — Division-by-zero geguarded?
- [ ] Pipeline-Konsistenz: Phase 1 → Phase 2 → SA → Telemetrie-Werte sollten am Ende NICHT verloren sein (war v1.12.0-Bug)
- [ ] `_ProgressCallback.history`-Wachstum: bei sehr langen Läufen (~24h, >1000 Improvements) RAM-Bedenken?

**Mündung:** Befunde in `BACKLOG.md` als „Code-Review Runde 7 – Block A".

---

## Block B: Neue Datenmodule (Karte + Kalender)

**Dateien:**
- `spielplan_multi/geocode.py` (Nominatim, Cache, set_manual_coord)
- `spielplan_multi/map_output.py` (build_route_map)
- `spielplan_multi/calendar_output.py` (build_calendar_events, _date_from_kw, _guess_season_year)

**Fokus:** Korrektheit + Robustheit der neu hinzugekommenen Module.

**Checkliste:**
- [ ] Geocode-Cache: was passiert bei concurrent Schreibzugriff (mehrere Streamlit-Sitzungen)? File-Locking nötig?
- [ ] `_normalize`: Behandelt Umlaute (ä, ö, ü) konsistent? Mehrere Whitespace-Arten?
- [ ] Nominatim-API-Vertrag: User-Agent ok, rate-limit 1.1s reicht laut Policy?
- [ ] `set_manual_coord`: Validierung (Wertebereich) liegt nur in der UI, nicht im Helper — bewusst?
- [ ] `build_route_map` bei leeren Schedule, Single-Team-Liga, allen Teams am selben Ort: alle 3 Fälle?
- [ ] `build_calendar_events` `_guess_season_year`-Heuristik: was bei einem Lauf der über 2 Saisons geht?
- [ ] DST-Block (z. B. 2 Tage in 2 verschiedenen Wochen): wird er korrekt im Kalender dargestellt oder als 2 Events?
- [ ] Calendar mit `include_uhrzeit=True`: Uhrzeit `'24:00'` oder leerstring?
- [ ] Default-Calendar-Options `firstDay=1` für DE — korrekt für FullCalendar v5+?

**Mündung:** Befunde als „Code-Review Runde 7 – Block B".

---

## Block C: UI-Erweiterungen + JSON-Persistenz

**Dateien:**
- `app.py` (neue Sections: Karte, Kalender, Telemetrie, missing_geocodes-Editor)
- `app.py` `_session_to_json` + `_session_from_json` (Schema 1.1)
- `app.py` `_translate_solver_log` + `_BEST_LINE_RE`

**Fokus:** UX-Korrektheit der neuen Sektionen, Save/Load-Roundtrip, Log-Parser-Robustheit.

**Checkliste:**
- [ ] JSON Schema 1.0 → 1.1: Lade-Test mit alten Sessions? Crash-frei?
- [ ] `S.map_obj`-Cache: wird er bei jeder Liga-/Schedule-Änderung wirklich invalidiert?
- [ ] Adressen-Editor: was, wenn User Liga-Konfiguration ändert WÄHREND ein Geocoding-Lauf läuft?
- [ ] `_BEST_LINE_RE`: gibt es CP-SAT-Output-Varianten die nicht matchen (`[combined with: ...]`-Suffix)?
- [ ] Live-Log-Übersetzung bei sehr großem `S.opt_log` (>10k Zeilen): Performance?
- [ ] Telemetrie-Section bei Phase-1-only-Modus (Phase 2 failed → Fallback): wird korrekt der pro-Liga-Modus aktiviert?
- [ ] CSV-Export: Encoding (utf-8 vs. utf-8-sig für Excel-Kompatibilität)? Spalten-Namen mit Umlauten?
- [ ] Defensive Fallbacks (folium/streamlit-folium/streamlit-calendar fehlen): Info-Boxen erscheinen korrekt?
- [ ] `missing_geocodes` Session-State: kollidiert mit anderen Wizard-Schritten?

**Mündung:** Befunde als „Code-Review Runde 7 – Block C".

---

## Block D: CI-Quality + Test-Coverage

**Dateien:**
- `.github/workflows/test.yml`, `coverage.yml`, `codeql.yml`, `release.yml`
- `.github/dependabot.yml`, `.pre-commit-config.yaml`, `ruff.toml`, `.coveragerc`
- `run_coverage.py`, `test_pytest_runner.py`
- Neue Tests in `test_all.py` (Test 14) und `test_features.py` (Feature 7-10)

**Fokus:** CI-Infrastruktur-Korrektheit, Test-Aussagekraft, Edge-Cases bei Workflows.

**Checkliste:**
- [ ] Ruff-Config: deckt sie auch `_translate_solver_log` (neu, regex-heavy) korrekt ab?
- [ ] Test-Coverage: noch ≥ 70 % für die neuen Module (geocode, map_output, calendar_output)?
- [ ] CodeQL-Findings: bei letztem grünen Lauf — gab es ignored alerts?
- [ ] Dependabot: alle Major-Updates seit v1.7.0 sauber durchgegangen (`pandas 3.0` insbesondere)?
- [ ] Release-Workflow F-M2 (Tag-VERSION-Konsistenz): noch aktiv und sauber?
- [ ] `run_coverage.py`: Failed-Subprocess wird korrekt als Exit ≠ 0 propagiert?
- [ ] Pre-Commit-Hook installiert auf Dev-Maschine? Falls nicht: ungeprüfte Lokal-Commits möglich

**Mündung:** Befunde als „Code-Review Runde 7 – Block D".

---

## Block E: Dokumentation + Distribution + Memory

**Dateien:**
- `CLAUDE.md`, `BENUTZERHANDBUCH.md`, `INSTALLATION.md`, `README.md`, `ROADMAP.md`, `SPRINT_SNAPSHOT.md`
- `installer/spielplan.iss`, `installer/build_bootstrap.bat`
- `requirements.txt`
- `Spielplaene/telemetrie/*` (pre/post-F1-Daten)
- Memory: `project_state.md`, `project_roadmap.md`, etc.

**Fokus:** Konsistenz der Dokumentation mit Code, Wartbarkeit, Endnutzer-Verständlichkeit.

**Checkliste:**
- [ ] BENUTZERHANDBUCH: alle neuen Buttons/Sections dokumentiert (Karte, Kalender, Telemetrie, Adressen-Editor)?
- [ ] INSTALLATION: Hinweis auf folium/streamlit-folium/streamlit-calendar drin?
- [ ] CLAUDE.md: Section 9 (Code-Reviews) hat eindeutige Reihenfolge der Sprints v1.3.0 → v1.12.1?
- [ ] requirements.txt: Versionsbereiche (`>=`/`<`) sinnvoll für Endnutzer? Reproducibility-Risiken?
- [ ] Bootstrap-Installer v1.11.3: enthält er alle Pakete für die UI-Features?
- [ ] Memory-Konsistenz: `project_state.md` reflektiert wirklich v1.12.1?
- [ ] `Spielplaene/telemetrie/`-Daten: sind gitignored (lokal) — bewusst, oder gehört das Verifikations-MD ins Repo (`docs/`)?
- [ ] README.md: GitHub-Account-Suspension-Hinweis nötig oder verzichtbar?

**Mündung:** Befunde als „Code-Review Runde 7 – Block E".

---

## Erwartete Befund-Größe

Runde 6 hatte 73 priorisierte Items. Runde 7 fokussiert auf 5 statt 7 Blöcke und betrachtet eine kleinere (frischere) Code-Basis — Erwartung: **20-30 Befunde**, davon vielleicht 1-3 wichtig (Hoch-Prio) und der Rest mittel/niedrig.

## Was nicht in dieser Runde

Bewusst aus dem Scope:
- `solver.py`-Constraints (außer F1-bedingt) — wurden in CR6 Block A vollständig geprüft
- `tt_scheduler.py`, `excel_output.py`, `wizard.py` — wurden in CR6 ausführlich abgedeckt
- Unveränderte UI-Wizard-Schritte 1-7 — in CR6 abgedeckt
- `launcher.py` — in CR6-Block F + R2-Refactor durchgeprüft

Falls in einem Block-Review ein Issue auf diese Module verweist, kann jederzeit nachgehakt werden — aber keine systematische Re-Review nötig.

## Aktueller Account-Status (27.05.2026)

GitHub-Account `Office-FD` ist seit 26.05.2026 ~12:00 UTC bei Actions blockiert (Anti-Abuse-Filter nach 18 Tag-Pushes in 24h). Support-Ticket läuft. Bis zur Reaktivierung:
- ✅ Lokale Commits sind ok
- ❌ Kein `git push` / `git tag` (würde nur main-Inhalt aktualisieren ohne CI)
- ❌ Keine neuen Releases auf GitHub
- → Review-Befunde lokal sammeln, Hotfixes lokal committen, später als Batch pushen
