import csv
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

import bot

ROOT = Path.home() / "btc40"
REPORT = ROOT / "pattern_audit_v2_report.txt"
TRADES = ROOT / "pattern_audit_v2_trades.csv"

START_INDEX = 50
MAX_HOLD = 12
COST_PCT = 0.08  # هزینه رفت‌وبرگشت فرضی؛ بعداً با کارمزد واقعی جایگزین شود.
MIN_TRADES = 8

def stamp(c):
    return datetime.fromtimestamp(
        c["time"] / 1000, timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

def fetch_timeframes():
    data = {}
    for label, interval, seconds in bot.TIMEFRAMES:
        try:
            if interval == "AGG4H":
                if "hourly" not in data:
                    data["hourly"] = bot.fetch("Min60", 3600)
                cs = bot.aggregate_4h(data["hourly"])
            else:
                cs = bot.fetch(interval, seconds)
            data[label] = cs
            print(f"{label}: {len(cs)} کندل بسته دریافت شد.")
        except Exception as exc:
            print(f"خطا در دریافت {label}: {type(exc).__name__}: {exc}")
    return data

def run_pattern(tf, cs, name, direction, rows):
    trades = []
    next_allowed = START_INDEX
    detected = 0

    # برای هر الگو یک آزمایش مستقل؛ سیگنال الگوهای دیگر دخالت داده نمی‌شود.
    for i in range(START_INDEX, len(cs) - MAX_HOLD):
        matches = bot.detect(cs[:i + 1])
        if not any(n == name and d == direction for n, d in matches):
            continue
        detected += 1

        if i < next_allowed:
            continue

        entry = float(cs[i]["close"])
        volatility = bot.atr(cs[:i + 1])
        risk = max(volatility * 1.2, entry * 0.001)

        if direction == "LONG":
            sl, tp = entry - risk, entry + risk * 1.5
        else:
            sl, tp = entry + risk, entry - risk * 1.5

        outcome = None
        exit_price = None
        exit_time = ""
        bars = 0
        end_index = i + MAX_HOLD

        for j in range(i + 1, i + MAX_HOLD + 1):
            c = cs[j]
            bars = j - i

            if direction == "LONG":
                hit_sl = c["low"] <= sl
                hit_tp = c["high"] >= tp
            else:
                hit_sl = c["high"] >= sl
                hit_tp = c["low"] <= tp

            if hit_sl and hit_tp:
                outcome = "AMBIGUOUS"
                exit_time = stamp(c)
                end_index = j
                break
            if hit_sl:
                outcome, exit_price = "SL", sl
                exit_time, end_index = stamp(c), j
                break
            if hit_tp:
                outcome, exit_price = "TP", tp
                exit_time, end_index = stamp(c), j
                break

        if outcome is None:
            c = cs[i + MAX_HOLD]
            outcome, exit_price = "TIMEOUT", float(c["close"])
            exit_time, end_index = stamp(c), i + MAX_HOLD

        pnl = ""
        net = ""
        if outcome != "AMBIGUOUS":
            if direction == "LONG":
                pnl = (exit_price - entry) / entry * 100
            else:
                pnl = (entry - exit_price) / entry * 100
            net = pnl - COST_PCT

        row = {
            "timeframe": tf,
            "pattern": name,
            "direction": direction,
            "signal_time": stamp(cs[i]),
            "entry": round(entry, 6),
            "sl": round(sl, 6),
            "tp": round(tp, 6),
            "outcome": outcome,
            "exit_time": exit_time,
            "exit_price": "" if exit_price is None else round(exit_price, 6),
            "bars": bars,
            "gross_pnl_pct": "" if pnl == "" else round(pnl, 4),
            "net_pnl_pct": "" if net == "" else round(net, 4),
        }
        trades.append(row)
        rows.append(row)
        next_allowed = end_index + 1

    return detected, trades

def summarize(trades):
    usable = [t for t in trades if t["outcome"] != "AMBIGUOUS"]
    tp = sum(t["outcome"] == "TP" for t in trades)
    sl = sum(t["outcome"] == "SL" for t in trades)
    timeout = sum(t["outcome"] == "TIMEOUT" for t in trades)
    amb = sum(t["outcome"] == "AMBIGUOUS" for t in trades)
    decided = tp + sl
    win = (tp / decided * 100) if decided else 0
    gross = sum(float(t["gross_pnl_pct"]) for t in usable)
    net = sum(float(t["net_pnl_pct"]) for t in usable)
    return {
        "n": len(trades), "tp": tp, "sl": sl, "timeout": timeout,
        "amb": amb, "win": win, "gross": gross, "net": net
    }

def main():
    print("BTC40 PATTERN AUDIT | OURBIT | TEST ONLY | NO ORDERS")
    print("هر الگو جداگانه آزمایش می‌شود؛ این آزمایش به‌تنهایی تضمین سود نیست.\n")

    data = fetch_timeframes()
    all_rows = []
    report_lines = [
        "BTC40 PATTERN AUDIT V2",
        "TEST ONLY - NO REAL ORDERS",
        f"Assumed round-trip cost: {COST_PCT:.3f}%",
        f"Start index: {START_INDEX}; max hold: {MAX_HOLD} candles",
        "Each pattern is evaluated independently; ambiguous candles excluded from PnL.",
        "Results are preliminary and not statistically conclusive.",
        ""
    ]

    for tf, cs in data.items():
        if tf == "hourly":
            continue
        print(f"\n===== {tf} | {len(cs)} کندل =====")
        if len(cs) <= START_INDEX + MAX_HOLD + 2:
            msg = f"{tf}: داده ناکافی برای ارزیابی معتبر ({len(cs)} کندل)."
            print(msg)
            report_lines.append(msg)
            continue

        names = defaultdict(set)
        counts = defaultdict(int)
        for i in range(START_INDEX, len(cs) - MAX_HOLD):
            for name, direction in bot.detect(cs[:i + 1]):
                if direction in ("LONG", "SHORT"):
                    names[name].add(direction)
                    counts[(name, direction)] += 1

        results = []
        for name in sorted(names):
            for direction in sorted(names[name]):
                detected, trades = run_pattern(
                    tf, cs, name, direction, all_rows
                )
                s = summarize(trades)
                results.append((name, direction, detected, s))

        results.sort(key=lambda x: x[3]["net"], reverse=True)
        report_lines.append(f"\n===== {tf} | {len(cs)} candles =====")
        for name, direction, detected, s in results:
            sample = "مقایسه اولیه (حداقل نمونه)" if s["n"] >= MIN_TRADES else "نمونه کم"
            line = (
                f"{name} | {direction} | detected={detected} | "
                f"trades={s['n']} TP={s['tp']} SL={s['sl']} "
                f"TIMEOUT={s['timeout']} AMBIG={s['amb']} | "
                f"win={s['win']:.1f}% | gross={s['gross']:.3f}% "
                f"net={s['net']:.3f}% | {sample}"
            )
            print(line)
            report_lines.append(line)

    fields = [
        "timeframe", "pattern", "direction", "signal_time", "entry",
        "sl", "tp", "outcome", "exit_time", "exit_price", "bars",
        "gross_pnl_pct", "net_pnl_pct"
    ]
    with open(TRADES, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    report_lines += [
        "",
        "CAUTION: Historical sample only; not proof of future performance.",
        "Net PnL uses an assumed cost of 0.08 percentage points per trade.",
        "Patterns with fewer than 8 trades are too small for meaningful comparison.",
        f"Total individual trades: {len(all_rows)}"
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("\nگزارش ذخیره شد:")
    print(REPORT)
    print(TRADES)
    print("\nکد اصلی bot.py تغییر نکرده است.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nآزمایش متوقف شد.")
    except Exception as exc:
        print(f"خطای آزمایش: {type(exc).__name__}: {exc}")
        sys.exit(1)
