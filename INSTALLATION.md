# Installationsanleitung – Spielplan-Optimierer

---

## Systemvoraussetzungen

| Anforderung | Mindest |
|---|---|
| Betriebssystem | Windows 10 oder Windows 11 (64-Bit) |
| Arbeitsspeicher | 4 GB RAM (8 GB empfohlen bei mehreren Ligen) |
| Speicherplatz | ca. 600 MB |
| Internetverbindung | Erforderlich bei Installation und Updates |
| Browser | Edge, Chrome oder Firefox (aktuell) |

---

## Installation

### Schritt 1 – Setup-Datei herunterladen

1. Öffnen Sie die Seite:
   **https://github.com/Office-FD/spielplan-optimierer/releases/latest**

2. Klicken Sie unter **Assets** auf die Datei
   `Spielplan-Optimierer-Setup-vX.X.X.exe`

3. Falls Ihr Browser eine Sicherheitswarnung zeigt:
   Klicken Sie auf **„Behalten"** oder **„Trotzdem herunterladen"** –
   die Datei ist sicher.

### Schritt 2 – Setup-Datei ausführen

1. Doppelklicken Sie auf die heruntergeladene Datei.

2. Falls Windows eine Sicherheitsmeldung zeigt
   (*„Windows hat Ihren PC geschützt"*):
   Klicken Sie auf **„Weitere Informationen"** und dann **„Trotzdem ausführen"**.

3. Der Installationsassistent öffnet sich. Klicken Sie auf **„Weiter"**.

4. Wählen Sie optional, ob eine **Desktop-Verknüpfung** erstellt werden soll
   (standardmäßig aktiviert). Klicken Sie auf **„Weiter"** und dann **„Installieren"**.

5. Der Installer lädt jetzt automatisch die aktuellste Programmversion
   von GitHub herunter. Dazu ist eine Internetverbindung nötig.
   > Dieser Schritt dauert je nach Verbindung 10–30 Sekunden.

6. Nach Abschluss klicken Sie auf **„Fertigstellen"**.
   Das Programm startet automatisch im Browser.

---

## Programm starten

Nach der Installation gibt es zwei Möglichkeiten das Programm zu starten:

- **Desktop-Verknüpfung** doppelklicken: `Spielplan-Optimierer`
- **Startmenü** → `Spielplan-Optimierer`

Der Browser öffnet sich automatisch. Es erscheint **kein** Kommandozeilenfenster.

> **Hinweis:** Der erste Start nach der Installation kann 10–15 Sekunden dauern,
> da der Server im Hintergrund gestartet wird.

---

## Automatische Updates

Bei jedem Programmstart prüft der Spielplan-Optimierer, ob eine neue Version
auf GitHub verfügbar ist.

Wenn ja, erscheint folgende Meldung:

> *„Version X.X.X ist auf GitHub verfügbar. Jetzt aktualisieren? (Empfohlen)"*

- **Ja:** Das Update wird heruntergeladen (~2–5 MB) und installiert.
  Das Programm startet danach wie gewohnt.
- **Nein:** Das Programm startet mit der aktuellen Version.

Das Update ändert nur die Programmdateien – Ihre gespeicherten Konfigurationen
und erstellten Spielpläne bleiben erhalten.

> **Hinweis bei neuen Versions-Features:** Wenn ein Update zusätzliche Python-
> Pakete benötigt (z. B. für die Karten-Visualisierung seit v1.9 oder die
> Kalenderansicht seit v1.10), zeigt das Programm bei der entsprechenden
> Funktion einen Hinweis mit Installationsbefehl. In der Regel löst ein
> einmaliges manuelles Update des Bootstrap-Installers (durch den IT-Support
> bereitgestellt) das Problem dauerhaft.

---

## Programm beenden

Das Programm läuft als Hintergrunddienst weiter, auch wenn Sie den Browser
schließen. So können Sie jederzeit erneut auf `http://localhost:8501` zugreifen.

Um den Hintergrunddienst vollständig zu beenden:

1. Drücken Sie `Strg` + `Alt` + `Entf` → **Task-Manager**
2. Suchen Sie in der Liste nach `python.exe`
3. Rechtsklick → **Task beenden**

---

## Deinstallation

> **Hinweis:** Beim Deinstallieren werden **alle Dateien im Programmordner gelöscht**,
> einschließlich Ihrer erstellten Spielpläne. Sichern Sie diese vorher, falls Sie
> sie behalten möchten.

Die Spielpläne befinden sich unter:
```
C:\Users\IhrName\AppData\Local\Programs\Spielplan-Optimierer\Spielplaene\
```

Das Deinstallationsprogramm öffnet diesen Ordner automatisch zur Sicherung,
bevor die Deinstallation beginnt.

1. Windows-Taste → **Einstellungen** → **Apps**
2. Suchen Sie nach `Spielplan-Optimierer`
3. Klicken Sie auf **„Deinstallieren"**
4. Falls Spielpläne vorhanden sind: Sicherheitsdialog erscheint →
   **„Ja"** öffnet den Ordner und bricht ab (danach erneut deinstallieren),
   **„Nein"** deinstalliert sofort.

---

## Häufige Probleme bei der Installation

**„Windows hat Ihren PC geschützt" – Meldung**
Das Programm ist nicht von Microsoft signiert. Klicken Sie auf
„Weitere Informationen" → „Trotzdem ausführen". Die Datei ist sicher.

**Download der App-Dateien schlägt fehl**
Prüfen Sie Ihre Internetverbindung. Falls ein Proxy oder eine Unternehmens-Firewall
aktiv ist, fragen Sie Ihren IT-Administrator ob GitHub-Verbindungen erlaubt sind
(`https://github.com` und `https://objects.githubusercontent.com`).

**Browser öffnet sich nicht automatisch**
Öffnen Sie manuell: **http://localhost:8501**

**Das Programm startet nicht nach Installation**
Starten Sie den Computer neu und versuchen Sie es erneut.
Falls das Problem bestehen bleibt, wenden Sie sich an:
it@floorball.de
