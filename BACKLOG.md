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

### [intern] Code-Review Runde 5 – Block 1: Datenmodell & Validierung

**Typ:** Verbesserung / Fehler
**Bereich:** Spielplan-Optimierung / Validierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**

**B1-M1: `config_validator.py` `validate()` + `validate_cfgs()`: Pflichtspiel- und Sperrtag-Teams nicht gegen Teamliste geprüft**
Wenn ein Pflichtspiel-Teamnamen oder ein Sperrtag-Teamname durch Tipp- oder Importfehler nicht in der Liga existiert, landet er ungeprüft im Solver → konfuser INFEASIBLE statt klarer Meldung. Im UI tritt das nicht auf (Selectbox), aber beim Excel/JSON-Konfig-Upload schon.
Fix: In `validate()` und `validate_cfgs()` prüfen ob `pm.get('teamA')` und `pm.get('teamB')` in `teams` enthalten sind; analog für Sperrtag-Teamnamen.

**B1-M2: `config_validator.py` `validate()` + `validate_cfgs()`: Doppelte Pflichtspiel-Paarung bei n_rounds=1 (Einfachrunde) nicht erkannt**
Bei Einfachrunde muss jede Paarung genau 1× stattfinden. Wird dieselbe Paarung auf zwei verschiedenen Spieltagen als Pflichtspiel eingetragen, kombiniert der Solver `x[m,d1]==1` und `x[m,d2]==1` mit `sum_d x[m,d]==1` → unlösbar ohne erklärende Meldung.
Fix: Bei `n_rounds==1` prüfen ob `frozenset({teamA, teamB})` mehr als einmal in den Pflichtspiel-Einträgen vorkommt → Error.

**B1-L1: `config.py` Z.3: `from collections import defaultdict` – unbenutzter Import**
Seit Einführung von `_TeamColorDict` nicht mehr verwendet.
Fix: Import entfernen.

**B1-L2: `config_validator.py`: kein Check `teamA == teamB` in Pflichtspielen**
Ein Team gegen sich selbst → kein gültiges Match im Solver → stilles INFEASIBLE.
Fix: `if pm.get('teamA') == pm.get('teamB'): err(...)`.

**B1-L3: `distances.py` Z.211 + Z.232: negative km-Werte beim Datei-Import nicht abgefangen**
`int(float(val[0]))` und `int(float(row[km_col]))` akzeptieren negative Zahlen kommentarlos. Negative Distanz korrumpiert die Reiseoptimierung.
Fix: Nach Konvertierung `if km < 0: warn(...)` ergänzen.
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

### [intern] .gitattributes hinzufügen (CRLF-Konsistenz)

**Typ:** Verbesserung
**Bereich:** Sonstiges
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Bei jedem Commit auf Windows erscheinen CRLF-Warnungen. `.gitattributes` mit `*.py text eol=lf`, `*.bat text eol=crlf`, `*.xlsx binary` etc. beseitigt das dauerhaft.
**Status:** Erledigt

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
**Status:** Erledigt

---

### [intern] Ersten GitHub Release anlegen (v1.1.0-Tag setzen)

**Typ:** Aufgabe
**Bereich:** Distribution / GitHub
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Voraussetzung dafür, dass der Installer und der Auto-Updater funktionieren.
Sobald Inno Setup installiert und der Bootstrap-Installer fertig ist:

```bat
git tag v1.1.0
git push --tags
```

GitHub Actions läuft automatisch und erstellt den Release mit `app-files.zip`.
Danach kann der Bootstrap-Installer die App-Dateien beim Installieren herunterladen
und der Auto-Updater hat einen Referenzpunkt für zukünftige Updates.
**Status:** Erledigt

---

### [intern] Bootstrap-Installer bauen (installer\build_bootstrap.bat)

**Typ:** Aufgabe
**Bereich:** Distribution
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein (einmaliger Aufwand ~30 Min inkl. Download)
**Beschreibung:**
Erstellt die verteilbare `Spielplan-Optimierer-Setup-v1.1.0.exe` (~200 MB).
Muss nur neu gebaut werden wenn sich Python-Version oder Pakete ändern.

Voraussetzungen:
1. Inno Setup 6 installieren: https://jrsoftware.org/isinfo.php
2. `iscc.exe` muss im PATH sein (Inno Setup Installer-Compiler)

Dann:
```bat
installer\build_bootstrap.bat
```

Ergebnis liegt in `installer\Output\`.
**Status:** Erledigt

---

### [intern] Installer-Flow auf frischem System testen

**Typ:** Verbesserung / Test
**Bereich:** Distribution
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Nach dem Bau des Bootstrap-Installers auf einem zweiten Windows-PC (ohne
Python-Installation) testen:
1. Setup.exe ausführen → installiert ohne Fehler?
2. Desktop-Verknüpfung startet Browser ohne Terminal-Fenster?
3. Auto-Updater: zweiten Tag v1.1.1 anlegen + app-files.zip hochladen,
   dann prüfen ob der Launcher die Update-Meldung zeigt und das Update korrekt anwendet.
4. Deinstallation über Windows-Einstellungen funktioniert sauber?
**Status:** Erledigt (Mai 2026 – Installer auf frischem Windows-System getestet, funktioniert)

---

### [intern] clubs_db.csv committen

**Typ:** Aufgabe
**Bereich:** Vereinsdatenbank
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`clubs_db.csv` hat lokale Änderungen die noch nicht committed sind (seit vor
dieser Sitzung). Änderungen prüfen und bei Gelegenheit committen.
**Status:** Erledigt (keine Änderungen vorhanden)

---

### [intern] Phase-2-Solver OOM-Kill durch bool_core-Klausel-Explosion

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Bei langen Phase-2-Läufen (8h-Preset) kann der CP-SAT-Solver in eine exponentielle Klausel-Generierungsphase geraten: Der `bool_core`-Subsolver produziert fortlaufend neue Clauses, ohne noch bessere Lösungen zu finden, bis Windows den Prozess wegen Speichermangels (OOM) ohne Ergebnis beendet. Beobachtet Mai 2026: Clauses stiegen von 65.000 auf 1.200.000, bool_core-Cores von 57 auf 882, bis der Prozess nach ~4h gecrasht ist.

**Fix (bereits umgesetzt in multi_solver.py):**
- `solver.parameters.max_memory_in_mb = 4096` – CP-SAT bricht sauber ab und gibt die bisher beste Lösung zurück, statt vom OS gekillt zu werden.
- `solver.parameters.symmetry_level = 1` (war 2) – reduziert die Aggressivität des bool_core-Algorithmus; Level 2 generiert zusätzliche Symmetrie-Constraints, die bool_core als Ausgangsbasis für weitere Ableitungen nutzt und so die Klausel-Kaskade verstärkt.
**Status:** Erledigt

---

### [intern] Nachtlauf-Modus: rel_gap nicht auf 0 setzen

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Im Nachtlauf-Modus (`night_mode=True`) setzt `multi_solver.py` das `rel_gap`-Limit auf 0.0, was einen vorzeitigen Abbruch verhindert. Der Solver läuft dann stur 8h durch – auch wenn er seit Stunden keine bessere Lösung mehr findet. Aus dem Absturz-Log Mai 2026 erkennbar: letzte Verbesserung nach ~2,8h, danach 4,4h Stagnation bis zum OOM-Kill.

**Fix:** In `multi_solver.py` `rel_gap` im Nachtlauf auf 0.005 (0,5%) statt 0.0 setzen:
```python
if night_mode:
    phase2_time = 28800
    rel_gap     = 0.005  # war 0.0 – Solver kann jetzt bei nahezu-optimalem Ergebnis abbrechen
```
0,5% Gap ist in der Praxis nicht wahrnehmbar, spart aber potenziell mehrere Stunden Laufzeit.
**Status:** Erledigt

---

### [intern] Solver-Ergebnisse bei Session-Verlust nicht wiederherstellbar

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Mittel
**Beschreibung:**
Der Solver-Thread speichert Ergebnisse ausschließlich in `st.session_state`. Wenn Streamlit während eines langen Laufs die Session neustartet (z.B. Browser-Verbindung verloren, OOM-Kill, Neustart), ist das Ergebnis verloren – auch wenn der Solver selbst erfolgreich abgeschlossen hat. Beobachtet Mai 2026: Phase 2 lief 8h durch und fand eine FEASIBLE-Lösung, aber kein Excel wurde geschrieben weil die Session beim Fertigstellen schon tot war.

**Fix:** Nach Abschluss jeder Phase das `LeagueResult`-Dict als Pickle auf Disk schreiben, unabhängig vom Session-State:
```python
# in multi_solver.py oder app.py nach run_phase2() / run_phase3()
import pickle, pathlib
_cache = pathlib.Path('.cache') / 'last_result.pkl'
_cache.write_bytes(pickle.dumps(results))
```
Beim App-Start prüfen ob `last_result.pkl` existiert und neuer als die aktuelle Session ist → Nutzer anbieten das letzte Ergebnis wiederherzustellen. Nach erfolgreichem Download/Export die Datei löschen.

**Umgesetzt:** `_solver_thread` speichert nach `solve_all()` sofort `{results, clubs, kw_compat}` als Pickle in `.cache/last_result.pkl`. `_step8()` zeigt beim nächsten App-Start ein Recovery-Banner mit Alter und Liga-Namen. „Wiederherstellen" lädt Pickle, baut Excel-Dateien neu, setzt `S.opt_done = True`. „Verwerfen" löscht die Datei. „Neu berechnen" und „Neuen Spielplan erstellen" löschen die Datei ebenfalls.
**Status:** Erledigt

---

### [intern] Distanzmatrizen werden beim Konfigurations-Import nicht geladen

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI / Schritt 1
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Mittel
**Beschreibung:**
Beim Export einer Konfiguration werden die Distanzmatrizen korrekt in die Excel-Datei geschrieben. Beim Re-Import dieser Konfigurationsdatei bleiben die Distanzmatrizen in der App jedoch leer. Der Import-Code lud die Daten korrekt in `S.dist_matrices`, aber das `st.data_editor`-Widget (key `de_{lid}`) zeigte weiterhin den gecachten leeren Zustand. Fix: nach dem Import `st.session_state.pop(f'de_{_lid}', None)` für alle geladenen Ligen, damit der Editor beim nächsten Render neu aus `S.dist_matrices` initialisiert.
**Status:** Erledigt

---

### [intern] Bessere Beschreibungen der Optimierungsgewichte in der UI (Schritt 3)

**Typ:** Verbesserung
**Bereich:** Streamlit-UI / Schritt 3
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Die vier Gewichtungs-Slider in Schritt 3 sind für Nicht-Techniker zu abstrakt beschriftet. Jeder Slider sollte einen erklärenden Hilfstext (z.B. als `st.caption` oder `help=`-Tooltip) erhalten:

- **Heimrechtswechsel** – „Wie oft wechselt ein Team zwischen Heim- und Auswärtsspielen. Höherer Wert = abwechslungsreichere Spielfolge (z.B. Heim–Auswärts–Heim statt drei Heimspiele hintereinander)."
- **Wechsel-Fairness** – „Wie gleichmäßig die Wechselhäufigkeit über alle Teams verteilt ist. Höherer Wert = kein Team hat deutlich mehr oder weniger Wechsel als die anderen."
- **Reisedistanz** – „Gesamte Fahrtstrecke aller Teams über die Saison. Höherer Wert = kürzere Gesamtkilometer werden stärker bevorzugt."
- **Reise-Fairness** – „Wie gleichmäßig die Reisebelastung auf alle Teams verteilt ist. Höherer Wert = kein Team muss deutlich mehr fahren als die anderen."
**Status:** Erledigt

---

### [intern] stdout-Interleaving bei parallelen Phase-1-Läufen

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`solver.py`: `_ProgressCallback` schreibt direkt auf `sys.stdout`. Bei parallelen Phase-1-Läufen können Ausgaben verschiedener Ligen interleaven wenn Streamlits `sys.stdout`-Ersatz nicht thread-safe ist. Fix: Ausgabe in `threading.Lock` kapseln.
**Status:** Zurückgestellt – kosmetisch; Streamlit-Ausgaben sind bereits auf Sessionebene isoliert. Kein Absturzrisiko.

---

### [intern] Code-Review Runde 3 – Fixes aus vollständigem Review

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung / Streamlit-UI
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
Vollständiges Code-Review aller Module (app.py, solver.py, multi_solver.py, sa_refine.py, tt_scheduler.py, schedule_utils.py, excel_output.py, calendar_parser.py, distances.py, config_validator.py). Folgende Fixes umgesetzt:

- **R1-1**: `solver.py` Phase 1: `symmetry_level=1` (war 2) – konsistent mit Phase 2, reduziert bool_core-Klauselkaskaden.
- **R1-2**: `solver.py` Phase 1: `max_memory_in_mb=4096` ergänzt – parallele Seeds können sonst RAM erschöpfen.
- **R1-3**: `multi_solver.py:_phase1_worker`: Docstring "Prozess" → "Thread" korrigiert (ThreadPoolExecutor, kein ProcessPoolExecutor).
- **R1-4**: `solver.py:_ProgressCallback.on_solution_callback`: `import sys` aus Hot-Path in Modul-Ebene verschoben (wird tausende Male aufgerufen).
- **R2-1**: `app.py:Neuen Spielplan erstellen`: `_DEFAULTS`-Reset nutzte gemeinsam genutzte mutable Objekte; nach erstem Reset + Bearbeitung würde `_DEFAULTS['league_order']` etc. bereits befüllt sein. Fix: `copy.deepcopy(v)` beim Reset.
- **R3-1**: `wizard.py:step3_routing`: Routing-Mindestprozent war 0 – führt bei 0% zu Faktor 100/100 = 1.0 (exakte Distanz gefordert), identisch zu R2-N7 in app.py. Fix: `min=1` statt `min=0`.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Kritische Crashes (sofort beheben)

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI / CLI-Wizard
**Wichtigkeit:** Blocker
**Aufwand:** Klein
**Beschreibung:**
Zwei Bugs, die sofort behoben werden müssen – beide sind Crashes auf dem direkten Nutzungspfad:

**CR4-K1: `app.py` Z.1945/1946/1954: `_sys` undefiniert → NameError bei Google-Maps-Distanzberechnung**
`import sys` steht auf Modulebene (Z.17) als `sys`, aber an drei Stellen im Distanz-Berechnen-Block wird `_sys.stdout` referenziert. Jeder Klick auf „Distanzen berechnen (Google Maps)" crasht sofort mit `NameError: name '_sys' is not defined`.
Fix: `_sys.stdout` → `sys.stdout` (und analog `.stderr`) an allen drei Stellen.

**CR4-K2: `wizard.py` Z.341: `n_active` undefiniert für Formate 1/2/3 → UnboundLocalError**
`n_active = 0` wird nur innerhalb des `else: # '4' Turniertag`-Zweigs (Z.204) gesetzt. Bei Format Einfach-, Hin-Rück- und Dreifachrunde (Formate '1'/'2'/'3') ist die Variable beim Erstellen des Konfigurationstupels in Z.341 undefiniert.
Fix: `n_active = 0` direkt nach `tt_settings: dict = {}` (Z.159) als Default setzen.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Launcher: Versionsvergleich + Update-Download-Integrität

**Typ:** Fehler/Bug
**Bereich:** Distribution / Launcher
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**
Mehrere Bugs im Update-Mechanismus des Launchers:

**CR4-L1: Lexikografischer Versionsvergleich → 1.10.0 wird nicht als Upgrade über 1.9.0 erkannt**
`latest > local` ist ein String-Vergleich: `"1.9.0" > "1.10.0"` ergibt `True` (da `'9' > '1'`). Sobald die App Minor-Version 10 erreicht, erhalten Nutzer mit 1.9.x kein Update mehr angeboten.
Fix: `tuple(int(x) for x in v.split('.'))` für den `>`-Vergleich verwenden.

**CR4-L2: `tempfile.mktemp()` – TOCTOU Race Condition**
`mktemp()` gibt einen Dateinamen zurück ohne die Datei anzulegen. Zwischen Namensvergabe und `urlretrieve()` kann ein anderer Prozess die Datei belegen.
Fix: `tempfile.NamedTemporaryFile(suffix='.zip', delete=False)` verwenden: `with ... as f: tmp = f.name`.

**CR4-L3: Partial-Download hinterlässt inkonsistente App-Dateien**
Bei Verbindungsabbruch während `urlretrieve()` wird das teilweise ZIP trotzdem entpackt und `VERSION_FILE` auf die neue Version gesetzt. Die App ist danach inkonsistent und nicht mehr startbar.
Fix: In temporäres Verzeichnis entpacken, erst nach vollständiger Extraktion nach `BASE_DIR` verschieben und `VERSION_FILE` schreiben.

**CR4-L4: ZIP-Path-Traversal (Security)**
`z.extract(member, BASE_DIR)` ohne Pfadvalidierung. Ein kompromittiertes `app-files.zip` könnte mit `../`-Pfaden Dateien außerhalb von `BASE_DIR` schreiben.
Fix: `dest = os.path.realpath(os.path.join(BASE_DIR, member)); assert dest.startswith(os.path.realpath(BASE_DIR))` vor jedem `extract()`.

**CR4-L5: Browser öffnet alten Server-Prozess nach Update**
Nach einem erfolgreich installierten Update springt der Launcher auf einen noch laufenden Streamlit-Prozess ab, der die alte Version ausführt.
Fix: Wenn ein Update durchgeführt wurde, bestehenden Streamlit-Prozess ignorieren und neu starten.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Solver: blocked_weekends + Phase-2-Turniertag

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**CR4-S1: `solver.py`: `blocked_weekends` prüft nur `wdays[0]` statt alle Tage eines DST-Wochenendes**
Ein DST-Wochenende `[d1, d2]` wird nur dann als gesperrt markiert, wenn `d1` in den Sperrtagen liegt. Wenn nur `d2` gesperrt ist, versucht der Sliding-Window-Constraint trotzdem mindestens 1 Heimspiel in diesem Wochenende zu erzwingen → INFEASIBLE obwohl ein gültiger Plan existiert.
Fix: `if any(d in blocked_per_team[_ti] for d in _wdays)` statt nur `_wdays[0]` prüfen.

**CR4-S2: `multi_solver.py`: Turniertag-Liga erhält nach Phase 2 veraltete `hosts`/`game_times`**
`result.hosts` und `result.game_times` werden nach Phase 2 direkt aus dem Phase-1-Ergebnis übernommen. Da Phase 2 den Spielplan verändern kann, passen diese nicht mehr zum neuen Spielplan → falsche Excel-Exports für Turniertag-Ligen.
Fix: `apply_tournament_ordering()` nach Phase 2 für Turniertag-Ligen erneut aufrufen.

**CR4-S3: `multi_solver.py` Z.328: Phase-2-Ergebnis-Dict wird direkt mutiert wenn `sa_time=0`**
`phase3 = phase2` (direkter Verweis, keine Kopie). Die anschließende Turniertag-Nachbearbeitung mutiert `phase3[lid]` und damit auch `phase2[lid]`.
Fix: `phase3 = dict(phase2)` (shallow copy) wenn `sa_time == 0`.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – tt_scheduler: Backtracking + stille Ausrichter-Ignorierung

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**CR4-T1: `tt_scheduler.py` Z.199: `_try_solve` wählt immer das erste Ausrichter-Spiel im Pool**
Der Backtracker legt den Ausrichter-Slot auf `host_idxs[0]` fest, ohne weitere Kandidaten zu probieren. Wenn `host_idxs[0]` nicht mit dem `min_gap`-Constraint verträglich ist, scheitert der Backtracker – obwohl ein anderes Ausrichter-Spiel eine valide Reihenfolge ergeben würde.
Fix: Alle `host_idxs` als Kandidaten im Backtracking durchprobieren statt nur den ersten.

**CR4-T2: `tt_scheduler.py` Z.329: Ausrichter nicht im Spielplan → stilles Ignorieren ohne Warnung**
Wenn `host_per_day[d]` ein Team enthält, das an Spieltag `d` kein Spiel hat (z.B. nach manuellen Änderungen), wird `host = None` gesetzt ohne Meldung. Der Ausrichter fehlt kommentarlos im Ergebnis.
Fix: `warn(f'{cfg.name}: Ausrichter {host} an Spieltag {d} nicht im Spielplan – wird ignoriert.')` vor dem `host = None`.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Schedule-Utils: Wechselzähler + Turniertag-Guards + iCal

**Typ:** Fehler/Bug
**Bereich:** Spielplanverwaltung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**CR4-U1: `schedule_utils.py` Z.49: `prev` nicht zurückgesetzt bei fehlendem `home_val` → Wechselzähler nach Absagen falsch**
In `recompute_result_stats()` wird bei `cur is None` (kein home_val für diesen Spieltag) `continue` ausgeführt ohne `prev = None`. Ein Wechsel kann über eine Lücke hinweg fälschlich erkannt oder übersehen werden.
Fix: `prev = None; continue` statt `continue`.

**CR4-U2: `schedule_utils.py` Z.84: `swap_home_away` korrumpiert `home_vals` im Turniertag-Kontext**
`swap_home_away` setzt `home_vals[(ti, d)]` pauschal auf 0 oder 1, aber für Turniertage enthält `home_vals` Zähler (Anzahl Heimspiele ≥ 1). Ein Aufruf via UI korrumpiert die Statistik.
Fix: Guard am Anfang: `if cfg.games_per_team_per_day > 1: return`.

**CR4-U3: `schedule_utils.py` Z.152: `move_game` kein Guard für Turniertag**
Analoges Problem: `move_game` setzt `home_vals[(ti, new_day)] = 1`, was für Turniertage falsch ist.
Fix: `if cfg.games_per_team_per_day > 1: return 'Verschieben bei Turniertag nicht unterstützt.'`

**CR4-U4: `schedule_utils.py` Z.332: iCal-Fallbackdatum setzt alle Spiele ohne Kalender auf den 1. Januar**
Mehrere Spieltage ohne Kalender-Eintrag erhalten alle `{season_year}0101` als Datum. In Kalender-Apps entstehen dadurch hunderte überlagernde Events am 1. Januar.
Fix: Spiele ohne Kalenderdatum aus dem iCal-Export ausschließen und eine Gesamtwarnung ausgeben.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Config / Distanzen / Excel: Mittel-Bugs

**Typ:** Fehler/Bug
**Bereich:** Distanzen / Config / Excel-Export
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**CR4-D1: `distances.py` Z.200: KeyError bei case-abweichendem Spaltennamen in Distanzmatrix-CSV**
Spaltenüberschriften werden beim Prüfen case-insensitiv verglichen, aber der Zugriff `df.loc[..., team_j.strip()]` ist case-sensitiv. Wenn Header-Groß-/Kleinschreibung von den Team-Namen abweicht, entsteht ein `KeyError`.
Fix: Mapping-Tabelle aufbauen: `col_map = {c.strip().lower(): c for c in df.columns}`; dann `df.loc[..., col_map[team_j.strip().lower()]]` verwenden.

**CR4-D2: `config.py` Z.34: `defaultdict(get_team_color)` erzeugt defekten Fallback**
`defaultdict` ruft die Factory mit null Argumenten auf, aber `get_team_color(idx: int)` erwartet ein Pflichtargument. Ein direkter Zugriff auf `TEAM_COLORS[20]` würde `TypeError` werfen.
Fix: `class _TeamColorDict(dict):\n    def __missing__(self, k): return get_team_color(k)` statt `defaultdict`.

**CR4-D3: `config_validator.py` Z.250: `validate_cfgs()` erkennt NaN in Distanzmatrix nicht**
`float(cfg.dist.sum()) == 0.0` ist `False` wenn die Matrix NaN enthält. Die Warnung vor ungültiger Matrix bleibt aus; `validate()` (Einzel-Liga) hat diesen Check korrekt.
Fix: `or bool(np.isnan(cfg.dist).any())` zur Bedingung ergänzen.

**CR4-D4: `excel_output.py` Z.127: DST-Routing-Anzeige zeigt falschen Prozentwert**
`f'{cfg.f_num}%'` zeigt z.B. „110%" (den Faktor-Zähler), gemeint ist „10%" (der Umweg-Mehrprozentsatz).
Fix: `f'{cfg.f_num - 100}%'`.

**CR4-D5: `calendar_parser.py` Z.52: `_to_date_str()` gibt `'nan'` für leere Excel-Zellen zurück**
Pandas liefert `float('nan')` für leere Zellen. `_to_date_str(nan)` gibt den String `'nan'` zurück, der als `week_start`/`week_end` in die Kalendereinträge gelangt.
Fix: `if isinstance(cell, float) and math.isnan(cell): return ''` als zweite Guard-Zeile.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – App.py: sys.stdout + Rename + opt_warnings

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**CR4-A1: `app.py` Z.3184: `sys.stdout` wird global für alle Threads ersetzt**
`_solver_thread` setzt `sys.stdout = _QueueWriter(log_q)` prozessweit. Wenn der Thread crasht und `old_out` durch einen weiteren Start bereits überschrieben wurde, geht die echte Konsole dauerhaft verloren. Kein Guard gegen Doppelstart.
Fix: Vor Thread-Start prüfen ob `S.opt_running` bereits True ist; `old_out` mit Lock sichern.

**CR4-A2: `app.py` Z.1811: Liga-ID umbenennen ohne `st.rerun()` → UI-Inkonsistenz**
Nach dem Rename ist `st.session_state[f'lid_{i}']` noch auf den alten Wert gesetzt. Beim nächsten Frame zeigt das Textfeld wieder den alten Namen und kann erneut einen Rename triggern.
Fix: `st.session_state[f'lid_{i}'] = new_lid` setzen und `st.rerun()` aufrufen.

**CR4-A3: `app.py` Z.3526: Solver-Thread-Absturz wird nicht als Warnung angezeigt**
`[FEHLER]`-Zeilen im Log werden nicht nach `S.opt_warnings` übernommen (nur `[!!]`-Prefix). Bei einem Thread-Absturz sieht der Nutzer nur leere Ergebnisse ohne Fehlerhinweis.
Fix: `if '[FEHLER]' in l or '[!!]' in l:` für den `opt_warnings`-Append.

**CR4-A4: `app.py` Z.1912: Upload-Fehler blockiert Navigation wenn vorherige gültige Matrix existiert**
Bei Parse-Fehler wird `errors.append(lid)` gesetzt – auch wenn in `S.dist_matrices[lid]` bereits eine gültige Matrix vom vorherigen Upload liegt.
Fix: `if lid not in S.dist_matrices: errors.append(lid)`.

**CR4-A5: `app.py` Z.2965: JSON-Restore: Teams als `list` statt `tuple` nach Konfigurations-Import**
`json.loads()` deserialisiert Tuples als Lists. Bei erneutem Export entsteht gemischtes Format.
Fix: In `_session_from_json`: `ld['teams'] = [tuple(e) for e in ld.get('teams', [])]` für jede Liga.
**Status:** Erledigt

---

### [intern] Code-Review Runde 4 – Niedrig-Priorität

**Typ:** Verbesserung
**Bereich:** Diverse
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**

**CR4-N1: `schedule_utils.py` Z.431: `build_print_html` ohne Längenprüfung auf `result.travels[ti]`**
Nach manuellen Änderungen kann `result.travels` kürzer als `cfg.n_teams` sein → `IndexError`.
Fix: `km_val = result.travels[ti] if ti < len(result.travels) else 0`.

**CR4-N2: `excel_output.py` Z.429+534: Fairness-Sheet-Merge-Breiten falsch**
- Z.429: Titel merged auf 8 Spalten (hardcoded), aber bei `n_rounds ≥ 2` gibt es 9+ Spalten.
  Fix: `end_column=5 + 2 * cfg.n_rounds`.
- Z.534: Section-C-Header merged 7 Spalten, aber nur 6 Datenspalten vorhanden.
  Fix: Merge-Breite 7 → 6.

**CR4-N3: `excel_output.py` Z.891: `get_team_color(-1)` bei unbekanntem Team im Hallenbelegungsplan**
Python-Index -1 ergibt die letzte Farbe statt eines Fallbacks.
Fix: `hi if hi >= 0 else 0` als Guard.

**CR4-N4: `app.py` Z.4338: `_prev_tot` – toter Code (Variable berechnet aber nie verwendet)**
Fix: Zeilen 4338–4341 entfernen.

**CR4-N5: `wizard.py` Z.264: `k_group` nicht gesetzt im Auto-Select-Ast bei Turniertag Stufe 2**
Wenn genau eine Gruppengrößen-Option valide ist, wird `k_group` nicht gesetzt; `n_events` berechnet dann mit `k_group=0` falsch.
Fix: `k_group = K` nach der `info()`-Ausgabe ergänzen.

**CR4-N6: `main.py` Z.90: `import numpy as np` innerhalb der `for`-Schleife**
Fix: Import an den Dateianfang verschieben.

**CR4-N7: `multi_solver.py` Z.152: Co-Home-Bool-Äquivalenz unvollständig modelliert**
`co_var=1 ⟹ alle home_vars=1` ist modelliert, aber nicht die Umkehrung. In der Praxis kein Problem (Maximierung treibt `co_var=1`), aber bei negativem Bonus wäre das Verhalten inkonsistent.
Fix: `model.Add(co_var >= sum(home_vars) - len(home_vars) + 1)` als dritte Klausel.
**Analyse:** Kein Bug. Constraint 2 (`co_var=0 → ∃ home_var=0`) ist das Kontrapositive von `alle home_vars=1 → co_var=1`, daher ist das Modell vollständig. Kein Fix erforderlich.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 2: Solver-Kleinigkeiten

**Typ:** Verbesserung / Fehler
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**

**B2-L1: `solver.py`: `needs_bye` doppelt berechnet (Z.178 und Z.244)**
`needs_bye = (n * gpd) % 2 == 1` steht einmal vor dem Modellaufbau und einmal inmitten der Constraint-Schleife – redundante Berechnung, keine Auswirkung auf Korrektheit.
Fix: Zweite Zeile (Z.244) entfernen.

**B2-L2: `solver.py`: `home_team`-Validierung in Pflichtspiel-Constraint stille Falllback**
`model.Add(h[m] == (0 if home_team == can_a else 1))` setzt `h[m]=1` (B-Heim) wenn `home_team` weder `can_a` noch `can_b` ist – z.B. durch Tippfehler im Import. Der Solver liefert eine Lösung, aber das Heimrecht ist falsch ohne jede Meldung.
Fix: Explizit prüfen: `if home_team not in (can_a, can_b): warn(...); continue` vor dem `model.Add`.

**B2-L3: `multi_solver.py`/`app.py`: `rel_gap` erreicht Phase 1 nicht**
`solve_all()` nimmt `rel_gap` als Parameter entgegen und gibt ihn an `run_phase2()` weiter. `run_phase1()` verwendet stets den hardcodierten Default `0.05`. Phase-1-Läufe können daher nicht über den UI-Solver-Slider gesteuert werden.
Fix: `run_phase1()` ebenfalls ein `rel_gap`-Parameter hinzufügen und in `solve_all()` übergeben. Alternativ: als bekannte Einschränkung dokumentieren.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 3: SA + Schedule-Utils + TT-Scheduler

**Typ:** Fehler/Bug
**Bereich:** Spielplan-Optimierung / Spielplanverwaltung
**Wichtigkeit:** Wichtig für Alltag (B3-H1) / Kleiner Wunsch (B3-M1, B3-L1)
**Aufwand:** Klein
**Beschreibung:**

**B3-H1 (Hoch): `sa_refine.py` Z.80: `loc`-Array mit `0` statt Teamindex initialisiert**
```python
loc: List[List[int]] = [[0] * (N + 2) for _ in range(n)]
```
Für Spieltage vor dem ersten Spiel (bye-Tage bei ungerader Teamzahl) bleibt `loc[ti][d] = 0` (immer Team 0's Standort). Die SA berechnet damit für jeden bye-Tag die Reise von Team-0-Heimort statt vom tatsächlichen Heimort des Teams – `_recompute_team` gibt falsche Reisekosten zurück, SA nimmt Tausch-Entscheidungen auf Basis falscher Werte.
Fix: `[[ti] * (N + 2) for ti in range(n)]` – jedes Team startet an seinem eigenen Standort.
Betroffen: alle Ligen mit ungerader Teamzahl (Spielfrei-Modus, in v1.2.2 neu eingeführt).

**B3-M1 (Mittel): `schedule_utils.py` `recompute_result_stats()`: Reisedistanz-Formel inkonsistent mit Solver**
`recompute_result_stats` summiert pro Auswärtsspiel `dist[ai, hi]` (Einzel-Fahrt Heimort Auswärtsteam → Spielort). Solver und SA verwenden dagegen `dist[loc[d], loc[d+1]]` (Übergänge zwischen aufeinanderfolgenden Spieltagen). Bei aufeinanderfolgenden Auswärtsspielen an verschiedenen Orten weichen die Werte systematisch ab – nach manuellen Spielplanänderungen zeigt die UI falsche km-Zahlen.
**Fix (umgesetzt):** `recompute_result_stats` nutzt jetzt das Transitions-Modell: `loc[ti][pos]` = Venue-Index an Tag-Position pos, Default = eigener Standort; summiert `dist[loc[ti][pos], loc[ti][pos+1]]` über alle aufeinanderfolgenden Spieltage.

**B3-L1 (Niedrig): `tt_scheduler.py` Z.324–325: `int(s)` ohne try-except auf rohen Slot-Strings**
`raw_slots` kommt aus `tt_settings['slots']` (Nutzereingabe). `int(s)` wirft `ValueError` wenn ein nicht-numerischer String übergeben wird → unbehandelter Absturz in der Nachbearbeitung.
Fix: `try: slots = [int(s) for s in raw_slots] except ValueError: warn(...); slots = []`.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 4: Excel-Export & Kalender-Parser

**Typ:** Verbesserung
**Bereich:** Excel-Export
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**

**B4-L1 (Niedrig): `excel_output.py` Z.800: `is_home == 1` statt `>= 1` in Co-Home-Zusammenfassung**
`is_home = res.home_vals.get((ti, st), 0) == 1` – für Turniertag-Ligen enthält `home_vals` Zähler (Anzahl Heimspiele, kann > 1 sein). Der strikte Vergleich `== 1` gibt für Zähler ≥ 2 `False` zurück → Co-Home-Übersicht zeigt für Turniertag-Teams immer „nein" statt „JA". Gleiches Muster wie der bereits behobene CR4-U2 in `schedule_utils.py`.
Fix: `>= 1` statt `== 1`.

`calendar_parser.py`: keine Befunde.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 5: CLI-Wizard & Distribution

**Typ:** Fehler/Bug
**Bereich:** CLI / Distribution
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Klein
**Beschreibung:**

**B5-H1 (Hoch): `wizard.py` – Spieltagzahl-Formel für ungerades n nicht auf Stand von v1.2.2**
Vier Stellen im CLI-Wizard verwenden noch die alte Formel `n_rounds * (n-1)` statt der korrekten `n_rounds * n * (n-1) // 2 // games_per_day`:

1. `_calc_n_matchdays` Z.51: Rückgabewert für K=0 – liefert 8 statt 10 für n=5, n_rounds=2.
2. `build_configs` Z.880: `n_md = n_rounds * (n-1)` → `days = [1..8]` → `LeagueConfig` hat 8 Tage, erwartet aber 10 → CLI-Solver liefert INFEASIBLE für ungerades n.
3. `step2_calendar_and_dst` Z.476: `n_md = n_rounds_lid * (len(teams) - 1)` → DST-Tage 9 und 10 werden bei n=5 als außerhalb des erlaubten Bereichs abgelehnt.
4. `step2_calendar_and_dst` Z.493: identischer Fehler im manuellen DST-Pfad.

Hintergrund: Gleicher Bug wurde in `app.py` für v1.2.2 behoben; `wizard.py` wurde dabei nicht mitgezogen.

Fix: An allen vier Stellen entweder `_calc_n_matchdays(ld)` aufrufen oder direkt die korrekte Formel einsetzen:
```python
games_per_day = max(1, n * gpd // 2)
total_matches = n_rounds * n * (n - 1) // 2
n_md = total_matches // games_per_day
```

`main.py`, `launcher.py`: keine Befunde.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 6: app.py (vollständig)

**Typ:** Fehler/Bug
**Bereich:** Streamlit-UI
**Wichtigkeit:** Mittel (B6-M1) / Kleiner Wunsch (B6-L1)
**Aufwand:** Klein
**Beschreibung:**

**B6-M1 (Mittel): `app.py` Z.1371–1388: `NameError` bei Konfigurationsimport ohne `Einstellungen`-Sheet**
In `_step0()` (Konfigurationsdatei hochladen): Variable `s = parsed['settings']` wird nur im `if 'settings' in parsed:`-Block (Z.1367) definiert. Der nachfolgende `if _has_loaded_matrices:`-Block (Z.1371) greift auf `s` zu – unabhängig davon, ob `settings` in `parsed` vorhanden ist. Wenn eine Excel-Datei das `Distanzmatrizen`-Sheet enthält (→ `_has_loaded_matrices=True`), aber kein `Einstellungen`-Sheet, → `NameError: name 's' is not defined`.
Fix: `s = parsed.get('settings', {})` als erste Zeile setzen, `if 'settings' in parsed:`-Block und zugehörige `s`-Zuweisung entfernen.

**B6-L1 (Niedrig): `app.py` Z.3465–3500: `_solver_thread` ist toter Code**
Die Funktion `_solver_thread` (Thread-basierter Solver-Start) ist seit der Subprocess-Migration via `spielplan_multi/_worker.py` nicht mehr aufgerufen – `_step8` verwendet ausschließlich `multiprocessing.Process`. Die Funktion nimmt ~35 Zeilen ein und erzeugt keinen Schaden, ist aber irreführend.
Fix: `_solver_thread` entfernen.

Restliche app.py (Schritte 0–8, Serialisierung, Ergebnisanzeige, Spielplan-Nachbearbeitung): keine weiteren Befunde.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 7: app.py Z.2600–3800 (Schritte 3–8, Sitzungsserialierung)

**Typ:** Review
**Bereich:** Streamlit-UI
**Wichtigkeit:** –
**Aufwand:** –
**Beschreibung:**

Vollständig gereviewed zusammen mit Block 6 (app.py in einem Durchgang). Abgedeckte Bereiche: `_step3` (Gewichte, Co-Home), `_step4` (Pflichtspiele), `_step5` (Sperrtage/Pflichttage), `_step6` (Co-Home-Erkennung), `_step7` (Solver-Konfiguration), `_session_to_json` / `_session_from_json`, `_build_league_configs`, `_solver_thread` (als toter Code identifiziert → B6-L1), Beginn `_step8`.

Keine eigenen neuen Befunde – gefundene Bugs sind unter Block 6 (B6-M1, B6-L1) dokumentiert.
**Status:** Erledigt

---

### [intern] Code-Review Runde 5 – Block 8: app.py Z.3800–4877 (Ergebnisanzeige, Downloads, Nachbearbeitung)

**Typ:** Review
**Bereich:** Streamlit-UI
**Wichtigkeit:** –
**Aufwand:** –
**Beschreibung:**

Vollständig gereviewed zusammen mit Block 6. Abgedeckte Bereiche: `_step8` Ergebnisanzeige (Kennzahlen, Warnungen, Fairness-Tabelle, Spielpläne, Downloads), Spielzeiten-Zuweisung, Spielplan manuell anpassen (Heim/Auswärts-Tausch), Spiel verschieben / absagen / Nachholtermin, Spielplan-Vergleich, `_step_intro`, Haupt-Rendering, `_inject_floorball_css`.

Keine eigenen neuen Befunde.
**Status:** Erledigt
