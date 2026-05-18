# Spielplan-Optimierer – Vollständige Projektdokumentation

> **Version 1.2.2 · Stand Mai 2026 · Status: Produktionsbereit, drei vollständige Code-Reviews + Runde 4 abgeschlossen, keine bekannten Bugs**

---

## 1. Schnell-Überblick

Automatisierte Spielplanerstellung für Floorball-Ligen (FLOORBALL VERBAND DEUTSCHLAND e.V.).
Streamlit-Web-App + Python-Backend. Drei-Phasen-Pipeline: CP-SAT (OR-Tools) + Simulated Annealing.

**Start (Entwicklung):** `start.bat` → Browser öffnet `localhost:8501`
**Start (Endnutzer):** `Spielplan-Optimierer.exe` (Desktop-Verknüpfung) → Browser öffnet automatisch
**Ausgabe:** `Spielplaene/` (Excel pro Liga + Co-Home-Zusammenfassung)
**Cache:** `.cache/` (Distanzmatrizen von Google Maps, JSON-Dateien)
**Distribution:** Bootstrap-Installer via `installer\build_bootstrap.bat` → `Spielplan-Optimierer-Setup-vX.X.X.exe`
**Updates:** Automatisch beim Start via GitHub Releases API; neue Version → `git tag vX.X.X && git push --tags`

---

## 2. Dateistruktur

```
app.py                    ← Streamlit-UI (9 Wizard-Schritte + Ergebnisansicht), ~3800 Zeilen
requirements.txt          ← ortools>=9.14,<10  numpy pandas openpyxl requests streamlit>=1.32
install.bat               ← Erstinstallation: Python-Check, .venv erstellen, pip install
start.bat                 ← .venv/Scripts/streamlit run app.py (Entwicklung)
launcher.py               ← Endnutzer-Starter: Update-Check via GitHub API, startet Streamlit ohne Fenster, öffnet Browser
build_release.py          ← Erstellt app-files.zip für GitHub Releases (nur App-Code, ~2-5 MB)
VERSION                   ← Aktuelle Versionsnummer (z. B. 1.1.0); Referenz für Launcher + GitHub Actions
create_release.bat        ← Altlast: ZIP für manuelle Distribution (durch Installer-System ersetzt)
BACKLOG.md                ← Feature-Wünsche und Bugs (App schreibt direkt rein)
README.md                 ← GitHub-Projektseite: Überblick, Links zu Doku, Developer-Infos
INSTALLATION.md           ← Installationsanleitung für Endnutzer (Laien)
BENUTZERHANDBUCH.md       ← Schritt-für-Schritt Bedienungsanleitung aller Wizard-Schritte
clubs_db.csv              ← Vereinsdatenbank mit Adressen (für Team-Suche in Schritt 0)
test_all.py               ← Umfassende Tests (Solver, Constraints, Export)
test_smoke.py             ← Schnelle Smoke-Tests
test_distances.py         ← Distanzmatrix-Tests
test_features.py          ← Feature-Tests (HTML-Druckansicht, iCal, Hallenbelegung, Co-Home)
create_overview_doc.py    ← Standalone-Skript: generiert DOCX-Projektübersicht (python-docx nötig, nicht in requirements.txt; kein Teil der App-Pipeline)

installer/
  spielplan.iss           ← Inno Setup Script: Bootstrap-Installer (lädt App-Dateien von GitHub)
  build_bootstrap.bat     ← Developer-Build: Embedded Python + Pakete + PyInstaller + Inno Setup
  build/                  ← Gitignored: Embedded Python-Umgebung + kompilierter launcher.exe
  Output/                 ← Gitignored: fertige Setup-EXE

.github/
  workflows/
    release.yml           ← GitHub Actions: bei git push --tags → Release + app-files.zip automatisch

spielplan_multi/
  __init__.py
  __main__.py             ← Einstiegspunkt für python -m spielplan_multi (ruft main.py auf)
  main.py                 ← CLI-Pipeline: Wizard → solve_all → Excel-Export
  league_types.py         ← Datenklassen: LeagueConfig, LeagueVars, LeagueResult
  config.py               ← Solver-Gewichte (WEIGHT_LABELS, w_scaled), Teamfarben (get_team_color)
  config_validator.py     ← Constraint-Vorab-Prüfung vor dem Solver: validate() → [{level, lid, msg}]
  multi_solver.py         ← Pipeline-Orchestrierung: Phase 1+2+3, run_phase1/2/3()
  solver.py               ← CP-SAT-Modellbau: build_league_vars(), add_league_objective()
  sa_refine.py            ← Simulated Annealing Phase 3: refine_schedule()
  tt_scheduler.py         ← Turniertag Post-Processing (nach Phase 3): apply_tournament_ordering(), Ausrichter-Zuweisung, Heim-Balance
  excel_output.py         ← Excel-Export: write_league_excel(), write_cohome_excel()
  schedule_utils.py       ← Nachbearbeitung + Export-Hilfsfunktionen (siehe §6)
  distances.py            ← Distanzmatrix: get_distance_matrix() per Google Maps API / CSV
  calendar_parser.py      ← Rahmenterminplan-Parser: parse_calendar(), build_weekends()
  ui.py                   ← CLI-Ausgabe: banner(), step(), ok(), warn(), err(), info()
  wizard.py               ← CLI-Wizard (Alternative zu Streamlit): Schritt-für-Schritt-Konfiguration via Terminal; Einstieg über python -m spielplan_multi
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
raw_weights: Dict[str,float]  # Rohgewichte 0-10 (für Anzeige)
pinned: List[dict]            # [{teamA, teamB, day, home}]
blocked: Dict[str,List[int]]  # {team: [gesperrte_spieltage]}
calendar: Dict[int,dict]      # {spieltag: {kw, week_start, week_end}}
hier_weight: float            # Ligahierarchie-Gewicht im gemeinsamen Modell
games_per_team_per_day: int   # 1=Standard, 2+=Turniertag Stufe 1
n_rounds: int                 # 1=Einfach, 2=Hin-Rück, 3=Dreifach
n_teams_per_group: int        # 0=Stufe1 (alle Teams), >0=Stufe2 (Gruppen-Turniertag)
n_active_per_day: int         # 0=alle Teams, >0=Spielfrei-Modus
tt_settings: dict             # Turniertag-Spielreihenfolge
```
Computed properties: `n_teams, n_matchdays, hinrunde_end, n_games_per_day, days, n_transitions, dst_days`

### LeagueResult (Ausgabe)
```python
league_id, status: int        # cp_model.OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN
objective: float
schedule: Dict[int, List[(ht,at)]]   # Spieltag → [(Heimteam, Auswärtsteam)]
sw_counts: List[int]          # Heimrecht-Wechsel pro Team
sw_rates: List[float]         # Wechselquote % pro Team
travels: List[int]            # Gesamtkilometer pro Team
mins, secs: int               # Solver-Laufzeit
home_vals: Dict[(ti,d),int]   # 1=Heimspiel, 0=Auswärts für team_idx ti an Tag d
h_vals: Dict[m,int]           # Match-Index → 0/1 (Phase-2-Hints)
x_vals: Dict[(m,d),int]       # (Match, Tag) → 0/1 (Phase-2-Hints)
cfg: LeagueConfig             # Rückreferenz auf Konfiguration
groups: Dict[int,List[List[str]]]  # Turniertag Stufe 2: Tag → Gruppen
hosts: Dict[int,str]          # Turniertag: Tag → Ausrichter-Teamname
game_times: Dict[int,List[str]]    # Tag → [Uhrzeiten je Spiel]
```

---

## 4. 3-Phasen-Pipeline (multi_solver.py)

```
Phase 1: solve_league_phase1()
  – Jede Liga unabhängig, n Seeds parallel (ThreadPoolExecutor)
  – CP-SAT mit Zeitlimit p1 Sekunden pro Seed
  – Constraint: jedes Match 1×, Hin-/Rückrunde getrennt, max 2× konsekutiv Heim/Auswärts
  – Sliding-Window 3er+4er: min 1 Heim, max 2/3 Heim (DST-Tage ausgenommen!)
  – DST: gleiches Heimrecht an beiden Tagen; DST-Routing: Umwegbegrenzung

Phase 2: run_phase2()
  – Gemeinsames CP-SAT-Modell für alle Ligen
  – Verteilt Spieltage auf Kalenderwochen
  – Co-Home-Bonus: Mehrspartenvereine → gleiche KW Heimspiele
  – Nutzt h_vals/x_vals aus Phase 1 als Warmstart-Hints

Phase 3: run_phase3() → sa_refine.refine_schedule()
  – Simulated Annealing pro Liga, ~2 min
  – Tauscht Heim-/Auswärtspaare ohne Terminänderung
  – Erhält groups/hosts/game_times aus Phase 1
  – Typisch: 3-8% weniger Gesamtkilometer
```

---

## 5. Streamlit-UI (app.py) – Struktur

### Session-State-Schlüssel (S = st.session_state)
```python
S.step              # int 0-8, aktueller Wizard-Schritt
S._wizard_started   # bool
S.opt_running       # bool – Optimierung läuft gerade
S.opt_done          # bool – Ergebnisse vorhanden
S.leagues           # Dict[lid, dict] – Wizard-Konfiguration je Liga
S.results           # Dict[lid, LeagueResult|None]
S.w_cohome          # float – Co-Home-Gewicht
S.clubs             # Dict[club_name, Dict[lid, team]] – Co-Home-Konfiguration
S.kw_compat         # {kw: {lid: [days]}} – aus calendar_parser, für DST-Vorschlag
S.solver            # dict: {seeds, p1, p2, sa}
S.move_pending      # None|{lid,day,idx,ht,at} – laufende Verschiebe-Aktion
S.cancel_pending    # None|{lid,ht,at} – Spiel ausgefallen, Nachholtermin pending
```

### Wizard-Schritte
| Schritt | Inhalt |
|---|---|
| 0 | Ligen & Teams konfigurieren (Vereinssuche, Konfiguration Download/Upload) |
| 1 | Distanzmatrizen (manuell / CSV-Excel / Google Maps API) |
| 2 | Kalender laden (Rahmenterminplan-Excel) + DST-Blöcke konfigurieren |
| 3 | DST-Routing (Umwegbegrenzung) + Optimierungsgewichte (switch/sw_fair/travel/trav_fair/dst_eff) + Co-Home-Gewicht |
| 4 | Pflichtspiele (teamA, teamB, Spieltag, Heimrecht) |
| 5 | Heimspiel-Sperrtage (Team + Spieltagnummern) |
| 6 | Co-Home-Vereine (automatische Erkennung + manuelle Eingabe) |
| 7 | Solver-Konfiguration (Seeds, p1, p2-Preset, sa) |
| 8 | Optimierung starten + Ergebnisanzeige |

### Ergebnisansicht (Schritt 8, nach Optimierung)
- **Kennzahlen-Metriken**: Gesamt-km, Ø km/Team, Ø Wechselquote
- **Hinweise zur Plan-Qualität**: Warnungen bei ≥4× konsekutiv Auswärts/Heim, >35% km-Ausreißer
- **Fairness-Überblick**: Tabelle (km, Abw%, Heim, Heim%, Wechsel, Quote) je Liga
- **Spielpläne**: aufklappbar je Liga, mit Heimrecht-Heatmap-Link
- **Download-Buttons**: Excel je Liga (ZIP), Co-Home-Excel, iCal-ZIP, Druckansicht (HTML)
- **Spiel verschieben / Absagen & Nachholspiele**: Spiel auswählen → 📅 verschieben / ❌ absagen mit Nachholtermin
- **Spielplan vergleichen**: Ergebnis-Excel hochladen → Delta-Tabelle (km, Wechselquote)

---

## 6. schedule_utils.py – Hilfsfunktionen

| Funktion | Beschreibung |
|---|---|
| `assign_game_times(result, slots)` | Spielzeiten in result.game_times schreiben |
| `recompute_result_stats(result, cfg)` | travels/sw_counts/sw_rates aus Schedule neu berechnen |
| `swap_home_away(result, cfg, day, match_idx)` | Heim↔Auswärts tauschen (inkl. DST-Partner, Stats neu) |
| `find_schedule_warnings(result, cfg)` | Unausgewogene Konstellationen prüfen (Liste von Dicts) |
| `move_game(result, cfg, old_day, match_idx, new_day)` | Spiel verschieben, '' = OK, sonst Fehlermeldung |
| `cancel_game(result, cfg, day, match_idx)` | Spiel entfernen, gibt (ht, at) zurück |
| `reschedule_game(result, cfg, day, ht, at)` | Neues Spiel eintragen, '' = OK |
| `find_free_days(result, cfg, team_a, team_b)` | Spieltage ohne Spiel für beide Teams |
| `build_ics_bytes(result, season_year)` | iCal-Bytes (VCALENDAR) |
| `build_print_html(result, season_year)` | Druckbarer HTML-Spielplan |

**Hinweis:** Alle Mutationsfunktionen (move/cancel/reschedule/swap) rufen `recompute_result_stats()` intern auf.

---

## 7. Optimierungsgewichte (config.py)

```python
WEIGHT_SCALES = {
    'switch':   80.0,   # Heimrecht-Wechsel maximieren
    'sw_fair':   2.0,   # max-min Wechsel minimieren
    'travel':   0.05,   # Gesamtkilometer minimieren
    'trav_fair': 0.02,  # max-min km minimieren
    'dst_eff':   0.03,  # DST-Reiseeffizienz maximieren (Standard: aus = 0)
}
```
Rohgewichte 0-10 (Slider) werden mit dem Skalar multipliziert → w_scaled.
Zielfunktion: `sum(switch·scale·sw) - sum(sw_fair·scale·(max_sw-min_sw)) - sum(travel·scale·km) - sum(trav_fair·scale·(max_km-min_km)) + sum(dst_eff·scale·dst_eff_total)`

**DST-Reiseeffizienz (`dst_eff`):** Belohnt DST-Blöcke, bei denen beide Auswärtsspiele eines Teams räumlich nah beieinander liegen. Formel je Paar (ti, d1→i, d2→j): `gain = dist(ti,i) + dist(ti,j) − dist(i,j)`. Positiv wenn i und j nahe zueinander, aber weit von ti entfernt (→ Randlagen-Teams profitieren). Nur aktiv wenn `w_scaled['dst_eff'] > 0` und DST-Blöcke vorhanden; Standard-UI-Wert = 0 (aus). Wird als IntVar `dst_eff_total` in `LeagueVars` gespeichert.

---

## 8. Kritische Constraints im Solver (solver.py)

- Jedes Match genau 1× pro Phase; Hin-/Rückrunde strikt getrennt (hinrunde_end)
- Jedes Team genau gpd Spiele pro Spieltag
- Konsekutiv: max 2× Heim oder 2× Auswärts hintereinander (außer DST-Tage)
- **Sliding-Window 3er**: in jedem Spieltag-Tripel min 1 Heim und max 2 Heim — **überspringt Wochen mit DST-Tagen**
- **Sliding-Window 4er**: in jedem Quadrupel max 3 Heim — **überspringt Wochen mit DST-Tagen** (fix für back-to-back DST)
- DST: beide Tage haben identisches Heimrecht
- **DST-Nachbarschaft (Constraints A/B/C):** Rund um jeden DST-Block max 3 Spiele in Folge mit gleicher Heim-/Auswärtszuteilung. A: `home[pre1]+home[post1] ≤ 1` (DST=H) / `≥ 1` (DST=A). B: `home[post1]+home[post2]` analog. C: `home[pre2]+home[pre1]` analog. Nur gpd==1, via `OnlyEnforceIf`. ≥1-Constraints werden bei Sperrtagen übersprungen.
- DST-Routing: Reiseweg zwischen DST-Tag 1 → Tag 2 ≤ (1 + f_num/f_den) × Direktweg
- **Spielfrei-Modus (ungerade Teamzahl):** `needs_bye = (n * gpd) % 2 == 1`. Wenn True: Pro-Team-Constraint `cstr <= gpd` statt `== gpd` (Spielfrei-Tage). Locations-Constraint: `sum(loc[ti,d,i]) <= 1` statt `== 1`. Sliding-Window-Minima konditionalisiert: `sum(seg) >= plays_in_window - k` (k=2 für 3er, k=3 für 4er). `n_matchdays` = `n_rounds * n * (n-1) / 2 / (n * gpd // 2)` → für ungerades n: `n_rounds * n` Spieltage (statt `n_rounds * (n-1)`).
- Sperrtage und Pflichtspiele: Hard Constraints

---

## 9. Code-Reviews Mai 2026

Zwei vollständige Code-Reviews wurden im Mai 2026 durchgeführt. Alle gefundenen Bugs sind behoben. Übersicht der wichtigsten Fixes:

**Runde 1 (Kritisch/Hoch/Mittel/Niedrig – alle erledigt):**

| Datei | Problem | Fix |
|---|---|---|
| `sa_refine.py` | LeagueResult fehlte `groups`, `hosts`, `game_times` | Felder in return-Statement ergänzt |
| `excel_output.py` | Heatmap-Spaltenindex bei nicht-sequenziellen Tagen falsch | Mapping-Dict `{day: col_idx}` |
| `calendar_parser.py` | DST-Blöcke außerhalb der Range → KeyError | `build_weekends()` filtert beide Tage |
| `calendar_parser.py` | Jahreswechsel-Bug im Datums-Parsing (week_start/week_end) | Jahr aus Monat ableiten |
| `solver.py` | 4er-Fenster bei back-to-back-DST → INFEASIBLE | Fenster überspringt DST-Tage |
| `solver.py` + `multi_solver.py` | OR-Tools 9.15: `SolveWithSolutionCallback()` entfernt | Auf `solver.Solve(model, callback)` umgestellt |
| `config_validator.py` | NaN in Distanzmatrix nicht erkannt | `np.isnan(dist).any()` zusätzlich prüfen |
| `solver.py` | DST-Routing: `d1+1` statt `d2` → KeyError bei nicht-konsekutiven DST-Blöcken | `for d1, d2 in cfg.dst_blocks` |
| `schedule_utils.py` | DTSTAMP fehlt in iCal-VEVENTs (RFC 5545) | DTSTAMP in jeden VEVENT |
| `app.py` | `S.sol` vs `S.solver` Key-Mismatch → Sitzung speichern crasht | `S.sol` → `S.solver` |

**Sitzung Mai 2026 – Streamlit-Kompatibilität:**

| Datei | Problem | Fix |
|---|---|---|
| `app.py:379` | `st.image(width=None)` → `StreamlitInvalidWidthError` ab Streamlit 1.4x | `width='content'` |

**Runde 2 (Kritisch/Hoch/Mittel/Niedrig – alle erledigt):**

| Datei | Problem | Fix |
|---|---|---|
| `sa_refine.py` | `t_idx[ht]` KeyError nach manuellen Spielplanänderungen | `t_idx.get()` mit Guard |
| `schedule_utils.py` | `travels[ti]` IndexError in `find_schedule_warnings()` | Längen-Guard |
| `schedule_utils.py` | `move_game` validiert `new_day` nicht gegen `cfg.days` | Validierung ergänzt |
| `schedule_utils.py` | `reschedule_game` validiert Teamnamen nicht | Validierung gegen `cfg.teams` |
| `schedule_utils.py` | iCal: kein RFC 5545-Escaping + kein Line-Folding | `_ical_escape()` + `_ical_fold()` |
| `config_validator.py` | `pin_key` str/int-Mismatch bei JSON-Import | `int(pm.get('day', 0))` |
| `solver.py` | Turniertag: Switch-Summation erzeugt unnötige CP-Terme | Turniertag-Branch überspringen |
| `config.py` | `TEAM_COLORS` KeyError ab 20 Teams | `defaultdict(get_team_color)` |
| `multi_solver.py` | Fehlender Guard für leeres `cfgs` in `run_phase2` | Early-return mit Warnung |
| `tt_scheduler.py` | Fallback-Schleifen ohne globales Abbruchkriterium | `MAX_TRIES = 20` |
| `excel_output.py` | Spaltenbreiten falsch für `n_rounds > 2`; n_bcols off-by-one | Beide korrigiert |
| `app.py` | Liga-ID leer → korrumpiert `S.leagues`; Liga löschen bereinigt `S.clubs` nicht | Guards ergänzt |
| `app.py` | INFEASIBLE-Diagnose: False Positives bei ähnlichen Liga-IDs | Zeilenweise Log-Prüfung |
| `app.py` | Routing-Slider: `min_value=0` führt nahezu immer zu INFEASIBLE | `min_value=1` |
| `wizard.py` | `n_md` für Stufe-2-Turniertag in Schritten 5/6/6b falsch | `_calc_n_matchdays(ld)` |
| `distances.py` | Meter→km per Truncation statt Rounding | `round(meters / 1000)` |

**Runde 3 (Kritisch/Hoch/Mittel/Niedrig – alle erledigt):**

| Datei | Problem | Fix |
|---|---|---|
| `app.py` | `_sys.stdout` NameError bei Google-Maps-Berechnung | `_sys` → `sys` |
| `app.py` | `_QueueWriter` ersetzt `sys.stdout` global für alle Threads | Thread-ID-Guard in `_QueueWriter` |
| `app.py` | Liga-ID-Rename ohne `st.rerun()` → UI zeigt alten Namen | `st.session_state[f'lid_{i}'] = new_lid; st.rerun()` |
| `app.py` | Solver-Exception erscheint nicht in `opt_warnings` | `[FEHLER]`-Zeilen zusätzlich erfassen |
| `app.py` | Upload-Fehler blockiert Navigation trotz vorhandener gültiger Matrix | Guard: nur `errors.append` wenn keine Matrix vorhanden |
| `app.py` | JSON-Restore: `teams` als `list` statt `tuple` | `[tuple(e) for e in ld['teams']]` in `_session_from_json` |
| `app.py` | Toter Code `_prev_tot` in Vergleichsansicht | Zeilen entfernt |
| `launcher.py` | Lexikografischer Versionsvergleich: `1.10.0 < 1.9.0` | `tuple(int(x) for x in v.split('.'))` |
| `launcher.py` | `tempfile.mktemp()` TOCTOU-Race | `tempfile.mkstemp()` |
| `launcher.py` | Partial-Download hinterlässt inkonsistente App-Dateien | Atomar: erst temp-Dir, dann verschieben |
| `launcher.py` | ZIP-Path-Traversal (Security) | `os.path.realpath()`-Guard vor jedem `extract()` |
| `launcher.py` | Browser öffnet alten Prozess nach Update | `updated`-Flag: `_server_ready()` nach Update überspringen |
| `solver.py` | `blocked_weekends` prüft nur `wdays[0]` statt alle DST-Tage | `any(d in blocked for d in wdays)` |
| `multi_solver.py` | `phase3 = phase2` mutiert Phase-2-Dict wenn `sa_time=0` | `dict(phase2)` (shallow copy) |
| `tt_scheduler.py` | `_try_solve` probiert nur ersten Host-Kandidaten | Alle Permutationen via `itertools.permutations` |
| `tt_scheduler.py` | Ausrichter nicht im Spielplan → stilles Ignorieren | `warn(...)` vor `host = None` |
| `schedule_utils.py` | `prev` nicht zurückgesetzt bei fehlendem `home_val` | `prev = None; continue` |
| `schedule_utils.py` | `swap_home_away` korrumpiert `home_vals` bei Turniertag | Guard: `if gpd > 1: return` |
| `schedule_utils.py` | `move_game` kein Guard für Turniertag | Guard: `if gpd > 1: return Fehlermeldung` |
| `schedule_utils.py` | iCal: Fallbackdatum 1. Januar für Spiele ohne Kalender | Spiele ohne Datum überspringen |
| `schedule_utils.py` | `build_print_html` ohne Längenprüfung auf `travels[ti]` | `ti < len(travels)` Guard |
| `config.py` | `defaultdict(get_team_color)` TypeError (Factory ohne Argument) | `_TeamColorDict.__missing__` |
| `config_validator.py` | `validate_cfgs()` erkennt NaN in Distanzmatrix nicht | `np.isnan(dist).any()` ergänzt |
| `calendar_parser.py` | `_to_date_str()` gibt `'nan'` für leere Excel-Zellen zurück | `isinstance(cell, float) and np.isnan(cell)` Guard |
| `distances.py` | Case-sensitiver Spaltenname bei Distanzmatrix-CSV | `col_map` mit `.lower()` Lookup |
| `excel_output.py` | DST-Routing-Anzeige zeigt Faktor statt Umweg-Prozent | `f_num - 100` statt `f_num` |
| `excel_output.py` | Fairness-Sheet Merge-Breiten falsch | Dynamische Breite + 7→6 Korrektur |
| `excel_output.py` | `get_team_color(-1)` im Hallenbelegungsplan | Guard: `hi if hi >= 0 else 0` |
| `wizard.py` | `n_active` undefiniert für Formate 1/2/3 → UnboundLocalError | `n_active = 0` als Default vor Format-Auswahl |
| `wizard.py` | `k_group` nicht gesetzt im Auto-Select-Ast | `k_group = K` ergänzt |
| `main.py` | `import numpy as np` innerhalb der `for`-Schleife | Import an Dateianfang verschoben |

**Sitzung Mai 2026 – Kalender/Excel/UI-Fixes (v1.1.1 → v1.1.2):**

| Datei | Problem | Fix |
|---|---|---|
| `app.py` | Excel-Konfiguration speicherte `cal_table` (KW-Zuteilungen je Spieltag) nicht | Neues Sheet „Kalender" in `_full_config_excel_bytes()` + Lesen in `_load_full_config_excel()` + Anwenden in `_step0()`; `_cal_table_to_kw_compat()` leitet daraus DST-Blöcke ab |
| `app.py` | „DST-Blöcke"-Sheet redundant nach Einführung des Kalender-Sheets | Sheet aus Export entfernt; Lese-Code bleibt für Rückwärtskompatibilität |
| `app.py` | `use_container_width=True` deprecated (Streamlit ≥1.40) | `width='stretch'` in `st.link_button` und `st.data_editor` (2 Stellen) |
| `app.py` | `pd.DataFrame(mat, …)` mit int-Array → `ArrowTypeError` in `st.data_editor` | `mat.astype(float)` beim DataFrame-Bau |
| `app.py` | `st.text_input('Ligabezeichnung', ld['name'], key='lnm_{i}')` erzeugt Streamlit-Warnung nach Konfig-Upload (Session State + value= gleichzeitig gesetzt) | Session State initialisieren wenn nicht vorhanden, kein `value=`-Parameter |

**Sitzung Mai 2026 – Spielfrei-Modus, Floorball-Icon, Log-Cleanup (v1.2.1 → v1.2.2):**

| Datei | Problem | Fix |
|---|---|---|
| `league_types.py` | `n_matchdays` für ungerades n falsch (lieferte `n_rounds*(n-1)` statt `n_rounds*n`) | Allgemeine Formel: `n_rounds * n * (n-1) // 2 // games_per_day` |
| `solver.py` | Per-Team-Constraint `== gpd` → INFEASIBLE bei ungerader Teamzahl (Spielfrei-Tage) | `needs_bye = (n * gpd) % 2 == 1`; Guard `<= gpd` statt `== gpd` |
| `solver.py` | Sliding-Window-Minima zwingen Spielfrei-Teams zu Heimspielen → INFEASIBLE | Konditionalisiert: `>= plays_in_window - k` bei `needs_bye` |
| `solver.py` | `sum(loc[ti,d,i]) == 1` → INFEASIBLE für Teams ohne Location (Spielfrei) | `<= 1` statt `== 1` |
| `app.py` | `_calc_n_matchdays()` im Wizard lieferte falsche Spieltagzahl für ungerades n | Gleiche Formel wie `league_types.py` |
| `config_validator.py` | Ungerade Teamzahl wurde als Fehler (INFEASIBLE-Signal) behandelt | Downgrade zu Warnung mit Hinweis auf Spielfrei-Modus |
| `app.py` | Streamlit-Ladeindikator (Laufmännchin) ohne FBD-Branding | `_inject_floorball_css()`: hüpfender weißer Ball (`::before`-Pseudo-Element, Bounce-Animation) ersetzt Standard-SVG |
| `_worker.py` | Subprocess reimportiert Streamlit → hunderte „missing ScriptRunContext"-Warnungen | `logging.getLogger('streamlit').setLevel(logging.ERROR)` auf Modulebene |

---

## 10. Nutzer-Feedback

### Feedback-Kanal

Nutzer melden Fehler und Wünsche über den **„📋 Funktionswunsch / Fehler melden"-Button** in der App-Sidebar (Schritt 0–8, immer sichtbar).

**Ablauf:**
1. Nutzer füllt das Formular aus (Typ, Bereich, Wichtigkeit, Titel, Beschreibung, optionaler Kontakt)
2. Klick auf „E-Mail vorbereiten" → App öffnet das Standard-E-Mail-Programm mit vorausgefüllter Nachricht
3. Nutzer klickt „Senden" → E-Mail geht direkt an `it@floorball.de`

**Kontaktadresse für alle Nutzer-Meldungen:** `it@floorball.de`
Diese Adresse ist in `app.py` (`_show_backlog_dialog()`), `INSTALLATION.md` und `BENUTZERHANDBUCH.md` hinterlegt. Bei Änderung alle drei Stellen aktualisieren.

### Offene Features (BACKLOG.md)

Details im BACKLOG.md. Offene Punkte nach Priorität:

**Ausstehend:**

| Aufgabe | Aufwand |
|---|---|
| Installer-Flow auf frischem Windows-System testen | Klein |

**Feature-Wünsche (langfristig):**

| Feature | Aufwand |
|---|---|
| Interaktive Kalenderansicht im Browser | Groß |
| Karten-Visualisierung Reiserouten | Groß |
| Multi-Saison-Planung | Groß |
| REST-API für externe Integration | Groß |

---

## 11. Spielplan-Formate

| Format | n_rounds | gpd | n_teams_per_group | Beschreibung |
|---|---|---|---|---|
| Einfachrunde | 1 | 1 | 0 | Jede Paarung 1×; n-1 ST (gerades n) / n ST (ungerades n, 1 Spielfrei/Tag) |
| Hin-Rückrunde | 2 | 1 | 0 | Jede Paarung 2×; 2(n-1) ST (gerades n) / 2n ST (ungerades n) |
| Dreifachrunde | 3 | 1 | 0 | Jede Paarung 3×; 3(n-1) ST (gerades n) / 3n ST (ungerades n) |
| Turniertag Stufe 1 | 2 | 2+ | 0 | Alle Teams an einem Ort, gpd Spiele/Team/Tag |
| Turniertag Stufe 2 | 2 | 2+ | K>0 | Wie Stufe 1, aber aufgeteilt in Gruppen à K Teams |

---

## 12. Laufzeiten & Empfehlungen

| Phase | Dauer | Hinweis |
|---|---|---|
| Phase 1 | ~15 min/Liga (×seeds) | Alle Ligen parallel; 2-3 Seeds = gute Balance |
| Phase 2 | 90 min / 3h / 8h | Standard reicht für 1-2 Ligen; Nachtlauf ab 3+ Ligen |
| Phase 3 | ~2 min/Liga (nacheinander) | 120s reicht fast immer; auf 0 für Turniertag automatisch deaktiviert |

**"Keine Lösung gefunden":** Häufigste Ursachen: zu viele Pflichtspiele, zu viele Sperrtage, DST-Blöcke decken alle Spieltage ab (Solver-Timeout). Lösung: Zeitlimit erhöhen, Constraints lockern, Seeds erhöhen.

---

## 13. Technologie-Stack

- Python 3.13, Streamlit ≥1.32, Google OR-Tools CP-SAT (ortools ≥9.14,<10)
- NumPy, pandas, openpyxl, requests
- `@st.dialog` für Backlog-Modal (requires Streamlit ≥1.32 mit experimental_dialog oder ≥1.40 mit stabilem dialog)
- Tests: `test_all.py`, `test_smoke.py`, `test_distances.py`
- Clubs-Datenbank: `clubs_db.csv`

---

## 14. Excel-Ausgabe (excel_output.py)

Sheets je Liga-Excel:
- `Spielplan` – Haupttabelle mit allen Spielen, farbig nach Teams
- `Heimrecht-Heatmap` – Team × Spieltag, grün=Heim / rot=Auswärts
- `Kilometerstatistik` – Team | km | Switches | Wechselquote % (wird für Vergleich geparst)
- `Distanzmatrix` – n×n km-Tabelle
- `Fahrtkostenausgleich` – Berechnungsgrundlage
- `Gruppen` – nur Turniertag Stufe 2: Gruppenaufstellungen je Spieltag

Co-Home-Excel: Übersicht aller Ligen nebeneinander, KW-Heimspiel-Synchronisation hervorgehoben.

---

## 15. Konfiguration Download/Upload

- **Download:** Leere Vorlage oder vollständige Konfiguration als Excel (Schritt 0)
- **Upload:** Konfigurationsdatei → überschreibt aktuelle Wizard-Einstellungen
- Kein serverseitiger Speicher – Nutzer verwaltet Konfigurationsdateien selbst
- Gleichzeitige Nutzung durch mehrere Nutzer: jeder Browser hat eigene Session

### Excel-Sheets der vollständigen Konfigurationsdatei

| Sheet | Inhalt |
|---|---|
| `Ligen & Teams` | Liga-ID, Name, Format, Teams, Standorte, Gewicht, TT-Parameter |
| `Einstellungen` | dist_method, same_weights, w_cohome, solver_p1/p2/sa/seeds |
| `Distanzmatrizen` | NxN km-Matrizen je Liga (Liga-Header + Tabellenblock) |
| `Gewichte` | switch / sw_fair / travel / trav_fair je Liga |
| `Kalender` | Spieltag → KW + Datum je Liga; **Quelle für DST-Blöcke** (werden per `_detect_dst_blocks()` abgeleitet) |
| `Routing` | DST-Routing aktiv (J/N) + Mehrkilometer-% je Liga |
| `Pflichtspiele` | Fixierte Paarungen mit Spieltag + Heimrecht |
| `Sperrtage` | Team + kommagetrennte gesperrte Spieltagnummern |
| `Pflichtheim` | Team + kommagetrennte Pflicht-Heimspieltage |
| `Co-Home` | Verein → Liga → Teamname |
| `TT-Spielreihenfolge` | Turniertag-Parameter (nur wenn Turniertag-Ligen vorhanden) |
| `Hinweise` | Lesbare Beschreibung aller Sheets |

**Hinweis Rückwärtskompatibilität:** Alte Dateien mit „DST-Blöcke"-Sheet werden weiterhin geladen (Fallback). Neue Exporte enthalten stattdessen das „Kalender"-Sheet.

---

## 16. Distribution & Release-Prozess

### Komponenten

| Datei | Rolle |
|---|---|
| `launcher.py` | Endnutzer-EXE (via PyInstaller kompiliert): Update-Check, Server-Start, Browser-Öffnung |
| `VERSION` | Versionsnummer (z. B. `1.1.0`); lokal + in app-files.zip |
| `build_release.py` | Erstellt `app-files.zip` (App-Code ohne Python/venv/cache) |
| `installer/spielplan.iss` | Inno Setup Script: Bootstrap-Installer |
| `installer/build_bootstrap.bat` | Einmaliger Build-Prozess (Embedded Python + alle Pakete + launcher.exe + Setup-EXE) |
| `.github/workflows/release.yml` | GitHub Actions: bei Tag-Push automatisch Release + app-files.zip |

### Zwei Installer-Typen

**Bootstrap-Installer** (`Spielplan-Optimierer-Setup-vX.X.X.exe`, ~200 MB):
- Enthält: Python 3.13 Embeddable + alle pip-Pakete + kompilierter launcher.exe
- Lädt bei Installation: `app-files.zip` von GitHub (neueste App-Version)
- Muss nur neu gebaut werden wenn sich Python-Version oder Pakete ändern
- Erstellen: `installer\build_bootstrap.bat` (erfordert Inno Setup 6)

**app-files.zip** (~2-5 MB):
- Enthält nur App-Code (kein Python, keine Pakete)
- Wird automatisch durch GitHub Actions bei jedem Tag-Push erstellt
- Wird beim Bootstrap-Installer als Download-Quelle genutzt
- Wird vom Auto-Updater im Launcher heruntergeladen

### Normaler Update-Zyklus (bei App-Änderungen)

```
1. Änderungen in app.py / spielplan_multi/ etc. vornehmen
2. VERSION-Datei erhöhen (z. B. 1.1.0 → 1.2.0)
3. git add -A && git commit -m "feat: ..."
4. git tag v1.2.0
5. git push && git push --tags
   → GitHub Actions: erstellt Release + app-files.zip automatisch
   → Alle Nutzer sehen beim nächsten Start den Update-Dialog
```

### Bootstrap-Installer neu bauen (selten, nur bei Python/Paket-Änderungen)

```
installer\build_bootstrap.bat
```
Voraussetzung: Inno Setup 6 installiert (https://jrsoftware.org/isinfo.php)

### Auto-Updater (launcher.py)

- Prüft beim Start: `GET https://api.github.com/repos/Office-FD/spielplan-optimierer/releases/latest`
- Vergleicht `tag_name` mit lokalem `VERSION`-File
- Bei neuer Version: Windows-Dialog „Jetzt aktualisieren?"
- Update: lädt `app-files.zip` → entpackt nach `BASE_DIR` (überschreibt App-Code, nicht `python/`)
- Timeout 5 Sek. – Fehler werden ignoriert (Programm startet trotzdem)
- Installationsverzeichnis: `%LOCALAPPDATA%\Programs\Spielplan-Optimierer\` (kein Admin-Recht nötig)
