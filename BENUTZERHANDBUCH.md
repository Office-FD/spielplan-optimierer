# Benutzerhandbuch – Spielplan-Optimierer

---

## Überblick

Der Spielplan-Optimierer erstellt automatisch optimierte Spielpläne für
Floorball-Ligen. Sie werden durch einen **9-stufigen Assistenten (Wizard)**
geführt. Am Ende startet die Optimierung und Sie erhalten die
Spielpläne als Excel-Datei zum Herunterladen.

**Typischer Ablauf:**

```
Schritt 1  Ligen und Teams eingeben
Schritt 2  Distanzen zwischen den Spielorten festlegen
Schritt 3  Rahmenterminplan laden und Doppelspieltage konfigurieren
Schritt 4  Optimierungsgewichte einstellen
Schritt 5  Pflichtspiele festlegen (optional)
Schritt 6  Sperrtage eingeben (optional)
Schritt 7  Co-Home-Vereine konfigurieren (optional)
Schritt 8  Solver-Einstellungen wählen
Schritt 9  Optimierung starten → Ergebnisse herunterladen
```

---

## Programm starten

Doppelklicken Sie auf die Desktop-Verknüpfung **„Spielplan-Optimierer"**.
Nach 10–15 Sekunden öffnet sich Ihr Browser automatisch.

Die Adresse lautet: `http://localhost:8501`

> Bei einem Update-Hinweis beim Start empfehlen wir, das Update zu
> installieren (Klick auf „Ja").

---

## Schritt 1 – Ligen und Teams

Hier legen Sie fest, für welche Ligen Sie einen Spielplan erstellen möchten.

**Liga hinzufügen:**
1. Klicken Sie auf **„+ Liga hinzufügen"**
2. Vergeben Sie eine **Liga-ID** (z. B. `1BL`, `JBLA`) und einen **Namen**
3. Wählen Sie das **Spielformat:**
   - *Einfachrunde:* Jede Paarung einmal
   - *Hin- und Rückrunde:* Jede Paarung zweimal (Standard)
   - *Turniertag:* Alle Teams treffen sich an einem Ort

**Teams eingeben:**
- Geben Sie jeden Teamnamen ein (Vereinssuche in der Datenbank möglich)
- Jedes Team benötigt einen eindeutigen **Spielort** (Hallennamen oder Ort)
- **Ungerade Teamzahl** (z. B. 5 oder 7 Teams) ist möglich: an jedem Spieltag hat dann ein Team spielfrei. Die Anzahl der Spieltage erhöht sich entsprechend (bei 5 Teams: 10 statt 8 Spieltage bei Hin- und Rückrunde).

**Konfiguration speichern / laden:**
- **Download Vorlage:** Leere Excel-Vorlage zum Ausfüllen
- **Download Konfiguration:** Aktuelle Einstellungen als Excel sichern
- **Upload Konfiguration:** Gespeicherte Einstellungen wiederherstellen

> **Tipp:** Speichern Sie Ihre Konfiguration regelmäßig. So können Sie die
> gleiche Konfiguration nächste Saison als Ausgangspunkt nutzen.

---

## Schritt 2 – Distanzmatrizen

Das Tool benötigt die Entfernungen zwischen allen Spielorten in Kilometern,
um reisekostenminimierende Spielpläne zu erstellen.

**Drei Eingabemöglichkeiten:**

**A) Manuell:**
Tragen Sie die Kilometerwerte in die angezeigte Tabelle ein.
Geeignet für kleine Ligen mit wenigen Teams.

**B) CSV/Excel hochladen:**
Laden Sie eine vorbereitete Distanzmatrix-Datei hoch.
Format: n×n Tabelle mit Orts-/Teamnamen als Zeilen- und Spaltenköpfe.

**C) Google Maps API (empfohlen):**
Das Tool berechnet die Entfernungen automatisch per Routenplaner.
Dazu benötigen Sie einen **Google Maps API-Schlüssel**.

> Einmal berechnete Distanzmatrizen werden im Ordner `.cache\` gespeichert
> und müssen nicht erneut abgerufen werden.

---

## Schritt 3 – Kalender und Doppelspieltage

**Rahmenterminplan laden:**
Laden Sie die Excel-Datei mit dem Rahmenterminplan des Verbands hoch.
Das Tool liest automatisch alle Spielwochenenden ein.

**Doppelspieltage (DST):**
Doppelspieltage sind Wochenenden, an denen Teams zweimal spielen
(Samstag und Sonntag). An DST-Tagen haben beide Teams das gleiche Heimrecht.

- Wählen Sie die Spieltag-Paare aus, die als Doppelspieltag gelten sollen
- Das Tool macht automatisch Vorschläge basierend auf dem Kalender

---

## Schritt 4 – Optimierungsgewichte und DST-Routing

**Optimierungsgewichte:**
Steuern Sie, was bei der Optimierung wichtiger ist:

| Gewicht | Bedeutung |
|---|---|
| Heimrecht-Wechsel | Wie oft wechselt ein Team zwischen Heim und Auswärts (höher = mehr Abwechslung) |
| Fairness Wechsel | Wie ausgeglichen sind die Wechsel zwischen allen Teams |
| Gesamtkilometer | Minimierung der Gesamtreisekilometer |
| Fairness km | Wie ausgeglichen sind die Reisekilometer zwischen allen Teams |
| DST-Reiseeffizienz | Belohnt DST-Blöcke mit räumlich nahen Auswärtsspielen (Randlagen-Teams profitieren). Standard: 0 (aus). |
| Heim-Balance pro Runde | Bestraft progressive Abweichung der Heim-Anzahl pro Team und Runde vom Mittelwert (sw_fair-ähnlich, aber pro Runde). Default: 0 (aus); Empfehlung: 5 wenn aktiviert. |

Schieberegler von 0 (egal) bis 10 (sehr wichtig).
Für die meisten Ligen sind die Standardwerte ein guter Ausgangspunkt.

**DST-Routing:**
Begrenzt, wie weit ein Team am zweiten DST-Tag umweg fahren darf.
Wert „1" = kein Umweg erlaubt (selten lösbar).
Empfehlung: Wert **2 bis 3** für eine gute Balance.

**Reise-Entlastung für Randlagen-Teams (optional):**
Weit abgelegene Teams (z. B. Hamburg, München) können von der normalen
Heim-/Auswärts-Balance der Doppelspieltage ausgenommen werden, damit ihre
langen Fahrten in **Auswärts-Doppelwochenenden gebündelt** werden.

- Der Abschnitt erscheint nur, wenn mindestens eine Liga **2 oder mehr
  Doppelspieltage** hat.
- Wählen Sie je Liga die zu entlastenden Teams aus.
- Legen Sie pro Team die **maximale Anzahl Heim-Doppelspieltage** fest
  (0 = alle DST-Fahrten auswärts / maximale Bündelung; der Standardwert
  entspricht der normalen Balance).
- Die übrigen Teams der Liga übernehmen entsprechend **mehr** Heim-Doppelspieltage.

> **Achtung:** Werden zu viele Teams entlastet, kann der Spielplan unlösbar
> werden („Keine Lösung gefunden"). Empfehlung: höchstens etwa ein Viertel
> der Teams einer Liga.

**Co-Home-Gewicht:**
Gibt an, wie stark Mehrspartenvereine (z. B. Herren und Damen eines Vereins)
dazu gebracht werden, ihre Heimspiele in der gleichen Kalenderwoche zu haben.

---

## Schritt 5 – Pflichtspiele

Hier können Sie festlegen, dass bestimmte Spiele an einem bestimmten Spieltag
stattfinden müssen (z. B. Eröffnungsspiel, Stadtderby).

**Pflichtspiel hinzufügen:**
1. Klicken Sie auf **„+ Pflichtspiel hinzufügen"**
2. Wählen Sie **Heimteam**, **Auswärtsteam** und **Spieltag**
3. Heimrecht ist optional – leer lassen wenn beliebig

> **Achtung:** Zu viele Pflichtspiele können dazu führen, dass keine Lösung
> gefunden wird. Im Zweifelsfall lieber wenige, wichtigste Pflichtspiele
> festlegen.

---

## Schritt 6 – Sperrtage

Sperrtage sind Spieltage, an denen ein Team **nicht** spielen kann
(z. B. wegen Hallensperrungen, Schulferien, anderen Veranstaltungen).

**Sperrtag hinzufügen:**
1. Team auswählen
2. Spieltagnummern eingeben, an denen das Team gesperrt ist

> **Achtung:** Wie bei Pflichtspielen gilt: Zu viele Sperrtage können die
> Lösbarkeit erschweren.

---

## Schritt 7 – Co-Home-Vereine

Co-Home bedeutet: Mehrere Teams eines Vereins (z. B. Herren und Damen)
teilen sich eine Halle und sollen ihre Heimspiele möglichst in der
**gleichen Kalenderwoche** haben.

Das Tool erkennt Co-Home-Vereine anhand gleicher Ortsnamen automatisch.
Sie können die Zuordnungen hier prüfen und manuell anpassen.

---

## Schritt 8 – Solver-Einstellungen

Diese Einstellungen beeinflussen Rechenzeit und Qualität des Ergebnisses.

| Einstellung | Empfehlung |
|---|---|
| **Seeds** | 2–3 (mehrere Startpunkte = besseres Ergebnis) |
| **Phase 1 Zeitlimit** | 60–900 Sek. je Liga (längere Zeit = besseres Ergebnis) |
| **Phase 2 Preset** | „Standard" für 1–2 Ligen; „Nachtlauf" für 3+ Ligen |
| **Phase 3 (SA)** | 120 Sek. reicht fast immer; 0 deaktiviert SA |

**Richtwerte für die Gesamtdauer:**
- 1 Liga, 2 Seeds, Standard-Einstellungen: ~20–30 Minuten
- 2 Ligen, 3 Seeds: ~1–2 Stunden
- 3+ Ligen: Über Nacht laufen lassen (Nachtlauf-Preset)

> **Tipp:** Starten Sie mit kürzeren Zeiten für einen ersten Entwurf.
> Für den finalen Spielplan die Zeiten erhöhen.

---

## Schritt 9 – Optimierung und Ergebnisse

### Optimierung starten

Klicken Sie auf **„Optimierung starten"**. Der Fortschritt wird angezeigt.
Das Browser-Fenster **muss offen bleiben** während die Optimierung läuft.

### Ergebnisse verstehen

Nach Abschluss werden folgende Informationen angezeigt:

**Kennzahlen:**
- Gesamtkilometer aller Teams
- Durchschnittliche Wechselquote (Heimrecht-Wechsel)

**Solver-Telemetrie (📊, seit v1.11):**
- **Objective** – erreichter Zielfunktionswert
- **Best Bound** – theoretisches Optimum (LP-Schranke)
- **Gap** – wie nah am Optimum: `|Bound − Objective| / |Bound|`
  - 0 % = bewiesen optimal
  - <5 % = sehr gute Lösung
  - 15–20 % = typisch bei langen Phase-2-Läufen
- **Improvements** – wie viele neue Bestlösungen während des Laufs gefunden wurden
- **Verlaufs-Chart** zeigt den Objective über die Zeit
- **CSV-Download** für externe Auswertung / Vergleich mit anderen Läufen

**Warnungen** erscheinen bei:
- 4 oder mehr aufeinanderfolgende Heim- oder Auswärtsspiele
- Reisekilometer-Ausreißern (>35% über dem Durchschnitt)

**Fairness-Tabelle:** Zeigt für jedes Team Kilometer, Wechselquote und
Heimspielanteil.

**Spielplan:** Aufklappbar je Liga, mit farbiger Heimrecht-Übersicht.

**Karten-Visualisierung (🗺, seit v1.9):**
Klick auf **„Karte erstellen / aktualisieren"** zeigt die Standorte aller Teams
auf einer Karte (OpenStreetMap), mit Verbindungslinien zwischen den Paarungen.
Liga-Layer oben rechts umschaltbar.

- **Erste Erstellung dauert einige Sekunden pro neuer Adresse** (Geocoding via
  OpenStreetMap, danach lokal gecacht — Folge-Aufrufe sind sofort fertig)
- **Tooltip auf Marker:** Team-Name, Standort, Liga
- **Tooltip auf Linie:** Paarung, km-Distanz, alle Spieltage
- **Fehlende Adressen:** Erscheinen in einem Expander „📍 N Adresse(n) manuell
  ergänzen" — dort lat/lon-Koordinaten aus Google Maps eintragen, Speichern
  schreibt sie in den Cache für künftige Karten

**Kalenderansicht (📅, seit v1.10):**
Interaktiver Monats-/Wochen-/Listen-Kalender direkt in der App.

- Buttons oben rechts: Monat / Woche / Liste
- Wechsel zwischen Spielzeiten- (Wochenansicht) und Übersichtsdarstellung (Monatsansicht)
- Voraussetzung: Rahmenterminplan in Schritt 3 geladen oder KW pro Spieltag gesetzt

### Downloads

| Download | Inhalt |
|---|---|
| **Excel (alle Ligen)** | Spielpläne als ZIP mit einer Excel-Datei je Liga |
| **Co-Home-Excel** | Übersicht der Heimspielwochen aller Ligen |
| **Hallenbelegungsplan** | Liga-übergreifende Hallenbelegung pro Tag |
| **Gesamtübersicht** | Alle Spielpläne nebeneinander mit Co-Home-Markierung |
| **Telemetrie-CSV** | Gap-Verlauf des Solvers (für externe Auswertung) |
| **iCal** | Kalender-Datei zum Import in Outlook, Google Kalender etc. |
| **Druckansicht** | Spielpläne als HTML-Seite zum Ausdrucken |

---

## Spielplan nachbearbeiten

Nach der Optimierung können Sie den Spielplan direkt im Tool anpassen.

### Spiel verschieben

1. Wählen Sie im Spielplan das gewünschte Spiel
2. Klicken Sie auf **📅** (Verschieben)
3. Wählen Sie den neuen Spieltag aus der Liste freier Termine

### Spiel absagen und Nachholtermin eintragen

1. Wählen Sie das abgesagte Spiel
2. Klicken Sie auf **❌** (Absagen)
3. Das Spiel wird entfernt
4. Wählen Sie anschließend einen **Nachholtermin** aus der Liste

### Heim/Auswärts tauschen

Klicken Sie im Spielplan auf das Heimrecht-Symbol eines Spiels,
um Heim- und Auswärtsteam zu tauschen.

---

## Spielpläne vergleichen

Laden Sie eine früher exportierte Excel-Datei hoch, um zwei Varianten
direkt zu vergleichen (Unterschiede in km und Wechselquote werden angezeigt).

---

## „Keine Lösung gefunden" – Was tun?

Wenn der Solver keine Lösung findet, erscheint eine Diagnose-Meldung.
Häufigste Ursachen und Lösungen:

| Ursache | Lösung |
|---|---|
| Zu viele Pflichtspiele | Pflichtspiele reduzieren |
| Zu viele Sperrtage | Sperrtage reduzieren oder Solver-Zeitlimit erhöhen |
| DST-Routing zu eng | DST-Routing-Wert erhöhen (Schritt 4) |
| Zeitlimit zu kurz | Phase-1-Zeitlimit und Seeds erhöhen (Schritt 8) |
| Alle Spieltage durch DST blockiert | DST-Blöcke überprüfen (Schritt 3) |

> **Tipp:** Die Diagnose-Meldung gibt einen Hinweis auf die wahrscheinlichste
> Ursache. Starten Sie mit der dort genannten Lösung.

---

## Sitzung speichern und wiederherstellen

Alle Einstellungen können als Excel-Konfigurationsdatei gespeichert werden
(Schritt 1 → **„Download Konfiguration"**). Beim nächsten Mal laden Sie die
Datei einfach wieder hoch und alle Einstellungen sind wiederhergestellt.

---

## Tipps für gute Ergebnisse

- **Mehr Seeds = besseres Ergebnis:** 3 Seeds statt 1 kostet dreimal so lange,
  liefert aber deutlich bessere Spielpläne.
- **Phase 3 aktiviert lassen:** Simulated Annealing reduziert die Gesamtkilometer
  nochmals um typisch 3–8%.
- **Co-Home konsequent nutzen:** Wenn Vereine mit mehreren Teams mitmachen,
  spart das Hallenwarte und Fahrten.
- **Konfiguration dokumentieren:** Laden Sie nach der Optimierung die
  Konfiguration herunter und benennen Sie die Datei mit Saison und Liga
  (z. B. `Konfiguration_2026-27_Bundesligen.xlsx`).

---

## Support

Bei Fragen oder Problemen wenden Sie sich an:

**FLOORBALL VERBAND DEUTSCHLAND e.V. – IT** · it@floorball.de

Fehler und Verbesserungsvorschläge können auch direkt in der App gemeldet werden (Sidebar-Button „Funktionswunsch / Fehler melden").
