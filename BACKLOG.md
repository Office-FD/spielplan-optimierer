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
**Status:** Offen

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
**Status:** Offen

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
**Status:** Offen

---

### [intern] clubs_db.csv committen

**Typ:** Aufgabe
**Bereich:** Vereinsdatenbank
**Wichtigkeit:** Kleiner Wunsch
**Aufwand:** Klein
**Beschreibung:**
`clubs_db.csv` hat lokale Änderungen die noch nicht committed sind (seit vor
dieser Sitzung). Änderungen prüfen und bei Gelegenheit committen.
**Status:** Offen

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
