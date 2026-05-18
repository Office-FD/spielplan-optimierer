# Spielplan-Optimierer

Automatische Spielplanerstellung für Floorball-Ligen des **FLOORBALL VERBAND DEUTSCHLAND e.V.**

Das Tool erstellt optimierte Spielpläne für eine oder mehrere Ligen gleichzeitig – mit minimalen Reisewegen, ausgeglichenem Heimrecht und Berücksichtigung von Doppelspieltagen, Pflicht- und Sperrtagen sowie Co-Home-Vereinen.

**Aktuelle Version:** 1.2.3

---

## Für Anwender

| Dokument | Inhalt |
|---|---|
| [Installationsanleitung](INSTALLATION.md) | Setup-Datei herunterladen, installieren, starten |
| [Benutzerhandbuch](BENUTZERHANDBUCH.md) | Schritt-für-Schritt durch alle Wizard-Schritte |

**Download:** [Neueste Version](https://github.com/Office-FD/spielplan-optimierer/releases/latest)

---

## Funktionen

### Spielplan-Optimierung
- Drei-Phasen-Pipeline: **CP-SAT (Google OR-Tools)** + **Simulated Annealing**
- Mehrere Ligen gleichzeitig optimieren (gemeinsames Modell in Phase 2)
- Minimiert Gesamtreisekilometer und maximiert ausgeglichenes Heimrecht
- Co-Home-Synchronisation: Mehrspartenvereine spielen in der gleichen Kalenderwoche zuhause
- Doppelspieltage (DST): identisches Heimrecht an beiden Tagen, optionale Reiseweg-Begrenzung (DST-Routing)
- Wiederherstellung nach Verbindungsverlust: letztes Ergebnis wird gesichert und kann nach Browser-Neustart geladen werden

### Unterstützte Spielformate
| Format | Beschreibung |
|---|---|
| Einfachrunde | Jede Paarung einmal; n-1 Spieltage (gerades n), n Spieltage (ungerades n) |
| Hin- und Rückrunde | Jede Paarung zweimal; Standard für Bundesligen |
| Dreifachrunde | Jede Paarung dreimal |
| Turniertag Stufe 1 | Alle Teams an einem Ort; mehrere Spiele pro Team und Tag |
| Turniertag Stufe 2 | Wie Stufe 1, aufgeteilt in Gruppen |
| Ungerade Teamzahl | Vollständig unterstützt; ein Team hat je Spieltag spielfrei (Berger-Tableau) |

### Konfiguration & Constraints
- Pflichtspiele: bestimmte Paarungen auf festen Spieltagen erzwingen
- Sperrtage: Team kann an bestimmten Spieltagen nicht spielen
- Heimspiel-Pflichttage: Team muss an bestimmten Spieltagen zuhause spielen
- Fünf gewichtbare Optimierungsziele: Heimrecht-Wechsel, Wechsel-Fairness, Gesamtkilometer, km-Fairness, DST-Reiseeffizienz

### Distanzmatrizen
- Manuell eingeben
- CSV/Excel hochladen
- Automatisch per Google Maps API berechnen (Ergebnis wird gecacht)

### Export & Nachbearbeitung
- **Excel** je Liga (Spielplan, Heimrecht-Heatmap, Kilometertabelle, Distanzmatrix, Fahrtkostenausgleich)
- **Co-Home-Excel**: KW-Heimspiel-Übersicht aller Ligen
- **iCal**: Import in Outlook, Google Kalender etc.
- **HTML-Druckansicht**
- Spielpläne vergleichen: zwei Varianten gegenüberstellen (Delta km und Wechselquote)
- Spielplan nachbearbeiten: Spiele verschieben, absagen, Nachholtermine eintragen, Heimrecht tauschen

### Sonstiges
- **Automatische Updates** beim Programmstart (via GitHub Releases)
- Konfiguration als Excel speichern und wiederladen
- Fehler und Wünsche direkt aus der App melden (E-Mail an it@floorball.de)

---

## Grenzen & bekannte Einschränkungen

| Bereich | Einschränkung |
|---|---|
| Betriebssystem | Nur Windows (Endnutzer-EXE); Entwicklung auf Windows/Linux/Mac möglich |
| Laufzeit | 3+ Ligen erfordern Nachtlauf (8 h); kurze Zeitlimits können zu „Keine Lösung" führen |
| Constraints | Zu viele Pflichtspiele oder Sperrtage können die Lösbarkeit verhindern |
| Turniertag | Spiele verschieben/absagen im UI nicht unterstützt (manuell im Excel nachbearbeiten) |
| DST-Routing | Zu enger Umwegfaktor (< 2%) führt häufig zu INFEASIBLE |
| Lagen-Visualisierung | Keine Karten-Ansicht; nur Kilometertabelle und Excel |
| Multi-Saison | Heimrechts-Kontinuität über zwei Saisons hinweg nicht unterstützt |
| Skalierung | Getestet bis ~12 Teams/Liga; bei sehr großen Ligen (>16 Teams) deutlich längere Laufzeiten |

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

1. `VERSION`-Datei auf neue Versionsnummer setzen (z. B. `1.3.0`)
2. Git-Tag setzen und pushen:
   ```bat
   git tag v1.3.0
   git push && git push --tags
   ```
   → GitHub Actions erstellt den Release mit `app-files.zip` automatisch
   → Alle Nutzer sehen beim nächsten Start den Update-Dialog

### Bootstrap-Installer bauen

Nur nötig wenn sich Python-Version oder Pakete geändert haben:

```bat
installer\build_bootstrap.bat
```

Voraussetzung: [Inno Setup 6](https://jrsoftware.org/isinfo.php) installiert.

---

## Technologie

- Python 3.13 · Streamlit ≥1.32 · Google OR-Tools CP-SAT (ortools ≥9.14,<10)
- NumPy · pandas · openpyxl · requests
