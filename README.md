# Spielplan-Optimierer

Automatische Spielplanerstellung für Floorball-Ligen des **FLOORBALL VERBAND DEUTSCHLAND e.V.**

Das Tool erstellt optimierte Spielpläne für eine oder mehrere Ligen gleichzeitig – mit minimalen Reisewegen, ausgeglichenem Heimrecht und Berücksichtigung von Doppelspieltagen, Pflicht- und Sperrtagen sowie Co-Home-Vereinen.

---

## Für Anwender

| Dokument | Inhalt |
|---|---|
| [Installationsanleitung](INSTALLATION.md) | Setup-Datei herunterladen, installieren, starten |
| [Benutzerhandbuch](BENUTZERHANDBUCH.md) | Schritt-für-Schritt durch alle Wizard-Schritte |

**Download:** [Neueste Version](https://github.com/Office-FD/spielplan-optimierer/releases/latest)

---

## Funktionen

- Optimierung mit **Google OR-Tools CP-SAT** + **Simulated Annealing**
- Unterstützt Einfach-, Hin-Rück- und Dreifachrunden sowie Turniertage
- Co-Home-Synchronisation für Mehrspartenvereine
- Export als **Excel**, **iCal** und **HTML-Druckansicht**
- Spielplan nachbearbeiten: Spiele verschieben, absagen, Nachholtermine eintragen
- **Automatische Updates** beim Programmstart

---

## Für Entwickler

### Voraussetzungen

- Python 3.13
- Pakete: `pip install -r requirements.txt`

### Starten

```bat
start.bat
```

### Tests ausführen

```bat
python -m pytest test_smoke.py        # Schnell (~30 Sek.)
python -m pytest test_all.py          # Vollständig (~5 Min.)
```

### Release erstellen

1. `VERSION`-Datei auf neue Versionsnummer setzen (z. B. `1.2.0`)
2. `python build_release.py` – erstellt `app-files.zip`
3. Git-Tag setzen und pushen:
   ```bat
   git tag v1.2.0
   git push && git push --tags
   ```
   → GitHub Actions erstellt den Release automatisch

### Bootstrap-Installer bauen

Nur nötig wenn sich Python-Version oder Pakete geändert haben:

```bat
installer\build_bootstrap.bat
```

Voraussetzung: [Inno Setup 6](https://jrsoftware.org/isinfo.php) installiert.

---

## Technologie

- Python 3.13 · Streamlit · Google OR-Tools CP-SAT
- NumPy · pandas · openpyxl · requests
