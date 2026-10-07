"""
SIGNAL-SCANNER – das Hauptprogramm.

    python scanner.py          -> echter Scan mit Kursdaten von Yahoo Finance
    python scanner.py --demo   -> Demo mit erfundenen Kursen (zum Ausprobieren ohne Internet)

Ablauf:
  1. Liste der Aktien laden (Nasdaq 100)
  2. Tageskurse der letzten 2 Jahre herunterladen
  3. Für jede Aktie alle Indikatoren berechnen (indicators.py)
  4. Ergebnis als Webseite speichern: docs/index.html  (+ docs/data.json)
"""

import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as cfg
from indicators import analyze

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
TICKER_FILE = ROOT / "tickers_nasdaq100.csv"
TEMPLATE = ROOT / "template.html"


# ---------------------------------------------------------------------------
# 1) Aktienliste
# ---------------------------------------------------------------------------

def load_tickers() -> pd.DataFrame:
    fallback = pd.read_csv(TICKER_FILE)
    if not cfg.AUTO_UPDATE_TICKERS:
        return fallback
    try:
        import requests
        html = requests.get("https://en.wikipedia.org/wiki/Nasdaq-100",
                            headers={"User-Agent": "signal-scanner/1.0 (private use)"}, timeout=20).text
        for table in pd.read_html(io.StringIO(html)):
            cols = {str(c).lower(): c for c in table.columns}
            tick_col = cols.get("ticker") or cols.get("symbol")
            name_col = cols.get("company") or cols.get("security")
            if tick_col is not None and name_col is not None and 90 <= len(table) <= 110:
                fresh = pd.DataFrame({"ticker": table[tick_col].astype(str).str.strip(),
                                      "name": table[name_col].astype(str).str.strip()})
                fresh = fresh.drop_duplicates("ticker").sort_values("ticker")
                fresh.to_csv(TICKER_FILE, index=False)  # Liste im Repo aktuell halten
                print(f"Aktienliste von Wikipedia: {len(fresh)} Werte")
                return fresh
        print("Wikipedia-Tabelle nicht gefunden – benutze tickers_nasdaq100.csv")
    except Exception as e:
        print(f"Wikipedia nicht erreichbar ({e}) – benutze tickers_nasdaq100.csv")
    return fallback


# ---------------------------------------------------------------------------
# 2) Kursdaten
# ---------------------------------------------------------------------------

def drop_unfinished_bar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Läuft der Scan während der US-Handelszeit, ist die heutige Tageskerze noch nicht fertig.
    Dann wird sie weggelassen, damit nur mit echten Schlusskursen gerechnet wird.
    """
    from zoneinfo import ZoneInfo
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    market_closed = (now_ny.hour, now_ny.minute) >= (16, 15)
    if len(df) and df.index[-1].date() == now_ny.date() and not market_closed:
        return df.iloc[:-1]
    return df


def download(tickers: list) -> dict:
    import yfinance as yf

    result = {}
    todo = [t.replace(".", "-") for t in tickers]  # Yahoo schreibt BRK.B als BRK-B
    for attempt in range(3):
        if not todo:
            break
        print(f"Lade Kurse für {len(todo)} Aktien (Versuch {attempt + 1}) ...")
        data = yf.download(todo, period=cfg.HISTORY_PERIOD, interval="1d", group_by="ticker",
                           auto_adjust=True, threads=True, progress=False)
        missing = []
        for t in todo:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if t in data.columns.get_level_values(0):
                        df = data[t]
                    else:
                        df = data.xs(t, axis=1, level=1)
                else:
                    df = data
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
                df = drop_unfinished_bar(df)
            except Exception:
                df = None
            if df is None or len(df) < 60:   # Neuzugänge mit kurzer Historie trotzdem prüfen
                missing.append(t)
            else:
                result[t] = df
        todo = missing
        if todo:
            time.sleep(20 * (attempt + 1))  # kurz warten, falls Yahoo bremst
    if todo:
        print(f"Keine Daten für: {', '.join(todo)}")
    return result


def demo_data(tickers: list) -> dict:
    """Erfundene Kursverläufe, damit man das Dashboard ohne Internet testen kann."""
    rng = np.random.default_rng(7)
    days = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=500)
    out = {}
    for k, t in enumerate(tickers):
        vol = rng.uniform(0.012, 0.035)
        drift = rng.normal(0.0004, 0.0012)
        rets = rng.normal(drift, vol, len(days))
        # ein paar Trendphasen einbauen, damit Swings entstehen
        for _ in range(4):
            a = rng.integers(0, len(days) - 60)
            rets[a:a + rng.integers(20, 60)] += rng.normal(0, vol * 0.6)
        close = 100 * rng.uniform(0.5, 6) * np.exp(np.cumsum(rets))
        open_ = np.roll(close, 1) * np.exp(rng.normal(0, vol * 0.3, len(days)))
        open_[0] = close[0]
        high = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, vol * 0.5, len(days))))
        low = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, vol * 0.5, len(days))))
        volume = rng.lognormal(15, 0.4, len(days))
        out[t] = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
                              index=days)
    return out


# ---------------------------------------------------------------------------
# 3) Auswerten
# ---------------------------------------------------------------------------

def r(x, digits=None):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if digits is None:
        digits = 2 if abs(x) >= 10 else 4
    return round(float(x), digits)


def build_stock(ticker: str, name: str, df: pd.DataFrame) -> dict:
    signals, values = analyze(df)
    close = df["Close"].to_numpy()
    n = len(df)
    s = max(0, n - cfg.CHART_BARS)  # Startindex des Mini-Charts
    if values.get("fib"):           # Chart so weit zurück, dass die ganze ABC-Struktur drauf ist
        s = max(0, n - 200, min(s, values["fib"]["points"][0]["i"] - 8))

    def series(arr):
        return [r(x) for x in arr[s:]]

    chart = dict(
        d=[d.strftime("%Y-%m-%d") for d in df.index[s:]],
        o=series(df["Open"].to_numpy()), h=series(df["High"].to_numpy()),
        l=series(df["Low"].to_numpy()), c=series(close),
    )
    lines = {}
    for key in [f"ema{x}" for x in cfg.PRICE_CROSS_EMAS] + [f"sma{cfg.GOLDEN_CROSS_SLOW}"]:
        if key in values:
            lines[key] = series(values[key])
    chart["lines"] = lines

    fib = values.get("fib")
    if fib:
        fib = dict(fib)
        fib["points"] = [dict(p, i=p["i"] - s, p=r(p["p"])) for p in fib["points"]]
        fib["c_low"] = dict(i=fib["c_low"]["i"] - s, p=r(fib["c_low"]["p"]))
        fib["levels"] = {k: r(v) for k, v in fib["levels"].items()}
    liq = [dict(z, i=z["i"] - s, end=None if z["end"] is None else z["end"] - s)
           for z in values.get("liq_zones", [])]

    rsi_now = values.get("rsi", [np.nan])[-1]
    sma_slow = values.get(f"sma{cfg.GOLDEN_CROSS_SLOW}", [np.nan])[-1]
    signals.sort(key=lambda x: (x["age"], {"bull": 0, "bear": 1, "watch": 2}[x["dir"]]))
    return dict(
        t=ticker, n=name, tv=f"NASDAQ:{ticker.replace('-', '.')}",
        c=r(close[-1]), chg=r((close[-1] / close[-2] - 1) * 100, 2),
        rsi=r(rsi_now, 1),
        above200=None if np.isnan(sma_slow) else bool(close[-1] > sma_slow),
        sig=signals, ch=chart, fib=fib, liq=liq,
    )


# ---------------------------------------------------------------------------
# 4) Speichern
# ---------------------------------------------------------------------------

def write_output(payload: dict, demo: bool):
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").touch()
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (DOCS / "data.json").write_text(text, encoding="utf-8")

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", text.replace("</", "<\\/"))
    (DOCS / "index.html").write_text(html, encoding="utf-8")

    if not demo:  # kleines Tagesprotokoll (nur Signale), z. B. für spätere Auswertungen
        hist = DOCS / "history"
        hist.mkdir(exist_ok=True)
        slim = {"date": payload["data_date"],
                "signals": {s["t"]: s["sig"] for s in payload["stocks"] if s["sig"]}}
        (hist / f"{payload['data_date']}.json").write_text(
            json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    demo = "--demo" in sys.argv
    tickers = pd.read_csv(TICKER_FILE) if demo else load_tickers()
    names = dict(zip(tickers["ticker"], tickers["name"]))
    data = demo_data(list(names)) if demo else download(list(names))
    if not data:
        sys.exit("Keine Kursdaten erhalten – Scan abgebrochen.")
    newest = max(df.index[-1] for df in data.values())
    stale = [t for t, df in data.items() if (newest - df.index[-1]).days > 10]
    for t in stale:  # z. B. nicht mehr gehandelte Aktien
        print(f"Veraltete Daten, übersprungen: {t}")
        del data[t]

    stocks = []
    for t, df in sorted(data.items()):
        print(f"  {t:6s}", end="")
        stock = build_stock(t, names.get(t, names.get(t.replace("-", "."), t)), df)
        print(f"  {len(stock['sig'])} Signal(e)")
        stocks.append(stock)

    last_date = newest
    payload = dict(
        demo=demo,
        index=cfg.INDEX_NAME,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        data_date=last_date.strftime("%Y-%m-%d"),
        lookback=cfg.SIGNAL_LOOKBACK_BARS,
        failed=sorted(set(names) - set(data)),
        settings=dict(rsi=[cfg.RSI_LENGTH, cfg.RSI_OVERSOLD, cfg.RSI_OVERBOUGHT],
                      macd=[cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL],
                      emas=cfg.PRICE_CROSS_EMAS, cross=[cfg.GOLDEN_CROSS_FAST, cfg.GOLDEN_CROSS_SLOW],
                      fib=cfg.FIB_LEVELS, fib_signal=cfg.FIB_SIGNAL_LEVELS, liq=[cfg.LIQ_PIVOT_LENGTH, cfg.LIQ_MIN_VOLUME_FACTOR]),
        stocks=stocks,
    )
    write_output(payload, demo)
    total = sum(len(s["sig"]) for s in stocks)
    print(f"\nFertig: {len(stocks)} Aktien, {total} Signale -> docs/index.html")


if __name__ == "__main__":
    main()
