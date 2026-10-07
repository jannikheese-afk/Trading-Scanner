"""
INDIKATOREN – hier wird gerechnet.

Jede Funktion bekommt die Kursdaten einer Aktie (Open, High, Low, Close, Volume)
und gibt eine Liste von Signalen zurück. Ein Signal ist ein kleines Dictionary:

    {"cat": "rsi", "dir": "bull", "label": "RSI überverkauft", "detail": "RSI 27,4", "age": 0}

    cat    = Kategorie (rsi, macd, ma, fib, liq) – für die Filter im Dashboard
    dir    = "bull" (bullisch), "bear" (bärisch) oder "watch" (beobachten)
    age    = vor wie vielen Kerzen das Signal kam (0 = heute)
"""

import numpy as np
import pandas as pd

import config as cfg


# ===========================================================================
# Grundbausteine (so gerechnet wie in TradingView / Pine Script)
# ===========================================================================

def sma(values: np.ndarray, length: int) -> np.ndarray:
    return pd.Series(values).rolling(length).mean().to_numpy()


def ema(values: np.ndarray, length: int) -> np.ndarray:
    """ta.ema: startet mit dem einfachen Durchschnitt, danach exponentiell."""
    out = np.full(len(values), np.nan)
    if len(values) < length:
        return out
    alpha = 2 / (length + 1)
    out[length - 1] = np.mean(values[:length])
    for i in range(length, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def rma(values: np.ndarray, length: int) -> np.ndarray:
    """ta.rma (Wilder-Glättung), wird für RSI und ATR benutzt."""
    out = np.full(len(values), np.nan)
    valid = ~np.isnan(values)
    first = np.argmax(valid)  # erster gültiger Wert
    if valid.sum() < length:
        return out
    seed_end = first + length
    out[seed_end - 1] = np.mean(values[first:seed_end])
    alpha = 1 / length
    for i in range(seed_end, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(close: np.ndarray, length: int = 14) -> np.ndarray:
    change = np.diff(close, prepend=np.nan)
    gain = np.where(np.isnan(change), np.nan, np.maximum(change, 0))
    loss = np.where(np.isnan(change), np.nan, np.maximum(-change, 0))
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        out = 100 - 100 / (1 + rs)
    out = np.where(avg_loss == 0, 100.0, out)
    out = np.where(avg_gain == 0, 0.0, out)
    out[np.isnan(avg_gain) | np.isnan(avg_loss)] = np.nan
    return out


def macd(close: np.ndarray, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    sig = np.full(len(close), np.nan)
    valid = ~np.isnan(macd_line)
    if valid.sum() >= signal:
        first = np.argmax(valid)
        sig[first:] = ema(macd_line[first:], signal)
    return macd_line, sig


def atr(high, low, close, length=14) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan
    tr = np.nanmax(np.vstack([high - low,
                              np.abs(high - prev_close),
                              np.abs(low - prev_close)]), axis=0)
    return rma(tr, length)


def last_cross(a: np.ndarray, b: np.ndarray, lookback: int):
    """
    Sucht die jüngste Kreuzung von Linie a über/unter Linie b in den letzten
    `lookback` Kerzen. Gibt ("up"|"down", alter) oder None zurück.
    """
    n = len(a)
    for age in range(lookback):
        i = n - 1 - age
        if i < 1 or np.isnan([a[i], b[i], a[i - 1], b[i - 1]]).any():
            continue
        if a[i] > b[i] and a[i - 1] <= b[i - 1]:
            return "up", age
        if a[i] < b[i] and a[i - 1] >= b[i - 1]:
            return "down", age
    return None


def fmt(x: float, digits: int = 2) -> str:
    """Zahl im deutschen Format: 1234.5 -> '1.234,50'"""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ===========================================================================
# 1) RSI
# ===========================================================================

def rsi_signals(df: pd.DataFrame, values: dict) -> list:
    r = rsi(df["Close"].to_numpy(), cfg.RSI_LENGTH)
    values["rsi"] = r
    now = r[-1]
    if np.isnan(now):
        return []
    if now <= cfg.RSI_OVERSOLD:
        return [dict(cat="rsi", dir="bull", label="RSI überverkauft",
                     detail=f"RSI {fmt(now, 1)} (unter {cfg.RSI_OVERSOLD})", age=0)]
    if now >= cfg.RSI_OVERBOUGHT:
        return [dict(cat="rsi", dir="bear", label="RSI überkauft",
                     detail=f"RSI {fmt(now, 1)} (über {cfg.RSI_OVERBOUGHT})", age=0)]
    return []


# ===========================================================================
# 2) MACD-Kreuzung
# ===========================================================================

def macd_signals(df: pd.DataFrame, values: dict) -> list:
    close = df["Close"].to_numpy()
    line, sig = macd(close, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
    values["macd"], values["macd_signal"] = line, sig
    cross = last_cross(line, sig, cfg.SIGNAL_LOOKBACK_BARS)
    if not cross:
        return []
    direction, age = cross
    zone = "über" if line[-1 - age] > 0 else "unter"
    if direction == "up":
        return [dict(cat="macd", dir="bull", label="MACD kreuzt nach oben",
                     detail=f"MACD über Signallinie, {zone} der Nulllinie", age=age)]
    return [dict(cat="macd", dir="bear", label="MACD kreuzt nach unten",
                 detail=f"MACD unter Signallinie, {zone} der Nulllinie", age=age)]


# ===========================================================================
# 3) Gleitende Durchschnitte
# ===========================================================================

def ma_signals(df: pd.DataFrame, values: dict) -> list:
    close = df["Close"].to_numpy()
    out = []
    lb = cfg.SIGNAL_LOOKBACK_BARS

    fast = sma(close, cfg.GOLDEN_CROSS_FAST)
    slow = sma(close, cfg.GOLDEN_CROSS_SLOW)
    values[f"sma{cfg.GOLDEN_CROSS_SLOW}"] = slow
    cross = last_cross(fast, slow, lb)
    if cross:
        d, age = cross
        if d == "up":
            out.append(dict(cat="ma", dir="bull", label="Golden Cross",
                            detail=f"SMA {cfg.GOLDEN_CROSS_FAST} kreuzt SMA {cfg.GOLDEN_CROSS_SLOW} nach oben", age=age))
        else:
            out.append(dict(cat="ma", dir="bear", label="Death Cross",
                            detail=f"SMA {cfg.GOLDEN_CROSS_FAST} kreuzt SMA {cfg.GOLDEN_CROSS_SLOW} nach unten", age=age))

    for length in cfg.PRICE_CROSS_EMAS:
        e = ema(close, length)
        values[f"ema{length}"] = e
        cross = last_cross(close, e, lb)
        if cross:
            d, age = cross
            if d == "up":
                out.append(dict(cat="ma", dir="bull", label=f"Kurs über EMA {length}",
                                detail=f"Schlusskurs kreuzt EMA {length} ({fmt(e[-1 - age])}) nach oben", age=age))
            else:
                out.append(dict(cat="ma", dir="bear", label=f"Kurs unter EMA {length}",
                                detail=f"Schlusskurs kreuzt EMA {length} ({fmt(e[-1 - age])}) nach unten", age=age))
    return out


# ===========================================================================
# 4) Elliott-ABC-Korrektur mit trendbasierter Fibonacci-Extension
#
#    Start (signifikantes Hoch)
#      -> A (signifikantes Tief, Ende von Welle A)
#      -> B (Erholung, bleibt unter dem Start, Ende von Welle B)
#      -> Welle C läuft gerade nach unten.
#
#    Trendbasierte Extension (wie das TradingView-Werkzeug "Trend-Based Fib Extension"):
#      Level = B - (Start - A) × Ratio
#    also die Länge von Welle A, ab dem Punkt B nach unten abgetragen.
#    Nur Abwärtsstrukturen – das Ziel ist ein möglichst günstiger Einstieg.
# ===========================================================================

def zigzag(high: np.ndarray, low: np.ndarray, dev: float):
    """
    Findet signifikante Hochs und Tiefs: Ein Wendepunkt zählt erst, wenn sich der
    Kurs danach um mindestens `dev` (z. B. 0.08 = 8 %) in die Gegenrichtung bewegt.

    Rückgabe: (bestätigte Wendepunkte, aktueller Schenkel)
      Wendepunkte: Liste von (index, preis, "H"|"L")
      aktueller Schenkel: (index, preis, "H"|"L") des bisherigen Extrems im laufenden Schenkel
    """
    n = len(high)
    pivots = []
    hi_i = lo_i = 0
    trend = 0
    ext = 0
    for i in range(1, n):
        if trend == 0:
            if high[i] > high[hi_i]:
                hi_i = i
            if low[i] < low[lo_i]:
                lo_i = i
            if high[hi_i] >= low[lo_i] * (1 + dev):
                if hi_i > lo_i:   # erst Tief, dann Hoch -> Aufwärtsschenkel läuft
                    pivots.append((lo_i, low[lo_i], "L"))
                    trend, ext = 1, hi_i
                else:
                    pivots.append((hi_i, high[hi_i], "H"))
                    trend, ext = -1, lo_i
        elif trend == 1:
            if high[i] >= high[ext]:
                ext = i
            elif low[i] <= high[ext] * (1 - dev):
                pivots.append((ext, high[ext], "H"))
                trend, ext = -1, i
        else:
            if low[i] <= low[ext]:
                ext = i
            elif high[i] >= low[ext] * (1 + dev):
                pivots.append((ext, low[ext], "L"))
                trend, ext = 1, i
    if trend == 0:
        return pivots, None
    leg = (ext, high[ext], "H") if trend == 1 else (ext, low[ext], "L")
    return pivots, leg


def fib_signals(df: pd.DataFrame, values: dict) -> list:
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()
    n = len(close)
    values["fib"] = None

    # Wie groß muss eine Bewegung sein, um "signifikant" zu sein? -> abhängig von der Volatilität
    a = atr(high, low, close, 14)
    atr_pct = np.nanmedian((a / close)[-250:]) * 100
    dev_pct = float(np.clip(atr_pct * cfg.FIB_SWING_ATR_MULT, cfg.FIB_SWING_MIN_PCT, cfg.FIB_SWING_MAX_PCT))

    pivots, leg = zigzag(high, low, dev_pct / 100)
    if leg is None or len(pivots) < 3:
        return []

    S, A, B = pivots[-3], pivots[-2], pivots[-1]
    # Nur Abwärts-ABC: Start = Hoch, A = Tief, B = Hoch unter dem Start, Welle C fällt gerade
    if not (S[2] == "H" and A[2] == "L" and B[2] == "H" and leg[2] == "L" and B[1] < S[1]):
        return []

    wave_a = S[1] - A[1]
    levels = {r: B[1] - wave_a * r for r in cfg.FIB_LEVELS}
    if min(levels.values()) <= 0:   # Bewegung zu extrem, die Extension ergibt keinen Sinn
        return []

    values["fib"] = dict(
        points=[dict(i=int(p[0]), p=float(p[1]), name=name) for p, name in ((S, "Start"), (A, "A"), (B, "B"))],
        levels={f"{r:g}": float(v) for r, v in levels.items()},
        signal_levels=[f"{r:g}" for r in cfg.FIB_SIGNAL_LEVELS],
        c_low=dict(i=int(leg[0]), p=float(leg[1])),          # bisher tiefster Punkt von Welle C
        retrace_b=round((B[1] - A[1]) / wave_a * 100, 1),   # wie weit B Welle A zurückgeholt hat
        dev_pct=round(dev_pct, 1),
    )

    tol = cfg.FIB_TOLERANCE_PCT / 100
    near = cfg.FIB_NEAR_PCT / 100
    lb = cfg.SIGNAL_LOOKBACK_BARS
    first = B[0] + 1
    ratios = sorted(r for r in cfg.FIB_SIGNAL_LEVELS if r in levels)

    def pct_label(r):
        return fmt(r * 100, 1).replace(",0", "")

    # Wann hat Welle C welches Signal-Level zum ersten Mal erreicht? (Tagestief bis auf 1 % dran)
    first_hits = {}
    for r in ratios:
        reached = np.where(low[first:] <= levels[r] * (1 + tol))[0]
        if len(reached):
            first_hits[r] = first + int(reached[0])

    # Signal: das tiefste erreichte Signal-Level – wenn es frisch ist oder der Kurs noch dort steht
    if first_hits:
        r = max(first_hits)
        lvl = levels[r]
        age = n - 1 - first_hits[r]
        in_zone = abs(close[-1] / lvl - 1) <= tol
        if age < lb or in_zone:
            return [dict(cat="fib", dir="bull", label=f"Welle C: Fib {pct_label(r)} % erreicht",
                         detail=f"Trendbasierte Extension Start→A→B bei {fmt(lvl)} – mögliche Kaufzone",
                         age=int(age) if age < lb else 0)]

    # Sonst: Annäherung an das nächste noch nicht erreichte Signal-Level
    pending = [r for r in ratios if r not in first_hits]
    if pending:
        r = pending[0]
        lvl = levels[r]
        dist = close[-1] / lvl - 1
        if 0 < dist <= near:
            return [dict(cat="fib", dir="watch", label=f"Welle C nähert sich Fib {pct_label(r)} %",
                         detail=f"Noch {fmt(dist * 100, 1)} % bis {fmt(lvl)} – mögliche Kaufzone", age=0)]
    return []


# ===========================================================================
# 5) Liquidity Swings (Logik nach "Liquidity Swings [LuxAlgo]", CC BY-NC-SA 4.0)
#    Swing-Hoch/-Tief mit Pivot-Lookback. Die Zone reicht vom Docht-Extrem bis zum
#    Kerzenkörper. Jede spätere Kerze, die in die Zone läuft, zählt als Kontakt und
#    ihr Volumen wird aufsummiert. Schließt der Kurs jenseits der Zone, ist sie
#    "gekreuzt". Wir melden Kreuzungen von Zonen mit viel gesammeltem Volumen.
# ===========================================================================

def liquidity_signals(df: pd.DataFrame, values: dict) -> list:
    o = df["Open"].to_numpy()
    h = df["High"].to_numpy()
    l = df["Low"].to_numpy()
    c = df["Close"].to_numpy()
    v = df["Volume"].to_numpy().astype(float)
    n = len(c)
    L = cfg.LIQ_PIVOT_LENGTH
    lb = cfg.SIGNAL_LOOKBACK_BARS
    avg_vol = np.nanmean(v[-50:])
    if not avg_vol or np.isnan(avg_vol):
        return []  # ohne Volumen keine Liquiditäts-Analyse

    zones = []
    for i in range(max(L, n - cfg.LIQ_MAX_AGE_BARS), n - L):
        window_h = h[i - L:i + L + 1]
        window_l = l[i - L:i + L + 1]
        for kind in ("high", "low"):
            if kind == "high":
                if h[i] != window_h.max() or np.argmax(window_h) != L:
                    continue
                top = h[i]
                btm = max(c[i], o[i]) if cfg.LIQ_AREA == "wick" else l[i]
            else:
                if l[i] != window_l.min() or np.argmin(window_l) != L:
                    continue
                btm = l[i]
                top = min(c[i], o[i]) if cfg.LIQ_AREA == "wick" else h[i]

            touches, vol, crossed_at = 0, 0.0, None
            for j in range(i + 1, n):
                if (kind == "high" and c[j] > top) or (kind == "low" and c[j] < btm):
                    crossed_at = j
                    break
                if h[j] > btm and l[j] < top:
                    touches += 1
                    vol += v[j]
            zones.append(dict(kind=kind, i=i, top=float(top), btm=float(btm), touches=touches,
                              score=vol / avg_vol, crossed=crossed_at,
                              confirmed_at=i + L))

    def strong(z):
        return z["score"] >= cfg.LIQ_MIN_VOLUME_FACTOR and z["touches"] >= cfg.LIQ_MIN_TOUCHES

    out = []
    for z in zones:
        if z["crossed"] is None or not strong(z):
            continue
        if z["crossed"] < z["confirmed_at"]:
            continue  # wurde gekreuzt, bevor der Swing überhaupt bestätigt war
        age = n - 1 - z["crossed"]
        if age >= lb:
            continue
        if z["kind"] == "high":
            out.append(dict(cat="liq", dir="bull", label="Ausbruch über Liquiditätszone",
                            detail=f"Swing-Hoch {fmt(z['top'])}: {z['touches']} Kontakte, "
                                   f"{fmt(z['score'], 1)}× Ø-Tagesvolumen", age=int(age), score=z["score"]))
        else:
            out.append(dict(cat="liq", dir="bear", label="Bruch unter Liquiditätszone",
                            detail=f"Swing-Tief {fmt(z['btm'])}: {z['touches']} Kontakte, "
                                   f"{fmt(z['score'], 1)}× Ø-Tagesvolumen", age=int(age), score=z["score"]))
    # Pro Richtung nur die stärkste Zone melden
    best = {}
    for s in out:
        if s["dir"] not in best or s["score"] > best[s["dir"]]["score"]:
            best[s["dir"]] = s
    out = list(best.values())
    for s in out:
        s["score"] = round(s["score"], 1)

    # Für den Chart: noch offene starke Zonen + frisch gekreuzte
    show = [z for z in zones if strong(z) and (z["crossed"] is None or n - 1 - z["crossed"] < lb)]
    show.sort(key=lambda z: -z["score"])
    values["liq_zones"] = [dict(kind=z["kind"], i=int(z["i"]), top=round(z["top"], 4), btm=round(z["btm"], 4),
                                touches=z["touches"], score=round(z["score"], 1),
                                end=None if z["crossed"] is None else int(z["crossed"]))
                           for z in show[:6]]
    return out


# ===========================================================================
# Alles zusammen
# ===========================================================================

ALL = [rsi_signals, macd_signals, ma_signals, fib_signals, liquidity_signals]


def analyze(df: pd.DataFrame):
    """Berechnet alle Indikatoren für eine Aktie. Rückgabe: (signale, werte)"""
    values = {}
    signals = []
    for func in ALL:
        try:
            signals.extend(func(df, values))
        except Exception as e:  # ein kaputter Indikator soll nicht den ganzen Scan stoppen
            print(f"    ! {func.__name__}: {e}")
    return signals, values
