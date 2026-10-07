# Signal-Scanner – Nasdaq 100

**Dein Dashboard:** <https://jannikheese-afk.github.io/Trading-Scanner/>
(funktioniert, sobald GitHub Pages eingeschaltet ist – siehe Schritt 4)

Prüft jeden Abend automatisch alle Nasdaq-100-Aktien auf deine Indikator-Signale
und zeigt die Treffer auf einer eigenen Webseite – auch auf dem Handy.

**Geprüft wird (Tageschart):**

| Indikator | Signal |
|---|---|
| RSI (14) | unter 30 = überverkauft ▲, über 70 = überkauft ▼ |
| MACD (12, 26, 9) | MACD kreuzt die Signallinie ▲▼ |
| Gleitende Durchschnitte | Golden/Death Cross (SMA 50/200), Kurs kreuzt EMA 20 bzw. EMA 50 ▲▼ |
| Trendbasierte Fibonacci-Extension | Abwärtstrend (Hoch A → Tief B → tieferes Hoch C): Kurs erreicht 100 % oder 138,2 % = mögliche Kaufzone ▲. Aufwärtstrend (Tief → Hoch → höheres Tief): Kursziel erreicht ▼. ◆ = Kurs nähert sich dem Level. |
| Liquidity Swings (nach LuxAlgo) | Schlusskurs bricht durch eine Swing-Zone, in der sich viel Volumen gesammelt hat ▲▼ |

Kreuzungen zählen, wenn sie in den letzten 3 Handelstagen passiert sind. Alles lässt sich in `config.py` einstellen.

---

## Einrichtung (einmalig, ca. 10 Minuten, am besten am Computer)

### 1. GitHub-Account anlegen
Auf <https://github.com/signup> kostenlos registrieren.

### 2. Neues Repository erstellen
1. Oben rechts auf **+** → **New repository**
2. Name: `signal-scanner`
3. **Public** auswählen (nötig, damit die Webseite im kostenlosen Plan funktioniert)
4. Keine weiteren Häkchen → **Create repository**

### 3. Dateien hochladen
1. Die ZIP-Datei entpacken.
2. Auf der neuen Repository-Seite auf **uploading an existing file** klicken.
3. **Den Inhalt** des Ordners `signal-scanner` (nicht den Ordner selbst) ins Browserfenster ziehen –
   inklusive der Ordner `docs` und `.github`.
4. Unten auf **Commit changes**.

> **Wichtig:** `.github` ist ein versteckter Ordner.
> Mac: im Finder `Cmd + Shift + .` drücken, dann wird er sichtbar.
> Windows: im Explorer *Ansicht → Einblenden → Ausgeblendete Elemente*.
>
> Falls er trotzdem fehlt: **Add file → Create new file**, als Namen
> `.github/workflows/scan.yml` eintippen (die Schrägstriche legen die Ordner an),
> den Inhalt der Datei `scan.yml` hineinkopieren und speichern.

### 4. Webseite einschalten
1. Im Repository: **Settings → Pages**
2. Bei *Source*: **Deploy from a branch**
3. Branch: **main**, Ordner: **/docs** → **Save**
4. Nach 1–2 Minuten steht oben die Adresse, z. B. `https://DEINNAME.github.io/signal-scanner/`

Dort siehst du zuerst eine **Demo-Ansicht** mit erfundenen Kursen.

### 5. Ersten echten Scan starten
1. Reiter **Actions** öffnen (falls gefragt: *I understand my workflows, go ahead and enable them*)
2. Links **Täglicher Scan** → rechts **Run workflow** → grüner Knopf **Run workflow**
3. Nach 2–3 Minuten ist er fertig (grüner Haken). Webseite neu laden – jetzt mit echten Daten.

Ab jetzt läuft der Scan **Montag bis Freitag um 22:30 UTC** automatisch
(00:30 Uhr deutscher Sommerzeit, 23:30 Uhr Winterzeit), also nach US-Börsenschluss.
Morgens beim Kaffee ist alles aktuell.

### 6. Aufs Handy
Webseite im Browser öffnen → **Teilen → Zum Home-Bildschirm**. Dann startet sie wie eine App.

---

## Einstellungen ändern

Alle Schwellenwerte stehen in **`config.py`** und sind auf Deutsch kommentiert.
Auf GitHub: Datei öffnen → Stift-Symbol → ändern → **Commit changes**.
Der nächste Scan benutzt die neuen Werte (oder sofort per *Run workflow*).

Beispiele:
- Nur heutige Kreuzungen: `SIGNAL_LOOKBACK_BARS = 1`
- Fibonacci-Ziele im Aufwärtstrend ausblenden: `FIB_SIGNAL_UPTREND = False`
- Nur sehr starke Liquiditätszonen: `LIQ_MIN_VOLUME_FACTOR = 10`

---

## So ist das Projekt aufgebaut

| Datei | Was sie macht |
|---|---|
| `config.py` | Alle Einstellungen |
| `scanner.py` | Hauptprogramm: Aktienliste laden → Kurse holen → auswerten → Webseite schreiben |
| `indicators.py` | Die Berechnungen (RSI, MACD, Durchschnitte, Fibonacci, Liquidität) |
| `template.html` | Aussehen des Dashboards; die Daten werden beim Scan eingesetzt |
| `tickers_nasdaq100.csv` | Aktienliste (wird automatisch von Wikipedia aktualisiert) |
| `.github/workflows/scan.yml` | Der Zeitplan, der den Scan jeden Abend startet |
| `docs/` | Die fertige Webseite (wird bei jedem Scan neu erzeugt) |
| `docs/history/` | Pro Tag eine kleine Datei mit allen Signalen – gut für spätere Auswertungen |

### Lokal ausprobieren (optional, z. B. mit Claude Code)
```bash
pip install -r requirements.txt
python scanner.py --demo   # ohne Internet, mit erfundenen Kursen
python scanner.py          # echter Scan
```
Danach `docs/index.html` im Browser öffnen.

---

## Gut zu wissen

- **Öffentlich:** Im kostenlosen GitHub-Plan sind Repository und Webseite öffentlich.
  Wer den Link kennt, kann die Signale sehen. Suchmaschinen sind per `noindex` ausgesperrt.
- **Datenquelle:** Yahoo Finance über die Bibliothek `yfinance` (inoffiziell, kostenlos).
  Fällt sie mal aus, schickt GitHub dir eine E-Mail und das Dashboard zeigt den letzten Stand.
- **Pause durch GitHub:** Bei öffentlichen Repositories kann GitHub geplante Abläufe nach
  60 Tagen ohne Aktivität pausieren. Dann bekommst du eine E-Mail – im Reiter *Actions*
  einfach wieder aktivieren.
- **Liquidity Swings:** Die Logik ist dem offenen Skript „Liquidity Swings [LuxAlgo]“
  nachempfunden (Lizenz CC BY-NC-SA 4.0). Für private Nutzung kein Problem –
  falls du daraus ein kommerzielles Produkt machst, die Lizenz beachten.
- **Keine Anlageberatung.** Die Signale sind ein Werkzeug zum Vorfiltern, die
  Entscheidung triffst du im Chart.

## Ideen für später
- Push-Nachricht aufs Handy (z. B. Telegram), wenn eine Aktie mehrere Signale gleichzeitig hat
- Weitere Indizes (DAX, S&P 500) als eigene Seiten
- Auswertung der `history/`-Dateien: Wie gut waren die Signale im Rückblick?
