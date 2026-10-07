"""
EINSTELLUNGEN – hier kannst du alles anpassen, ohne den restlichen Code anzufassen.
Nach einer Änderung einfach speichern; beim nächsten Scan gilt die neue Einstellung.
"""

# ---------------------------------------------------------------------------
# Allgemein
# ---------------------------------------------------------------------------
INDEX_NAME = "Nasdaq 100"

# Aktuelle Mitglieder automatisch von Wikipedia holen?
# Falls das scheitert, wird die Datei tickers_nasdaq100.csv benutzt.
AUTO_UPDATE_TICKERS = True

# Wie viele Kerzen (Handelstage) laden? 2 Jahre reichen für SMA 200 + Swings.
HISTORY_PERIOD = "2y"

# Ein Kreuzungs-Signal gilt als "frisch", wenn es in den letzten X Kerzen passiert ist.
# 1 = nur heute, 3 = heute + die zwei Tage davor.
SIGNAL_LOOKBACK_BARS = 3

# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------
RSI_LENGTH = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ---------------------------------------------------------------------------
# Gleitende Durchschnitte
# ---------------------------------------------------------------------------
GOLDEN_CROSS_FAST = 50     # SMA 50 ...
GOLDEN_CROSS_SLOW = 200    # ... kreuzt SMA 200
PRICE_CROSS_EMAS = [20, 50]  # Kurs kreuzt diese EMAs

# ---------------------------------------------------------------------------
# Elliott-ABC-Korrektur mit trendbasierter Fibonacci-Extension (nur Abwärtstrend)
#   Start (Hoch) -> A (Tief) -> B (Erholung unter dem Start) -> Welle C fällt
#   Level = B - (Start - A) × Ratio   (wie "Trend-Based Fib Extension" in TradingView)
# ---------------------------------------------------------------------------
FIB_LEVELS = [1.0, 1.382, 1.618, 2.0]   # Diese Level werden im Chart angezeigt
FIB_SIGNAL_LEVELS = [1.0, 1.382, 2.0]   # Bei diesen Leveln kommt ein Signal
# "Signifikant" = die Bewegung ist mindestens X-mal die typische Tagesschwankung (ATR).
FIB_SWING_ATR_MULT = 4.0
FIB_SWING_MIN_PCT = 5.0     # aber mindestens 5 % ...
FIB_SWING_MAX_PCT = 25.0    # ... und höchstens 25 %
FIB_TOLERANCE_PCT = 1.0     # Level gilt als erreicht, wenn das Tagestief bis auf 1 % rankommt
FIB_NEAR_PCT = 3.0          # "Beobachten"-Hinweis, wenn der Kurs nur noch 3 % über dem Level ist

# ---------------------------------------------------------------------------
# Liquidity Swings (Nachbau der Logik von "Liquidity Swings [LuxAlgo]")
# ---------------------------------------------------------------------------
LIQ_PIVOT_LENGTH = 14       # Pivot-Lookback wie im Original
LIQ_AREA = "wick"           # "wick" = Wick Extremity (Standard), "full" = Full Range
LIQ_MAX_AGE_BARS = 250      # Nur Swings aus dem letzten Jahr betrachten
# "Hohe Liquidität" = gesammeltes Volumen in der Zone entspricht mindestens
# X durchschnittlichen Tagesvolumen (Durchschnitt der letzten 50 Tage).
LIQ_MIN_VOLUME_FACTOR = 5.0
LIQ_MIN_TOUCHES = 2         # und die Zone wurde mindestens so oft angelaufen

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
CHART_BARS = 120            # So viele Kerzen zeigt der Mini-Chart
