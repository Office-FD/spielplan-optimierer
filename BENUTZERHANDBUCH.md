# Benutzerhandbuch – Spielplan-Optimierer

---

## Überblick

Der Spielplan-Optimierer erstellt automatisch optimierte Spielpläne für
Floorball-Ligen. Sie werden durch einen **8-stufigen Assistenten (Wizard)**
geführt. Am Ende startet die Optimierung und Sie erhalten die Spielpläne
als Excel-Datei zum Herunterladen.

**Typischer Ablauf:**

```
Schritt 0  Ligen und Teams eingeben
Schritt 1  Distanzen zwischen den Spielorten festlegen
Schritt 2  Rahmenterminplan laden und Doppelspieltage konfigurieren
Schritt 3  Optimierungsgewichte einstellen
Schritt 4  Pflichtspiele festlegen (optional)
Schritt 5  Sperrtage eingeben (optional)
Schritt 6  Co-Home-Vereine konfigurieren (optional)
Schritt 7  Solver-Einstellungen wählen
Schritt 8  Optimierung starten → Ergebnisse herunterladen
```

---

## Programm starten

Doppelklicken Sie auf die Desktop-Verknüpfung **„Spielplan-Optimierer"**.
Nach 10–15 Sekunden öffnet sich Ihr Browser automatisch.

Die Adresse lautet: `http://localhost:8501`

> Bei einem Update-Hinweis beim Start empfehlen wir, das Update zu
> installieren (Klick auf „Ja").

---

## Schritt 0 – Ligen und Teams

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

## Schritt 1 – Distanzmatrizen

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

## Schritt 2 – Kalender und Doppelspieltage

**Rahmenterminplan laden:**
Laden Sie die Excel-Datei mit dem Rahmenterminplan des Verbands hoch.
Das Tool liest automatisch alle Spielwochenenden ein.

**Doppelspieltage (DST):**
Doppelspieltage sind Wochenenden, an denen Teams zweimal spielen
(Samstag und Sonntag). An DST-Tagen haben beide Teams das gleiche Heimrecht.

- Wählen Sie die Spieltag-Paare aus, die als Doppelspieltag gelten sollen
- Das Tool macht automatisch Vorschläge basierend auf dem Kalender

---

## Schritt 3 – Optimierungsgewichte und DST-Routing

**Optimierungsgewichte:**
Steuern Sie, was bei der Optimierung wichtiger ist:

| Gewicht | Bedeutung |
|---|---|
| Heimrecht-Wechsel | Wie oft wechselt ein Team zwischen Heim und Auswärts (höher = mehr Abwechslung) |
| Fairness Wechsel | Wie ausgeglichen sind die Wechsel zwischen allen Teams |
| Gesamtkilometer | Minimierung der Gesamtreisekilometer |
| Fairness km | Wie ausgeglichen sind die Reisekilometer zwischen allen Teams |

Schieberegler von 0 (egal) bis 10 (sehr wichtig).
Für die meisten Ligen sind die Standardwerte ein guter Ausgangspunkt.

**DST-Routing:**
Begrenzt, wie weit ein Team am zweiten DST-Tag umweg fahren darf.
Wert „1" = kein Umweg erlaubt (selten lösbar).
Empfehlung: Wert **2 bis 3** für eine gute Balance.

**Co-Home-Gewicht:**
Gibt an, wie stark Mehrspartenvereine (z. B. Herren und Damen eines Vereins)
dazu gebracht werden, ihre Heimspiele in der gleichen Kalenderwoche zu haben.

---

## Schritt 4 – Pflichtspiele

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

## Schritt 5 – Sperrtage

Sperrtage sind Spieltage, an denen ein Team **nicht** spielen kann
(z. B. wegen Hallensperrungen, Schulferien, anderen Veranstaltungen).

**Sperrtag hinzufügen:**
1. Team auswählen
2. Spieltagnummern eingeben, an denen das Team gesperrt ist

> **Achtung:** Wie bei Pflichtspielen gilt: Zu viele Sperrtage können die
> Lösbarkeit erschweren.

---

## Schritt 6 – Co-Home-Vereine

Co-Home bedeutet: Mehrere Teams eines Vereins (z. B. Herren und Damen)
teilen sich eine Halle und sollen ihre Heimspiele möglichst in der
**gleichen Kalenderwoche** haben.

Das Tool erkennt Co-Home-Vereine anhand gleicher Ortsnamen automatisch.
Sie können die Zuordnungen hier prüfen und manuell anpassen.

---

## Schritt 7 – Solver-Einstellungen

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

## Schritt 8 – Optimierung und Ergebnisse

### Optimierung starten

Klicken Sie auf **„Optimierung starten"**. Der Fortschritt wird angezeigt.
Das Browser-Fenster **muss offen bleiben** während die Optimierung läuft.

### Ergebnisse verstehen

Nach Abschluss werden folgende Informationen angezeigt:

**Kennzahlen:**
- Gesamtkilometer aller Teams
- Durchschnittliche Wechselquote (Heimrecht-Wechsel)

**Warnungen** erscheinen bei:
- 4 oder mehr aufeinanderfolgende Heim- oder Auswärtsspiele
- Reisekilometer-Ausreißern (>35% über dem Durchschnitt)

**Fairness-Tabelle:** Zeigt für jedes Team Kilometer, Wechselquote und
Heimspielanteil.

**Spielplan:** Aufklappbar je Liga, mit farbiger Heimrecht-Übersicht.

### Downloads

| Download | Inhalt |
|---|---|
| **Excel (alle Ligen)** | Spielpläne als ZIP mit einer Excel-Datei je Liga |
| **Co-Home-Excel** | Übersicht der Heimspielwochen aller Ligen |
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
| DST-Routing zu eng | DST-Routing-Wert erhöhen (Schritt 3) |
| Zeitlimit zu kurz | Phase-1-Zeitlimit und Seeds erhöhen (Schritt 7) |
| Alle Spieltage durch DST blockiert | DST-Blöcke überprüfen (Schritt 2) |

> **Tipp:** Die Diagnose-Meldung gibt einen Hinweis auf die wahrscheinlichste
> Ursache. Starten Sie mit der dort genannten Lösung.

---

## Sitzung speichern und wiederherstellen

Alle Einstellungen können als Excel-Konfigurationsdatei gespeichert werden
(Schritt 0 → **„Download Konfiguration"**). Beim nächsten Mal laden Sie die
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
