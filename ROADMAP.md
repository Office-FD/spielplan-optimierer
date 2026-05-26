# Roadmap — Spielplan-Optimierer

> Stand: Mai 2026, Version 1.8.1. Drei Pfade in Priorisierungs-Reihenfolge. Pfad A wird zuerst umgesetzt, Pfad B danach. Pfad C (Pause) ist Standard wenn weder A noch B aktiv sind.

---

## Pfad A — User-sichtbare UX-Features

**Ziel:** Direkter Nutzen für FLVD-Alltag — sichtbar nach jeder Optimierung in der App.

### A1 · Karten-Visualisierung Reiserouten
**Wichtigkeit:** Hoch — hilft Plan-Reviewern, ungewöhnlich lange Reisen sofort zu erkennen
**Aufwand:** Mittel (~1-2 Tage)
**Technik:** `folium` + `streamlit-folium` (oder `pydeck` als Fallback)
**Inhalt:**
- Pin für jeden Team-Standort (clubs_db.csv-Geolocation oder Adress-Geocoding)
- Pro Spieltag (oder über alle Spieltage gemittelt): Polylinien zwischen Standorten
- Heatmap der Gesamt-km pro Team
- Klick auf Pin/Linie zeigt Details (Team, Liga, km)

**Status:** Erledigt in v1.9.0 — siehe CLAUDE.md Section 9 für Details.

### A2 · Interaktive Kalenderansicht im Browser
**Wichtigkeit:** Mittel — ergänzt Excel-Export um schnellen Überblick
**Aufwand:** Mittel (~1-2 Tage)
**Technik:** `streamlit-calendar` oder eigene HTML-Komponente via `st.components.v1.html`
**Inhalt:**
- Monatsansicht mit allen Spielen, farblich nach Liga/Team
- Click-to-Detail (Heim/Gast/Ort/Uhrzeit)
- Wechsel zwischen Monaten/Wochen/Saison-Übersicht

**Status:** Erledigt in v1.10.0 — `streamlit-calendar` mit Monats-/Wochen-/Listenansicht, deutscher Lokalisierung, Wochennummern, Team-Farben. Siehe CLAUDE.md Section 9 für Details.

---

## Pfad B — Operative Verbesserungen

**Ziel:** Wartbarkeit + Verifikation der bisherigen Optimierungen.

### B1 · Gap-Monitoring / Telemetrie
**Wichtigkeit:** Hoch — verifiziert ob H1/H3/H2 (Sprint F1) wirken
**Aufwand:** Klein (~3-4h)
**Technik:** Phase-2-Solver-Log parsen, Werte in Streamlit-Charts darstellen
**Inhalt:**
- Aktuell loggt CP-SAT bereits `obj` und `best_bound`. Diese Werte abfangen
- Gap-Verlauf während Optimierung als Live-Chart (best_obj vs. best_bound über Zeit)
- Finale Gap-Kennzahl in der Ergebnis-Übersicht
- Über mehrere Optimierungs-Läufe Vergleichswerte sammeln (CSV-Export)

**Status:** Erledigt in v1.11.0 — `LeagueResult` erweitert um gap_history + best_bound + final_gap; `_ProgressCallback` zeichnet auf; UI-Section mit Metriken + Live-Chart + CSV-Export.

### B2 · Doku-Update v1.8.x
**Wichtigkeit:** Mittel — Endnutzer sollten neue Features finden
**Aufwand:** Klein (~2h)
**Technik:** Markdown-Edits
**Inhalt:**
- `BENUTZERHANDBUCH.md`: neue Slider/Buttons aus v1.5.0-v1.8.1 dokumentieren (round_balance, dst_eff, Coverage-Reports etc.)
- `INSTALLATION.md`: Hinweise zur neuen Pre-Commit-Hook-Option für Power-User
- Screenshots auffrischen falls UI sich verändert hat

**Status:** Erledigt in v1.11.2 — BENUTZERHANDBUCH.md auf v1.11-Stand (Karten, Kalender, Telemetrie, neue Gewichte). Schritt-Nummerierung 1-basiert konsistent mit UI. INSTALLATION + README ergänzt.

### B3 · Real-World-Verifikation
**Wichtigkeit:** Hoch — beweist Effektivität von Sprint F1 (~25% Gap-Reduktion erwartet)
**Aufwand:** Wandzeit ~8h (1 Saison-Optimierungs-Lauf), 1h Auswertung
**Technik:** Vorher/Nachher-Vergleich
**Inhalt:**
- Nächste reale Saison-Konfig (4 Ligen, 8h-Nachtmodus)
- Mit v1.6.2 (vor F1) und v1.8.1 (nach F1) je einen Vergleichslauf
- Gap-Werte, Lösungsqualität (Gesamt-km), Wechselrate dokumentieren
- Ergebnis in BACKLOG.md unter "Optimierungslücke verringern" als verifizierte Wirkung anhängen

**Status:** Offen — wartet auf User-Action (manueller Lauf bei nächster Saison-Planung)

---

## Pfad C — Pause (Default)

**Wann:** Wenn weder Pfad A noch Pfad B aktiv ist und keine neuen Anforderungen aufkommen.

**Aktivitäten:**
- Echte Nutzer-Erfahrung sammeln (1-2 Saisons)
- Auf konkrete Schmerzpunkte reagieren, statt spekulativ Features bauen
- Dependabot-PRs durchgehen, CodeQL-Findings prüfen
- Bei Bedarf einzelne Bugs aus User-Feedback adressieren

**Status:** Permanent verfügbar zwischen aktiven Sprints

---

## Nicht-priorisierte / zurückgestellte Items

Aus BACKLOG.md übernommen, nicht im aktuellen Plan:

| Item | Grund |
|---|---|
| Multi-Saison-Planung | Niche-Use-Case; FLVD plant typisch eine Saison auf einmal |
| REST-API für externe Integration | Nur sinnvoll wenn konkrete Integration geplant |
| F1-H5 (Phase-2-Dekomposition) | 2-3 Wochen Refactor, Risiko sinkender Lösungsqualität; nicht prio |
| stdout-Interleaving Phase-1 | Kosmetisch, kein Absturzrisiko |

Diese werden nicht aktiv ignoriert — sie können jederzeit gefördert werden, wenn ein konkreter Treiber kommt.

---

## Reihenfolge & Versions-Plan

| Sprint | Version (vsl.) | Inhalt |
|---|---|---|
| A1 | v1.9.0 | Karten-Visualisierung |
| A2 | v1.10.0 | Interaktive Kalenderansicht |
| B1 | v1.10.1 | Gap-Monitoring |
| B2 | v1.10.2 | Doku-Update |
| B3 | (manuell) | Real-World-Verifikation, ergänzt CLAUDE.md / BACKLOG.md mit Messwerten |

Nach B3 wird der Pfad-C-Modus aktiviert, bis neue Anforderungen kommen.
