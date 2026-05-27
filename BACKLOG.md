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
**Status:** Erledigt – in v1.10.0 implementiert (`spielplan_multi/calendar_output.py`). Streamlit-Calendar mit Monats-/Wochen-/Listenansicht, deutscher Lokalisierung, Wochennummern, Team-Farben.

---

### [intern] Karten-Visualisierung der Reiserouten

**Typ:** Neue Funktion
**Bereich:** Distanzen / Karte
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Groß
**Beschreibung:**
Reiserouten pro Spieltag auf einer interaktiven Karte einblenden (Folium oder Leaflet via streamlit-folium). Standorte der Teams als Pins, Verbindungen zeigen welches Team wohin reist. Kann helfen Ausreißer-Spieltage mit ungewöhnlich langen Wegen zu identifizieren.
**Status:** Erledigt – in v1.9.0 implementiert (`spielplan_multi/geocode.py` + `spielplan_multi/map_output.py`). Folium-Map mit Liga-LayerGroups, CircleMarker pro Team-Standort und PolyLines pro Paarung (Dicke = Anzahl Begegnungen). Geocoding via OSM Nominatim mit Cache.

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

---

### [intern] Code-Review Runde 6 – Block A: Solver-Modell (Constraints & Performance)

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag (A-H1, A-H2) / Mittel (A-M1, A-M2) / Kleiner Wunsch (A-L1 … A-L5)
**Aufwand:** Klein-Mittel
**Beschreibung:**

Reviewed: `solver.py`, `multi_solver.py`, `sa_refine.py`, `tt_scheduler.py` (+ `league_types.py` für Properties).

**A-H1 (Hoch): `sa_refine.py` Z.289 – `result.home_vals` wird nicht aktualisiert nach SA-Lauf**
SA verändert den Spielplan (Heimrecht-Tausch pro Paar), gibt aber `home_vals=result.home_vals` aus dem Input-LeagueResult zurück. Das schedule ist neu, home_vals ist alt → inkonsistent. Folgen:
- `excel_output.py` Heatmap liest `home_vals` direkt → falsche Farben für SA-veränderte Tage
- `excel_output.py` Co-Home-Sheet liest `home_vals` → falsche Indikatoren für Mehrspartenvereine
- `schedule_utils.py recompute_result_stats()` liest `home_vals` → falsche `sw_counts` nach manuellen Spielplanänderungen
Identisch zum Pattern, das Bugfix v1.2.7→v1.2.8 für Session-Restore fixte – hier in der SA-Pipeline.
Fix: Vor dem `return` ein frisches `home_vals` aus dem neuen `schedule` rekonstruieren:
```python
new_home_vals = {}
for d, games in schedule.items():
    for ht, at in games:
        hi = t_idx.get(ht)
        ai = t_idx.get(at)
        if hi is not None: new_home_vals[(hi, d)] = 1
        if ai is not None: new_home_vals[(ai, d)] = 0
```
Und `home_vals=new_home_vals` statt `result.home_vals`. Hits Normalfall: SA ist standardmäßig aktiv (`sa_time=120`).

**A-H2 (Hoch): `sa_refine.py` Z.40 – `_objective()` ignoriert `dst_eff`-Term**
Die SA-Zielfunktion summiert nur switch + sw_fair + travel + trav_fair. Der CP-SAT-Solver hat zusätzlich einen `dst_eff`-Term (Belohnung für räumlich nahe Auswärts-Paarungen in DST-Blöcken). Wenn der Nutzer `w_scaled['dst_eff'] > 0` setzt, optimiert SA gegen eine andere Zielfunktion als der CP-SAT-Solver → SA kann eine "bessere" Lösung im SA-Sinne finden, die aber `dst_eff` verschlechtert. Da SA-Swaps Venues verschieben (anderes Heimteam = anderer Spielort), ist `dst_eff` SA-relevant.
Default-Wert ist 0 (Feature inaktiv), Bug fällt nur bei aktiver `dst_eff`-Optimierung auf.
Fix: `_objective()` um den `dst_eff`-Term erweitern. Da SA `loc[ti][d]` direkt verwaltet, ist die Formel `gain = dist[ti, loc[ti][d1]] + dist[ti, loc[ti][d2]] - dist[loc[ti][d1], loc[ti][d2]]` pro DST-Block direkt berechenbar.

**A-M1 (Mittel): `solver.py` Z.342-369 – DST-Nachbarschaft (A/B/C) berücksichtigt `needs_bye` nicht**
Die Constraints rund um DST-Blöcke (max 3 in Folge) erzwingen `home[pre1] + home[post1] >= 1` (bzw. analog B/C), wenn der DST-Block Auswärts ist. Bei ungerader Teamzahl (`needs_bye=True`) hat jedes Team Spielfrei-Tage; an diesen ist `home[ti, bye] = 0` automatisch.
Edge-Case: Wenn DST-Block UND pre1 UND post1 alle Bye-Tage für dasselbe Team sind → `0 + 0 >= 1` ist unlösbar → Phase 1/2 INFEASIBLE. Wahrscheinlichkeit gering (etwa bei n=5 mit 2 Byes pro Team und DST-Block), aber nicht null.
Die Sliding-Window-Constraints (Z.249-283, Z.302-339) haben bereits den `needs_bye`-Pattern: `model.Add(sum(seg) >= plays - k)`. DST-Nachbarschaft sollte dieselbe Logik bekommen.
Fix: In A/B/C-Constraints bei `needs_bye=True` die `>= 1`-Schranken durch `>= sum_plays_in_window - len_window + 1` ersetzen.

**A-M2 (Mittel): `solver.py` Z.540-547 – Blocked vs. Forced-Home Konflikt wird stillschweigend zugunsten von forced_home aufgelöst**
Wenn ein Tag sowohl in `cfg.blocked[team]` (Sperrtag) als auch in `cfg.forced_home[team]` (Pflichtheim) steht, wird die Sperrtag-Constraint übersprungen (Z.546: `if d in days and d not in forced_set`). Forced_home wird angewendet → Team hat Heim trotz Sperrtag. Keine Warnung, keine Fehlermeldung.
Auch denkbar: Pflichtspiel mit Heimrecht für Team A am Tag D, gleichzeitig D in A's Sperrtag-Liste → CP-SAT sieht `home == 0` und `home == 1` → INFEASIBLE mit kryptischer Meldung.
Fix: In `config_validator.py` (Block B) als Konflikt erkennen + Warnung in `solver.py` ergänzen, wenn ein Tag sowohl blocked als auch forced_home/pinned ist.

**A-L1 (Niedrig): `multi_solver.py` Z.85 – Fehlermeldung sagt "Prozess-Absturz", verwendet aber Threads**
ThreadPoolExecutor wird verwendet (Z.75), aber die Fehlermeldung schreibt "Phase-1-Worker-Fehler (Prozess-Absturz): ...". Verwirrend beim Debugging.
Fix: `Prozess-Absturz` → `Worker-Absturz`.

**A-L2 (Niedrig): `tt_scheduler.py` Z.75 – Hardcoded `random.Random(42)` für Host-Zuweisung**
`_assign_hosts` nutzt einen festen Seed unabhängig vom Solver-Seed. Bei Re-Run mit anderem Seed sind die Spielreihenfolge und das Backtracking unterschiedlich, die Ausrichter-Zuweisung aber identisch. Bei großen Turnier-Ligen wäre Variation wünschenswert.
Fix: `apply_tournament_ordering(result, cfg, seed=42)` als Parameter, durch `multi_solver.py` weiterleiten.

**A-L3 (Niedrig): `sa_refine.py` Z.199 – SA-Hauptschleife ist zeitgesteuert, nicht iterationsgesteuert**
`while time.time() - t0 < time_limit:` macht das Ergebnis nicht deterministisch zwischen unterschiedlich schnellen Maschinen. Bei gleichem Seed läuft eine schnelle Maschine länger und kann andere Lösungen finden.
Akzeptabler Trade-off (Zeitbudget ist intuitiver für den Nutzer als Iterationszahl), aber dokumentieren als bekannte Einschränkung.
Fix: Im Docstring der `refine_schedule()` ergänzen: "Reproduzierbarkeit nur bei gleicher Maschine; Iterationsanzahl variiert mit CPU-Geschwindigkeit."

**A-L4 (Niedrig): `league_types.py` Z.58, Z.64 – Vestigial Fallbacks in `n_matchdays`**
```python
return total_matches // games_per_day if games_per_day > 0 else self.n_rounds * (n - 1) // gpd
```
`games_per_day` ist `n_active * gpd // 2` (oder `G * K * gpd // 2`). Mit `gpd >= 1` und `n_active >= 2` bzw. `K >= 1, G >= 1` ist `games_per_day >= 1`. Der Fallback ist nur bei degenerierten Fällen erreichbar (n_active < 2, K=1+gpd=1).
Fix: Fallbacks entfernen, da unerreichbar. Oder mit `ValueError` ersetzen, damit degenerierte Konfigurationen früh auffallen.

**A-L5 (Niedrig): `multi_solver.py` – `_phase1_worker`-Logging zeigt keinen Seed-Identifier**
Bei `n_seeds > 1` und parallelem Lauf produzieren mehrere Worker `[BEST] cfg.league_id obj=...`-Zeilen, die nicht unterscheidbar sind. Beim Debug ist unklar, welcher Seed welche Lösung gefunden hat.
Fix: `_ProgressCallback`-Konstruktor um `seed` erweitern oder Liga-ID um Seed ergänzen: `f'[BEST] {lid}#s{seed} obj=...'`.

**Status:** Erledigt (v1.3.0-rc1, v1.3.0, v1.3.1, v1.4.1) – alle A-Befunde behoben. Wichtige Erkenntnis aus dem A-H2-Fix: SA überspringt DST-Tage komplett, daher ist `dst_eff_total` während SA konstant — der Fix ergänzt den Term im `_objective` nur für Wert-Konsistenz zum Phase-2-Objective.

---

### [intern] Code-Review Runde 6 – Block B: Datenmodell & Eingabe-Validierung

**Typ:** Verbesserung / Fehler
**Bereich:** Spielplan-Optimierung / Validierung
**Wichtigkeit:** Mittel (B-M1 … B-M3) / Kleiner Wunsch (B-L1 … B-L8)
**Aufwand:** Klein
**Beschreibung:**

Reviewed: `league_types.py`, `config.py`, `config_validator.py` (validate + validate_cfgs), `calendar_parser.py`, `distances.py`. Validator ist nach Runde 5 bereits sehr umfassend; gefundene Lücken sind primär Validierungs-Korner-Cases und Robustheit. Kein Hoch-Bug.

**B-M1 (Mittel): `config_validator.py` validate() + validate_cfgs() – Pflichtspiel-Heimrecht + Sperrtag-Konflikt nicht erkannt**
Wenn ein Pflichtspiel `(A vs. B, day 5, home=A)` gesetzt ist UND `blocked[A] = [5]`, prüft der Validator das nicht. Solver setzt `h[m]=0` (A=Heim) und `home[A, 5]=0` (Sperrtag → keine Override durch forced_home, da nicht in forced_home) → INFEASIBLE mit kryptischer Meldung.
Bestehender Check deckt nur `forced_home + pinned-Auswärts`-Konflikt ab (Z.192-205), aber nicht `pinned-home + blocked`.
Fix: In beiden Validatoren nach dem `pinned`-Loop einen zusätzlichen Check ergänzen:
```python
for pm in pins:
    if pm.get('home') and pm.get('day'):
        team = pm['home']
        d = int(pm['day'])
        if d in set(blk.get(team, [])):
            err(lid, f'**{name}**: Pflichtspiel ST{d} – Team «{team}» hat Heimrecht, '
                      f'aber ST{d} ist gleichzeitig Sperrtag → unlösbar.')
```

**B-M2 (Mittel): `config_validator.py` – Doppelte Pflichtspiel-Paarung im selben Round bei n_rounds≥2 nicht erkannt**
Der bestehende Check für „doppelte Paarung" prüft nur n_rounds=1 (Z.131-141). Bei n_rounds=2 mit z.B. Pflichtspiel `(A, B, day 3, home=A)` UND `(A, B, day 5, home=B)`: beide fallen in dieselbe Round 1 (round_len=N/2), Solver setzt `x[m, 3]=1` UND `x[m, 5]=1`, aber `sum_d x[m, d] == 1` → INFEASIBLE.
Pinning auf Tag in Round 1 + Tag in Round 2 ist dagegen legitim (verschiedene Match-Indizes).
Fix: Pro Pair die Tage gruppieren und prüfen, dass nicht zwei Tage in derselben Round liegen:
```python
round_len = max(1, n_md // n_rounds)
pin_pairs: dict = {}  # pair -> set of rounds
for pm in pins:
    if not (pm.get('teamA') and pm.get('teamB') and pm.get('day')):
        continue
    pair = frozenset([pm['teamA'], pm['teamB']])
    round_num = min(n_rounds, (int(pm['day']) - 1) // round_len + 1)
    pin_pairs.setdefault(pair, []).append(round_num)
for pair, rounds in pin_pairs.items():
    if len(rounds) != len(set(rounds)):
        err(lid, f'**{name}**: Paarung {sorted(pair)} mehrfach im selben Round gepinnt → unlösbar.')
```

**B-M3 (Mittel): `config_validator.py` validate() – `forced_home`-Teamnamen werden nicht gegen Teamliste geprüft**
Sperrtag-Loop (Z.77-89) prüft `if team not in _teams_set` und warnt. Pflichtspiel-Loop (Z.94-97) prüft analog. Aber forced_home-Loop (Z.169 ff.) prüft nicht. Unbekannte Teamnamen in forced_home werden vom Solver still ignoriert (t_idx.get → None → continue) — gleicher Inkonsistenz-Pattern wie der in Runde 5 (B1-M1) gefixte Sperrtag-Check.
Fix: In validate() vor `frc_set = set(fdays)` ergänzen: `if team not in _teams_set: warn(lid, ...); continue`. Analog in validate_cfgs() Z.332.

**B-L1 (Niedrig): `config_validator.py` – Sperrtag-Tage außerhalb gültiger Range werden nicht gewarnt**
Pflichtheim-Validierung hat `invalid = frc_set - days` mit Fehler bei Tagen außerhalb 1..N (Z.179-183). Sperrtag-Validierung hat das nicht: gibt ein Nutzer Tag 999 als Sperrtag ein, wird das stillschweigend im Solver gefiltert (Z.226-227 in solver.py). Keine Rückmeldung an den Nutzer, dass die Eingabe ignoriert wird.
Fix: Analog zu forced_home: `invalid_blk = set(bdays) - days; if invalid_blk: warn(lid, ...)`.

**B-L2 (Niedrig): `calendar_parser.py` `_parse_cell` – akzeptiert DST-Block mit identischen Tagen**
Regex `(\d+)\s*[-/&]\s*(\d+)` matcht `"5/5"` → returns `[5, 5]`. Dann erzeugt `parse_rahmenterminplan` einen DST-Block (5, 5). Im Solver wird `model.Add(home[ti, 5] == home[ti, 5])` zur trivialen Constraint. Kein Fehler, aber unnötige Constraint und verwirrendes Modell.
Fix: In `_parse_cell` nach dem Match `if d1 == d2: return [d1]` (Einzelspieltag, kein DST).

**B-L3 (Niedrig): `calendar_parser.py` – doppelter Spieltag in zwei verschiedenen KWs überschreibt still**
Wenn z.B. Zeile 5 ST 3 in KW 10 hat und Zeile 8 ST 3 in KW 15 (Eingabefehler), überschreibt der zweite Eintrag den ersten in `spieltage[lid][3]`. Keine Warnung. Im DST-Loop wird nur (3, X) bei der ersten Sichtung in `dst_blocks` eingefügt — eine zweite (3, Y)-Sichtung würde nicht angehängt.
Fix: In `parse_rahmenterminplan` Z.186 prüfen `if st in spieltage[lid] and spieltage[lid][st]['kw'] != kw: warn(...)`.

**B-L4 (Niedrig): `config_validator.py` – validate() und validate_cfgs() duplizieren ca. 80% der Logik**
Beide Funktionen implementieren denselben Validierungssatz, einmal für Wizard-Daten (dicts), einmal für LeagueConfig-Objekte. Maintenance-Burden: Runde 5 hat Lücken in einer Variante geschlossen, aber die andere nicht überall mitgezogen (z.B. Pflichtheim-Teamnamen, siehe B-M3).
Fix (langfristig): Gemeinsame interne Hilfsfunktion `_validate_common(name, teams, n_md, dst, blk, pins, forced, dist, ...)` extrahieren, beide Public-Funktionen rufen sie auf. Nicht in dieser Review-Runde, aber als Refactoring-Aufgabe vormerken.

**B-L5 (Niedrig): `config_validator.py` – `np.isnan(int_array)` numpy-Versions-Abhängigkeit**
Z.64 und Z.282: `np.isnan(cfg.dist).any()` — auf int-Arrays raisert numpy 1.24+ `TypeError`, in älteren numpy 1.x kommen `False`-Werte zurück. Da `distances.py` immer int-Arrays produziert (`dtype=int`), funktioniert die Prüfung de facto nicht — sie zielt aber auf den Fall, dass das Streamlit-`data_editor` einen float-Array mit NaN liefert (was es tatsächlich tut, siehe app.py Excel-Import-Bug aus Mai 2026).
Robuster Fix:
```python
try:
    has_nan = bool(np.isnan(mat).any())
except TypeError:
    has_nan = False  # int-Array kann keine NaN enthalten
```

**B-L6 (Niedrig): `league_types.py` `n_games_per_day` ignoriert `n_active_per_day`**
```python
@property
def n_games_per_day(self):
    return len(self.teams) * max(1, self.games_per_team_per_day) // 2
```
Für K=0 (Stufe 1) + `n_active_per_day > 0` (Spielfrei-Modus): die Property liefert `n*gpd/2`, aber tatsächlich sollten nur `n_active*gpd/2` Spiele pro Tag stattfinden. Aktuell vom UI nicht zugänglich (Spielfrei-Modus nur für K>0 oder via `needs_bye`), aber latent inkonsistent zu `n_matchdays`, das `n_active` korrekt berücksichtigt.
Fix: Property auf `n_active`-aware umstellen:
```python
@property
def n_games_per_day(self):
    n_active = self.n_active_per_day if self.n_active_per_day > 0 else len(self.teams)
    return n_active * max(1, self.games_per_team_per_day) // 2
```

**B-L7 (Niedrig): `config_validator.py` – Pflichtspiele in Anzahl > total_games nicht als Fehler erkannt**
Validator warnt bei `len(pins) > total_games * 0.4`. Aber bei `len(pins) > total_games` (mehr Pins als möglich) erscheint nur die 40%-Warnung, kein expliziter Fehler. Beispiel: n=4, n_rounds=1: total_games=6. Bei 8 Pflichtspielen → kann nicht aufgehen, aber Validator zeigt nur die Warnung.
Fix: `if len(pins) > total_games: err(lid, f'**{name}**: {len(pins)} Pflichtspiele aber nur {total_games} Spiele in der Saison – nicht alle können stattfinden.')`.

**B-L8 (Niedrig): `distances.py` `load_distances_from_file` – Half-matching Headers fallen still durch zu Format 2**
Format-1-Erkennung: `if all(t.strip().lower() in col_names for t in teams)`. Wenn z.B. 7 von 8 Team-Namen im Header matchen (1 Tippfehler), wird `all()` False → Format 2 wird probiert. Format 2 erwartet von/nach/km – nicht vorhanden → finale „Dateiformat nicht erkannt"-Fehlermeldung. Nutzer erfährt nicht, dass nur ein Team gefehlt hat.
Fix: Falls `>=80% Teams im Header matchen` → spezifischere Warnung: „Format 1 erkannt, aber Team-Name(n) X, Y nicht in Header gefunden – bitte Spaltennamen prüfen.".

**Status:** Großteils erledigt – B-M1 + B-M2 + B-M3 in v1.3.0 gefixt; B-L1, B-L2, B-L3, B-L5, B-L6, B-L7, B-L8 in v1.4.1 gefixt; **B-L4 (Validator-Konsolidierung) als Refactor zurückgestellt** – größerer Umbau, nicht im Sprint 5 vorgesehen.

---

### [intern] Code-Review Runde 6 – Block C: Spielplan-Nachbearbeitung & Export

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** Spielplanverwaltung / Excel-Export
**Wichtigkeit:** Wichtig für Alltag (C-H1) / Mittel (C-M1 … C-M3) / Kleiner Wunsch (C-L1 … C-L5)
**Aufwand:** Klein-Mittel
**Beschreibung:**

Reviewed: `schedule_utils.py` (vollständig, alle Mutationsfunktionen + iCal + HTML), `excel_output.py` (build_league_excel, build_cohome_summary, build_hall_schedule, build_overview_excel).

**C-H1 (Hoch): `schedule_utils.py swap_home_away` korrumpiert State bei DST-Tagen**
Der DST-Constraint im Solver erzwingt `home[ti, d1] == home[ti, d2]` für ALLE Teams. Daraus folgt: die Spielpaare auf d1 und d2 sind verschieden (z.B. `(A,B)` auf d1 und `(A,X)` auf d2). Wenn der Nutzer `swap_home_away(day=d1, match=(A,B))` aufruft, geschieht:
- d1: (A,B) → (B,A) ✓
- home_vals[(A, d1)] = 0, home_vals[(B, d1)] = 1 ✓
- home_vals[(A, d2)] = 0, home_vals[(B, d2)] = 1 ← **bug**: B spielt auf d2 nicht (anderer Match), wird aber als „home" markiert
- schedule auf d2: wird nur geswapped wenn `{ht, at} == {A, B}` — bei DST mit unterschiedlichen Paaren wird (A, X) NICHT auf (X, A) umgedreht → **schedule bleibt inkonsistent zu home_vals** (Spielplan sagt A=Heim, home_vals sagt A=Auswärts)

Die `if {pht, pat} == {ht, at}`-Bedingung trifft in der Praxis nie zu, weil verschiedene DST-Tage immer verschiedene Paarungen haben (Phase-Trennung im Solver).

SA in `sa_refine.py` umgeht den Bug korrekt: `if hd in dst_days or rd in dst_days: continue`. Das UI muss prüfen, ob es Manual-Swap an DST-Tagen erlaubt — wenn ja, ist der Bug aktiv.

Fix-Optionen:
1. **Konservativ:** Refusen: `if day in cfg.dst_days: return 'Manueller Tausch an DST-Tagen nicht unterstützt.'` — analog zum `gpd > 1`-Guard.
2. **Vollständig:** DST-Partner-Tag korrekt mitspiegeln — bei (A, X) auf d2 auch `(X, A)` setzen und X's home_val anpassen. Komplexer.

Empfehlung: Option 1 in dieser Runde, Option 2 als Backlog-Feature.

**C-M1 (Mittel): `schedule_utils.py cancel_game / reschedule_game` fehlen Turniertag-Guards**
`swap_home_away` (Z.84) und `move_game` (Z.181) haben `if cfg.games_per_team_per_day > 1: return ...`-Guards (CR4-U2, CR4-U3). Bei `cancel_game` (Z.221) und `reschedule_game` (Z.245) fehlen sie. `recompute_result_stats()` setzt nach beiden für Turniertag falsche `travels` (Transitions-Modell von Standort → Standort, aber Turniertag-`travels` sind im Solver immer 0).
Fix: Analog zu move_game und swap_home_away beide Funktionen mit `if cfg.games_per_team_per_day > 1: return ...` schützen.

**C-M2 (Mittel): `schedule_utils.py recompute_result_stats` sw_rates inkonsistent zum Solver**
- Solver: `sw_rate = sw_count / cfg.n_transitions * 100` (Z.661 in solver.py), wobei `n_transitions = n_matchdays - 1`.
- recompute: `sw_rate = sw_count / (len(weekends) - 1) * 100` (Z.78).

Beide Denominatoren sind nur gleich, wenn keine DST-Blöcke existieren. Bei DST verkleinern Blöcke `len(weekends)`, also wird der Denominator kleiner → recompute zeigt höhere Wechselquoten als der Solver direkt.

Folge: Nach manuellen Spielplan-Änderungen springen die Wechselquoten plötzlich, ohne dass sich der schedule tatsächlich relevant geändert hat — verwirrend für den Nutzer.
Fix: In recompute_result_stats `n_transitions = cfg.n_matchdays - 1` als Denominator verwenden (konsistent zum Solver):
```python
n_tr = max(1, cfg.n_matchdays - 1)
sw_rates = [round(100.0 * sw / n_tr, 1) for sw in sw_counts]
```

**C-M3 (Mittel): `schedule_utils.py build_print_html` km-Spalte zeigt Einzel-Fahrten, nicht Transitions**
Z.557: `km_val = int(cfg.dist[ti, oi]) if not is_home and 0 <= oi < n else 0`. Das ist die Direktdistanz vom Heimort zum Gegner — entspricht dem v1.2.4→v1.2.5 gefixten Einzel-Fahrten-Bug, hier aber im HTML-Druck.

Folge: Summe der per-Spiel-km im Druck-HTML weicht systematisch von `result.travels[ti]` (Header-Statistik) ab — besonders bei aufeinanderfolgenden Auswärtsspielen.

Fix: Entweder „Einzel-Fahrt"-Anzeige beibehalten und im Header klarstellen, dass dies nicht die Gesamtreise ist, ODER per-Tag-Transition-km berechnen (`dist[loc[d], loc[d+1]]`) und im HTML zeigen. Pragmatisch: Spaltenbezeichnung in „Direkt-km" umbenennen und Hinweis ergänzen.

**C-L1 (Niedrig): `schedule_utils.py cancel_game` keine DST-Konsistenz-Bereinigung**
Wenn ein Spiel auf einem DST-Tag (d1) gecancelt wird, bleibt der DST-Partner-Tag (d2) potenziell mit alten Heim-/Auswärts-Zuteilungen, die nicht mehr zum geänderten d1 passen. Ähnlich zu C-H1, aber weniger schwerwiegend (kein Schreibzugriff, nur Inkonsistenz).
Fix: Nach cancel ggf. Warnung „DST-Partner-Tag möglicherweise nicht mehr konsistent — prüfen."

**C-L2 (Niedrig): `schedule_utils.py build_ics_bytes` Skip-Warning fehlt**
Spiele ohne Kalendereintrag werden mit `continue` aus dem iCal ausgeschlossen (Z.353-354). Wenn 30% der Spiele kein Datum haben, fehlen 30% der Events — keine Warnung an den Nutzer.
Fix: Counter mitführen und am Ende `if skipped > 0: warn(f'{skipped} Spiele ohne Kalenderdatum nicht im iCal enthalten.')`.

**C-L3 (Niedrig): `excel_output.py build_overview_excel _parse_date` fängt `Exception` zu breit**
Z.1001-1013: `except Exception: pass` schluckt alle Fehler, auch unerwartete (z.B. AttributeError bei nicht-string Input). Bessere Praxis: explizit `(ValueError, TypeError, IndexError)`.

**C-L4 (Niedrig): `excel_output.py build_hall_schedule` Magic-Number 999 als KW-Fallback**
Z.882: nicht-numerische KWs werden mit 999 sortiert, landen am Ende. Hardcoded Magic-Number — sollte als Modul-Konstante `_UNKNOWN_KW_SORT_KEY = 999` benannt oder mit `float('inf')` ersetzt werden.

**C-L5 (Niedrig): `excel_output.py build_overview_excel` Co-Home: stilles Skipping bei nur 1 aktiver Liga**
Z.1061: `if len(entries) < 2: continue`. Wenn ein Verein in 3 Ligen konfiguriert ist, aber nur 1 Liga ein gültiges Result hat, wird ohne Hinweis übersprungen. Auch bei 2 valid + 1 ohne Result wird Co-Home angezeigt, aber ohne Erklärung warum die dritte Liga fehlt.
Fix: Am Ende des Loops einen Hinweis ausgeben, wenn Vereine wegen fehlender Liga-Results übersprungen wurden.

**Status:** Erledigt – C-M1 + C-M2 in v1.3.0-rc1, C-H1 in v1.3.0, C-M3 + C-L1 … C-L5 in v1.4.1 gefixt.

---

### [intern] Code-Review Runde 6 – Block D: UI Wizard-Schritte 0-7

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** Streamlit-UI / Wizard
**Wichtigkeit:** Mittel (D-M1 … D-M4) / Kleiner Wunsch (D-L1 … D-L7)
**Aufwand:** Klein-Mittel
**Beschreibung:**

Reviewed: `app.py` Zeilen 1-3505 (Helpers, `_step0` bis `_step7`, `_session_to_json` / `_session_from_json`, `_build_league_configs`, `_validate_constraints`, `_QueueWriter`). `_worker.py` bereits in Runde 5 reviewed.

**D-M1 (Mittel): `_step0` Liga-Entfernung lässt verwaiste State-Einträge zurück**
Bei Reduktion der Liga-Anzahl (`while len(S.league_order) > n`) werden `S.dist_matrices`, `S.dst_per_liga`, `S.routing`, `S.weights`, `S.pinned`, `S.blocked`, `S.forced_home`, `S.clubs` per Liga aufgeräumt (Z.1489-1493). NICHT aufgeräumt:
- `S.cal_table[lid]` (Kalender-Tabelle der Liga)
- `S.time_templates[lid]` (Uhrzeiten-Vorlage)
- `S.opt_best[lid]` (bestes Solver-Ergebnis)
- Widget-Keys: `lid_{i}`, `lnm_{i}`, `fmt_{i}`, `hw_{i}`, `_exp_{lid}`, `cal_editor_{lid}`, …

Folge: Wenn eine Liga gelöscht und mit derselben ID neu angelegt wird, erbt sie alten Kalender/Zeit-Status. Auch beim Excel-Export wird der alte Kalender wieder mit ausgegeben.
Fix: Im `while`-Loop Z.1486 zusätzlich `S.cal_table.pop(_removed, None)`, `S.time_templates.pop(_removed, None)`, `S.opt_best.pop(_removed, None)`.

**D-M2 (Mittel): `_step0` Liga-Rename überträgt `cal_table` nicht zur neuen Liga-ID**
Bei Rename (Z.1921 ff.) werden 7 State-Dicts korrekt übertragen, aber `S.cal_table[lid]` bleibt unter alter ID liegen → Kalender ist nach Rename "weg". Analog `time_templates`, `opt_best`, `team_verein_map`-Einträge.
Fix: `S.cal_table`-Loop in den Übertragungs-Block ergänzen, plus die anderen oben genannten Dicts.

**D-M3 (Mittel): `_full_config_excel_bytes` exportiert `host_slots` nicht — Round-Trip-Verlust für Turniertag**
Sheet „TT-Spielreihenfolge" exportiert `host_position` (J/N), `min_gap`, `max_gap`, `host_mode`, `host_counts`, `host_per_day` (Z.1014-1022). Das neue Feld `host_slots` (Liste von Slot-Positionen, ersetzt seit v1.1.x das alte `host_position`) ist NICHT dabei.

Folge: User konfiguriert „Ausrichter-Spiel 1 in Position 3, Spiel 2 in Position 6" → Export → Re-Import: `host_slots = []`. Stattdessen wird aus `host_position=J` der Fallback `[2, N-1]` rekonstruiert (Z.1687-1688), was nicht den ursprünglichen Wert ist.
Fix: In Sheet-Header `Ausrichter-Slots (JSON)` ergänzen, beim Export `_json.dumps(_tt.get('host_slots', []))`. Beim Import in `_load_full_config_excel` analoge Parse-Logik ergänzen.

**D-M4 (Mittel): `_step1` manueller Distanzmatrix-Editor kann NaN-Werte in `S.dist_matrices` schreiben**
Z.1997-2010: `st.data_editor` mit leerer Zelle liefert NaN. Die Spiegel-Logik `if mat2[r, c] > 0` behandelt NaN nicht (`NaN > 0` ist False). `np.fill_diagonal(mat2, 0)` setzt nur die Diagonale. Off-diagonale NaN bleiben.

`S.dist_matrices[lid] = mat2` mit NaN → `cfg.dist.astype(int)` in `solver.py:74` cast NaN auf garbage-Integer (`-9223372036854775808` in CPython). Validator warnt zwar (`np.isnan(...)`), aber wenn der Nutzer ignoriert, crasht oder verfälscht der Solver.

Fix: Nach `np.fill_diagonal(mat2, 0)` ein `mat2 = np.nan_to_num(mat2, nan=0.0)` oder explizit `if np.isnan(mat2).any(): st.error('...'); errors.append(lid)`.

**D-L1 (Niedrig): `_step0` Liga-ID-Rename eager**
Z.1921: `if new_lid and new_lid != lid and new_lid not in S.league_order:` triggert sofort bei jedem Focus-Out des Text-Inputs. User tippt „BL" und tabbt weg → wird umbenannt. Will dann „BL1" → muss erneut umbenennen.
Fix: Rename erst auf expliziten Button („Speichern" / Enter) statt auf Focus-Out.

**D-L2 (Niedrig): `_session_from_json` clears `de_{lid}` Editor-Cache nicht**
`_load_full_config_excel` macht `st.session_state.pop(f'de_{_lid}', None)` (Z.1365). `_session_from_json` macht das nicht — der Distanzmatrix-Editor zeigt nach JSON-Restore möglicherweise alte Werte aus dem Widget-Cache.
Fix: In `_session_from_json` nach `S.dist_matrices = ...` analog `st.session_state.pop(f'de_{lid}', None)` für jede geladene Liga.

**D-L3 (Niedrig): `_session_from_json` überschreibt `S.solver` ohne Merge**
Z.3249-3250: `S.solver = cfg_data['solver']`. Alte JSON-Dateien können `sa` oder `nm` fehlen → solver-Dict unvollständig → spätere `S.solver.get('sa', 120)`-Aufrufe greifen auf Default zurück, aber `S.solver['sa'] = …`-Zuweisungen würden neu definieren ohne Konsistenz.
Fix: `S.solver = {**S.solver, **cfg_data['solver']}` (Merge mit Defaults aus `_DEFAULTS`).

**D-L4 (Niedrig): `_step2` Calendar-Import überschreibt manuelle Datumswerte ohne Warnung**
Im Schritt 2 kann der Nutzer manuell Datumswerte in die Kalender-Tabelle eingeben. „Kalender laden" mit der Excel-Datei ruft `_apply_weekend_dates()` auf, das alle date-Felder neu setzt. Manuell eingetragene Termine sind verloren ohne Hinweis.
Fix: Vor `_apply_weekend_dates()` prüfen ob manuelle Werte existieren und ggf. Konfirmation einholen, oder manuelle Werte überschreiben verbieten.

**D-L5 (Niedrig): `_session_to_json` exportiert `team_verein_map` nicht**
Die Map `{teamname: verein}` wird beim Hinzufügen von Teams aus der DB befüllt und ist relevant für Co-Home-Auto-Detection. Beim JSON-Restore fehlt sie → Auto-Detection greift nur auf die DB zurück, manuelle DB-Treffer sind verloren.
Excel-Import rekonstruiert die Map aus der DB (Z.1412-1423). JSON-Restore tut das nicht.
Fix: In `_session_to_json` `'team_verein_map': S.team_verein_map` ergänzen, in `_session_from_json` zurücklesen oder analog aus DB rekonstruieren.

**D-L6 (Niedrig): `_step1` Google-Maps stdout-Capture nicht thread-safe**
Z.2057-2067: `sys.stdout = _buf` setzt stdout PROZESSWEIT für die Dauer der API-Abfrage. Während Schritt 1 normalerweise keine Solver-Threads laufen, ist der globale Side-Effect riskant — z.B. wenn parallel ein anderer Tab/Worker Streamlit-Aktionen auslöst.
Fix: `contextlib.redirect_stdout(_buf)` als context-manager nutzen — funktional äquivalent, aber explizit Scope-begrenzt. Oder besser: `calculate_distance_matrix` so anpassen, dass es einen Logger statt stdout nutzt.

**D-L7 (Niedrig): `_session_from_json` setzt `S.opt_done=True` auch wenn `excel_bytes` leer**
Z.3340-3342: `except Exception: pass` schluckt Excel-Build-Fehler still. Z.3371: `S.opt_done = True`. Der Nutzer landet in Step 8 mit `opt_done=True`, aber Excel-Download-Buttons funktionieren nicht (kein `excel_bytes`).
Fix: Mindestens warnen wenn `len(S.excel_bytes) < len(S.results)`, oder Re-Generate-Button anbieten.

**Status:** Erledigt – D-M4 in v1.3.0, D-M1/M2/M3 in v1.3.1, D-L2 … D-L7 in v1.4.1 gefixt, D-L1 in v1.6.2 (st.form mit Enter-Submit oder „Übernehmen"-Button, Live-Validation-Caption + Toast).

---

### [intern] Code-Review Runde 6 – Block E: UI Ergebnisansicht & Aktionen (Schritt 8)

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** Streamlit-UI / Result-View
**Wichtigkeit:** Mittel (E-M1 … E-M3) / Kleiner Wunsch (E-L1 … E-L7)
**Aufwand:** Klein
**Beschreibung:**

Reviewed: `app.py` Zeilen 3506-4939 — `_step8`, `_show_results`, `_diagnose_infeasible_league`, `_result_fname_suffix`, alle Mutation-Bindings (`_swap_home_away`, `_move_game`, `_cancel_game`, `_reschedule_game`, `_assign_game_times`), Vergleich-Funktion, `_step_intro`, Sub-Process-Start, Recovery-Pickle-Flow.

**E-M1 (Mittel): `_show_results` Spielplan-Tabelle zeigt keine Uhrzeit-Spalte**
Z.4250-4257: die Spielplan-Tabelle für jede Liga (`pd.DataFrame`, im Expander) enthält nur ST/Phase/Typ/Heim/Gast. Excel-Export und HTML-Druck zeigen Uhrzeit, die UI-Tabelle nicht — Inkonsistenz nach Spielzeit-Zuweisung. User sieht den Effekt der Spielzeit-Zuweisung nur im Excel, nicht im Streamlit-Browser.
Fix: Wenn `res.game_times` befüllt ist, Spalte `Uhrzeit` ergänzen: `'Uhrzeit': res.game_times.get(d, [''])[game_idx]`.

**E-M2 (Mittel): `_diagnose_infeasible_league` läuft Regex über volle `opt_log` pro Render**
Z.4002-4010: `for ln in _log_lines` mit `re.search(_lid_pat, ln)` für jede Liga. Bei langem 8h-Lauf-Log (~50.000 Zeilen) und 4 Liga(s) ohne Lösung: 200k Regex-Calls pro Streamlit-Rerun. Spürbare UI-Latenz im Failure-Case.
Fix: Diagnose-Ergebnis in `S` cachen (`S._diagnose_cache[lid]`), nur neu berechnen wenn opt_log gewachsen.

**E-M3 (Mittel): `_regen_league_excel` lässt `S.overview_bytes` stale bei Fehler**
Z.3982-3988: `except Exception: pass` schluckt Overview-Build-Fehler. Wenn `S.overview_bytes` aus früherem Lauf gesetzt war, bleibt es unverändert → User lädt veraltete Gesamtübersicht herunter, die nicht zum aktuellen `S.results` passt.
Fix: Vor dem try-Block `S.overview_bytes = None`, dann erst bei Erfolg neu setzen. Oder im Fehlerfall Warnung in `S.opt_warnings` anhängen.

**E-L1 (Niedrig): Cancel-/Move-Aktion warnt nicht bei DST-Tag-Bezug**
Z.4633-4658: Move-Button (📅) und Cancel-Button (❌) für ein Spiel. Wenn der Spieltag Teil eines DST-Blocks ist, hat der Partner-Tag im CP-SAT-Modell eine DST-Invariante (gleiches Heimrecht). Nach Move/Cancel ist diese Invariante gebrochen — keine Warnung an den Nutzer.
Bei Swap (Z.4473-4480) gibt es bereits einen DST-Hinweis. Bei Move/Cancel fehlt analog.
Fix: Wenn `_sel_day_mv in _cfg_mv.dst_days`: `st.info('Hinweis: DST-Tag – Partner-Tag bleibt unverändert, DST-Konsistenz wird ggf. gebrochen.')`.
**Verwandt:** C-L1 (`cancel_game` keine DST-Bereinigung).

**E-L2 (Niedrig): Optimierungs-Poll `time.sleep(2)` → bis 2s Latenz zum Anzeigen des Endes**
Z.3770-3771: nach jedem Queue-Lese-Loop wird 2s geschlafen, dann `st.rerun()`. Wenn `__DONE__` 0,5s nach letztem Polling kommt, sieht der User erst 1,5s später das Ergebnis.
Fix: `time.sleep(0.5)` oder `time.sleep(1)` als Kompromiss zwischen Latenz und Server-Last.

**E-L3 (Niedrig): `_step8` Solver-Start ohne try/except für `proc.start()`**
Z.3919-3926: `multiprocessing.Process(...).start()` kann bei Pickle-Fehlern (z.B. unerwartet nicht-picklebares Objekt in `S.solver`) eine Exception werfen. Kein try/except → Streamlit zeigt rohen Stack-Trace.
Fix: `try: proc.start() except Exception as exc: st.error(f'Optimierung konnte nicht gestartet werden: {exc}'); return`.

**E-L4 (Niedrig): iCal Saison-Startjahr Default ist hardcoded 2026**
Z.4328-4334: `st.number_input(..., 2020, 2035, 2026, ...)`. In drei Jahren ist 2026 nicht mehr der natürliche Default für eine neue Saison.
Fix: `datetime.now().year` als Default verwenden (mit Heuristik: wenn aktueller Monat > 7 → aktuelles Jahr, sonst Vorjahr).

**E-L5 (Niedrig): Phase-Label in UI-Spielplan-Tabelle für n_rounds=3 inkonsistent**
Z.4247: `phase_lbl = {1: 'Hin', 2: 'Rue'} if n_rounds == 2 else {}`. Für Dreifachrunde (n_rounds=3) fällt der Code auf Default `f'R{rnd}'` zurück → Anzeige „R1/R2/R3". Excel und HTML zeigen für n_rounds=3 dagegen „Hinrunde/Rueckrunde/Dritte Runde".
Fix: `phase_lbl = {1: 'Hin', 2: 'Rück', 3: 'Dritte'}` ohne `if n_rounds == 2`-Bedingung.

**E-L6 (Niedrig): `_show_results` zeigt `[FEHLER]`-Zeilen als `st.warning` statt `st.error`**
Z.4141-4142: alle `S.opt_warnings` werden mit `st.warning(_w)` ausgegeben — auch Fehlerzeilen (CR4-A3 fügte `[FEHLER]` der opt_warnings-Liste hinzu, aber als Warnung dargestellt).
Fix: Beim Befüllen Severity merken (`{'level':'error|warn', 'msg': ...}`) und im Display `st.error()` vs `st.warning()` unterscheiden.

**E-L7 (Niedrig): „Spielzeiten automatisch zuweisen" rebuildet alle Liga-Excel auch bei unveränderten Templates**
Z.4396-4412: `for _tl in _time_lids` → `if _slots: ...` → Excel neu bauen. Wenn nur 1 von 4 Ligen geänderte Slots hat, werden trotzdem alle 4 Excels neu gebaut.
Fix: Vor dem `_assign_game_times_fn` prüfen ob `_slots != res.game_times.get(d, [])` (oder vergleichbarer Identitäts-Check) und nur dann regenerieren.

**Status:** Erledigt – E-M3 in v1.3.1, E-M1 + E-M2 + E-L1 … E-L7 in v1.4.1 gefixt.

---

### [intern] Code-Review Runde 6 – Block F: Distribution & Lifecycle

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** Distribution / Launcher / Installer / CI
**Wichtigkeit:** Mittel (F-M1, F-M2) / Kleiner Wunsch (F-L1 … F-L8)
**Aufwand:** Klein-Mittel
**Beschreibung:**

Reviewed: `launcher.py`, `build_release.py`, `installer/spielplan.iss`, `installer/build_bootstrap.bat`, `.github/workflows/release.yml`, `VERSION`. `_worker.py` bereits in Runde 5 reviewed.

**F-M1 (Mittel): `launcher.py _apply_update` ist nicht atomar — Partial-Update-State möglich**
Z.105-115: `for root, dirs, files in os.walk(tmp_extract): ... shutil.move(src, dst)`. Wenn der Loop in der Mitte fehlschlägt (z.B. Datei durch laufenden Prozess gesperrt), sind einige Dateien aktualisiert, andere nicht. `VERSION_FILE` wird zwar erst NACH dem Loop geschrieben — d.h. der Launcher würde beim nächsten Start das Update erneut anbieten — aber zwischen den Versuchen ist die App in einem inkonsistenten Zustand (neuer `app.py` aber alter `solver.py`, oder umgekehrt).

Es gibt auch keine Backup-Möglichkeit für Rollback.
Fix: Vor dem Move alle alten App-Dateien (außer `python/`, `VERSION`, `Spielplaene/`) nach `BASE_DIR/.backup_v{old}/` umbenennen. Wenn Move-Loop erfolgreich: `.backup_v{old}` löschen. Bei Fehler: `.backup_v{old}` → BASE_DIR rückbewegen.

**F-M2 (Mittel): `release.yml` validiert nicht, dass Git-Tag mit VERSION-Datei übereinstimmt**
Bei `git tag v1.2.10 && git push --tags` würde die Action laufen, app-files.zip mit dem aktuellen VERSION-Inhalt (z.B. 1.2.9) bauen, und einen Release v1.2.10 anlegen. Folge: nach Install zeigt der Launcher `latest_tag=1.2.10 > local=1.2.9` → Endlos-Update-Loop, weil das eben installierte ZIP weiterhin "1.2.9" enthält.
Fix: In `release.yml` einen Step vor `build_release.py` ergänzen:
```yaml
- name: Versionsprüfung
  run: |
    TAG_VERSION="${GITHUB_REF_NAME#v}"
    FILE_VERSION=$(cat VERSION | tr -d '[:space:]')
    if [ "$TAG_VERSION" != "$FILE_VERSION" ]; then
      echo "Tag-Version $TAG_VERSION != VERSION-Datei $FILE_VERSION"; exit 1;
    fi
```

**F-L1 (Niedrig): `launcher.py _parse_version` versagt bei non-numeric Tags**
Z.45-50: `int(x) for x in v.split(".")`. Für Pre-Release-Tags wie `v1.3.0-beta` oder `v1.3.0.rc1` schlägt `int("0-beta")` fehl → return `(0,)` → kein Update angeboten. Aktuell werden nur saubere `vX.Y.Z`-Tags genutzt, also latent.
Fix: Pre-Release-Suffix abtrennen vor Parse: `v.split("-")[0].split(".")` oder `packaging.version.Version` (extra-dep) nutzen.

**F-L2 (Niedrig): `launcher.py _check_update` 5s-Timeout blockiert Start auf langsamen Verbindungen**
Z.67: `urllib.request.urlopen(req, timeout=5)`. User mit schwacher Verbindung wartet bis 5s bevor die App startet, ohne Feedback.
Fix: Update-Check in Background-Thread auslagern, App startet sofort, Dialog erscheint später wenn Update gefunden wurde.

**F-L3 (Niedrig): `[UninstallDelete] Name: {app}` löscht Spielpläne**
`spielplan.iss` Z.54-57: löscht `{app}` komplett. `InitializeUninstall` warnt zwar und bietet Abbruch — gute Mitigation. Trotzdem: könnte vergessen werden bei automatisierter Deinstallation.
Fix: Spielplaene/ explizit aus `[UninstallDelete]` ausnehmen (Inno Setup `Excludes:`-Klausel).

**F-L4 (Niedrig): `spielplan.iss` MyAppVersion-Default „1.1.0" stale**
Z.6: `#define MyAppVersion "1.1.0"`. Wenn `iscc.exe` direkt (ohne `/DMyAppVersion=`) aufgerufen wird, erhalten Builds eine Version, die seit langem überholt ist (aktuell v1.2.9). Nur Build-Path-Risiko.
Fix: Default-Wert dynamisch aus VERSION-Datei lesen oder `1.2.9` als aktuellen Default setzen.

**F-L5 (Niedrig): `build_release.py` exit 0 auch bei leerem ZIP**
Wenn alle Dateien gefiltert werden (z.B. neue EXCLUDE-Regel zu breit), wird trotzdem ein leeres app-files.zip erstellt und der GitHub-Workflow gilt als erfolgreich. Resultat: kaputter Release.
Fix: `if count < 5: print('Zu wenige Dateien im Release-ZIP, vermutlich Filter-Bug.'); sys.exit(1)`.

**F-L6 (Niedrig): `build_bootstrap.bat` lädt Python-Embedded-ZIP ohne Checksum-Verifikation**
Z.58-62: `Invoke-WebRequest -Uri '%PYURL%' -OutFile '%BUILD%\%PYZIP%'`. Keine SHA256-Verifikation. Bei kompromittiertem python.org-TLS oder MITM könnte ein manipuliertes Python eingebunden werden. Niedriges Risiko, aber Build-Time-Concern.
Fix: SHA256 von `python-3.13.3-embed-amd64.zip` (auf python.org veröffentlicht) hardcoden und nach Download per `Get-FileHash` verifizieren.

**F-L7 (Niedrig): GitHub Actions ohne Commit-SHA-Pinning**
`release.yml` Z.16/19/27 nutzt Tag-Versionen (`@v4`, `@v5`, `@v2`). Tags sind mutable — ein gehackter Action-Owner könnte Code unter altem Tag publizieren. GitHub empfiehlt SHA-Pinning.
Fix: `uses: actions/checkout@<full-sha>` mit Kommentar `# v4`. Setzt regelmäßiges Update voraus (Dependabot).

**F-L8 (Niedrig): `release.yml` ohne Test-Gate**
Workflow läuft `build_release.py` und published. Keine Test-Ausführung. Defektes Coding-Standard-konformer Code könnte released werden.
Fix: Vor `build_release.py` einen `pytest` oder `python test_smoke.py`-Step ergänzen. Tests müssen vorher CI-fähig gemacht werden (siehe Block G).

**Status:** Erledigt – F-M2 in v1.3.1, F-L8 in v1.4.0, F-L1/L3/L4/L5/L6/L7 in v1.4.1, F-M1 + F-L2 in v1.6.1 (atomarer Update mit Rollback + Background-Update-Check).

---

### [intern] Code-Review Runde 6 – Block G: CLI-Wizard & Tests

**Typ:** Fehler/Bug + Verbesserung
**Bereich:** CLI-Wizard / Test-Coverage
**Wichtigkeit:** Mittel (G-M1 … G-M4) / Kleiner Wunsch (G-L1 … G-L6)
**Aufwand:** Klein-Mittel
**Beschreibung:**

Reviewed: `spielplan_multi/wizard.py`, `spielplan_multi/main.py`, `spielplan_multi/ui.py`, `spielplan_multi/__init__.py`, `spielplan_multi/__main__.py`, `test_all.py`, `test_smoke.py`, `test_distances.py`, `test_features.py` (Strukturanalyse).

**G-M1 (Mittel): CLI `step4_weights` Default für `dst_eff` ist 5.0, UI verwendet 0.0**
Z.573-575: `ask_float('Wichtigkeit (0-10)', 0, 10, default=5)` für ALLE Gewichte gleich, inkl. `dst_eff`. UI dagegen verwendet `_W_DEFAULTS = {'dst_eff': 0.0}` (app.py Z.2579).
Folge: CLI-Nutzer aktiviert ungewollt das `dst_eff`-Feature mit Default 5.0 — der Solver führt eine andere Optimierung durch als die UI mit Defaults. Bei kombinierten Workflows (Excel-Config aus CLI → UI laden) inkonsistent.
Fix: In `WEIGHT_LABELS` oder im step4_weights eine Default-Override-Map einführen, analog zu app.py `_W_DEFAULTS`.

**G-M2 (Mittel): Tests fehlen für `forced_home` (Pflichtheim-Feature)**
Pflichtheim (`cfg.forced_home`) wurde in v1.2.x eingeführt mit umfangreicher Logik (Sperrtag-Override, DST-Konflikt, Pflichtspiel-Konflikt). `test_all.py` hat keinen Test, der ein Pflichtheim-Setup testet. Bugs im forced_home-Pfad würden nicht von der Test-Suite gefangen.
Fix: In `test_all.py` zwei neue Tests ergänzen:
- `t_forced_home_respektiert`: Team hat forced_home=[3,5] → schedule hat home=1 an diesen Tagen.
- `t_forced_home_vs_blocked`: Konflikt erkannt (Validator returnt error).

**G-M3 (Mittel): Tests fehlen für `n_active_per_day > 0` (Spielfrei-Modus)**
Der Spielfrei-Modus für ungerade Teamzahl und explizites n_active wurde in v1.2.2 eingeführt mit komplexen Solver-Anpassungen (`needs_bye`, conditionalized sliding-window-Constraints, A-M1). Keine Tests.
Fix: Test mit 5 Teams (ungerade) + n_rounds=2 + gpd=1. Erwartung: solver liefert FEASIBLE, je Tag spielt 1 Team frei.

**G-M4 (Mittel): Tests fehlen für Mutation-Funktionen `move_game`, `cancel_game`, `reschedule_game`, `recompute_result_stats`**
`test_features.py` testet `swap_home_away` und `assign_game_times`. Die anderen Mutation-Funktionen sind ungetestet. Bug C-M1 (Turniertag-Guards in cancel/reschedule fehlend) wäre durch einen Test sofort erkennbar gewesen.
Fix: In `test_features.py` Tests ergänzen:
- `t_move_game_konsistent`: nach move_game stimmt Schedule und home_vals überein.
- `t_cancel_reschedule`: cancel + reschedule → identisch zu vorherigem Zustand.
- `t_recompute_after_move`: travels und sw_counts nach move passend zum neuen Schedule.
- `t_move_turniertag_geguarded`: gpd>1 → move_game returnt Fehler.

**G-L1 (Niedrig): `wizard.py _calc_n_matchdays` Index-basiert auf Tuples → fragil**
Z.36-52: `teams = ld[0]; gpd = ld[4] if len(ld) > 4 else 1; ...`. League-Defs sind Tuples mit positional Access. Beim Einfügen neuer Felder bricht das. Wäre als Dict oder dataclass robuster.
Fix: `step0_leagues` zu Dict/dataclass migrieren. Größerer Refactor.

**G-L2 (Niedrig): `wizard.py build_configs` 7/8-Tuple-Legacy-Support → Dead Code**
Z.862-872: drei `if len()`-Branches für 7/8/9-Tuple. `step0_leagues` returniert IMMER 9-Tuple. Die 7/8-Branches sind Dead Code für ältere Sessions, aber Sessions werden nicht gepickled — Dead Code.
Fix: Auf 9-Tuple vereinfachen.

**G-L3 (Niedrig): `wizard.py step3_routing` Format `(apply, f_num, f_den)` inkonsistent zur UI**
CLI: `(False, 125, 100)` — apply, faktor-num, faktor-denom.
UI: `(False, 25)` — apply, prozent (siehe app.py Z.2565, 3441).
Beide Wege konvertieren zu `f_num = 100 + pct`, aber das Tupel-Format der internen Repräsentation unterscheidet sich. Bei zukünftigem Refactor leicht zu übersehen.
Fix: Einheitliches `(apply, pct)`-Format in beiden Wegen, Konvertierung erst beim `LeagueConfig`-Build.

**G-L4 (Niedrig): `main.py` ruft `build_overview_excel` nicht auf — CLI fehlt Gesamtübersicht**
`main.py` Z.99-116 baut Liga-Excel, Co-Home-Excel, Hallenbelegungsplan. Aber nicht die neue Gesamtübersicht (v1.2.5). CLI-Nutzer erhalten den Output nicht.
Fix: In `main.py` analog zu `build_cohome_summary` einen Aufruf von `build_overview_excel` ergänzen.

**G-L5 (Niedrig): `test_smoke.py make_config` setzt `w_scaled=WEIGHT_SCALES` direkt (verwirrend)**
Z.44-45: `w_scaled=WEIGHT_SCALES, raw_weights=WEIGHT_SCALES`. WEIGHT_SCALES sind die Skalierungs-Faktoren (z.B. switch=80.0), nicht die Raw-Weights. Der Test funktioniert nur, weil im Solver `W = v * coef_scale * hier_weight` rechnet — durch die Verwendung der Skalierungs-Faktoren als "Raw"-Weights entstehen sehr hohe Werte. Funktioniert, aber misleading.
Fix: `raw = {k: 5.0 for k in WEIGHT_SCALES}; w_scaled = {k: v * WEIGHT_SCALES[k] for k, v in raw.items()}`.

**G-L6 (Niedrig): Tests laufen nicht in CI**
Verknüpft mit F-L8. test_all.py, test_smoke.py, test_distances.py, test_features.py existieren, werden aber im GitHub-Actions-Workflow nicht ausgeführt. Regressionen werden erst von einem manuellen Lauf gefangen.
Fix: `release.yml` (oder neuer `.github/workflows/test.yml` für PRs) → pytest-Step. Vorab: test_*.py auf pytest-Kompatibilität prüfen (aktuell `sys.exit(1)` als Test-Failure-Indikator — pytest erwartet AssertionError).

**Status:** Großteils erledigt – G-M2, G-M3, G-M4 + G-L4, G-L5, G-L6 + G-M1 in v1.4.0/v1.4.1 gefixt; **G-L1, G-L2, G-L3 (wizard.py Tuple → Dict-Refactor) zurückgestellt** – ist ein größerer Umbau, der mit B-L4 (Validator-Konsolidierung) gemeinsam in einem eigenen Refactor-Sprint angegangen werden sollte.

---

### Heimrecht-Balance pro Runde mit exponentieller Strafe

**Typ:** Verbesserung / Neue Funktion
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Wichtig für Alltag
**Aufwand:** Mittel
**Beschreibung:**

Aktuelles Verhalten: Die Heimrecht-Constraints (`pair_h == h_lo` in `solver.py:207`) garantieren, dass jedes Team über die GESAMTE Saison ausgeglichen Heim- und Auswärtsspiele hat (bei n_rounds=2: n-1 Heim, n-1 Auswärts). Innerhalb einer einzelnen Runde (Hin- bzw. Rückrunde) kann die Verteilung aber stark unausgewogen sein — beobachtet z. B. 7 Heim / 4 Auswärts in der Hinrunde, dann 4 Heim / 7 Auswärts in der Rückrunde.

**Gewünschtes Verhalten:** Sofern keine harten Constraints (Pflichtspiele, Sperrtage, Pflichtheim, DST-Routing) dagegen sprechen, soll auch INNERHALB jeder Runde eine annähernd ausgeglichene Heim/Auswärts-Verteilung angestrebt werden. Da bei ungerader Anzahl Spieltage pro Runde (z. B. 11 Spiele bei 12 Teams) keine 50/50-Verteilung möglich ist, wird die Abweichung vom Mittelwert (5,5 Heim) im Objective progressiv (quadratisch / exponentiell) bestraft.

**Beispiel:** 12 Teams, Hin/Rückrunde, 11 Spiele pro Runde
- 5/6 oder 6/5 Heim/Auswärts: |dev| = 0,5 → ~9 % Abweichung → minimale Strafe
- 4/7 oder 7/4: |dev| = 1,5 → ~27 % Abweichung → deutlich höhere Strafe
- 3/8 oder 8/3: |dev| = 2,5 → ~45 % Abweichung → sehr hohe Strafe

**Implementierungs-Skizze:**

1. **Solver-seitig** (`solver.py: build_league_vars` + `add_league_objective`)
   - Pro (Team, Runde): IntVar `home_in_round[ti, r]` = `sum(home[ti, d] for d in round_r_days)`
   - Pro (Team, Runde): IntVar `dev2[ti, r]` = `(2 * home_in_round[ti, r] - n_days_per_round)`, also doppelte Abweichung vom Mittelwert (vermeidet halbe Werte)
   - Pro (Team, Runde): IntVar `abs_dev2[ti, r] = |dev2[ti, r]|` via `model.AddAbsEquality`
   - Quadratisch: IntVar `sq_dev[ti, r] = abs_dev2 * abs_dev2` via `model.AddMultiplicationEquality` (CP-SAT unterstützt das)
   - Total: `round_balance_penalty = sum(sq_dev[ti, r] for ti, r)` — als IntVar in `LeagueVars`
   - Objective: `-W['round_balance'] * round_balance_penalty` (negativ, da minimieren)

2. **Gewichts-Definition** (`config.py`)
   - Neuer Eintrag in `WEIGHT_SCALES`: `'round_balance': 0.5` (Skalierung muss kalibriert werden — Größenordnung quadrierter Wert kann pro Team und Runde ~25 erreichen, dann sum über n Teams und 2 Runden ~50n)
   - Neuer Eintrag in `WEIGHT_LABELS` (`app.py:251`): `'round_balance': ('Heim-Balance pro Runde', 'Wie ausgeglichen Heim- und Auswärtsspiele innerhalb der Hinrunde bzw. Rückrunde verteilt sind. Höherer Wert = stärker bestrafte Abweichungen wie z. B. 7:4-Verteilungen. Default: 5')`

3. **UI** (`app.py:_step3`)
   - Automatisch durch die generische `_weight_inputs()`-Funktion abgedeckt, da sie über `WEIGHT_LABELS` iteriert. Default-Wert in `_W_DEFAULTS` ergänzen.

4. **Wizard CLI** (`spielplan_multi/wizard.py:step4_weights`)
   - Analog automatisch abgedeckt.

5. **Excel-Output** (`excel_output.py:build_league_excel`)
   - „Fairness-Analyse"-Sheet Block B („HEIMRECHT PRO PHASE") existiert bereits und zeigt Heim/Ausw. pro Runde an. Bewertung erweitern: nicht nur 40–60% global, sondern auch pro Runde.

6. **Tests** (`test_all.py`)
   - Neuer Test: bei aktivem `round_balance`-Gewicht (z. B. 10), 12-Team-Liga, n_rounds=2, prüfen dass `home_in_round` für jedes Team in beiden Runden zwischen `(N_round-1)//2` und `(N_round+2)//2` liegt (also 5 oder 6 bei 11 Spielen).

**Trade-offs / Considerations:**
- **Quadratische Constraints** machen das CP-SAT-Modell rechenintensiver. Für 12 Teams, n_rounds=2 sind das 24 zusätzliche Multiplikations-Constraints — überschaubar, aber sollte mit `test_smoke.py`-Timings verglichen werden.
- **Soft Constraint**: Wie alle Fairness-Terme im Objective. Wenn Pflichtspiele/Sperrtage Balance verhindern, akzeptiert der Solver höhere Strafe (kein INFEASIBLE).
- **Wechselwirkung mit `switch`-Gewicht**: Mehr Heim-Auswärts-Wechsel innerhalb einer Runde korreliert mit ausgewogener Verteilung — aber nicht zwingend. Eine Sequenz HAHAHAHAHHH hat 8 Wechsel und ist trotzdem 7:4. Beide Gewichte sollten unabhängig wirken.
- **Stufe-2-Turniertag**: bei `gpd > 1` oder `K > 0` ist `home[ti, d]` ein Zähler (0..gpd), nicht BoolVar. Constraint braucht ggf. anderes Modell oder ist hier nicht relevant (Turniertag hat ohnehin Sonderlogik). Erste Implementierung: nur für `gpd == 1` aktivieren.

**Akzeptanzkriterien:**
- Bei aktivem `round_balance`-Gewicht (≥5) und sonst unrestriktiver Konfiguration: alle Teams haben pro Runde maximal 1 mehr Heim als Auswärts (oder umgekehrt), d.h. die optimale Verteilung wird erreicht.
- Bei restriktiven Pflichtspielen/Sperrtagen: Solver findet weiterhin eine Lösung (kein neues INFEASIBLE), Strafe steigt aber sichtbar im Objective-Wert.
- Phase-2-Laufzeit verschlechtert sich um maximal 20% bei einer 4-Liga-Konfiguration mit aktivem round_balance.

**Status:** Erledigt in v1.5.0. Verifiziert mit 12-Teams-Beispiel: alle Teams haben 5 oder 6 Heim pro Runde (max ±0.5 vom Mittel 5.5), Solver findet OPTIMAL in <1 Sekunde. Implementierung: `home_in_round[ti,r]` IntVar + `abs_dev2 = |2*home - n_days_r|` + `sq_dev = abs_dev2²` via `AddMultiplicationEquality`. Skala: 2.0 (analog `sw_fair`). UI- und CLI-Default: 0 (opt-in, da quadratische Constraints den Solver leicht verlangsamen). Default-Wert 5 als „empfohlen" im Help-Text. Excel-Konfig-Export erweitert um Spalte „Heim-Balance pro Runde".

---

### [intern] Optimierungslücke (Optimality Gap) verringern

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Mittel
**Beschreibung:**
Bei langen Phase-2-Läufen (8h-Nachtmodus) bleibt die Optimalitätslücke (`gap = (best_bound - best_objective) / best_bound`) typisch bei ~20%. Beobachtet Mai 2026 in einem 8h-Lauf: best=690.496.530, bound=862.666.720, Gap=19,96%. Die Lücke kommt primär aus einer schwer beweisbaren LP-Untergrenze, nicht aus fehlender Lösungsqualität. Trotzdem mehrere Hebel verfügbar:

**H1 (klein, mittel): Symmetry Breaking verstärken**
Aktuell `symmetry_level=1` (in v1.2.x bewusst gesenkt wegen bool_core-Kaskaden im OOM-Bug). Alternativen:
- `symmetry_level=2` plus zusätzliche manuelle Symmetry-Breaking-Constraints (erstes Heimspiel fix auf Team mit kleinstem Index, Reihenfolge der Spiele innerhalb Doppelspieltag nach Team-Index).
- Vorher gegen den OOM-Bug absichern (max_memory_in_mb bereits aktiv).
Erwartete Gap-Reduktion: 12-15%.

**H2 (klein, groß): Bessere Hints aus Phase 1 an Phase 2 übergeben**
Aktuell deckt der Phase-1-Hint nur 17% der Phase-2-Variablen ab (`solution hint is incomplete: 7094 out of 40438`). Zusätzlich zu `h_vals` und `x_vals` aus Phase 1 als Hints geben:
- KW-Zuteilung pro Spieltag (heuristisch: erste machbare KW)
- Switch-Indikatoren `sw[ti,d]` (aus Phase 1 ableitbar)
Wirkung: schnellere erste gute Lösung in Phase 2, mehr Solver-Zeit für Bound-Beweis. Erwartete Gap-Reduktion: 15-17%.

**H3 (mittel, sehr groß): Manuelle Obergrenze auf Switch-Term**
Wichtigster Hebel. Der dominante Objektivterm `sum(switch·sw)` hat eine mathematisch berechenbare Obergrenze, die das LP nicht entdeckt. Beispiel: Bei n Teams und d Spieltagen kann Team i maximal `(d - 2·anzahl_dst_blöcke - 1)` Wechsel haben. Im Modell als IntVar-Bound erzwingen:
```python
max_sw = cfg.n_matchdays - 2 * len(cfg.dst_blocks) - 1
model.Add(sw_total <= max_sw)
```
(Exakte Formel hängt von gpd, Pflichtspielen, Sperrtagen ab.) Erwartete Gap-Reduktion: 8-12%.

**H4 (klein, gering): Längere Laufzeit + relative_gap-Toleranz**
Mit aktuellem Modell wird selbst ein 24h-Lauf wahrscheinlich nicht unter 17-18% Gap kommen. Nicht lohnenswert ohne H1-H3.

**H5 (groß, sehr groß): Phase 2 weiter dekomponieren**
Zusätzliche Zwischen-Phase: erst nur KW-Zuteilung lösen (welcher Spieltag in welche KW), dann mit fixierter KW-Zuteilung den Heimrecht-Plan im 2. Schritt. ~2-3 Wochen Entwicklungsaufwand, Risiko dass Lösungsqualität sinkt, da Phasen nicht mehr gemeinsam optimiert werden. Erwartete Gap-Reduktion: 5-10%.

**Empfehlung:** Mit H3 + H1 beginnen (kombiniert ~10% Gap erreichbar), H2 als Ergänzung wenn nötig.
**Status:** Erledigt – H1 (symmetry_level=2) + H3 (Switch-Term-Obergrenze pro Team) in v1.8.0 implementiert, H2 (Phase-1→Phase-2 Hint-Boost mit switch/sw_count/travel/min-max) in v1.8.1. Erwartete kombinierte Gap-Reduktion ~25%. **Real-Verifikation 27.05.2026:** Gap 19,96 % → 15,35 % = −23,1 % relative Reduktion gemessen (Datei `Spielplaene/telemetrie/F1_VERIFIKATION_2026-05.md`). H4 (längere Laufzeit) und H5 (Phase-2-Dekomposition) blieben offen.

---

### [intern] Code-Review Runde 7 – Block A: Solver-Erweiterungen + Telemetrie

**Typ:** Code-Review-Befunde
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** siehe Einzel-IDs
**Aufwand:** Niedrig pro Befund
**Geprüft:** `solver.py`, `multi_solver.py`, `sa_refine.py`, `league_types.py` (alles seit v1.6.2 geänderten / neu hinzugekommenen Code)

**Befunde:**

**A7-M1 (Mittel): `gap_history` als geteilte Referenz in `multi_solver.run_phase2`**
Zeile 283: `gap_history=p2_history` wird an alle Liga-`LeagueResult`-Objekte mit derselben Listen-Referenz übergeben. Wenn nachfolgender Code die Liste mutiert (z. B. in `app.py` beim JSON-Save), könnte das alle Ligen betreffen. Aktuell kein Bug, weil nirgends mutiert wird, aber latent.
**Fix:** `gap_history=list(p2_history)` pro Liga.

**A7-M2 (Mittel): Phase-1-Seed-Auswahl verwirft Telemetrie nicht-gewählter Seeds**
`run_phase1` Z. 96: `best = max(candidates, key=lambda r: r.objective)` wählt den besten Seed. Die `gap_history` der anderen Seeds geht verloren. Bei Vergleichs-Analysen („welcher Seed konvergierte schneller?") nicht mehr nachvollziehbar.
**Fix-Idee:** Optional `seed_histories: Dict[int, List]` in `LeagueResult` ergänzen — sammelt alle Seed-Verläufe. Aufwand mittel, Nutzen für Debugging.

**A7-M3 (Mittel): SA-Refine schreibt eigene `objective`, aber Phase-2-`best_bound`**
Nach Sprint B1-Hotfix v1.12.1 reicht SA die Telemetrie-Felder durch. `objective` wird aber von SA mit eigenem km-optimiertem Wert überschrieben (kann höher oder niedriger sein als Phase-2-Wert). `final_gap = |bound − new_obj|/|bound|` ist dann nicht mehr exakt der Phase-2-Gap.
**Fix-Idee:** Zusätzliches Feld `phase2_objective` in `LeagueResult` einführen + UI/Excel zeigen explizit „Phase-2-Gap" vs. „SA-Endwert". Aufwand klein, Klarheit hoch.

**A7-L1 (Niedrig): switch-Hint bei Turniertag**
`set_hints` Z. 774-780 setzt `switch[ti, d]`-Hints aus `home_vals`, auch wenn `gpd > 1` (Turniertag). In diesem Modus ist `switch == 0` als Constraint erzwungen — Hint wird vom Solver ignoriert. Kein Bug, aber unnötiger Overhead.
**Fix:** `if cfg.games_per_team_per_day > 1: skip switch/sw_count-Hints` im Helper.

**A7-L2 (Niedrig): `_ProgressCallback.history` nicht deterministisch**
`elapsed = time.time() - t0` ist Wandzeit, nicht reproduzierbar. Zwei identische Solver-Läufe haben unterschiedliche Zeitstempel pro Improvement. Für striktes A/B-Testing ein Detail-Problem.
**Fix-Idee:** Optional `iteration` statt `elapsed` als Zeitachse (Solver gibt das nicht direkt, müsste man via callback-Zähler bauen). Nicht prio.

**A7-L3 (Niedrig): Comment in solver.py Z. 131 leicht missverständlich**
„Nicht-konsekutive Blöcke (d2 > d1+1) constraint switch nicht direkt" — korrekt formuliert, aber: die DST-Constraint `home[ti, d1] == home[ti, d2]` schränkt switch INDIREKT ein, wenn d1, d2 in derselben Phase liegen. Eine theoretisch tightere Bound-Formel wäre möglich (nicht-konsekutiv reduziert Switch-Maximum auch, wenn auch nicht um exakt 1).
**Fix-Idee:** Comment präzisieren, Bound-Formel optional verbessern (klein, aber komplex).

**A7-L4 (Niedrig): `final_gap`-Berechnung mit `abs()` redundant bei Maximize**
solver.py:904 + multi_solver.py:254: `gap = abs(bound - obj_val) / abs(bound)`. Bei `model.Maximize(...)` ist `bound ≥ obj`, also `bound - obj ≥ 0`. `abs()` ist defensiv aber unnötig. Bei hypothetischem `bound < 0` würde `abs(bound)` den Nenner verfälschen.
**Fix:** Bei reinen Maximize-Problemen: `gap = (bound - obj_val) / bound` ohne abs(). Kommentar im Code erklären.

**A7-L5 (Niedrig): Pipeline-Doku-Hinweis fehlt**
Bei Phase-2-Fallback (`return phase1_results`) erbt jedes Liga-Result die Phase-1-Telemetrie. Bei normalem Phase-2-Lauf erbt jedes Liga-Result die Phase-2-Telemetrie (gleicher Wert, weil gemeinsames Modell). Nach SA wird `objective` lokal überschrieben. Dieses Verhalten ist nirgends dokumentiert.
**Fix:** Kurzer Absatz in `CLAUDE.md` Section „Pipeline" erklären, was wann in `gap_history`/`best_bound`/`final_gap` steht.

**Hoch-Prio-Befunde:** keine.

**Status:** Offen — kann lokal abgearbeitet werden, ist nicht zeitkritisch (alle Bugs latent, nicht aktiv).

---

### [intern] Code-Review Runde 7 – Block B: Karte + Kalender Module

**Geprüft:** `spielplan_multi/geocode.py`, `spielplan_multi/map_output.py`, `spielplan_multi/calendar_output.py`

**B7-M1 (Mittel): Geocode-Cache File-Lock-Risiko**
`_save_cache` (Z. 42-50) öffnet/schreibt die JSON-Datei ohne File-Locking. Bei zwei parallelen Streamlit-Sitzungen, die gleichzeitig geocoden, kann ein Eintrag verloren gehen (Read-modify-write Race).
**Fix-Idee:** `portalocker` oder `fcntl.flock`/`msvcrt.locking` einbauen. Bei FLVD-Setup mit nur 1 User wahrscheinlich nie problematisch — niedrige Priorität.

**B7-L1 (Niedrig): User-Agent hardcoded auf veralteter Version**
`_USER_AGENT = 'spielplan-optimierer/1.9 (it@floorball.de)'` — App ist v1.12.1. Nominatim nutzt UA nur zur Kontaktaufnahme, deshalb harmlos, aber konsistent wäre besser.
**Fix:** Aus `VERSION`-Datei dynamisch lesen.

**B7-L2 (Niedrig): `_normalize` ohne Umlaut-Normalisierung**
„Köln" und „Koeln" haben unterschiedliche Cache-Keys. Bei FLVD-Daten wahrscheinlich gelegentliches Issue (manchmal mit Umlaut, manchmal ohne).
**Fix:** `unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')` als optionaler Schritt.

**B7-L3 (Niedrig): `time.sleep` blockiert Streamlit-Thread**
Beim Geocoding mit 50 Adressen blockiert 50 × 1.1s = 55s die UI (Spinner sichtbar, aber sonst unresponsiv). Bei Erstaufruf akzeptabel, später aus Cache instant.
**Fix-Idee:** Asynchroner Worker-Thread + Progress-Updates via Queue. Aufwand mittel, Nutzen klein.

**B7-L4 (Niedrig): `liga_idx` unused in `build_route_map`**
`for liga_idx, (lid, res) in enumerate(valid_results)` — `liga_idx` wird nicht verwendet. Ruff toleriert es (F841 ignored). Idee dahinter war evtl. eine liga-spezifische Farbe — aktuell wird `get_team_color(ti)` benutzt, was bei Multi-Liga zu Farb-Kollisionen führt.
**Fix:** Entweder `_ = liga_idx` oder die Variable nutzen für Liga-spezifische Marker-Form.

**B7-L5 (Niedrig): HTML im Folium-Tooltip nicht escaped**
`tooltip=f'<b>{team}</b>...'` — wenn ein Team-Name HTML-Special-Chars enthielte, würden sie als HTML interpretiert. Bei FLVD-Daten unkritisch (Vereine haben keine HTML-Namen), aber defensiv könnte man `html.escape` nutzen.

**B7-L6 (Niedrig): `_parse_date` bei 2-stelligem Jahr**
`_dt.date(int(parts[2][:4]), ...)` — wenn `parts[2] = "26"` (statt "2026"), wird Jahr 26 verwendet. Bei FLVD-Excel-Exports unwahrscheinlich (ISO-Format wird genutzt), aber defensive Validierung fehlt.

---

### [intern] Code-Review Runde 7 – Block C: UI + JSON-Persistenz

**Geprüft:** `app.py` neue UI-Sections (Karte, Kalender, Telemetrie, Adressen-Editor), `_session_to_json`/`_session_from_json` (Schema 1.0/1.1), `_translate_solver_log` + `_BEST_LINE_RE`

**C7-M1 (Mittel): `_translate_solver_log` Performance bei langen Läufen**
Bei jedem Streamlit-Rerun (alle ~2 Sek) wird die gesamte `S.opt_log`-Liste re-iteriert und Regex-gematcht. Bei 8h-Lauf × 14.400 Reruns × 10.000+ Log-Lines = hunderte Millionen Match-Operationen. Aktuell zeigt nur Letztes 12 — aber durchgegangen wird alles.
**Fix:** Caching mit `(log_len, last_translated_idx)` → nur neu hinzugekommene Zeilen verarbeiten. Aufwand klein, Performance-Impact bei langen Läufen messbar.

**C7-L1 (Niedrig): HTML-Escaping in Translator**
Liga-Namen werden direkt in Markdown eingebettet (`**{name}**`). Bei Namen mit `*`, `_` oder anderen Markdown-Sonderzeichen würde das Layout brechen. FLVD-Namen sind harmlos.

**C7-L2 (Niedrig): `[OK]`-Replace string-basiert**
`txt.replace('FEASIBLE', 'Lösung gefunden')` — würde auch in Liga-Namen ersetzen, die zufällig „FEASIBLE" enthielten. Edge-Case bei FLVD nicht relevant.

**C7-L3 (Niedrig): JSON-Lader nutzt `.get()` für Telemetrie-Felder**
Backward-compat zu Schema 1.0 ist sauber (`.get()` mit None-Defaults). Wenn ein User eine sehr alte Sitzung lädt, fehlt Telemetrie — wird korrekt mit None gefüllt, kein Crash.

---

### [intern] Code-Review Runde 7 – Block D: CI + Tests

**Geprüft:** `.github/workflows/{test,coverage,codeql,release}.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`, `ruff.toml`, `.coveragerc`, `run_coverage.py`, `test_pytest_runner.py`, neue Test-Funktionen

**D7-H1 (Hoch): Action-Versionen inkonsistent zwischen Workflows**
- `test.yml` nutzt `actions/checkout@v6` + `actions/setup-python@v6` (Dependabot-Updates angewandt)
- `coverage.yml` nutzt `actions/checkout@v4` + `actions/setup-python@v5` (alt!)
- `actions/upload-artifact@v4` ebenfalls in coverage.yml

Ursache: `coverage.yml` wurde NACH den Dependabot-Updates hinzugefügt → Dependabot kannte die Datei beim damaligen Lauf noch nicht.
**Fix:** Versionen in `coverage.yml` auf `@v6` bzw. `@v6` bringen. Dependabot wird beim nächsten wöchentlichen Run auch von selbst greifen. Aufwand: 30 Sek.

**D7-L1 (Niedrig): Coverage-Workflow ohne Quality-Gate**
`run_coverage.py` schreibt Report + Artifact, failt aber nicht bei Coverage-Drop. Könnte `--fail-under=70` ergänzt werden.
**Trade-off:** Striktes Threshold würde harmlose Refactorings rot färben — niedrige Prio.

**D7-L2 (Niedrig): Pre-Commit-Hook optional**
Wenn ein Dev `pre-commit install` nicht ausführt, gibt's keinen lokalen Ruff-Check. Im CI wird's dann gefangen. → OK so, aber Hinweis in CLAUDE.md könnte stärker sein.

**D7-L3 (Niedrig): `run_coverage.py` sequenziell**
4 Test-Scripts werden nacheinander ausgeführt (smoke + features + distances + test_all). `test_all` dominiert die Laufzeit (~14 min mit Coverage-Instrumentation). Parallel laufen geht prinzipiell, aber `coverage combine` wird komplexer.
**Trade-off:** Bei Hosted-Runner (2 Core) wenig Gewinn — niedrige Prio.

---

### [intern] Code-Review Runde 7 – Block E: Doku + Distribution + Memory

**Geprüft:** `CLAUDE.md`, `BENUTZERHANDBUCH.md`, `INSTALLATION.md`, `README.md`, `ROADMAP.md`, `SPRINT_SNAPSHOT.md`, `requirements.txt`, `installer/spielplan.iss`, Memory-Files

**E7-M1 (Mittel): `requirements.txt` ohne Upper-Bound (außer ortools)**
```
numpy>=2.4.6
pandas>=3.0.3
streamlit>=1.57.0
```
Wenn z. B. pandas 4.0 mit Breaking Changes kommt, würde eine frische Installation crashen ohne Code-Änderung. Reproducibility-Risiko für Endnutzer.
**Fix:** `<X.0` Upper-Bound pro Paket nach Major. Z. B. `pandas>=3.0.3,<4`. Dependabot bumpt dann nur Minor/Patch automatisch, Major-Bumps brauchen User-Review.

**E7-L1 (Niedrig): `installer/spielplan.iss` Version-Default veraltet**
ISS-Default ist (laut CR6 F-L4-Notiz) auf v1.4.0. Wird durch `/DMyAppVersion=` überschrieben — also kein Issue im Build, aber unsauber.
**Fix:** Default-Wert auf aktuelle Version ziehen (oder besser: aus `VERSION`-Datei lesen via `#define`-Preprocessing).

**E7-L2 (Niedrig): `Spielplaene/telemetrie/` gitignored**
Pre/post-F1-Daten + Verifikations-MD sind lokal, nicht im Repo. Wenn der Test-Beleg verloren geht (z. B. Festplatten-Crash), ist die Doku der F1-Verifikation weg.
**Fix-Idee:** Verifikations-MD und CSVs in `docs/verifikation/` checken (außerhalb von Spielplaene/), damit sie versioniert sind.

**E7-L3 (Niedrig): CLAUDE.md sehr lang (~700 Zeilen)**
Section 9 enthält chronologisch alle Sprints v1.3.0 → v1.12.1 als verschachtelte Tabellen. Für neue Mitarbeiter schwer überschaubar.
**Fix-Idee:** Older Sprints (v1.3.x – v1.6.x) in separate `CHANGELOG_v1.x.md` auslagern, CLAUDE.md fokussiert auf aktuelle Architektur.

**E7-L4 (Niedrig): `BENUTZERHANDBUCH` Screenshots fehlen**
Karten-Visualisierung und Kalenderansicht wurden in Text dokumentiert, aber kein Screenshot. Endnutzer würden visuelle Beispiele schätzen.
**Fix:** 2-3 Screenshots der Schritt-9-UI nach Optimierung anhängen.

**E7-L5 (Niedrig): `_USER_AGENT` in geocode.py + Bootstrap-Python-Hash veralten gemeinsam**
Bei `VERSION`-Bump müssten 3 Stellen synchron geändert werden: VERSION, geocode.py `_USER_AGENT`, evtl. installer/build_bootstrap.bat SHA-Hash für Python-Embedded.
**Fix:** Zentrale Versions-/Hash-Konstanten, die alle Stellen referenzieren.

---

**Block-Übersicht Code-Review Runde 7:**

| Block | Hoch | Mittel | Niedrig | Befunde gesamt |
|---|---|---|---|---|
| A — Solver + Telemetrie | 0 | 3 | 5 | 8 |
| B — Karte + Kalender Module | 0 | 1 | 6 | 7 |
| C — UI + JSON-Persistenz | 0 | 1 | 3 | 4 |
| D — CI + Tests | 1 | 0 | 3 | 4 |
| E — Doku + Distribution + Memory | 0 | 1 | 5 | 6 |
| **Gesamt** | **1** | **6** | **22** | **29** |

**Wichtigste Findings:**
- **D7-H1** (Hoch): Action-Versions-Inkonsistenz `coverage.yml` vs. `test.yml`. Quick-Fix in 30 Sek.
- **A7-M1**, **A7-M3**, **B7-M1**, **C7-M1**, **E7-M1**: 5 Mittel-Prio-Befunde — alle latent/Robustheit, nicht zeitkritisch.

**Status:** ✅ Großteils erledigt — 16/29 Befunde in v1.13.0 gefixt (siehe CLAUDE.md Section 9). 13 Befunde bleiben offen (alle Niedrig-Prio bzw. größere Refactors, alle dokumentiert oben).

---

### [intern] Code-Review Runde 8 – Block A: Solver-Modell + Pipeline

**Final-Review für Produktiv-Freigabe.**
**Geprüft:** `spielplan_multi/solver.py`, `spielplan_multi/multi_solver.py`
**Datum:** 27.05.2026, Stand v1.13.0

**Schweregrad-Skala:** 🛑 Show-Stopper / 🔴 Hoch / 🟡 Mittel / 🟢 Niedrig

**Show-Stopper:** **0**
**Hoch:** **0**
**Mittel:** **1**
**Niedrig:** **4**

#### Mittel

**🟡 R8-A-M1 — Co-Home-Gewicht-Skalierung kann bei sehr großen Werten Probleme verursachen**
`_add_cohome_constraints` Z. 196: `w_cohome_int = int(round(w_cohome * 1000))`. Mit Default w_cohome=5 ergibt 5.000. CP-SAT-Objective-Range ist Int-domain (typisch ±2^31). Bei sehr großen w_cohome (z. B. ≥ 1000) und vielen Co-Home-Bonus-Variablen könnte das Objective überlaufen.
**Risiko:** Bei FLVD-Default-Setup unkritisch (w_cohome typisch 5-10). Aber: kein Validierungs-Cap in der UI.
**Fix-Idee:** Validator-Warnung wenn w_cohome > 50; oder Cap in der UI auf 20.
**Produktions-Blocker?** Nein (Konfiguration mit Standard-Werten ist safe)

#### Niedrig

**🟢 R8-A-L1 — CP-SAT mit 1 num_search_worker bei vielen Phase-1-Jobs**
`run_phase1` Z. 60-61: `workers_per = max(1, cpu // n_jobs)`. Bei 8 Cores + 4 Ligen × 2 Seeds = 8 Jobs → 1 worker pro Solver. Phase-1-Solver läuft single-threaded. Parallelität via Job-Pool ist gegeben.
**Trade-off:** Mehr Worker pro Solver würden den Solver beschleunigen, weniger Parallelität wäre möglich. Aktuelles Setup balanciert Job-Throughput.
**Produktions-Blocker?** Nein

**🟢 R8-A-L2 — Spielfrei-Modus ohne explizite Bye-Verteilungs-Balance**
Bei n_active < n_teams kann ein Team theoretisch viele aufeinanderfolgende Bye-Tage haben (kein Constraint dagegen). Total-Spielzahl pro Team ist über round-Constraint geregelt, aber Verteilung über Saison nicht.
**Risiko:** In Praxis löst der Solver implizit fair, weil Travel-Term spielfreie Teams nicht reduziert (ein Team ohne Spiele hat hohe travel-Differenz zu spielenden Teams).
**Test:** Test 11 in test_all deckt „Bye fair verteilt" ab.
**Produktions-Blocker?** Nein

**🟢 R8-A-L3 — Co-Home nutzt nur ersten Spieltag pro KW**
`_add_cohome_constraints` Z. 141: `st = next((s for s in sts if s in days), None)` — bei DST-Wochenende mit 2 Spieltagen wird nur der erste betrachtet. Andere Spieltage in der KW haben keinen Co-Home-Bonus.
**Risiko:** Co-Home-Effekt etwas schwächer als theoretisch möglich. Bei FLVD-Saisons mit selten DST in Co-Home-Liga unkritisch.
**Produktions-Blocker?** Nein

**🟢 R8-A-L4 — Subprocess-Stacktrace im Streamlit-Warnung**
`_phase1_worker` Z. 42 schreibt komplette Traceback in `status_name`, der via `warn()` in der UI angezeigt wird (kann 1000+ Zeichen sein). Bei echten Crashes verstopft das den Log-Bereich.
**Fix-Idee:** Nur erste Zeile des Tracebacks anzeigen, vollen Stack in einer expandable-Section.
**Produktions-Blocker?** Nein

---

**Block-A-Fazit:** Solver-Modell ist sehr solide — kein Show-Stopper, keine harten Bugs. Alle Constraint-Familien sind nach 3 Code-Reviews + R1-R3-Refactors + R7-Fixes konsistent. Die wenigen verbleibenden Befunde sind alle latent oder Trade-offs.

---

### [intern] Code-Review Runde 8 – Block B: Nachbearbeitung

**Geprüft:** `spielplan_multi/sa_refine.py`, `spielplan_multi/tt_scheduler.py`, `spielplan_multi/schedule_utils.py`
**Datum:** 27.05.2026, Stand v1.13.0

**Show-Stopper:** **0** | **Hoch:** **0** | **Mittel:** **1** | **Niedrig:** **4**

#### Mittel

**🟡 R8-B-M1 — `move_game` und `reschedule_game` ohne DST-Konsistenz-Check**
`schedule_utils.move_game` Z. 174: verschiebt ein Spiel auf einen `new_day`, ohne zu prüfen ob `new_day` Teil eines DST-Blocks ist. Bei Move auf DST-Tag bleibt der DST-Partner-Tag mit alten Daten — die DST-Invariante (gleiches Heimrecht beider DST-Tage) kann gebrochen werden.
`schedule_utils.reschedule_game` Z. 251: gleiches Problem (Spiel kann auf DST-Tag platziert werden).
**Kontrast:** `cancel_game` Z. 243-247 gibt eine Warning aus, wenn DST-Tag betroffen ist. Move/reschedule machen das nicht.
**Risiko:** Wenn User aus der UI ein Spiel auf einen DST-Tag verschiebt, kann der Spielplan inkonsistent werden (Excel-Heatmap zeigt falsches Heimrecht für den DST-Partner-Tag).
**Fix-Idee:** Analoge Warning in move_game/reschedule_game wenn day in cfg.dst_days. UI könnte zusätzlich Buttons für DST-Tage deaktivieren.
**Produktions-Blocker?** Nein — UI hat aktuell keine Option, ein Spiel direkt auf einen DST-Tag zu verschieben (Spieltage in UI sind eingeschränkt). Aber latent.

#### Niedrig

**🟢 R8-B-L1 — `_dt.datetime.utcnow()` in `build_ics_bytes` deprecated**
Z. 348: `_dt.datetime.utcnow().strftime(...)`. Python 3.12+ markiert das als Deprecation-Warning. Modern: `_dt.datetime.now(_dt.timezone.utc)`.
**Risiko:** Bei Python 3.14 würde es eventuell entfernt. Aktuell nur stille Warning.
**Fix:** 1-Zeilen-Änderung.
**Produktions-Blocker?** Nein

**🟢 R8-B-L2 — `reschedule_game` validiert `day` nicht gegen `cfg.days`**
Im Gegensatz zu `move_game` (Z. 181: `if new_day not in cfg.days: return ...`) prüft `reschedule_game` Z. 251 nicht ob `day` ein gültiger Spieltag ist. Wenn ein User aus der UI einen Day außerhalb des Range einreicht, würde das Spiel an einen ungültigen Tag platziert.
**Risiko:** UI begrenzt den Tag-Selector auf gültige Spieltage, daher in Praxis unwahrscheinlich.
**Fix:** Validierungs-Check analog zu move_game.
**Produktions-Blocker?** Nein

**🟢 R8-B-L3 — `sa_refine` mutiert `loc[ai][0]` bei Einfachrunde (Sentinel)**
Bei `n_rounds=1` hat jede Paarung kein Rückspiel; `pair_info[pid] = (ai, bi, hd, 0)`. Im SA-Swap-Code Z. 230-231 wird `loc[ai][0]` mutiert (Position 0 = Sentinel). `_recompute_team` iteriert über Z. 34 `for d in range(1, N):` und ignoriert Position 0 → kein Schaden, aber unsauberer Code-Style.
**Fix-Idee:** Sentinel-Erkennung im Swap-Code: `if rd > 0: loc[ai][rd] = ...`.
**Produktions-Blocker?** Nein

**🟢 R8-B-L4 — `recompute_result_stats` liest `result.home_vals` für sw_counts**
Z. 65-75 nutzt `result.home_vals` für Switch-Zählung. Wenn `home_vals` stale ist (z. B. nach manueller Mutation ohne Update), sind sw_counts falsch. Aktuelle Mutations-Funktionen (move/cancel/reschedule/swap) aktualisieren home_vals — aber kein Schutz dagegen wenn der Code in Zukunft erweitert wird.
**Fix-Idee:** sw_counts auch aus dem Schedule rekonstruieren (analog zu travels via loc-Modell).
**Produktions-Blocker?** Nein

---

**Block-B-Fazit:** Nachbearbeitung ist solide. SA hat klare Determinismus-Garantie (gleicher Seed + gleiche Maschine = gleiche Lösung). Mutations-Funktionen sind nach R6 mit Turniertag-Guards versehen. Einziger latenter Punkt ist die fehlende DST-Konsistenz-Warnung in move/reschedule — bei der aktuellen UI nicht direkt triggerbar, aber als Defensive-Maßnahme empfehlenswert.

**Geprüfte Bereiche** ✓:
- SA-Akzeptanz-Kriterium (Metropolis), Cooling (geometrisch), Reset (kein expliziter Reset, läuft aus)
- SA-Verbote (pinned, DST, blocked, forced_home)
- `apply_tournament_ordering` mit Backtracking + MAX_NODES-Cap
- `_balance_home_away` (post-TT-Ordering)
- Ausrichter-Verteilung via `_assign_hosts` (deterministisch via seed)
- Mutations: move/cancel/reschedule/swap mit Turniertag-Guard
- DST-Warning in cancel_game
- iCal: RFC 5545 Escaping + Line-Folding + DTSTAMP + Skip-no-date-Hint
- HTML-Druckansicht (`build_print_html` nicht im Detail geprüft, aber strukturell ok)

**Geprüfte Bereiche** ✓:
- Match-Eindeutigkeit + Phasen-Trennung (n_rounds 1/2/3)
- Heimrecht-Balance pro Paarung
- DST-Constraints (Heimrecht-Gleichheit, A/B/C-Nachbarschaft)
- Sliding-Window 3er/4er (homeW-basiert seit v1.2.7)
- Spielfrei-Modus (needs_bye) konditional in allen Constraints
- Turniertag Stufe 1 + Stufe 2 (Gruppenformation)
- Switch-Term mit H3-Obergrenze (R7-Fix)
- Round-Balance (quadratische Strafe, opt-in)
- Pflichtspiele + Sperrtage + Pflichtheim (mit Override-Warnung)
- Phase 1 parallel mit Seeds + Crash-Handling
- Phase 2 gemeinsames Modell + Co-Home-Bonus
- Phase 1→2 set_hints (Primär + abgeleitet)
- Phase-2-INFEASIBLE-Fallback auf Phase-1-Ergebnisse
- Telemetrie-Persistenz durch alle Phasen (R7-Fix)
