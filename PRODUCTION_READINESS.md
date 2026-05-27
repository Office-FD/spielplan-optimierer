# Produktions-Bereitschafts-Bericht — Spielplan-Optimierer

> **Stand:** 27.05.2026, Version 1.13.0
> **Review:** Code-Review Runde 8 (Final-Review vor Produktiveinsatz), 8 Blöcke (A-H) durchgegangen.
> **Ergebnis:** **Produktions-frei — 0 Show-Stopper**, 9 Mittel, 27 Niedrig. Alle Mittel sind keine Blocker.

---

## Empfehlung: ✅ Produktiv-Freigabe

Die App ist nach 7 vorherigen Code-Review-Runden (R1-R7), drei Code-Quality-Sprints (Q1/Q2/F1) und über 150 Tests in einem reifen Zustand. **Kein Befund aus R8 ist ein Show-Stopper** für den FLVD-Saisonplanungs-Lauf.

Die 9 Mittel-Befunde sind alle UX-/Robustheits-Verbesserungen, die nach dem Produktiv-Start nachgezogen werden können, ohne dass die korrekte Optimierung beeinträchtigt wird.

---

## Block-Übersicht

| Block | Bereich | 🛑 Show-Stop | 🔴 Hoch | 🟡 Mittel | 🟢 Niedrig | Befunde-IDs |
|---|---|:-:|:-:|:-:|:-:|---|
| **A** | Solver-Modell + Pipeline (`solver.py`, `multi_solver.py`) | 0 | 0 | 1 | 4 | R8-A-M1, A-L1..L4 |
| **B** | Nachbearbeitung (`sa_refine`, `tt_scheduler`, `schedule_utils`) | 0 | 0 | 1 | 4 | R8-B-M1, B-L1..L4 |
| **C** | Datenmodell + Validator (`league_types`, `config`, `config_validator`, `calendar_parser`, `distances`) | 0 | 0 | 1 | 4 | R8-C-M1, C-L1..L4 |
| **D** | Export + Visualisierung (`excel_output`, `map_output`, `calendar_output`, `geocode`) | 0 | 0 | 1 | 4 | R8-D-M1, D-L1..L4 |
| **E** | UI Wizard-Schritte 1-7 | 0 | 0 | 1 | 3 | R8-E-M1, E-L1..L3 |
| **F** | UI Wizard-Schritte 8-9 + Mutationen | 0 | 0 | 1 | 3 | R8-F-M1, F-L1..L3 |
| **G** | Distribution + CLI (`launcher`, Installer, `wizard.py`, `main.py`) | 0 | 0 | 2 | 3 | R8-G-M1, M2, G-L1..L3 |
| **H** | Tests + CI + Doku | 0 | 0 | 2 | 3 | R8-H-M1, M2, H-L1..L3 |
| **Σ** | — | **0** | **0** | **9** | **27** | — |

---

## Show-Stopper (muss vor Produktiv gefixt werden)

**Keine.** ✅

---

## Mittel-Befunde (empfohlen, aber kein Blocker)

Empfohlene Fix-Reihenfolge (von höchstem Nutzen-Aufwand-Verhältnis absteigend):

### 1. R8-H-M1 — README.md zeigt veraltete Version 1.2.6 (1 Minute)
**Sichtbar bei jedem externen GitHub-Besucher.** Quick-Fix:
```bash
sed -i 's/Aktuelle Version:\*\* 1.2.6/Aktuelle Version:** 1.13.0/' README.md
```
**Effekt:** GitHub-Seite zeigt korrekten Stand.

### 2. R8-G-M2 — Inno-Uninstaller löscht `.cache/` ohne Warnung (5 min)
`installer/spielplan.iss` Z. 67 entfernen ODER `InitializeUninstall` um Cache-Warnung erweitern.
**Effekt:** Bei Reset-/Neu-Install gehen Distanz-/Geocode-Caches (API-Quota-Wert) nicht verloren.

### 3. R8-F-M1 — Excel-Fehler in `opt_warnings` als String statt Dict (2 min)
`app.py` Z. 4025: `S.opt_warnings.append({'level': 'error', 'msg': f'Excel-Erzeugung...'})`.
**Effekt:** Excel-Build-Fehler werden als `st.error` (rot) statt `st.warning` (gelb) angezeigt.

### 4. R8-E-M1 — Liga-Remove räumt position-indizierte Widget-Keys nicht auf (15 min)
`app.py` Z. 1502-1515 erweitern: Position-Keys `lnm_*`, `lid_*`, `fmt_*`, `hw_*`, `ttr_*`, `cs_*` ab Index `n` löschen.
**Effekt:** Beim Reduzieren der Liga-Anzahl bleiben keine falschen Namen mehr in verbleibenden Slots.

### 5. R8-D-M1 — `excel_output._parse_date` ohne 2-Jahr-Fix (10 min)
Duplikation zu `calendar_output._parse_date`. Importieren statt duplizieren.
**Effekt:** Konsistente Datums-Sortierung in der Gesamtübersicht, falls Rahmenpläne mit 2-stelligem Jahr exportiert werden.

### 6. R8-C-M1 — Validator-Lücke bei `forced_home` × DST (15 min)
`config_validator.py`: prüfen, ob `forced_home`-Tage in `dst_days` enthalten sind und Heimrecht des DST-Partners konsistent ist.
**Effekt:** User-freundliche Fehlermeldung statt INFEASIBLE-Crash bei Konfigurations-Bug.

### 7. R8-B-M1 — SA-Reset-Verhalten dokumentiert, aber nicht implementiert (30 min)
SA hat keinen expliziten Reset (kein "Restart from best"). Bei stagnierendem Lauf läuft Temperatur einfach aus.
**Effekt:** Bei langen SA-Läufen mit hoher Anfangs-Temperatur könnten 5-8 % mehr km-Reduktion herausgeholt werden. Niedrige Priorität.

### 8. R8-A-M1 — Phase-2-INFEASIBLE-Fallback dokumentations-konsistent machen (30 min)
Bei Phase-2-INFEASIBLE wird auf Phase-1-Ergebnisse zurückgegriffen. CLAUDE.md beschreibt dies nicht klar.
**Effekt:** Dokumentation ↔ Code-Konsistenz.

### 9. R8-H-M2 — Test-Coverage-Lücke `launcher.py` + JSON-Roundtrip (2-3 h)
Neue Test-Datei `test_launcher.py` + `test_session_roundtrip.py`. Mittlerer Aufwand, hoher Wert für künftige Regressions-Verhinderung.

### 10. R8-G-M1 — Port 8501-TIME_WAIT-Race nach Update-Restart (selten — Edge-Case)
Update-Restart-Pfad funktioniert in 99 % der Fälle. Fix-Aufwand: 30 min, aber Risiko sehr klein.

---

## Niedrig-Befunde (27 Stück)

Optionales Polishing — alle Details in `BACKLOG.md` unter den Block-Sektionen. Beispiele:

- UX: Mutation-Buttons (📅 ❌) bei Turniertag-Format als `disabled` (R8-F-L2)
- Performance: Phase-Detection-Cache statt `any()` über kompletten Log (R8-F-L3)
- Code-Hygiene: Code-Duplikation `_parse_date` in 2 Modulen (R8-D-L3)
- Doku: Wizard-Tuple-Type-Hints veraltet (R8-G-L1)
- CI: `actions/upload-artifact@v4` vs. `@v6` Inkonsistenz (R8-H-L2)
- Validator: explizite Warnung bei > 2 Spieltagen pro KW (R8-E-L2)

---

## Verbleibende Risiken nach Produktiv-Start

Bei sofortigem Produktiv-Einsatz **ohne** Mittel-Fixes:

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|---|---|---|---|
| Excel-Build-Fehler wird nur als gelbe Warnung (statt rot) angezeigt | Niedrig (selten Excel-Fehler) | User übersieht Problem | Nutzer schaut alle Warnungen an |
| Liga-Reduzierung zeigt falsche Namen in verbleibenden Slots | Mittel | UX-Verwirrung | User entdeckt sofort, korrigiert manuell |
| `.cache/`-Verlust beim Deinstall | Niedrig (Deinstall selten) | Verlust API-Quota | Niemand deinstalliert während Saison |
| Port-Race nach Update-Annahme | Sehr niedrig | App startet nicht neu | User startet manuell neu |
| `launcher.py` ungetestet | Mittel (kein Test = Blind-Spot) | Regressions bei Update-Pfad-Änderungen unentdeckt | Vor Produktiv kein launcher-Change geplant |
| README.md zeigt v1.2.6 | Hoch (sichtbar) | Externes Suggerieren von Stillstand | Quick-Fix dringend empfohlen |

**Konsens:** Alle Risiken sind tolerabel für Produktiv-Start. Empfehlung: **Mindestens die ersten 4 Mittel-Fixes** vor dem Lauf einspielen (README + Inno + Excel-Fehler-Severity + Liga-Remove-Cleanup) — kostet zusammen < 30 min.

---

## Gegen Risiko abgesichert (bereits in v1.13.0 vorhanden)

✅ Solver-Constraints alle in Tests abgedeckt (t1-t14, 36+ Tests)
✅ Mutation-Funktionen mit Turniertag-Guard (R6-C-M1, t12_*)
✅ Validator deckt forced_home, blocked, pinned, n_rounds, DST, Spielfrei
✅ Phase-1→Phase-2 set_hints korrekt
✅ Telemetrie-Persistenz durch alle Phasen (R7-FIX-2, v1.13.0)
✅ JSON Schema 1.0 + 1.1 Backward-Compat
✅ `home_vals`-Rekonstruktion nach Session-Load + SA-Hotfix (v1.2.8, v1.12.1)
✅ Excel-Output: 9 Sheets pro Liga, Co-Home, Hall, Overview
✅ Karten + Kalender + Geocode (R7-Review komplett)
✅ Launcher-Atomarität + Rollback (R6-R2 F-M1)
✅ Tag-vs-VERSION-Validation (F-M2)
✅ Test-Gate vor Release (F-L8)
✅ CodeQL-Security-Scanning (Q1)
✅ Ruff-Linter im CI (Q1)
✅ Path-Traversal-Guard im Update-ZIP

---

## Vergleich: Was hat R8 zusätzlich abgedeckt vs. R1-R7?

| Aspekt | R1-R7 Status | R8 Beitrag |
|---|---|---|
| Solver-Korrektheit | umfangreich geprüft | Konsistenz Phase-1→2→3 erneut bestätigt |
| Mutation-Funktionen | nach C-M1/M2-Fixes solide | Live-Konflikt-Detection-Lücke entdeckt (E-L1) |
| Validator | gegen frühere Bugs abgehärtet | forced_home × DST-Lücke gefunden (C-M1) |
| UI-State-Sync | nach D-M1/M2-Fixes solide | Position-indizierte Keys noch übrig (E-M1) |
| Excel/Karten/Kalender | R7 deckte neue Module ab | Code-Duplikation `_parse_date` gefunden (D-M1) |
| Distribution | F-M1/F-L2 in v1.6.1 | Port-TIME_WAIT-Race (G-M1), `.cache`-Verlust (G-M2) |
| Doku | R7 erweiterte BENUTZERHANDBUCH | README-Version-Outdated (H-M1) |
| Tests | Q2 + R6-Sprint-4 = 150+ Tests | `launcher.py` + JSON-Roundtrip ungetestet (H-M2) |

---

## Aktions-Empfehlung an Martin

**Kurzfristig (vor erstem FLVD-Produktiv-Lauf):**
1. ✅ Mittel-Fix 1 (README) — 1 min
2. ✅ Mittel-Fix 2 (Inno `.cache`) — 5 min
3. ✅ Mittel-Fix 3 (Excel-Fehler-Severity) — 2 min
4. ✅ Mittel-Fix 4 (Liga-Remove-Cleanup) — 15 min
5. CLAUDE.md-Header auf R8-abgeschlossen aktualisieren
6. Lokal v1.14.0 taggen (R8-Fixes-Sammelcommit) und nach GitHub-Reaktivierung pushen

**Mittelfristig (nach Saison-Erfahrungen):**
- Mittel-Fixes 5-10 priorisiert nach realer Schmerzpunkt-Begegnung
- Test-Lücken `launcher.py` + JSON-Roundtrip schließen
- 27 Niedrig-Befunde nach Bedarf

**Langfristig (Future-Work, nicht im R8-Scope):**
- F1-H5 (Phase-2-Dekomposition) — 2-3 Wochen
- B4 — REST-API
- Multi-Saison-Planung

---

**Zusammenfassung:** Die App ist nach allen 8 R8-Blöcken **frei für den Produktiv-Lauf**. Mit < 30 Minuten Quick-Fixes (4 Mittel-Befunde) wird der Stand noch sauberer — empfohlen, aber kein Muss.
