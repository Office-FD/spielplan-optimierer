# Spielplan-Optimierer – Projektdokumentation

> **v1.15.0 · Mai 2026 · Produktiv-freigegeben für FLVD-Saisonplanung.**
> Vollständige Änderungshistorie aller Code-Reviews und Sprints: **CHANGELOG.md**

---

## 1. Schnell-Überblick

Automatisierte Spielplanerstellung für Floorball-Ligen (FLOORBALL VERBAND DEUTSCHLAND e.V.).
Streamlit-Web-App + Python-Backend. Drei-Phasen-Pipeline: CP-SAT (OR-Tools) + Simulated Annealing.

**Entwicklung:** `start.bat` → `localhost:8501`
**Endnutzer:** `Spielplan-Optimierer.exe` → Browser öffnet automatisch
**Ausgabe:** `Spielplaene/` · **Cache:** `.cache/` · **Tests:** `.venv/Scripts/python test_all.py`
**Release:** `git tag vX.X.X && git push --tags` → GitHub Actions baut `app-files.zip` automatisch

---

## 2. Dateistruktur

```
app.py                    ← Streamlit-UI (9 Wizard-Schritte + Ergebnisansicht)
requirements.txt          ← ortools>=9.14,<10  numpy pandas openpyxl requests streamlit>=1.32
                             folium streamlit-folium streamlit-calendar
launcher.py               ← Endnutzer-Starter: Update-Check, Streamlit-Start, Browser-Öffnung
build_release.py          ← Erstellt app-files.zip für GitHub Releases
VERSION                   ← Aktuelle Versionsnummer (Referenz für Launcher + GitHub Actions)
BACKLOG.md                ← Feature-Wünsche und Bugs
clubs_db.csv              ← Vereinsdatenbank (für Team-Suche in Schritt 0)
test_all.py               ← Umfassende Tests (Solver, Constraints, Export)
test_smoke.py             ← Schnelle Smoke-Tests
test_distances.py         ← Distanzmatrix-Tests
test_features.py          ← Feature-Tests (Karte, Kalender, iCal, Co-Home)
test_launcher.py          ← Launcher-Tests (_parse_version, Port-Check, ZIP-Traversal-Guard)
test_session_roundtrip.py ← JSON-Session-Roundtrip-Tests (v1.0/v1.1, home_vals)
test_pytest_runner.py     ← pytest-Wrapper für CI (alle 6 Sub-Suites)

installer/
  spielplan.iss           ← Inno Setup Script: Bootstrap-Installer
  build_bootstrap.bat     ← Developer-Build (Python-Embedded + Pakete + PyInstaller + Inno Setup)

.github/workflows/
  test.yml                ← CI: Ruff-Lint + pytest bei push:main + PRs
  release.yml             ← Release + app-files.zip bei git push --tags (Test-Gate vorgelagert)
  coverage.yml            ← Coverage-Report bei push:main

spielplan_multi/
  league_types.py         ← Datenklassen: LeagueConfig, LeagueVars, LeagueResult
  config.py               ← Solver-Gewichte (WEIGHT_LABELS, w_scaled), _TeamColorDict
  config_validator.py     ← validate() + validate_cfgs() → [{level, lid, msg}]
  multi_solver.py         ← Pipeline-Orchestrierung: run_phase1/2/3()
  solver.py               ← CP-SAT-Modellbau: build_league_vars(), add_league_objective()
  sa_refine.py            ← Simulated Annealing Phase 3: refine_schedule()
  tt_scheduler.py         ← Turniertag Post-Processing: apply_tournament_ordering()
  excel_output.py         ← Excel-Export: write_league_excel(), build_overview_excel()
  schedule_utils.py       ← Nachbearbeitung + Export-Hilfsfunktionen
  distances.py            ← Distanzmatrix: get_distance_matrix() (Google Maps / CSV)
  calendar_parser.py      ← Rahmenterminplan-Parser: parse_calendar(), build_weekends()
  calendar_output.py      ← FullCalendar-Events: build_calendar_events()
  geocode.py              ← OSM-Geocoding mit JSON-Cache (.cache/geocodes.json)
  map_output.py           ← Folium-Karte: build_route_map()
  ui.py                   ← CLI-Ausgabe: banner(), step(), ok(), warn(), err()
  wizard.py               ← CLI-Wizard: WizardLeagueDef, step0_leagues(), build_configs()
  main.py                 ← CLI-Pipeline: solve_all → Excel-Export
```

---

## 3. Datenklassen (league_types.py)

### LeagueConfig (Eingabe)
```python
league_id, name, teams: List[str], locations: List[str]
dist: np.ndarray              # n×n km-Matrix
dst_blocks: List[(d1,d2)]     # Doppelspieltage
weekends: List[List[int]]     # [[d] oder [d1,d2]] – Spieltag-Gruppen
apply_routing: bool, f_num, f_den   # DST-Routing-Faktor (1 + f_num/f_den)
w_scaled: Dict[str,float]     # Skalierte Gewichte für Solver
raw_weights: Dict[str,float]  # Rohgewichte 0-10
pinned: List[dict]            # [{teamA, teamB, day, home}]
blocked: Dict[str,List[int]]  # {team: [gesperrte_spieltage]}
forced_home: Dict[str,List[int]]  # {team: [pflicht_heimspieltage]}
calendar: Dict[int,dict]      # {spieltag: {kw, week_start, week_end}}
hier_weight: float            # Ligahierarchie-Gewicht im gemeinsamen Modell
games_per_team_per_day: int   # 1=Standard, 2+=Turniertag
n_rounds: int                 # 1=Einfach, 2=Hin-Rück, 3=Dreifach
n_teams_per_group: int        # 0=Stufe1 (alle), >0=Stufe2 (Gruppen)
n_active_per_day: int         # 0=alle Teams, >0=Spielfrei-Modus
tt_settings: dict             # Turniertag-Spielreihenfolge
```
Computed: `n_teams, n_matchdays, hinrunde_end, n_games_per_day, days, n_transitions, dst_days`

### LeagueResult (Ausgabe)
```python
league_id, status: int        # cp_model.OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN
objective: float
phase2_objective: float       # Objective vor SA (für Gap-Berechnung)
schedule: Dict[int, List[(ht,at)]]   # Spieltag → [(Heimteam, Auswärtsteam)]
home_vals: Dict[(ti,d),int]   # 1=Heimspiel, 0=Auswärts für team_idx ti an Tag d
sw_counts: List[int]          # Heimrecht-Wechsel pro Team
sw_rates: List[float]         # Wechselquote % pro Team
travels: List[int]            # Gesamtkilometer pro Team
gap_history: List[Tuple[float,float]]  # (elapsed_s, obj) je Improvement
best_bound, final_gap: Optional[float]
groups: Dict[int,List[List[str]]]  # Turniertag Stufe 2: Tag → Gruppen
hosts: Dict[int,str]          # Turniertag: Tag → Ausrichter-Teamname
game_times: Dict[int,List[str]]    # Tag → [Uhrzeiten je Spiel]
cfg: LeagueConfig
```

---

## 4. 3-Phasen-Pipeline (multi_solver.py)

**Telemetrie:** Phase 1 schreibt `gap_history/best_bound/final_gap` ins Result. Phase 2 überschreibt alle Felder (gemeinsames Modell, `phase2_objective` gesetzt). SA reicht Telemetrie-Felder unverändert durch; nur `objective` (km) wird aktualisiert.

```
Phase 1: solve_league_phase1()
  – Ligen unabhängig, n Seeds parallel (ThreadPoolExecutor), symmetry_level=2, max_memory_in_mb=4096
  – CP-SAT mit Zeitlimit p1s; Warmstart-Hints: home/h/x/switch/sw_count/travel/max_sw/min_sw

Phase 2: run_phase2()
  – Gemeinsames CP-SAT-Modell; verteilt Spieltage auf Kalenderwochen
  – Co-Home-Bonus: Mehrspartenvereine → gleiche KW Heimspiele

Phase 3: run_phase3() → sa_refine.refine_schedule()
  – Simulated Annealing pro Liga, ~2 min; tauscht Heim-/Auswärtspaare
  – Überspringt DST-Tage; typisch 3-8% weniger km
```

---

## 5. Streamlit-UI (app.py)

### Session-State-Schlüssel
```python
S.step, S.opt_running, S.opt_done
S.leagues           # Dict[lid, dict] – Wizard-Konfiguration je Liga
S.results           # Dict[lid, LeagueResult|None]
S.w_cohome          # float – Co-Home-Gewicht (Hard-Cap: _W_COHOME_MAX=50)
S.clubs             # Dict[club_name, Dict[lid, team]]
S.kw_compat         # {kw: {lid: [days]}} – aus calendar_parser
S.solver            # dict: {seeds, p1, p2, sa}
S.cal_table         # {lid: DataFrame} – Spieltag→KW-Zuteilung (bei Remove/Rename mitpflegen!)
S.time_templates    # {lid: ...} – Spielzeit-Templates (bei Remove/Rename mitpflegen!)
S.opt_best          # {lid: ...} – bestes Ergebnis (bei Remove/Rename mitpflegen!)
S.move_pending      # None|{lid,day,idx,ht,at}
S.cancel_pending    # None|{lid,ht,at}
S.map_obj, S.map_lid_keys
S._translog_cache, S._phase_seen
```

### Wizard-Schritte
| Schritt | Inhalt |
|---|---|
| 0 | Ligen & Teams, Liga-ID (Form+Enter, Regex `[A-Z0-9_\-]{1,20}`), Config-Up/Download |
| 1 | Distanzmatrizen (manuell / CSV-Excel / Google Maps API) |
| 2 | Rahmenterminplan-Excel + DST-Blöcke konfigurieren |
| 3 | DST-Routing + Gewichte (switch/sw_fair/travel/trav_fair/dst_eff/round_balance) + Co-Home |
| 4 | Pflichtspiele (pinned) |
| 5 | Heimspiel-Sperrtage (blocked) |
| 6 | Co-Home-Vereine |
| 7 | Solver-Config (Seeds, p1, p2-Preset, sa) |
| 8 | Optimierung starten + Ergebnisansicht |

**Ergebnisansicht Reihenfolge:** Telemetrie 📊 → Kennzahlen → Fairness → Spielpläne → Karte 🗺 → Kalender 📅 → Downloads (Excel, iCal, HTML, CSV)

---

## 6. schedule_utils.py – Hilfsfunktionen

| Funktion | Beschreibung |
|---|---|
| `recompute_result_stats(result, cfg)` | travels/sw_counts/sw_rates neu (Transitions-Modell) |
| `swap_home_away(result, cfg, day, match_idx)` | Heim↔Auswärts tauschen; guard: `if day in cfg.dst_days: return` |
| `move_game(result, cfg, old_day, match_idx, new_day)` | Spiel verschieben; guard: gpd>1, DST-Hinweis; '' = OK |
| `cancel_game(result, cfg, day, match_idx)` | Spiel entfernen → (ht, at); guard: gpd>1 |
| `reschedule_game(result, cfg, day, ht, at)` | Spiel eintragen; guard: gpd>1, day in cfg.days; '' = OK |
| `find_free_days(result, cfg, team_a, team_b)` | Spieltage ohne Spiel für beide Teams |
| `build_ics_bytes(result, season_year)` | iCal-Bytes (RFC 5545, Escaping + Line-Folding) |
| `build_print_html(result, season_year)` | Druckbarer HTML-Spielplan |

Alle Mutationsfunktionen rufen `recompute_result_stats()` intern auf.

---

## 7. Optimierungsgewichte (config.py)

```python
WEIGHT_SCALES = {
    'switch':        80.0,   # Heimrecht-Wechsel maximieren
    'sw_fair':        2.0,   # max-min Wechsel minimieren
    'travel':         0.05,  # Gesamtkilometer minimieren
    'trav_fair':      0.02,  # max-min km minimieren
    'dst_eff':        0.15,  # DST-Reiseeffizienz (Standard-UI: 3.0)
    'round_balance':  2.0,   # quadr. Abw. Heim/Runde (Standard-UI: 0 = aus)
}
```
Rohgewichte 0-10 × Scale = w_scaled. Co-Home-Gewicht: `_W_COHOME_MAX=50` (Hard-Cap), `_W_COHOME_WARN=20` (Validator-Warnung).

---

## 8. Kritische Solver-Constraints (solver.py)

- Jedes Match genau 1× pro Phase; Hin-/Rückrunde strikt getrennt (`hinrunde_end`)
- Jedes Team genau `gpd` Spiele/Spieltag (`<= gpd` bei `needs_bye = (n*gpd)%2==1`)
- Max 2× konsekutiv Heim/Auswärts (außer DST-Tage)
- **Sliding-Window 3er/4er:** überspringen Wochen mit DST-Tagen; Minima bei `needs_bye` konditionalisiert (`>= plays_in_window - k`)
- **DST:** beide Tage identisches Heimrecht (`home[ti,d1] == home[ti,d2]`)
- **DST-Balance pro Runde:** pro Team `n_dst_r//2 .. ⌈n_dst_r/2⌉` Heim-DST — nur wenn `4*n_dst_r ≤ n` (sonst skip + Warnung)
- **DST-Nachbarschaft (A/B/C):** max 3 konsekutiv gleich rund um DST-Block; bei `needs_bye` konditionalisiert
- **DST-Routing:** Reiseweg d1→d2 ≤ (1 + f_num/f_den) × Direktweg; Iteration `for d1, d2 in cfg.dst_blocks`
- `round_balance`: aktiv nur bei `gpd==1, n_rounds≥2, w_scaled['round_balance']>0`
- Sperrtage, Pflichtspiele, forced_home: Hard Constraints (forced_home schlägt blocked)

---

## 9. Kritische Invarianten — nicht brechen

Diese Patterns haben in Code-Reviews wiederholt Bugs verursacht:

| Invariante | Begründung |
|---|---|
| SA muss `gap_history/best_bound/final_gap/phase2_objective` durchreichen | SA baut neues LeagueResult; Defaults überschreiben sonst Phase-2-Telemetrie |
| `home_vals` bei neuem LeagueResult aus `schedule` rekonstruieren (Heimteam→1, Gast→0) | SA + Session-Restore liefern sonst `sw_counts=0` und falsche Heatmap |
| DST-Routing: `for d1, d2 in cfg.dst_blocks` — nicht `d1+1` | Blöcke können nicht-konsekutiv sein → KeyError |
| `phase3 = dict(phase2)` (shallow copy) | Direktzuweisung mutiert Phase-2-Dict wenn `sa_time=0` |
| `swap_home_away`: `if day in cfg.dst_days: return` | DST-Phasen-Trennung: schedule-Swap und home_vals-Update passen nie zusammen |
| `recompute_result_stats`: Transitions-Modell (`loc[pos]→loc[pos+1]`) | Einzel-Fahrt-Modell weicht vom Solver ab |
| `sw_rates`-Denominator = `cfg.n_transitions` | `len(weekends)-1` weicht bei DST-Saisons ab |
| `_TeamColorDict.__missing__` statt `defaultdict(factory)` | defaultdict-Factory wird ohne Argument aufgerufen → TypeError |
| Liga-Remove/Rename: `S.cal_table`, `S.time_templates`, `S.opt_best` + Widget-Keys mitpflegen | Neue Liga erbt sonst alten Kalender-/Zeit-Status |
| `blocked_weekends`: `any(d in blocked for d in wdays)` | Prüfung nur `wdays[0]` übersieht mehrtägige DST-Blöcke |
| `_W_COHOME_MAX=50` Hard-Cap bei jedem Import-Pfad | w_cohome=1000 → CP-SAT-Objective-Overflow |

---

## 10. Tests ausführen

```powershell
# Einzelne Test-Suites
.venv/Scripts/python test_all.py         # ~14 min, 64 Tests
.venv/Scripts/python test_features.py   # ~5 min, 67 Tests
.venv/Scripts/python test_distances.py  # ~1 min, 18 Tests
.venv/Scripts/python test_smoke.py      # ~30 s

# pytest-Runner (für CI, alle 6 Suites inkl. test_launcher + test_session_roundtrip)
.venv/Scripts/pytest test_pytest_runner.py
```

Stand v1.14.0: **64/64** (test_all) · **67/67** (test_features) · **18/18** (test_distances) · **10/10** (test_launcher) · **9/9** (test_session_roundtrip)

---

## 11. Spielplan-Formate

| Format | n_rounds | gpd | n_teams_per_group | Spieltage |
|---|---|---|---|---|
| Einfachrunde | 1 | 1 | 0 | n-1 (gerade) / n (ungerade) |
| Hin-Rückrunde | 2 | 1 | 0 | 2(n-1) / 2n |
| Dreifachrunde | 3 | 1 | 0 | 3(n-1) / 3n |
| Turniertag Stufe 1 | ≥1 | ≥2 | 0 | alle Teams an einem Ort |
| Turniertag Stufe 2 | ≥1 | ≥2 | K>0 | wie Stufe 1, in Gruppen à K Teams |

Allgemeine Formel: `n_rounds * n * (n-1) // 2 // games_per_day`

---

## 12. Laufzeiten & Empfehlungen

| Phase | Dauer | Hinweis |
|---|---|---|
| Phase 1 | ~15 min/Liga ×seeds | 2-3 Seeds; alle Ligen parallel |
| Phase 2 | 90 min / 3h / 8h | Nachtlauf ab 3+ Ligen empfohlen |
| Phase 3 | ~2 min/Liga | 0 bei Turniertag (automatisch) |

**F1-Verifikation (Mai 2026):** symmetry_level=2 + Switch-Term-Obergrenze + Hint-Boost → **−23,1% Gap-Reduktion** (19,96% → 15,35% nach 8h).

INFEASIBLE-Ursachen: zu viele Pins/Sperrtage, DST-Blöcke decken alle Spieltage, Zeitlimit zu kurz. Lösung: Seeds erhöhen, Constraints lockern, Phase-2-Zeit erhöhen.

---

## 13. Technologie-Stack

Python 3.13 · Streamlit ≥1.32 · OR-Tools CP-SAT (ortools ≥9.14,<10) · NumPy · pandas · openpyxl · requests · folium · streamlit-folium · streamlit-calendar

CI/QA: Ruff (`ruff.toml`) · pytest · Coverage.py (`.coveragerc`) · CodeQL (`.github/workflows/codeql.yml`) · Dependabot (`.dependabot.yml`)

---

## 14. Excel-Ausgabe

**Liga-Excel** (`write_league_excel`): Konfiguration · Spielplan · Gruppen-Uebersicht (TT2) · Heatmap Heimrecht · Kilometerstatistik · Distanzmatrix · Fahrtkostenausgleich · Fairness-Analyse · Team-Ansichten

**Konfigurationsdatei** (`_full_config_excel_bytes`): Ligen & Teams · Einstellungen · Distanzmatrizen · Gewichte · **Kalender** (→ DST-Blöcke via `_detect_dst_blocks()`) · Routing · Pflichtspiele · Sperrtage · Pflichtheim · Co-Home · TT-Spielreihenfolge · Ausrichter-Slots (JSON) · Hinweise

Rückwärtskompatibilität: Alte Dateien mit „DST-Blöcke"-Sheet werden weiterhin gelesen.

---

## 15. Release-Prozess

```bash
# Normaler Update-Zyklus
# 1. VERSION-Datei erhöhen
# 2. git commit + tag + push
git tag v1.x.x && git push && git push --tags
# → GitHub Actions: Test-Gate → Release → app-files.zip automatisch

# Bootstrap-Installer neu bauen (nur bei Python/Paket-Änderungen)
installer\build_bootstrap.bat   # erfordert Inno Setup 6
```

**Auto-Updater (`launcher.py`):** Update-Check parallel zum Server-Start (daemon-Thread) · atomar (Backup→Move→Cleanup, Rollback bei Fehler) · Port-8501-Check vor Neustart (`_wait_for_port_free`) · Installiert nach `%LOCALAPPDATA%\Programs\Spielplan-Optimierer\` (kein Admin nötig)

**Nutzer-Feedback:** `it@floorball.de` — bei Adressänderung 3 Stellen aktualisieren: `app.py:_show_backlog_dialog()`, `INSTALLATION.md`, `BENUTZERHANDBUCH.md`
