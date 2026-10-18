import csv
import time
import requests
from datetime import datetime, timezone

SYMBOL = "BTC_USDT"
BASE = "https://futures.ourbit.io/api/v1/contract/kline/"
LIMIT = 12
RR = 1.5
COST_PCT = 0.08
OUT = "fvg_backtest_results.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 BTC40-TestBot/1.0"}

def fetch(interval):
    r = requests.get(
        BASE + SYMBOL,
        params={"interval": interval, "limit": 240},
        headers=HEADERS,
        timeout=(8, 35)
    )
    r.raise_for_status()
    j = r.json()

    if isinstance(j, dict):
        data = j.get("data", j.get("result", j))
        if isinstance(data, dict):
            data = data.get("list", data.get("rows", data))
        if isinstance(data, dict):
            keys = ("time", "open", "close", "high", "low", "vol")
            if all(k in data for k in keys):
                rows = []
                n = min(len(data[k]) for k in keys)
                for i in range(n):
                    rows.append({
                        "time": data["time"][i],
                        "open": data["open"][i],
                        "close": data["close"][i],
                        "high": data["high"][i],
                        "low": data["low"][i],
                        "vol": data["vol"][i],
                    })
                data = rows
    else:
        data = j

    if not isinstance(data, list) or not data:
        raise RuntimeError("ساختار پاسخ کندل Ourbit شناخته نشد: " + str(j)[:400])

    out = []
    for x in data:
        try:
            if isinstance(x, dict):
                t = x.get("time", x.get("timestamp"))
                o, h, l, c = (float(x[k]) for k in ("open", "high", "low", "close"))
                v = float(x.get("vol", x.get("volume", 0)) or 0)
            else:
                # قالب آرایه‌ای رایج: time, open, high, low, close, volume
                t = x[0]
                o, h, l, c = map(float, (x[1], x[2], x[3], x[4]))
                v = float(x[5]) if len(x) > 5 else 0
            t = int(float(t))
            if t > 10**12:
                t //= 1000
            out.append({"time": t, "open": o, "high": h,
                        "low": l, "close": c, "vol": v})
        except (ValueError, TypeError, KeyError, IndexError):
            continue

    out.sort(key=lambda z: z["time"])
    unique = {x["time"]: x for x in out}
    out = list(unique.values())

    # حذف کندل در حال تشکیل
    now = int(time.time())
    seconds = {"Min30": 1800, "Min60": 3600}[interval]
    out = [x for x in out if x["time"] + seconds <= now]
    if len(out) < 30:
        raise RuntimeError(f"کندل بسته کافی نیست: {interval}, تعداد={len(out)}")
    return out

def aggregate_4h(hourly):
    out = []
    bucket = {}
    for c in hourly:
        start = c["time"] - (c["time"] % 14400)
        bucket.setdefault(start, []).append(c)
    for start, group in sorted(bucket.items()):
        group.sort(key=lambda x: x["time"])
        # فقط بلوک کامل چهار کندل یک‌ساعته
        if len(group) != 4:
            continue
        if any(group[i]["time"] - group[i-1]["time"] != 3600
               for i in range(1, 4)):
            continue
        out.append({
            "time": start,
            "open": group[0]["open"],
            "high": max(x["high"] for x in group),
            "low": min(x["low"] for x in group),
            "close": group[-1]["close"],
            "vol": sum(x["vol"] for x in group)
        })
    return out

def backtest(candles, tf):
    trades = []
    # FVG سه‌کندلی: شکاف میان کندل اول و سوم
    for i in range(2, len(candles) - LIMIT):
        a, b, c = candles[i-2], candles[i-1], candles[i]

        if c["low"] > a["high"]:
            direction = "LONG"
            zlo, zhi = a["high"], c["low"]
        elif c["high"] < a["low"]:
            direction = "SHORT"
            zlo, zhi = c["high"], a["low"]
        else:
            continue

        # ورود فقط پس از بازگشت قیمت به ناحیه؛ نه در لحظه تشکیل
        entry_i = None
        for k in range(i+1, min(i+LIMIT+1, len(candles))):
            q = candles[k]
            touched = q["low"] <= zhi and q["high"] >= zlo
            if touched:
                entry_i = k
                break
        if entry_i is None:
            continue

        entry_c = candles[entry_i]
        entry = max(zlo, entry_c["low"])
        entry = min(entry, zhi)
        if not (entry_c["low"] <= entry <= entry_c["high"]):
            continue
        sl = zlo if direction == "LONG" else zhi
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + RR*risk if direction == "LONG" else entry - RR*risk

        # اگر در کندل ورود حد سود یا حد ضرر برخورد شده باشد،
        # نتیجه مبهم محسوب می‌شود؛ ورود در همان کندل فرض نمی‌شود.
        outcome = "TIMEOUT"
        exit_price = candles[min(entry_i+LIMIT, len(candles)-1)]["close"]
        exit_i = min(entry_i+LIMIT, len(candles)-1)

        # بررسی کندل ورود: نتیجه مبهم اگر هر دو سطح لمس شده باشند
        q = candles[entry_i]
        hit_sl = q["low"] <= sl if direction == "LONG" else q["high"] >= sl
        hit_tp = q["high"] >= tp if direction == "LONG" else q["low"] <= tp
        if hit_sl and hit_tp:
            outcome = "AMBIGUOUS_BOTH_HIT"
            exit_price, exit_i = sl, entry_i
        elif hit_sl:
            outcome, exit_price, exit_i = "SL", sl, entry_i
        elif hit_tp:
            outcome, exit_price, exit_i = "TP", tp, entry_i

        for k in range(entry_i+1, min(entry_i+LIMIT+1, len(candles))) if outcome == "TIMEOUT" else ():
            q = candles[k]
            hit_sl = q["low"] <= sl if direction == "LONG" else q["high"] >= sl
            hit_tp = q["high"] >= tp if direction == "LONG" else q["low"] <= tp
            if hit_sl and hit_tp:
                outcome, exit_price, exit_i = "AMBIGUOUS_BOTH_HIT", sl, k
                break
            if hit_sl:
                outcome, exit_price, exit_i = "SL", sl, k
                break
            if hit_tp:
                outcome, exit_price, exit_i = "TP", tp, k
                break

        if direction == "LONG":
            pnl = (exit_price-entry)/entry*100
        else:
            pnl = (entry-exit_price)/entry*100
        pnl -= COST_PCT

        trades.append({
            "timeframe": tf,
            "direction": direction,
            "zone_low": round(zlo, 6),
            "zone_high": round(zhi, 6),
            "entry_time": datetime.fromtimestamp(
                entry_c["time"], timezone.utc).isoformat(),
            "exit_time": datetime.fromtimestamp(
                candles[exit_i]["time"], timezone.utc).isoformat(),
            "entry": entry, "stop_loss": sl, "take_profit": tp,
            "exit_price": exit_price, "outcome": outcome,
            "pnl_net_percent": pnl, "bars_held": exit_i-entry_i
        })

    # نتایج هم‌پوشان حذف می‌شوند تا هر موقعیت مستقل باشد.
    selected, last_exit = [], -1
    for t in trades:
        ei = next((n for n, c in enumerate(candles)
                   if datetime.fromtimestamp(c["time"], timezone.utc).isoformat()
                   == t["entry_time"]), -1)
        xi = next((n for n, c in enumerate(candles)
                   if datetime.fromtimestamp(c["time"], timezone.utc).isoformat()
                   == t["exit_time"]), -1)
        if ei <= last_exit:
            continue
        selected.append(t)
        last_exit = xi
    return selected

def main():
    print("BTC40 | FVG PAPER BACKTEST | NO ORDERS")
    all_trades = []
    h1 = fetch("Min60")
    data = {
        "30m": fetch("Min30"),
        "1h": h1,
        "4h": aggregate_4h(h1)
    }
    for tf, candles in data.items():
        if len(candles) < LIMIT + 10:
            print(f"{tf}: کندل کافی نیست ({len(candles)})")
            continue
        trades = backtest(candles, tf)
        all_trades.extend(trades)
        tp = sum(t["outcome"] == "TP" for t in trades)
        sl = sum(t["outcome"] == "SL" for t in trades)
        timeout = sum(t["outcome"] == "TIMEOUT" for t in trades)
        ambiguous = sum(t["outcome"] == "AMBIGUOUS_BOTH_HIT" for t in trades)
        net = sum(t["pnl_net_percent"] for t in trades)
        print(f"\n{tf}: candles={len(candles)} trades={len(trades)}")
        print(f"TP={tp} SL={sl} TIMEOUT={timeout} BOTH_HIT={ambiguous}")
        print(f"Net={net:.3f}% | Avg={net/len(trades):.3f}%" if trades
              else "معامله‌ای ثبت نشد")

    if all_trades:
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_trades[0].keys()))
            w.writeheader()
            w.writerows(all_trades)
        print(f"\nذخیره شد: {OUT} | کل معاملات: {len(all_trades)}")
    else:
        print("\nمعامله‌ای ثبت نشد؛ فایل نتیجه ساخته نشد.")

if __name__ == "__main__":
    main()
