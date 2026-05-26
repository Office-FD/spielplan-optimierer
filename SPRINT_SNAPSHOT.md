# Sprint-Snapshot — Spielplan-Optimierer

> **Stand: 26. Mai 2026, Version 1.11.3** · Keine bekannten Bugs · Alle CI-Workflows grün

---

## Was wurde in dieser Iteration erreicht (v1.6.2 → v1.11.3)

In 18 Releases (9 Feature/Sprint-Tags + 9 Hotfix/Patch-Tags) wurden drei strategische Ziele umgesetzt:

### 1) Qualitätssicherung (v1.7.0 + v1.7.1)
- **CI-Quality-Sprint Q1** — Ruff-Linter im CI, Dependabot wöchentlich, Pre-Commit-Hook, CodeQL-Security-Scan
- **Test-Coverage Q2** — Coverage 67.8 % → **77.5 %** (+42 Tests, 1 Validator-Bugfix als Nebenfund)

### 2) Solver-Optimierung (v1.8.0 + v1.8.1)
- **F1 Sprint** — Phase-2-Optimierungslücke reduziert durch 3 Hebel:
  - H1: `symmetry_level=2` + bool_core-OOM-Schutz
  - H3: Switch-Term-Obergrenze pro Team (`n_transitions - consecutive_dst`)
  - H2: Phase-1→Phase-2 Hint-Boost (switch, sw_count, travel, min/max)
- **Erwartete Gap-Reduktion: ~25 %** (theoretisch, Verifikation siehe B3)

### 3) Endnutzer-Features (v1.9.x – v1.11.x)
- **🗺 Karten-Visualisierung** (v1.9.0–v1.9.2) — folium + Nominatim-Geocoding, Adressen-Editor für fehlende Standorte
- **📅 Kalenderansicht** (v1.10.0–v1.10.1) — Monats-/Wochen-/Listenansicht via streamlit-calendar, KW-Fallback für Multi-Liga
- **📊 Solver-Telemetrie** (v1.11.0–v1.11.3) — Objective, Best Bound, Gap %, Improvements + Live-Chart + CSV-Export + JSON-Persistenz
- **Doku-Update** (v1.11.2) — BENUTZERHANDBUCH auf v1.11-Stand, UI-konsistente Schritt-Nummerierung

### 4) Dependabot-Aufholjagd (Mai 2026)
9 PRs gemerged in einer Sitzung:
- Actions: checkout 4→6, setup-python 5→6, codeql-action 3→4, action-gh-release 2→3
- Python: requests 2.34.2, numpy 2.4.6, ortools 9.15.6755, **streamlit 1.57.0**, **pandas 3.0.3**

---

## Pre-F1-Referenz für die kommende Vorher/Nachher-Verifikation (B3)

**Datensatz:** 8h-Lauf vom 23.05.2026 mit 4 Ligen unter v1.6.x (vor F1)
**Pfad:** `Spielplaene/telemetrie/pre_F1_2026-05-23_8h.csv` + `_summary.md`

| Kennzahl | Wert |
|---|---|
| Objective | 690.496.530 |
| Best Bound | 862.666.720 |
| **Gap** | **19.96 %** |
| Improvements | 72 |
| Walltime | 28.810 s (~8 h 0 min) |

**Erwartung post-F1:** Gap **14–16 %** bei gleicher Konfig und Laufzeit. Verifikation beim nächsten realen Saison-Lauf mit v1.11.x — Telemetrie-CSV ist dort automatisch exportierbar, JSON-Sitzung speichert sie persistent.

---

## Was noch offen ist

| Aufgabe | Status | Größe | Wer? |
|---|---|---|---|
| **B3** — post-F1 8h-Lauf + CSV-Vergleich | Wartet auf Saison | Mittel (Wartezeit) | Martin |
| **Installer neu bauen** — Bootstrap mit folium/streamlit-folium/streamlit-calendar | Nice-to-have | Klein (~30 min) | Martin |
| F1-H5 (Phase-2-Dekomposition) | Future-Work | Sehr groß (2-3 Wo) | — |
| Multi-Saison-Planung | Backlog | Groß | — |
| REST-API | Backlog | Groß | — |

---

## Architekturzustand v1.11.3

**Stärken:**
- Test-Coverage 77.5 %, alle Core-Module ≥ 70 %
- 100 % CI-grün (Tests, Coverage, CodeQL, Release-Workflows)
- Solver mit drei Optimierungs-Hebeln aktiviert + Telemetrie-Tracking
- 3 UX-Features (Karte, Kalender, Telemetrie) ergänzen Excel-Export
- Auto-Updater mit atomarem Rollback (v1.6.1)
- JSON-Sitzungs-Schema 1.1 mit Telemetrie-Persistenz, backward-compatible zu 1.0

**Schwächen / Bekannte Einschränkungen:**
- Endnutzer-Installation noch ohne neue Karten-/Kalender-Pakete (Bootstrap-Installer muss neu gebaut werden)
- F1-Effektivität noch nicht real verifiziert (B3 ausstehend)
- Phase-2-Gap typisch immer noch 15–20 % bei langen Läufen (LP-Bound-Limitierung, H1+H3+H2 reduzieren, H5 wäre nächste Stufe)

---

## Roadmap-Quellen

- **`ROADMAP.md`** — Pfad-A/B/C-Detailplan
- **`BACKLOG.md`** — Einzel-Items mit Status
- **`CLAUDE.md`** Section 9 — Sprint-für-Sprint-Historie mit allen Code-Änderungen
- **`SPRINT_SNAPSHOT.md`** (diese Datei) — Kompakte Übersicht

---

*Generiert: 2026-05-26 nach Abschluss Sprint B1+B2+Bonus-4. Nächstes Update sinnvoll: nach B3-Verifikation oder bei nächster Sprint-Welle.*
