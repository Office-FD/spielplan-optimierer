# Fix-Plan – Code-Review Runde 6

> **Erstellt:** Mai 2026 nach Abschluss Code-Review Runde 6 (7 Blöcke, 70 Befunde)
> **Quellen:** Detail-Beschreibungen jedes Befunds in `BACKLOG.md` (suchen nach ID)

---

## Versionierung

| Sprint | Ziel-Version | Themen |
|---|---|---|
| 1 | v1.3.0-rc1 | Datenkonsistenz nach SA & Mutationen |
| 2 | v1.3.0 | DST-Swap absichern + Validator-Lücken |
| 3 | v1.3.1 | State-Management & Release-Robustheit |
| 4 | v1.4.0 | Test-Coverage + CI-Integration |
| 5 | je nach Bedarf | Niedrig-Prio-Cleanup |

---

## Sprint 1 · Datenkonsistenz wiederherstellen

**Ziel:** Heatmap, Fairness-Tabelle und Excel stimmen mit den Daten überein – auch nach SA und manuellen Mutationen.
**Acceptance:** Nach SA und nach jeder Mutation: `home_vals[(ti,d)]` stimmt mit `schedule[d]` überein, `sw_rates` aus recompute = sw_rates aus Solver.
**Aufwand:** ~2-3 Stunden

- [x] **A-H1** · `sa_refine.py:289` · `home_vals` aus neuem schedule rekonstruieren (gleiches Pattern wie v1.2.7→v1.2.8 Session-Restore-Fix)
- [x] **A-H2** · `sa_refine.py:40` · `dst_eff`-Term in `_objective()` aufnehmen (Konstante während SA, aber Wert-Konsistenz zu Phase 2)
- [x] **C-M2** · `schedule_utils.py:78` · sw_rates-Denominator auf `cfg.n_transitions` umgestellt (konsistent zu solver.py)
- [x] **C-M1** · `schedule_utils.py:221, 245` · `cancel_game` + `reschedule_game` mit Turniertag-Guard

**Status:** Erledigt · Version: v1.3.0-rc1 · Tests: test_smoke + test_features grün

---

## Sprint 2 · DST-Swap absichern + Validator-Lücken

**Ziel:** Manuelle Mutation und Validator-Vorprüfung sind robust gegen häufige Fehler.
**Acceptance:** Kein stilles INFEASIBLE bei häufigen Eingabefehlern; DST-Swap-Verhalten matcht der UI-Anzeige.
**Aufwand:** ~3-4 Stunden

- [x] **C-H1** · `schedule_utils.py:82` · `swap_home_away` auf DST-Tagen verbieten (Guard + UI-Button disabled + Warntext)
- [x] **D-M4** · `app.py:2010` · `np.nan_to_num(mat2, nan=0.0)` nach data_editor
- [x] **B-M1** · `config_validator.py` · Pflichtspiel-Heimrecht + Sperrtag-Konflikt-Check (in beiden Validatoren)
- [x] **B-M2** · `config_validator.py` · Doppelte Pflichtspiel-Paarung im selben Round bei n_rounds≥2
- [x] **B-M3** · `config_validator.py` · `forced_home`-Teamnamen gegen Teamliste prüfen (in beiden Validatoren)
- [x] **A-M2** · `solver.py:540` · Warn-Zeile bei blocked+forced_home-Override

**Status:** Erledigt · Version: v1.3.0 · Tests: test_smoke + test_features grün

---

## Sprint 3 · State-Management & Release-Robustheit

**Ziel:** Liga-Operationen hinterlassen keinen verwaisten State, Round-Trip Excel-Export/Import vollständig, Release-Workflow validiert sich selbst.
**Acceptance:** Liga löschen/umbenennen lässt keine `cal_table`-Reste, `host_slots` überleben Excel-Round-Trip, Tag-Mismatch im Release scheitert die Action.
**Aufwand:** ~3-4 Stunden

- [x] **D-M1** · `app.py:1486` · Liga-Removal cleant `S.cal_table`, `S.time_templates`, `S.opt_best` + Widget-Keys
- [x] **D-M2** · `app.py:1921` · Liga-Rename überträgt auch `S.cal_table` etc. + Widget-Keys
- [x] **D-M3** · `app.py:1014, 1294` · `host_slots` im TT-Spielreihenfolge-Sheet round-trippen
- [x] **F-M2** · `.github/workflows/release.yml` · Tag-Validation-Step vor Build
- [x] **E-M3** · `app.py:3982` · `_regen_league_excel`: bei Overview-Fehler `S.overview_bytes = None` statt stale
- [x] **A-M1** · `solver.py:342-369` · DST-Nachbarschaft mit `needs_bye`-Branch (`>= _plays - 1` statt `>= 1`)

**Status:** Erledigt · Version: v1.3.1 · Tests: test_smoke + test_features grün

---

## Sprint 4 · Test-Coverage + CI

**Ziel:** Die in Sprints 1-3 gefixten Bugs sind durch automatisierte Tests abgesichert, Regressionen werden in PRs gefangen.
**Acceptance:** `pytest` läuft grün in GitHub Actions auf jedem PR, deckt forced_home, Spielfrei, Mutationen ab.
**Aufwand:** ~4-6 Stunden

- [x] **G-M2** · Tests für `forced_home`: respektiert, Override-Verhalten gegen Sperrtag, Validator-Konflikt
- [x] **G-M3** · Test für `n_active_per_day > 0` Spielfrei-Modus (5 Teams, n_rounds=2) + faire Bye-Verteilung
- [x] **G-M4** · Tests für `move_game`, `cancel_game`, `reschedule_game`, `recompute_result_stats` + Turniertag-Guards
- [x] **G-L6** · Pytest-Wrapper `test_pytest_runner.py` ruft existierende CLI-Scripts via subprocess
- [x] **G-L6/F-L8** · GitHub-Actions `test.yml` für push:main + PRs; `release.yml` mit Test-Gate vor Build

**Status:** Erledigt · Version: v1.4.0 · Pending: lokale Test-Verifikation

---

## Sprint 5 · Optional · UX & Niedrig-Prio Cleanup

**Ziel:** Wahrnehmbare Verbesserungen und Aufräum-Arbeiten nach Bedarf / Nutzer-Feedback.
**Aufwand:** Variabel, je Item Klein.

### UX-Konsistenz
- [x] **E-M1** · UI-Spielplan-Tabelle: Uhrzeit-Spalte anzeigen
- [x] **C-M3** · `build_print_html` km-Spalte „Direkt-km" mit erklärendem Tooltip
- [x] **E-L1** · DST-Hinweis bei Cancel/Move analog zu Swap
- [x] **E-L5** · Phase-Label `{1: 'Hin', 2: 'Rück', 3: 'Dritte'}` für alle n_rounds
- [x] **E-L6** · `[FEHLER]` als `st.error`, `[!!]` als `st.warning` (dict-Struktur mit Level)

### Performance
- [x] **E-M2** · Diagnose-Cache (`_diagnose_infeasible_league`) keyed an `(lid, len(opt_log))`
- [x] **E-L2** · Polling `sleep(2)` → `sleep(0.5)`
- [x] **E-L7** · Excel-Regen nur bei geänderten Spielzeiten

### Distribution
- [x] **F-M1** · Atomarer `_apply_update` mit Backup/Rollback in `launcher.py` (v1.6.1)
- [x] **F-L1** · `_parse_version` für non-numeric Tag-Suffixe (pre-release split)
- [x] **F-L2** · Update-Check in Background-Thread, Server-Start parallel (v1.6.1)
- [x] **F-L3** · `Spielplaene/` aus `[UninstallDelete]` ausnehmen (explizite Dateilisten)
- [x] **F-L4** · `spielplan.iss` MyAppVersion-Default auf 1.4.0
- [x] **F-L5** · `build_release.py` Mindest-Dateianzahl prüfen (10)
- [x] **F-L6** · Python-Embedded SHA256-Verifikation in build_bootstrap.bat
- [x] **F-L7** · GitHub Actions: Kommentar zu SHA-Pinning (Tag-Pin bleibt, Dependabot empfohlen)

### CLI
- [x] **G-M1** · CLI `step4_weights` dst_eff-Default auf 0.0
- [x] **G-L4** · `main.py` ruft `build_overview_excel`
- [x] **G-L1, G-L2, G-L3** · `wizard.py` Refactor Tuple → `WizardLeagueDef`-Dataclass, Dead-Code entfernt, Routing-Format vereinheitlicht (v1.6.0)
- [x] **G-L5** · `test_smoke.py make_config` w_scaled-Setup korrigiert

### Solver/Validator/Sonstiges
- [x] **A-L1** · `multi_solver.py:85` „Prozess-Absturz" → „Worker-Absturz"
- [x] **A-L2** · `tt_scheduler.py` `random.Random(seed)` durchgereicht
- [x] **A-L3** · `sa_refine.py` Doku zur Zeit-Reproduzierbarkeit
- [x] **A-L4** · `league_types.py` Vestigial Fallbacks durch `max(1, …)` ersetzt
- [x] **A-L5** · `_ProgressCallback` mit `seed`-Tag im Log
- [x] **B-L1** · Sperrtag-Tage außerhalb 1..N werden gewarnt
- [x] **B-L2** · `_parse_cell("5/5")` → Einzelspieltag
- [x] **B-L3** · Doppelter Spieltag in 2 KWs warnen
- [x] **B-L4** · `validate()` vs `validate_cfgs()` Konsolidierung in `_validate_league_common()` + Adapter (v1.6.0)
- [x] **B-L5** · `np.isnan(int_array)` Robustheit via `_has_nan()`-Helper
- [x] **B-L6** · `n_games_per_day` nutzt `n_active_per_day`
- [x] **B-L7** · `len(pins) > total_games` als Fehler
- [x] **B-L8** · Half-matching Distanzmatrix-Header → 80%-Heuristik mit spezifischer Warnung
- [x] **C-L1** · `cancel_game` warnt bei DST-Tag (stdout-`[!!]`-Hinweis)
- [x] **C-L2** · iCal `X-WR-CALDESC`-Hinweis bei übersprungenen Spielen
- [x] **C-L3** · `_parse_date` Exception spezifisch
- [x] **C-L4** · Magic-Number 999 → Modul-Konstante `_UNKNOWN_KW_SORT`
- [x] **C-L5** · Co-Home Skipping-Hinweis im Sheet
- [ ] **D-L1** · Liga-ID-Rename auf expliziten Button (UX-Verhaltensänderung — zurückgestellt)
- [x] **D-L2** · `_session_from_json` clears `de_{lid}` Editor-Cache
- [x] **D-L3** · `S.solver`-Merge mit `_DEFAULTS` bei JSON-Restore
- [x] **D-L4** · Calendar-Import Warnung vor Overwrite manueller Datumswerte
- [x] **D-L5** · `team_verein_map` in JSON exportieren + importieren
- [x] **D-L6** · `contextlib.redirect_stdout()` Context-Manager
- [x] **D-L7** · Warning wenn `excel_bytes` nach Restore unvollständig
- [x] **E-L3** · `proc.start()` mit try/except + st.error
- [x] **E-L4** · iCal Saison-Startjahr Default = `datetime.now()` mit Saison-Heuristik

**Status:** Erledigt · Version: v1.4.1 · 6 große Refactor-Items zurückgestellt (siehe BACKLOG.md)

---

## Routine nach jedem Fix

1. **Code-Änderung committen** mit Format `fix: <ID> <kurze Beschreibung>` (z.B. `fix: A-H1 SA aktualisiert home_vals`)
2. **Checkbox in FIX_PLAN.md abhaken** (`[ ]` → `[x]`)
3. **Bei letztem Item eines Sprints:** Sprint-Status auf „Erledigt", VERSION-Tag setzen, CLAUDE.md-Header aktualisieren
4. **Im BACKLOG.md:** Befund-Status auf „Erledigt" setzen

---

## Übersicht-Status (am Ende immer aktualisiert)

| Sprint | Items | Erledigt | Status |
|---|---|---|---|
| 1 | 4 | 4 | **Erledigt (v1.3.0-rc1)** |
| 2 | 6 | 6 | **Erledigt (v1.3.0)** |
| 3 | 6 | 6 | **Erledigt (v1.3.1)** |
| 4 | 5 | 5 | **Erledigt (v1.4.0)** |
| 5 | 45 | 39 | **Erledigt (v1.4.1) — 6 Refactor-Items zurückgestellt** |
| R1 | 4 | 4 | **Erledigt (v1.6.0) — B-L4, G-L1, G-L2, G-L3** |
| R2 | 2 | 2 | **Erledigt (v1.6.1) — F-M1, F-L2** |
| **Σ** | **72** | **66** | |

(Σ < 70 weil einige Niedrig-Befunde zusammengefasst sind.)
