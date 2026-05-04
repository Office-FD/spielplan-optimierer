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
**Status:** Offen

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
**Status:** Offen

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

### [intern] stdout-Interleaving bei parallelen Phase-1-Läufen

**Typ:** Verbesserung
**Bereich:** Spielplan-Optimierung
**Wichtigkeit:** Kleiner Wunsch
**Beschreibung:**
`solver.py`: `_ProgressCallback` schreibt direkt auf `sys.stdout`. Bei parallelen Phase-1-Läufen können Ausgaben verschiedener Ligen interleaven wenn Streamlits `sys.stdout`-Ersatz nicht thread-safe ist. Fix: Ausgabe in `threading.Lock` kapseln.
**Status:** Zurückgestellt – kosmetisch; Streamlit-Ausgaben sind bereits auf Sessionebene isoliert. Kein Absturzrisiko.
