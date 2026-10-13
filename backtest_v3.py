import csv
import os
import sys
import math
import time
import importlib.util
from collections import defaultdict

import bot

DETAIL = os.path.expanduser("~/btc40/backtest_v3_results.csv")
SUMMARY = os.path.expanduser("~/btc40/backtest_v3_summary.csv")

HORIZON = 12
SL_ATR = 1.2
TP_ATR = 1.8

FIVE_CANDLE_PATTERNS = {
    "Rising Three Methods",
    "Falling Three Methods",
}

TIMEFRAMES = [
    ("30 دقیقه", "Min30", 30 * 60),
    ("1 ساعت", "Min60", 60 * 60),
]

def get_candles(name, interval, seconds):
    candles = bot.fetch(interval, seconds)
    if not candles:
        print(f"داده‌ای برای {name} دریافت نشد.")
        return []

    candles = sorted(candles, key=lambda x: int(x["time"]))
    unique = {}
    for candle in candles:
        unique[int(candle["time"])] = candle

    candles = list(unique.values())

    # آخرین کندل ممکن است هنوز بسته نشده باشد.
    now_ms = int(time.time() * 1000)
    candles = [
        c for c in candles
        if int(c["time"]) + seconds * 1000 <= now_ms
    ]
    return candles

def get_4h_candles():
    hourly = get_candles("1 ساعت", "Min60", 3600)
    if not hourly:
        return []
    candles = bot.aggregate_4h(hourly)
    if not candles:
        return []
    return sorted(candles, key=lambda x: int(x["time"]))

def safe_atr(candles):
    try:
        value = bot.atr(candles, 14)
        if value is None:
            return None
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            return None
        return value
    except Exception:
        return None

def simulate(candles, index, direction, atr_value):
    entry = float(candles[index]["close"])

    if direction == "LONG":
        stop = entry - SL_ATR * atr_value
        target = entry + TP_ATR * atr_value
    else:
        stop = entry + SL_ATR * atr_value
        target = entry - TP_ATR * atr_value

    future = candles[index + 1:index + 1 + HORIZON]
    if len(future) < HORIZON:
        return None

    for candle in future:
        high = float(candle["high"])
        low = float(candle["low"])

        if direction == "LONG":
            hit_sl = low <= stop
            hit_tp = high >= target
        else:
            hit_sl = high >= stop
            hit_tp = low <= target

        # اگر هر دو در یک کندل لمس شوند، ترتیب معلوم نیست.
        if hit_sl and hit_tp:
            return {
                "result": "AMBIGUOUS",
                "entry": entry,
                "exit": "",
                "pnl": "",
                "stop": stop,
                "target": target,
            }

        if hit_sl:
            return {
                "result": "SL",
                "entry": entry,
                "exit": stop,
                "pnl": (stop - entry) / entry * 100
                    * (1 if direction == "LONG" else -1),
                "stop": stop,
                "target": target,
            }

        if hit_tp:
            return {
                "result": "TP",
                "entry": entry,
                "exit": target,
                "pnl": (target - entry) / entry * 100
                    * (1 if direction == "LONG" else -1),
                "stop": stop,
                "target": target,
            }

    exit_price = float(future[-1]["close"])
    pnl = (exit_price - entry) / entry * 100
    if direction == "SHORT":
        pnl = -pnl

    return {
        "result": "TIMEOUT",
        "entry": entry,
        "exit": exit_price,
        "pnl": pnl,
        "stop": stop,
        "target": target,
    }

def detect_matches(history, expected_five=False):
    try:
        matches = bot.detect(history)
    except Exception as exc:
        print(f"هشدار تشخیص الگو: {exc}")
        return []

    output = []
    seen = set()

    for name, direction in matches or []:
        is_five = name in FIVE_CANDLE_PATTERNS
        if is_five != expected_five:
            continue
        if direction not in ("LONG", "SHORT"):
            continue

        key = (name, direction)
        if key not in seen:
            seen.add(key)
            output.append((name, direction))

    return output

def test_timeframe(name, candles, all_rows):
    print(f"{name}: {len(candles)} کندل بسته‌شده")

    if len(candles) < 40:
        print("کندل کافی نیست؛ این تایم‌فریم رد شد.")
        return

    # سیگنال‌های عادی در کندل i تأیید می‌شوند.
    # الگوهای پنج‌کندلی در همان کندل جاری تشخیص داده می‌شوند.
    for i in range(20, len(candles) - HORIZON):
        atr_value = safe_atr(candles[:i + 1])
        if atr_value is None:
            continue

        matches = []

        # در detect، کندل c سه کندل مانده به انتهای پنجره است.
        # دو کندل انتهایی برای الگوهای کوتاه استفاده نمی‌شوند.
        if i + 3 <= len(candles):
            matches.extend(
                detect_matches(candles[:i + 3], expected_five=False)
            )

        # الگوهای پنج‌کندلی فقط با داده‌های تا کندل i.
        matches.extend(
            detect_matches(candles[:i + 1], expected_five=True)
        )

        for pattern, direction in matches:
            outcome = simulate(candles, i, direction, atr_value)
            if outcome is None:
                continue

            all_rows.append({
                "timeframe": name,
                "signal_time_utc": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.gmtime(int(candles[i]["time"]) / 1000)
                ),
                "pattern": pattern,
                "direction": direction,
                "entry": outcome["entry"],
                "stop": outcome["stop"],
                "target": outcome["target"],
                "result": outcome["result"],
                "exit": outcome["exit"],
                "pnl_percent": outcome["pnl"],
            })

def write_csv(rows):
    fields = [
        "timeframe", "signal_time_utc", "pattern", "direction",
        "entry", "stop", "target", "result", "exit", "pnl_percent"
    ]
    with open(DETAIL, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    groups = defaultdict(list)
    for row in rows:
        groups[
            (row["timeframe"], row["pattern"], row["direction"])
        ].append(row)

    summary = []
    for (tf, pattern, direction), items in groups.items():
        tp = sum(x["result"] == "TP" for x in items)
        sl = sum(x["result"] == "SL" for x in items)
        ambiguous = sum(x["result"] == "AMBIGUOUS" for x in items)
        timeout = sum(x["result"] == "TIMEOUT" for x in items)

        resolved = tp + sl
        pnl_values = [
            float(x["pnl_percent"]) for x in items
            if x["pnl_percent"] not in ("", None)
        ]

        summary.append({
            "timeframe": tf,
            "pattern": pattern,
            "direction": direction,
            "signals": len(items),
            "TP": tp,
            "SL": sl,
            "ambiguous": ambiguous,
            "timeout": timeout,
            "resolved_win_rate_percent":
                round(tp / resolved * 100, 2) if resolved else "",
            "average_pnl_percent":
                round(sum(pnl_values) / len(pnl_values), 4)
                if pnl_values else "",
        })

    summary.sort(
        key=lambda x: (
            float(x["average_pnl_percent"])
            if x["average_pnl_percent"] != "" else -999
        ),
        reverse=True
    )

    with open(SUMMARY, "w", newline="", encoding="utf-8-sig") as f:
        fields = [
            "timeframe", "pattern", "direction", "signals",
            "TP", "SL", "ambiguous", "timeout",
            "resolved_win_rate_percent", "average_pnl_percent"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)

    print("\n===== BTC BACKTEST V3 =====")
    print(f"Signals: {len(rows)}")
    print(f"TP: {sum(r['result']=='TP' for r in rows)}")
    print(f"SL: {sum(r['result']=='SL' for r in rows)}")
    print(f"Ambiguous: {sum(r['result']=='AMBIGUOUS' for r in rows)}")
    print(f"Timeout: {sum(r['result']=='TIMEOUT' for r in rows)}")
    print(f"Details: {DETAIL}")
    print(f"Summary: {SUMMARY}")
    print("TEST ONLY — NO REAL TRADES")

def main():
    print("BTC BACKTEST V3 - TEST ONLY - NO REAL TRADES")
    rows = []

    for name, interval, seconds in TIMEFRAMES:
        try:
            candles = get_candles(name, interval, seconds)
            test_timeframe(name, candles, rows)
        except Exception as exc:
            print(f"خطا در {name}: {type(exc).__name__}: {exc}")

    try:
        candles4 = get_4h_candles()
        test_timeframe("4 ساعت", candles4, rows)
    except Exception as exc:
        print(f"خطا در 4 ساعت: {type(exc).__name__}: {exc}")

    if not rows:
        print("سیگنالی برای ارزیابی تولید نشد.")
        return

    write_csv(rows)

if __name__ == "__main__":
    main()
