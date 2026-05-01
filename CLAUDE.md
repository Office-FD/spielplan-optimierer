# Spielplan-Optimierer – Vollständige Projektdokumentation

> **Version 1.0.0-beta1 · Stand April 2026 · Status: Beta-fähig, keine bekannten kritischen Bugs**

---

## 1. Schnell-Überblick

Automatisierte Spielplanerstellung für Floorball-Ligen (FLOORBALL VERBAND DEUTSCHLAND e.V.).
Streamlit-Web-App + Python-Backend. Drei-Phasen-Pipeline: CP-SAT (OR-Tools) + Simulated Annealing.

**Start:** `start.bat` → Browser öffnet `localhost:8501`
**Ausgabe:** `Spielplaene/` (Excel pro Liga + Co-Home-Zusammenfassung)
**Cache:** `.cache/` (Distanzmatrizen von Google Maps, JSON-Dateien)
**Distribution:** `create_release.bat` → ZIP ohne `.venv/.cache/Spielplaene/__pycache__/.git/memory`

---

## 2. Dateistruktur

```
app.py                    ← Streamlit-UI (9 Wizard-Schritte + Ergebnisansicht), ~3800 Zeilen
requirements.txt          ← ortools>=9.14,<10  numpy pandas openpyxl requests streamlit>=1.32
install.bat               ← Erstinstallation: Python-Check, .venv erstellen, pip install
start.bat                 ← .venv/Scripts/streamlit run app.py
create_release.bat        ← ZIP für Distribution erstellen (Version in Datei anpassen)
BACKLOG.md                ← Feature-Wünsche und Bugs (App schreibt direkt rein)
clubs_db.csv              ← Vereinsdatenbank mit Adressen (für Team-Suche in Schritt 0)
test_all.py               ← Umfassende Tests (Solver, Constraints, Export)
test_smoke.py             ← Schnelle Smoke-Tests
test_distances.py         ← Distanzmatrix-Tests
test_features.py          ← Feature-Tests (HTML-Druckansicht, iCal, Hallenbelegung, Co-Home)
create_overview_doc.py    ← Standalone-Skript: generiert DOCX-Projektübersicht (python-docx nötig, nicht in requirements.txt; kein Teil der App-Pipeline)

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
S.sol               # dict: {seeds, p1, p2, sa}
S.move_pending      # None|{lid,day,idx,ht,at} – laufende Verschiebe-Aktion
S.cancel_pending    # None|{lid,ht,at} – Spiel ausgefallen, Nachholtermin pending
```

### Wizard-Schritte
| Schritt | Inhalt |
|---|---|
| 0 | Ligen & Teams konfigurieren (Vereinssuche, Konfiguration Download/Upload) |
| 1 | Distanzmatrizen (manuell / CSV-Excel / Google Maps API) |
| 2 | Kalender laden (Rahmenterminplan-Excel) + DST-Blöcke konfigurieren |
| 3 | DST-Routing (Umwegbegrenzung) + Optimierungsgewichte (switch/sw_fair/travel/trav_fair) + Co-Home-Gewicht |
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
WEIGHT_LABELS = {
    'switch':    ('Heimrecht-Wechsel', 80.0),   # maximieren
    'sw_fair':   ('Fairness Wechsel',   2.0),   # max-min minimieren
    'travel':    ('Gesamtkilometer',    0.05),  # minimieren
    'trav_fair': ('Fairness km',        0.02),  # max-min minimieren
}
```
Rohgewichte 0-10 (Slider) werden mit dem Skalar multipliziert → w_scaled.
Zielfunktion: `sum(switch·scale·sw) - sum(sw_fair·scale·(max_sw-min_sw)) - sum(travel·scale·km) - sum(trav_fair·scale·(max_km-min_km))`

---

## 8. Kritische Constraints im Solver (solver.py)

- Jedes Match genau 1× pro Phase; Hin-/Rückrunde strikt getrennt (hinrunde_end)
- Jedes Team genau gpd Spiele pro Spieltag
- Konsekutiv: max 2× Heim oder 2× Auswärts hintereinander (außer DST-Tage)
- **Sliding-Window 3er**: in jedem Spieltag-Tripel min 1 Heim und max 2 Heim — **überspringt Wochen mit DST-Tagen**
- **Sliding-Window 4er**: in jedem Quadrupel max 3 Heim — **überspringt Wochen mit DST-Tagen** (fix für back-to-back DST)
- DST: beide Tage haben identisches Heimrecht
- DST-Routing: Reiseweg zwischen DST-Tag 1 → Tag 2 ≤ (1 + f_num/f_den) × Direktweg
- Sperrtage und Pflichtspiele: Hard Constraints

---

## 9. Bekannte Bugfixes (April 2026)

| Datei | Problem | Fix |
|---|---|---|
| `sa_refine.py` | LeagueResult fehlte `groups`, `hosts`, `game_times` → stille Datenverlust für Turniertag Stufe 2 | Felder in return-Statement ergänzt |
| `excel_output.py:261` | `t_idx[host]` KeyError wenn host nicht in t_idx | `t_idx.get(host,-1)` + Bounds-Check |
| `distances.py:122` | `data['rows'][0]` IndexError wenn API `rows:[]` zurückgibt | Leere-Liste-Guard |
| `app.py:3144` | Division durch 0 bei `avg_km=0` (Turniertag travel=0) | `if avg_km else 0` Guard |
| `app.py:3769` | `S.step` außerhalb [0,8] → IndexError | `max(0,min(S.step,8))` Clamp |
| `calendar_parser.py` | DST-Blöcke mit Spieltagen außerhalb der Range → KeyError im Solver | `build_weekends()` filtert beide Tage |
| `solver.py` | 4er-Fenster bei back-to-back-DST → INFEASIBLE | Fenster überspringt DST-Tage |
| `solver.py` + `multi_solver.py` | OR-Tools 9.15 entfernte `SolveWithSolutionCallback()` → AttributeError in Phase 1+2 (kein Ergebnis, kein sichtbarer Fehler) | Auf `solver.Solve(model, callback)` umgestellt |

---

## 10. Feature-Status (BACKLOG.md)

| Feature | Status |
|---|---|
| iCal-Export pro Team (ZIP) | Erledigt – `build_ics_bytes()` in schedule_utils.py |
| Druckansicht HTML | Erledigt – `build_print_html()` in schedule_utils.py |
| Warnungen bei unausgewogenen Plänen | Erledigt – `find_schedule_warnings()` in schedule_utils.py |
| DST-Blöcke automatisch vorschlagen | Erledigt – Schritt 2 "Paare automatisch vorschlagen" |
| Manuelle Nachbearbeitung (verschieben) | Erledigt – move_game/cancel_game/reschedule_game |
| Spielplan-Vergleich zweier Konfigurationen | Erledigt – "Spielplan vergleichen" Expander, parsed Kilometerstatistik-Sheet |
| Spielabsagen & Nachholspiele | Erledigt – cancel_game + reschedule_game mit find_free_days |
| Interaktive Kalenderansicht | Offen (Aufwand Groß) |
| Karten-Visualisierung Reiserouten | Offen (Aufwand Groß) |
| Multi-Saison-Planung | Offen (Aufwand Groß) |
| REST-API | Offen (Aufwand Groß) |

---

## 11. Spielplan-Formate

| Format | n_rounds | gpd | n_teams_per_group | Beschreibung |
|---|---|---|---|---|
| Einfachrunde | 1 | 1 | 0 | Jede Paarung 1×, n-1 Spieltage |
| Hin-Rückrunde | 2 | 1 | 0 | Jede Paarung 2×, 2(n-1) Spieltage |
| Dreifachrunde | 3 | 1 | 0 | Jede Paarung 3×, 3(n-1) Spieltage |
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
