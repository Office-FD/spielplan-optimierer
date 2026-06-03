# Changelog – Spielplan-Optimierer

Vollständige Änderungshistorie aller Code-Reviews und Feature-Sprints.
Aktueller Entwicklungsstand und operative Dokumentation: **CLAUDE.md**

---

## v1.17.1 — Reise-Entlastung (Randlagen-Teams) · OneDrive-Cache + Worker-Fix · JSON-Restore-Bugfix

### Reise-Entlastung für Randlagen-Teams (`dst_relief`)

Neue per-Team-Option: Teams in Randlagen können auf eine maximale Anzahl Heim-Doppelspieltage pro Saison begrenzt werden → sie reisen ihre DST-Fahrten gebündelt auswärts, statt zur Standard-Balance gezwungen zu werden. Konfiguration in Wizard-Schritt 3 (per-Team), Persistenz in Konfigurations-Excel.

| Datei | Änderung |
|---|---|
| `spielplan_multi/league_types.py` | Neues Feld `dst_relief: Dict[str,int]` ({Team: max_Heim_DST}; leer = Standard-Balance) |
| `spielplan_multi/solver.py` | DST-Balance pro Runde: markierte Teams werden auf `Heim-DST ≤ cap` (Saison) gecappt; übrige Teams absorbieren (Runden-Obergrenze auf `n_dst_r` gelöst, Untergrenze `lo` bleibt) |
| `spielplan_multi/config_validator.py` | Validierung: Warnung bei unbekanntem Team, falschem Format (Turniertag/ungerade Teamzahl/<2 DST-Blöcke wirkungslos), und bei zu vielen Entlastungs-Teams (`R > n//4` → INFEASIBLE-Risiko) |
| `app.py` | Wizard-Schritt 3: per-Team-Eingabe; Session-State `S.dst_relief` (bei Liga-Remove/Rename mitgepflegt); Excel-Persistenz |
| `test_dst_relief.py` | Feasibility + Cap-Einhaltung + Reise-Entlastungs-Effekt |

**Wichtig:** Da die Summe der Heim-DST pro Tag fix ist (n/2), müssen nicht-markierte Teams die freigewordenen Heim-Slots absorbieren. Der Validator warnt, wenn zu viele Teams markiert sind (Empfehlung: höchstens `n//4`).

### OneDrive-freier Laufzeit-Cache + Worker-Exit-Fix

| Datei | Änderung |
|---|---|
| `spielplan_multi/runtime_paths.py` (neu) | `run_cache_dir()`: Laufdateien (pkl/log/pid) landen in lokalem Cache statt im OneDrive-`.cache` — OneDrive-Sync kann sonst Schreibzugriffe sperren und fertige Läufe verlieren |
| `spielplan_multi/_worker.py` | Ergebnis-Übergabe **nur** via `last_result.pkl`, nie durch `log_q` — großes Result-Objekt füllte sonst die 64-KB-Pipe, der QueueFeederThread blockte beim Exit, `__DONE__` kam nie an und die UI „blieb in Phase 2" |
| `test_worker_handoff.py` | Worker-Übergabe: kein Exit-Deadlock, results ausschließlich via Pickle |

### Bugfix: JSON-Restore ohne vollständige Liga-Konfiguration

Sitzungs-JSONs, die nach einem Session-Rejoin gespeichert wurden, enthielten eine leere `config.leagues`-Liste (weil `S.leagues` in der frischen Session-Rejoin-Sitzung nie befüllt wurde). Beim Laden einer solchen Datei gab `_build_league_configs()` ein leeres Dict zurück, alle Ligen wurden beim Restore übersprungen, und `S.results` blieb leer.

| Datei | Änderung |
|---|---|
| `app.py` | `_session_from_json()`: Fallback nach `_build_league_configs()` — wenn `cfgs` leer, aber `results_data` vorhanden, werden minimale `LeagueConfig`-Objekte aus den Spielplan-Daten rekonstruiert (Teams aus Schedule, Weekends/DST-Blöcke aus `kw_compat`, Kalender aus `kw_compat`; Distanzmatrix und Gewichte stehen als Nullwerte zur Verfügung) |

**Einschränkungen der rekonstruierten Konfiguration:** Distanzmatrizen (→ km-Statistiken sind 0), Solver-Gewichte (→ Fairness-Kennzahlen nicht berechnet), n_rounds-Inferenz per Heuristik (Standard-Hin-Rückrunden). Die Spielpläne und Visualisierungen (Karte, Kalender) werden korrekt wiederhergestellt.

---

## v1.17.0 — Gesamtübersicht Excel: Sort-Fix + Spaltenstruktur

| Datei | Änderung |
|---|---|
| `spielplan_multi/excel_output.py` | Sort-Key in `build_overview_excel()`: Tuple `(year_order, kw, slot_idx)` statt Datums-Parsing — DST-Wochenenden erscheinen jetzt chronologisch (KW > 26 → Herbst, KW ≤ 26 → Frühjahr) |
| `spielplan_multi/excel_output.py` | kw_compat-Fallback: wenn `cfg.calendar` leer (JSON-Restore), wird `kw_compat` als Datenquelle genutzt |
| `spielplan_multi/excel_output.py` | Trennerspalte (~25px) zwischen den Ligen |
| `spielplan_multi/excel_output.py` | Spaltenbreiten: Datum ~120px (16 Einh.), Liga-Heim/Gast je ~180px (24 Einh.), Trenner ~25px (3 Einh.) |

---

## v1.16.2 — Bugfix: Intro-Seite nach Session-Rejoin sofort entfernt

**Root Cause v1.16.1:** `st.rerun()` wurde innerhalb von `_render_detached_view()` aufgerufen, also mitten in einem Render-Zyklus. Streamlit sendet das "Finalize"-Signal (→ Frontend entfernt nicht mehr gerenderte Elemente) erst nach einem vollständigen Render-Zyklus. Da der Zyklus durch `RerunException` abgebrochen wurde, blieb die Intro-Seite im Browser-DOM solange erhalten, bis zufällig ein kompletter Zyklus durchlief.

| Datei | Änderung |
|---|---|
| `app.py` | `_render_detached_view()` gibt jetzt `'poll'`, `'done'` oder `''` zurück statt `st.rerun()` selbst aufzurufen |
| `app.py` | `st.rerun()` / `time.sleep(2)` erst **nach** dem vollständigen Dispatch-Block (nach dem Render-Zyklus) |

---

## v1.16.1 — Bugfix: Intro-Seite überlagerte Detached-Ansicht in Schritt 9

Nach dem Session-Rejoin war unterhalb des Solver-Logs die Intro-Seite (Floorball-Logo + Marketing-Text) sichtbar — weil das Detached-Rendering innerhalb von `_step8()` lag und `st.rerun()` in bestimmten Streamlit-Situationen nicht zuverlässig verhinderte, dass `_step_intro()` zusätzlich gerendert wurde.

| Datei | Änderung |
|---|---|
| `app.py` | Neue Funktion `_render_detached_view()` aus `_step8()` extrahiert |
| `app.py` | Detached-Branch aus `_step8()` entfernt |
| `app.py` | Top-Level-Dispatch: `if S.opt_detached and not S.opt_done:` als ersten Branch vor `_step_intro()` eingefügt — strukturell ausschließend via `if/elif/else` |

Mit `if/elif/else` kann exakt einer der drei Branches ausführen. `_step_intro()` kann strukturell nie gleichzeitig mit dem Detached-View gerendert werden.

---

## v1.16.0 — Session-Rejoin nach Browser-Verbindungsabbruch

Bei langen Optimierungsläufen (Phase 2, 90 min–8h) kann der Browser die Verbindung zum Streamlit-Server unterbrechen. Bisher war der Solver-Fortschritt dann nicht mehr sichtbar. Ab v1.16.0 kann die neue Session in den laufenden Prozess einsteigen und den Fortschritt live weiterverfolgen.

| Datei | Änderung |
|---|---|
| `spielplan_multi/_worker.py` | Subprocess schreibt PID in `.cache/opt_pid.txt` und alle Log-Zeilen parallel in `.cache/opt_log.txt`; PID-Datei wird in `finally` gelöscht |
| `app.py` | Neue Hilfsfunktionen `_pid_alive()`, `_detach_state()`, `_try_recover_pkl()` |
| `app.py` | Top-Level-Banner: zeigt "Optimierung läuft im Hintergrund" oder "Ergebnisse verfügbar" direkt auf der Startseite |
| `app.py` | Schritt 9: Detached-Polling-Zweig liest `.cache/opt_log.txt` inkrementell und zeigt Live-Log + beste Lösung |
| `app.py` | Step 9 Recovery refaktoriert auf `_try_recover_pkl()` (kein duplizierter Code mehr) |

**Ablauf nach Reconnect:**
1. Browser reconnectet → Startseite zeigt Banner "Optimierung läuft noch"
2. Klick auf "In laufende Optimierung einsteigen" → direkt zu Schritt 9 mit Live-Fortschritt
3. Wenn Solver fertig → `.cache/opt_pid.txt` verschwindet → Ergebnisse automatisch geladen

---

## v1.15.1 — Hotfix: dst_eff Default-Regression + Telemetrie-Anzeige

| Datei | Änderung |
|---|---|
| `app.py` | **Hotfix:** `_W_DEFAULTS['dst_eff']` von 3.0 → 0.0 zurückgesetzt — verhinderte Crash beim Solver-Start mit DST-Ligen |
| `app.py` | **Telemetrie-Fix:** `_BEST_LINE_RE` Regex `\d{2}:\d{2}` → `\d+:\d{2}(?::\d{2})?` — Telemetrie-Übersicht zeigte bei Läufen > 99 Minuten keine neuen Lösungen mehr |
| `spielplan_multi/solver.py` | **Lesbarkeit:** `_ProgressCallback` Zeitformat `mm:ss` → `h:mm:ss` ab einer Stunde Laufzeit |

**Ursache des Crashs:** `dst_eff=3.0` als Standard aktivierte erstmals den dst_eff-Modellbau für alle DST-Ligen. Dieser Codepfad war in Produktion nicht erprobt und führte zu einem unbehandelten Fehler im Solver-Subprocess. dst_eff bleibt auf 0 (opt-in) bis zur vollständigen Verifikation mit echten FLVD-Daten.

---

## v1.15.0 — dst_eff Skalierung

| Datei | Änderung |
|---|---|
| `spielplan_multi/config.py` | `WEIGHT_SCALES['dst_eff']` 0.03 → 0.15 (5×) — stärkere Belohnung geografisch effizienter DST-Paarungen für Randlagen-Teams |
| `app.py` | UI-Tooltip für dst_eff ergänzt |
| `CLAUDE.md` | `dst_eff`-Scale in Dokumentation aktualisiert |

---

## v1.14.0 — Niedrig-Cleanup R7+R8

Alle verbleibenden Niedrig-Befunde aus R7 (10 Items) und R8 (25 Items) sowie R8-H-M2 in 4 Etappen:

| Etappe | Inhalt | Befunde |
|---|---|---|
| A | Trivial-Niedrig B/C/D/E/F/G/H | B-L1 (iCal utcnow→timezone-aware), B-L3 (SA Sentinel-Schutz), B-L4 (sw_counts aus Schedule), C-L2 (Doku Symmetrisierung), C-L4 (sheet_name-Parameter), D-L1 (Phase-2-Objective-Anzeige in Liga-Excel), D-L2 (Hallenplan-Sortierung nach week_start), E-L1 (Pflichtspiel-Live-Konflikt-Check), E-L2 (KW>2 Warning), E-L3 (Schema-Version-Whitelist), F-L1 (Phase-2-Heuristik via phase2_objective), F-L2 (Mutation-Buttons disabled bei Turniertag), F-L3 (Phase-Detection-Cache `S._phase_seen`), G-L1 (Wizard Type-Hints), G-L2 (build_release EXCLUDE_DIRS), G-L3 (Launcher-Timeout 60→120 s), H-L2 (upload-artifact@v5) |
| B | Block-A-Niedrig (Solver) | A-L1 (Doku workers_per), A-L2 (Doku Bye-Verteilung), A-L3 (Co-Home OR über alle KW-Spieltage), A-L4 (Subprocess-Stacktrace verkürzt) |
| C | R7 zurückgestellt (10 Items) | A7-M2 (seed_histories-Feld), A7-L2 (Doku), C7-L1 (Markdown-Escape im Translator), C7-L2 (Doku), D7-L1 (Coverage-Threshold mit continue-on-error), D7-L2 (Pre-Commit-Hinweis). Skip: D7-L3 (Parallel-Tests), E7-L3 (CLAUDE.md-Aufteilung), E7-L4 (Screenshots), E7-L5 (bereits erledigt) |
| D | R8-H-M2 Test-Coverage | `test_launcher.py` (10 Tests), `test_session_roundtrip.py` (9 Tests), in `test_pytest_runner.py` integriert |

**Stand nach v1.14.0:** 0 Show-Stopper · 0 Hoch · 0 Mittel · 0 Niedrig offen · 4 dokumentierte Trade-off-Skips

---

## v1.13.1 — Code-Review Runde 8 (Mittel-Befunde)

Final-Review vor FLVD-Produktiveinsatz. 8 Blöcke (A–H), 0 Show-Stopper, 9 Mittel + 27 Niedrig.

| Datei | Befund | Fix |
|---|---|---|
| `README.md` | **R8-H-M1** Version 11 Releases veraltet | Update auf 1.13.1 |
| `installer/spielplan.iss` | **R8-G-M2** `.cache/` beim Deinstall gelöscht (API-Quota-Verlust) | `.cache` aus `[UninstallDelete]` entfernt; Info-Dialog |
| `app.py` | **R8-F-M1** Excel-Build-Fehler als String statt Dict → gelb statt rot | `{'level': 'error', 'msg': ...}` |
| `app.py` | **R8-E-M1** Liga-Remove räumte positions-indizierte Widget-Keys nicht auf | `_removed_pos`-basierter Cleanup |
| `app.py` | **R8-A-M1** Co-Home-Gewicht ohne Cap beim Import → Objective-Overflow | `_W_COHOME_MAX=50` + `_W_COHOME_WARN=20` in beiden Import-Pfaden |
| `excel_output.py` | **R8-D-M1** Eigene `_parse_date` mit 2-stelligem-Jahr-Bug (Duplikation) | Import `from .calendar_output import _parse_date as _parse_date_safe` |
| `config_validator.py` | **R8-C-M1** Validator: DST d1==d2, DST-Überlappung, forced_home > max-Heimspiele | 3 neue Checks in `_validate_league_common` |
| `schedule_utils.py` | **R8-B-M1** move_game/reschedule_game ohne DST-Konsistenz-Hinweis | DST-Warnings + `day not in cfg.days`-Validierung in reschedule_game |
| `launcher.py` | **R8-G-M1** Port 8501 TIME_WAIT-Race nach Update-Restart | `_port_is_free()` + `_wait_for_port_free(timeout=30)` |

---

## v1.13.0 — Code-Review Runde 7

5 Blöcke (A-E), 37 Befunde, 19 gefixt in 4 Commits. 18 Niedrig-Prio → BACKLOG.

| Commit | Inhalt |
|---|---|
| `647c02b` FIX-1 | D7-H1 + Quick-Wins: coverage.yml@v6, switch-Hint-Skip bei TT, final_gap ohne abs, User-Agent dynamisch, liga_idx weg |
| `8d1f575` FIX-2 | A7-M1 (gap_history-Kopie pro Liga), A7-M3 (`phase2_objective`-Feld + Gap-Berechnung) |
| `3083683` FIX-3 | B7-M1 (atomic write), C7-M1 (Log-Cache `S._translog_cache`), E7-M1 (requirements Upper-Bounds) |
| `edb43a7` FIX-4 | B7-L2/L5/L6 (Umlaute, HTML-Escape, 2-stelliges Jahr), A7-L3/L5, E7-L1 (ISS-Default) |

**Sprint B3 — F1-Verifikation bestätigt:**

| Lauf | Datum | Version | symmetry_level | Gap |
|---|---|---|---|---|
| pre-F1 | 23.05. | v1.6.x | 1 | **19,96%** |
| post-F1 | 26.05. | v1.12.0 | 2 | **15,35%** |

**−23,1% Gap-Reduktion** (Prognose: ~25%). F1-Hebel H1+H2+H3 quantitativ verifiziert.

---

## v1.12.1 — Hotfix SA-Telemetrie-Durchreichung

`sa_refine.py`: `gap_history/best_bound/final_gap` aus Input-Result durchreichen statt Default-Werte. Ursache: SA baut neues LeagueResult ohne Telemetrie-Felder → Werte aus Phase 2 gingen verloren.

---

## v1.12.0 — Solver-Log lesbar machen (UX-Sprint)

`app.py`: `_BEST_LINE_RE` + `_translate_solver_log` übersetzen `[BEST]`-Zeilen ins Deutsche. Section „📈 Was gerade passiert" (letzte 12 Übersetzungen, neuestes oben). Roh-Log im Expander.

---

## v1.11.3 — JSON-Telemetrie-Persistenz

`_session_to_json`: `objective/best_bound/final_gap/gap_history/mins/secs` je Liga. Schema-Version `'1.1'`. `_session_from_json`: backward-compatible (`.get()` mit Defaults).

---

## v1.11.2 — Endnutzer-Doku-Update

`BENUTZERHANDBUCH.md`: Schritt-Nummerierung 1-basiert, dst_eff + round_balance ergänzt, neue Sub-Sections für Telemetrie/Karte/Kalender. `README.md`: Feature-Liste aktualisiert.

---

## v1.11.1 — UX: Telemetrie-Section nach oben verschoben

Telemetrie direkt unter Kennzahlen-Metriken (war: nach Karte + Kalender).

---

## v1.11.0 — Sprint B1: Gap-Monitoring / Solver-Telemetrie

`league_types.py`: `gap_history/best_bound/final_gap` in LeagueResult. `solver.py`: `_ProgressCallback` speichert History. `multi_solver.py`: Phase-2-Werte in alle Liga-Results. `app.py`: „📊 Solver-Telemetrie"-Section mit Metriken, Line-Chart, CSV-Download.

---

## v1.10.1 — Hotfix Multi-Liga-Kalender

`build_calendar_events`: `season_year`-Parameter + `_guess_season_year()`. Fehlendes `week_start` → Datum aus `date.fromisocalendar(yr, kw, 6)`.

---

## v1.10.0 — Sprint A2: Interaktive Kalenderansicht

`calendar_output.py` (neu): `build_calendar_events()` → FullCalendar-Event-Format. `app.py`: „📅 Kalenderansicht"-Section. Defensiver Fallback bei fehlendem Paket.

---

## v1.9.2 — Sprint A1 Folge: Adressen-Editor

Bei fehlenden Geocodes: `st.expander` „📍 N Adresse(n) manuell ergänzen" mit lat/lon-Eingabe, Wertebereich-Validierung, Cache-Speicherung via `geocode.set_manual_coord`.

---

## v1.9.1 — Hotfix Optionale Karten-Pakete

`app.py`: Prüft ob `folium` + `streamlit_folium` installiert. Fehlende Pakete → `st.info` mit pip-Anweisung statt Crash.

---

## v1.9.0 — Sprint A1: Karten-Visualisierung Reiserouten

`geocode.py` (neu): OSM Nominatim mit JSON-Cache. `map_output.py` (neu): `build_route_map()` mit Folium. `app.py`: „🗺 Karten-Visualisierung"-Section mit Lazy-Loading.

---

## v1.10.0 — Dependabot-Update-Sprint

9 PRs gemerged: actions/checkout 4→6, setup-python 5→6, codeql-action 3→4, gh-release 2→3, requests 2.34.2, numpy 2.4.6, ortools 9.15.6755, streamlit 1.57.0, pandas 3.0.3.

---

## v1.8.1 — Sprint F1-H2: Phase-1→Phase-2 Hint-Boost

`solver.py:set_hints`: Zusätzlich `switch[ti,d]`, `sw_count[ti]`, `travel[ti]`, `max_sw/min_sw`, `max_travel/min_travel` gehintet. Erwartung: +15-17% Gap-Reduktion.

---

## v1.8.0 — Sprint F1: Solver-Optimierung (H1+H3)

`solver.py`: H3 — `sw_count`-Obergrenze `N-1-consecutive_dst` (tightert LP-Bound). H1 — `symmetry_level=2` mit `max_memory_in_mb=4096` (schützt vor OOM). Erwartung: ~10% Gap-Reduktion kombiniert.

---

## v1.7.1 — Test-Coverage-Sprint Q2

Coverage 67,8% → 77,5% (+9,7%). Neue Tests: 13 (calendar_parser), 23 (config_validator), 6 (build_overview_excel). Bug-Fix: `int(pm.get('day',0))` bei `day='abc'` crashte.

---

## v1.7.0 — CI-Quality-Sprint Q1

`ruff.toml`: Lint-Config (F/E4/E9/W6 strikt, Style toleriert). 26 Ruff-Auto-Fixes. `test.yml`: Ruff-Step vor pytest. `.dependabot.yml`: wöchentliche PRs. `.pre-commit-config.yaml`: lokale Hooks. `.github/workflows/codeql.yml`: Security-Scanning.

---

## v1.6.2 — Sprint R3: Liga-ID-Rename UX

`app.py`: `st.form(enter_to_submit=True)` für Liga-ID-Eingabe (kein Focus-Out-Rename). `_LID_RE = re.compile(r'[A-Z0-9_\-]{1,20}')`. Live-Caption + `st.toast` bei Erfolg.

---

## v1.6.1 — Sprint R2: Launcher-Hardening

`launcher.py` F-M1: atomare Updates (Backup→Move→Cleanup, Rollback bei Fehler). F-L2: Update-Check in daemon-Thread, Server startet parallel.

---

## v1.6.0 — Sprint R1: Wizard + Validator-Refactor

`wizard.py` G-L1/L2: `WizardLeagueDef`-Dataclass. G-L3: Routing-Format CLI auf `(apply, pct)` vereinheitlicht. `config_validator.py` B-L4: `_validate_league_common()` extrahiert (488→399 Zeilen).

---

## v1.5.0 — Feature: Heim-Balance pro Runde

Neues Gewicht `round_balance` (quadratische Abweichung Heim/Runde). `solver.py`: IntVars `home_in_round/dev2/abs_dev2/sq_dev`. Aktiv nur bei `gpd==1, n_rounds≥2, w>0`. 2 neue Tests.

---

## v1.4.1 — Code-Review Runde 6, Sprint 5: Niedrig-Cleanup

39/45 Items behoben. 6 größere Refactors zurückgestellt (→ R1-R3-Sprints erledigt). Wichtigste Fixes: A-L1/2/3/4/5, B-L1/5/6/7, C-L1-5/M3, D-L2-7, E-M1/2/L1-7, F-L1/3-7, G-M1/L4/5.

---

## v1.4.0 — Code-Review Runde 6, Sprint 4: Test-Coverage + CI

**G-M2** forced_home-Tests (3 neu). **G-M3** Spielfrei-Modus-Tests (2 neu). **G-M4** Mutations-Tests (4 neu). `test_pytest_runner.py` (neu). `test.yml` + `release.yml` mit Test-Gate. `distances.py`: `pd.ExcelFile` als context manager.

---

## v1.3.1 — Code-Review Runde 6, Sprint 3: State-Management + Release

**D-M1** Liga-Remove: `S.cal_table/time_templates/opt_best` + Widget-Keys aufräumen. **D-M2** Liga-Rename: gleiche Dicts transferieren. **D-M3** `host_slots` im Config-Excel. **F-M2** Tag-vs-VERSION-Validierung in `release.yml`. **E-M3** `S.overview_bytes=None` vor try. **A-M1** DST-Nachbarschaft + `needs_bye`.

---

## v1.3.0 — Code-Review Runde 6, Sprint 2: DST-Swap + Validator

**C-H1** `swap_home_away`: guard `if day in cfg.dst_days: return`. **D-M4** `np.nan_to_num(mat2, nan=0.0)` nach Distanzmatrix-Editor. **B-M1** Pin+blocked-Konflikt im Validator. **B-M2** Doppelte Pins pro Runde. **B-M3** forced_home-Teamnamen prüfen. **A-M2** Override-Warnung.

---

## v1.3.0-rc1 — Code-Review Runde 6, Sprint 1: Datenkonsistenz

**A-H1** SA: `home_vals` aus neuem Schedule rekonstruieren. **A-H2** `_compute_dst_eff_total()` für SA-Objective-Konsistenz. **C-M2** `sw_rates`-Denominator = `cfg.n_transitions`. **C-M1** `cancel_game/reschedule_game` Turniertag-Guard.

---

## v1.2.9 — Bugfix ScriptRunContext-Warnung

`_worker.py`: `warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')`.

---

## v1.2.8 — Bugfix home_vals beim Session-Laden

`app.py`: `home_vals` vor LeagueResult-Aufbau aus Schedule rekonstruieren.

---

## v1.2.7 — Bugfix Sliding-Window „tote Zone"

`solver.py`: 3-Wochenend-Fenster-Check auf `homeW` ergänzt; DST-Wochenenden beim Minimum-Check nicht mehr ausgenommen.

---

## v1.2.5–v1.2.6 — Features + Bugfixes

`schedule_utils.py`: Transitions-Modell in `recompute_result_stats`. `excel_output.py`: `build_overview_excel` komplett überarbeitet (je Spiel eine Zeile, Club-aware Farben, Datumssortierung). `app.py`: Dateinamen-Suffix mit Gewichten + Laufzeiten.

---

## v1.2.3–v1.2.4 — Code-Review Runde 5, Teil 1+2

| Datei | Fix |
|---|---|
| `sa_refine.py` | `loc`-Array-Init `[[ti]*…]` statt `[[0]*…]` |
| `wizard.py` | Spieltagzahl-Formel an 5 Stellen korrigiert |
| `app.py` | `s = parsed.get('settings', {})` immer setzen |
| `solver.py` | `needs_bye`-Dopplung entfernt; Pflichtspiel-Heimrecht-Validierung |
| `multi_solver.py` | `rel_gap` auch an `run_phase1` weitergeben |
| `config_validator.py` | Blocked/Pinned Teamnamen + Self-Play prüfen; Duplikat-Check |
| `config.py` | Ungenutzter `defaultdict`-Import entfernt |
| `distances.py` | Negative km-Werte verwerfen |

---

## v1.2.2 — Spielfrei-Modus (ungerade Teamzahl)

`league_types.py`: `n_matchdays`-Formel korrigiert. `solver.py`: `needs_bye`-Guards (`<= gpd`, `<= 1` für loc, konditionalisierte Sliding-Window-Minima). `config_validator.py`: ungerade Teamzahl → Warnung statt Fehler.

---

## v1.2.1 — Streamlit-Kompatibilität + Log-Cleanup

`app.py:379`: `width='content'` statt `width=None`. `_worker.py`: `logging.getLogger('streamlit').setLevel(ERROR)`.

---

## v1.1.2 — Kalender/Excel/UI-Fixes

`app.py`: Kalender-Sheet in Config-Excel (Up/Download). `use_container_width` → `width='stretch'`. `mat.astype(float)` für data_editor. Session-State-Init vor text_input.

---

## Code-Review Runde 2–4 (v1.0.x)

| Datei | Problem | Fix |
|---|---|---|
| `sa_refine.py` | `t_idx[ht]` KeyError | `.get()` mit Guard |
| `schedule_utils.py` | IndexError, fehlende Validierungen, iCal-Escaping | Guards + `_ical_escape()/_ical_fold()` |
| `config_validator.py` | pin_key str/int-Mismatch | `int(pm.get('day', 0))` |
| `solver.py` | Turniertag Switch-Summation | Branch überspringen |
| `config.py` | KeyError >20 Teams | `_TeamColorDict.__missing__` |
| `multi_solver.py` | Leeres `cfgs` in run_phase2 | Early-return |
| `tt_scheduler.py` | Fallback ohne Abbruch | `MAX_TRIES=20`; alle Permutationen |
| `excel_output.py` | Spaltenbreiten + n_bcols | Korrigiert |
| `app.py` | Liga-ID leer, INFEASIBLE False Positives, Routing min_value | Guards |
| `distances.py` | Truncation statt Rounding | `round(meters/1000)` |

---

## Code-Review Runde 1 (Erstimplementierung)

| Datei | Problem | Fix |
|---|---|---|
| `sa_refine.py` | LeagueResult ohne groups/hosts/game_times | Felder ergänzt |
| `excel_output.py` | Heatmap-Spaltenindex falsch | Mapping-Dict |
| `calendar_parser.py` | DST außerhalb Range → KeyError; Jahreswechsel-Bug | Filter + Jahr aus Monat |
| `solver.py` | 4er-Fenster bei back-to-back-DST → INFEASIBLE | Fenster überspringt DST |
| `solver.py` + `multi_solver.py` | OR-Tools 9.15: `SolveWithSolutionCallback` entfernt | `solver.Solve(model, callback)` |
| `config_validator.py` | NaN nicht erkannt | `np.isnan(dist).any()` |
| `solver.py` | DST-Routing `d1+1` statt `d2` | `for d1, d2 in cfg.dst_blocks` |
| `schedule_utils.py` | DTSTAMP fehlt in iCal | DTSTAMP in VEVENT |
| `app.py` | `S.sol` vs `S.solver` | `S.sol` → `S.solver` |
| `launcher.py` | Versionvergleich lexikografisch | `tuple(int(x) for x in v.split('.'))` |
| `launcher.py` | mktemp TOCTOU, Partial-Download, ZIP-Traversal | mkstemp + atomic + realpath-Guard |
| `schedule_utils.py` | `prev` nicht reset, swap_home_away bei TT, move_game kein TT-Guard | Guards |
| `config.py` | `defaultdict` TypeError | `_TeamColorDict.__missing__` |
| `calendar_parser.py` | `_to_date_str()` gibt 'nan' zurück | NaN-Guard |
| `distances.py` | Case-sensitiver CSV-Spaltenname | `.lower()` Lookup |
| `excel_output.py` | DST-Routing zeigt Faktor statt %; Fairness-Merge falsch | `f_num-100`; dynamische Breite |
| `wizard.py` | `n_active` undefiniert; `k_group` nicht gesetzt | Defaults ergänzt |
| `main.py` | Import in for-Schleife | An Dateianfang |
