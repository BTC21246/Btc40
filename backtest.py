import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import bot

ROOT = Path.home() / "btc40"
DETAIL = ROOT / "backtest_results.csv"
SUMMARY = ROOT / "backtest_summary.csv"
HORIZON = 12
RR = 1.5
ATR_MULT = 1.2

# Number of candles needed to confirm each pattern.
PATTERN_LENGTH = {
    "Hammer": 1, "Inverted Hammer": 1, "Hanging Man": 1,
    "Shooting Star": 1, "Bullish Marubozu": 1,
    "Bearish Marubozu": 1, "Doji": 1, "Dragonfly Doji": 1,
    "Gravestone Doji": 1, "Spinning Top": 1,
    "Bullish Engulfing": 2, "Bearish Engulfing": 2,
    "Bullish Harami": 2, "Bearish Harami": 2,
    "Harami Cross Bullish": 2, "Harami Cross Bearish": 2,
    "Piercing Line": 2, "Dark Cloud Cover": 2,
    "Tweezer Bottom": 2, "Tweezer Top": 2,
    "Bullish Meeting Lines": 2, "Bearish Meeting Lines": 2,
    "Bullish Kicking": 2, "Bearish Kicking": 2,
    "Morning Star": 3, "Evening Star": 3,
    "Morning Doji Star": 3, "Evening Doji Star": 3,
    "Three White Soldiers": 3, "Three Black Crows": 3,
    "Three Inside Up": 3, "Three Inside Down": 3,
    "Three Outside Up": 3, "Three Outside Down": 3,
    "Three Line Strike Bullish": 3, "Three Line Strike Bearish": 3,
    "Rising Three Methods": 5, "Falling Three Methods": 5,
    "Abandoned Baby Bullish": 3, "Abandoned Baby Bearish": 3,
}

FIELDS = [
    "signal_time_utc", "timeframe", "pattern", "direction",
    "entry", "stop_loss", "take_profit", "exit_time",
    "exit_price", "result", "bars", "pnl_percent"
]

def utc(ms):
    return datetime.fromtimestamp(
        ms / 1000, timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

def run_one(candles, i, pattern, direction, tf):
    signal = candles[i]
    entry = signal["close"]
    history = candles[:i + 1]
    risk = max(bot.atr(history) * ATR_MULT, entry * 0.001)

    if direction == "LONG":
        sl, tp = entry - risk, entry + risk * RR
    else:
        sl, tp = entry + risk, entry - risk * RR

    future = candles[i + 1:i + 1 + HORIZON]
    result, exit_price, exit_time, bars, pnl = (
        "TIMEOUT", future[-1]["close"],
        utc(future[-1]["time"]), len(future), None
    )

    for n, bar in enumerate(future, 1):
        if direction == "LONG":
            hit_sl = bar["low"] <= sl
            hit_tp = bar["high"] >= tp
        else:
            hit_sl = bar["high"] >= sl
            hit_tp = bar["low"] <= tp

        if hit_sl and hit_tp:
            result, exit_price, pnl = "AMBIGUOUS", "", ""
            exit_time, bars = utc(bar["time"]), n
            break
        if hit_sl or hit_tp:
            result = "SL" if hit_sl else "TP"
            exit_price = sl if hit_sl else tp
            exit_time, bars = utc(bar["time"]), n
            pnl = (
                (exit_price - entry) / entry * 100
                if direction == "LONG"
                else (entry - exit_price) / entry * 100
            )
            break

    if pnl is None:
        close = float(exit_price)
        pnl = (
            (close - entry) / entry * 100
            if direction == "LONG"
            else (entry - close) / entry * 100
        )

    return {
        "signal_time_utc": utc(signal["time"]),
        "timeframe": tf,
        "pattern": pattern,
        "direction": direction,
        "entry": round(entry, 4),
        "stop_loss": round(sl, 4),
        "take_profit": round(tp, 4),
        "exit_time": exit_time,
        "exit_price": round(float(exit_price), 4) if exit_price != "" else "",
        "result": result,
        "bars": bars,
        "pnl_percent": round(pnl, 4) if pnl != "" else "",
    }

def main():
    all_results = []
    print("BTC BACKTEST V2 - TEST ONLY - NO REAL TRADES")

    for label, interval, seconds in bot.TIMEFRAMES:
        try:
            if interval == "AGG4H":
                candles = bot.aggregate_4h(bot.fetch("Min60", 3600))
            else:
                candles = bot.fetch(interval, seconds)
            candles = sorted(candles, key=lambda x: x["time"])
            print(f"{label}: {len(candles)} closed candles")
        except Exception as exc:
            print(f"ERROR {label}: {type(exc).__name__}: {exc}")
            continue

        if len(candles) < HORIZON + 20:
            print(f"Not enough data for {label}")
            continue

        print(f"Testing {label}...")
        for i in range(19, len(candles) - HORIZON):
            matches = bot.detect(candles[:i + 1])
            for pattern, direction in matches:
                if direction not in ("LONG", "SHORT"):
                    continue

                # Ignore any pattern not explicitly accounted for.
                if pattern not in PATTERN_LENGTH:
                    continue

                all_results.append(
                    run_one(candles, i, pattern, direction, label)
                )

    with DETAIL.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_results)

    groups = defaultdict(list)
    for row in all_results:
        groups[(row["timeframe"], row["pattern"], row["direction"])].append(row)

    summary_fields = [
        "timeframe", "pattern", "direction", "signals",
        "tp", "sl", "ambiguous", "timeout",
        "resolved_win_rate_percent", "average_pnl_percent"
    ]
    summaries = []
    for (tf, pattern, direction), rows in sorted(groups.items()):
        tp = sum(r["result"] == "TP" for r in rows)
        sl = sum(r["result"] == "SL" for r in rows)
        amb = sum(r["result"] == "AMBIGUOUS" for r in rows)
        tout = sum(r["result"] == "TIMEOUT" for r in rows)
        resolved = tp + sl
        pnls = [float(r["pnl_percent"]) for r in rows if r["pnl_percent"] != ""]
        summaries.append({
            "timeframe": tf,
            "pattern": pattern,
            "direction": direction,
            "signals": len(rows),
            "tp": tp,
            "sl": sl,
            "ambiguous": amb,
            "timeout": tout,
            "resolved_win_rate_percent": round(tp / resolved * 100, 2) if resolved else "",
            "average_pnl_percent": round(sum(pnls) / len(pnls), 4) if pnls else "",
        })

    with SUMMARY.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)

    tp = sum(r["result"] == "TP" for r in all_results)
    sl = sum(r["result"] == "SL" for r in all_results)
    amb = sum(r["result"] == "AMBIGUOUS" for r in all_results)
    tout = sum(r["result"] == "TIMEOUT" for r in all_results)
    resolved = tp + sl

    print("\n===== BACKTEST V2 RESULTS =====")
    print(f"Signals: {len(all_results)}")
    print(f"TP: {tp} | SL: {sl} | Ambiguous: {amb} | Timeout: {tout}")
    print(f"Resolved win rate: {tp / resolved * 100:.2f}%" if resolved else "Win rate: N/A")
    print(f"Details: {DETAIL}")
    print(f"Summary: {SUMMARY}")
    print("No real orders were placed.")

if __name__ == "__main__":
    main()
