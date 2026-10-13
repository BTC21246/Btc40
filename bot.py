#!/usr/bin/env python3
# BTC 40 Candlestick Patterns - Ourbit Futures - TEST MODE / NO REAL TRADES
# Terminal-only. No Telegram, no orders, no API keys required.

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

def load_telegram_config():
    cfg = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram.txt")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    token = cfg.get("BOT_TOKEN", "")
    chat_id = cfg.get("CHAT_ID", "")
    if not token or not chat_id:
        raise ValueError("BOT_TOKEN یا CHAT_ID در telegram.txt خالی است")
    return token, chat_id


PATTERN_FA = {
    "Bullish Engulfing": "پوشای صعودی",
    "Bearish Engulfing": "پوشای نزولی",
    "Hammer": "چکش",
    "Inverted Hammer": "چکش وارونه",
    "Hanging Man": "مرد آویزان",
    "Shooting Star": "ستاره ثاقب",
    "Doji": "دوجی",
    "Dragonfly Doji": "دوجی سنجاقک",
    "Gravestone Doji": "دوجی سنگ قبر",
    "Morning Star": "ستاره صبحگاهی",
    "Evening Star": "ستاره شامگاهی",
    "Morning Doji Star": "ستاره دوجی صبحگاهی",
    "Evening Doji Star": "ستاره دوجی شامگاهی",
    "Piercing Line": "خط نفوذی صعودی",
    "Dark Cloud Cover": "پوشش ابر تیره",
    "Bullish Harami": "هارامی صعودی",
    "Bearish Harami": "هارامی نزولی",
    "Bullish Harami Cross": "صلیب هارامی صعودی",
    "Bearish Harami Cross": "صلیب هارامی نزولی",
    "Tweezer Bottom": "کف انبرکی",
    "Tweezer Top": "سقف انبرکی",
    "Three White Soldiers": "سه سرباز سفید",
    "Three Black Crows": "سه کلاغ سیاه",
    "Three Inside Up": "سه‌گانه داخلی صعودی",
    "Three Inside Down": "سه‌گانه داخلی نزولی",
    "Three Outside Up": "سه‌گانه خارجی صعودی",
    "Three Outside Down": "سه‌گانه خارجی نزولی",
    "Rising Three Methods": "سه روش صعودی",
    "Falling Three Methods": "سه روش نزولی",
    "Bullish Marubozu": "ماروبوزوی صعودی",
    "Bearish Marubozu": "ماروبوزوی نزولی",
    "Spinning Top": "فرفره",
    "Long Legged Doji": "دوجی پا‌بلند",
    "Abandoned Baby": "نوزاد رهاشده",
    "Upside Gap Two Crows": "دو کلاغ با شکاف صعودی",
    "Downside Tasuki Gap": "شکاف تاسکی نزولی",
    "Head and Shoulders": "سر و شانه",
    "Inverse Head and Shoulders": "سر و شانه معکوس",
    "Double Top": "سقف دوقلو",
    "Double Bottom": "کف دوقلو",
}

def send_telegram(message):
    try:
        token, chat_id = load_telegram_config()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(
            url,
            data={"chat_id": chat_id, "text": message},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()
        if not result.get("ok"):
            print("Telegram API پیام را نپذیرفت:", result.get("description", "خطای نامشخص"))
            return False
        print("پیام تلگرام ارسال شد.")
        return True
    except Exception as e:
        print("خطای تلگرام:", type(e).__name__, str(e)[:200])
        return False

PATTERN_FA = {
    "Bullish Engulfing": "پوشای صعودی",
    "Bearish Engulfing": "پوشای نزولی",
    "Hammer": "چکش",
    "Inverted Hammer": "چکش وارونه",
    "Hanging Man": "مرد آویزان",
    "Shooting Star": "ستاره ثاقب",
    "Doji": "دوجی",
    "Dragonfly Doji": "دوجی سنجاقک",
    "Gravestone Doji": "دوجی سنگ قبر",
    "Morning Star": "ستاره صبحگاهی",
    "Evening Star": "ستاره شامگاهی",
    "Morning Doji Star": "ستاره دوجی صبحگاهی",
    "Evening Doji Star": "ستاره دوجی شامگاهی",
    "Piercing Line": "خط نفوذی صعودی",
    "Dark Cloud Cover": "پوشش ابر تیره",
    "Bullish Harami": "هارامی صعودی",
    "Bearish Harami": "هارامی نزولی",
    "Bullish Harami Cross": "صلیب هارامی صعودی",
    "Bearish Harami Cross": "صلیب هارامی نزولی",
    "Tweezer Bottom": "کف انبرکی",
    "Tweezer Top": "سقف انبرکی",
    "Three White Soldiers": "سه سرباز سفید",
    "Three Black Crows": "سه کلاغ سیاه",
    "Three Inside Up": "سه‌گانه داخلی صعودی",
    "Three Inside Down": "سه‌گانه داخلی نزولی",
    "Three Outside Up": "سه‌گانه خارجی صعودی",
    "Three Outside Down": "سه‌گانه خارجی نزولی",
    "Rising Three Methods": "سه روش صعودی",
    "Falling Three Methods": "سه روش نزولی",
    "Bullish Marubozu": "ماروبوزوی صعودی",
    "Bearish Marubozu": "ماروبوزوی نزولی",
    "Spinning Top": "فرفره",
    "Long Legged Doji": "دوجی پا‌بلند",
    "Abandoned Baby": "نوزاد رهاشده",
    "Upside Gap Two Crows": "دو کلاغ با شکاف صعودی",
    "Downside Tasuki Gap": "شکاف تاسکی نزولی",
    "Head and Shoulders": "سر و شانه",
    "Inverse Head and Shoulders": "سر و شانه معکوس",
    "Double Top": "سقف دوقلو",
    "Double Bottom": "کف دوقلو",
}


BASE_URL = "https://futures.ourbit.io/api/v1/contract/kline/BTC_USDT"
SYMBOL = "BTC_USDT"
POLL_SECONDS = 60
CANDLE_LIMIT = 240
ROOT = Path.home() / "btc40"
ROOT.mkdir(parents=True, exist_ok=True)
SENT_FILE = ROOT / "sent.json"
EVAL_FILE = ROOT / "evaluation_state.json"
RESULTS_FILE = ROOT / "evaluation_results.csv"
TIMEFRAMES = [
    ("30 دقیقه", "Min30", 30 * 60),
    ("1 ساعت", "Min60", 60 * 60),
    ("4 ساعت", "AGG4H", 4 * 60 * 60),
]
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 BTC40-TestBot/1.0"})


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return default


def write_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_field(row, *names, index=None, default=None):
    if isinstance(row, dict):
        for name in names:
            if name in row and row[name] is not None:
                return row[name]
    elif isinstance(row, (list, tuple)) and index is not None and len(row) > index:
        return row[index]
    return default


def normalize_row(row):
    # Ourbit futures usually returns objects with time/open/close/high/low/vol,
    # but array-style rows are accepted too.
    t = get_field(row, "time", "timestamp", "t", index=0)
    o = get_field(row, "open", "o", index=1)
    # Array format used by this Ourbit futures endpoint: time, open, close, high, low, vol, amount.
    h = get_field(row, "high", "h", index=3)
    l = get_field(row, "low", "l", index=4)
    c = get_field(row, "close", "c", index=2)
    v = get_field(row, "vol", "volume", "v", index=5, default=0)
    try:
        t = int(float(t))
        # Normalize seconds to milliseconds internally.
        if t < 10_000_000_000:
            t *= 1000
        return {"time": t, "open": float(o), "high": float(h), "low": float(l),
                "close": float(c), "volume": float(v or 0)}
    except (TypeError, ValueError):
        return None



def fetch(interval, seconds):
    # Do not send start/end: Ourbit returned empty arrays with those parameters.
    params = {
        "interval": interval,
        "limit": CANDLE_LIMIT,
    }

    # Retry temporary Ourbit connection failures up to 3 times.
    last_error = None
    payload = None

    for attempt in range(3):
        try:
            response = SESSION.get(
                BASE_URL,
                params=params,
                timeout=(8, 35),
            )
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                wait_seconds = 2 * (attempt + 1)
                print(
                    f"Ourbit connection attempt {attempt + 1}/3 failed; "
                    f"retrying in {wait_seconds}s: {type(exc).__name__}"
                )
                time.sleep(wait_seconds)
            else:
                raise RuntimeError(
                    f"Ourbit failed after 3 attempts: "
                    f"{type(last_error).__name__}: {last_error}"
                ) from last_error

    if isinstance(payload, dict):
        code = payload.get("code")
        if code not in (None, 0, 200, "0", "200"):
            raise RuntimeError(
                f"Ourbit API code={code}: {payload.get('msg', payload)}"
            )
        rows = payload.get("data", payload.get("result", payload.get("list", [])))
    elif isinstance(payload, list):
        rows = payload
    else:
        raise RuntimeError("ساختار پاسخ API ناشناخته است")

    # Convert Ourbit parallel arrays into individual candle records.
    if isinstance(rows, dict):
        keys = ("time", "open", "close", "high", "low")
        if all(isinstance(rows.get(k), list) for k in keys):
            times = rows["time"]
            opens = rows["open"]
            closes = rows["close"]
            highs = rows["high"]
            lows = rows["low"]
            volumes = rows.get("vol", rows.get("volume", []))
            n = min(len(times), len(opens), len(closes), len(highs), len(lows))
            rows = [
                {
                    "time": times[i],
                    "open": opens[i],
                    "close": closes[i],
                    "high": highs[i],
                    "low": lows[i],
                    "vol": volumes[i] if i < len(volumes) else 0,
                }
                for i in range(n)
            ]
        else:
            rows = rows.get("list", rows.get("data", []))

    rows = rows or []
    candles = [c for c in (normalize_row(r) for r in rows) if c]
    candles.sort(key=lambda x: x["time"])

    now_ms = int(time.time() * 1000)
    candles = [
        c for c in candles
        if c["time"] + seconds * 1000 <= now_ms
    ]

    unique = {c["time"]: c for c in candles}
    candles = [unique[k] for k in sorted(unique)]

    if len(candles) < 5:
        latest = candles[-1]["time"] if candles else None
        raise RuntimeError(
            f"کندل کافی دریافت نشد: {len(candles)} "
            f"(interval={interval}, response_rows={len(rows)}, "
            f"latest_closed_ms={latest})"
        )

    return candles

def aggregate_4h(hourly):
    # Build 4h candles from completed hourly candles, avoiding uncertain Hour4 API support.
    grouped = {}
    for c in hourly:
        bucket = (c["time"] // (4 * 3600 * 1000)) * (4 * 3600 * 1000)
        grouped.setdefault(bucket, []).append(c)
    result = []
    now_ms = int(time.time() * 1000)
    for bucket, group in sorted(grouped.items()):
        group.sort(key=lambda x: x["time"])
        # Require four consecutive hourly candles and a fully closed 4h bucket.
        if len(group) != 4 or group[-1]["time"] - group[0]["time"] != 3 * 3600 * 1000:
            continue
        if bucket + 4 * 3600 * 1000 > now_ms:
            continue
        result.append({"time": bucket, "open": group[0]["open"],
                       "high": max(x["high"] for x in group),
                       "low": min(x["low"] for x in group),
                       "close": group[-1]["close"],
                       "volume": sum(x["volume"] for x in group)})
    return result


def candle(c):
    o, h, l, cl = c["open"], c["high"], c["low"], c["close"]
    rng = max(h - l, 1e-12)
    body = abs(cl - o)
    return {"o": o, "h": h, "l": l, "c": cl, "range": rng, "body": body,
            "bull": cl > o, "bear": cl < o, "small": body / rng <= 0.12,
            "long_body": body / rng >= 0.60, "upper": h - max(o, cl),
            "lower": min(o, cl) - l, "mid": (o + cl) / 2,
            "body_hi": max(o, cl), "body_lo": min(o, cl)}


def detect(cs):
    """Return matches from a set of 40 common candlestick-pattern rules."""
    if len(cs) < 5:
        return []
    a, b, c, d, e = [candle(x) for x in cs[-5:]]
    # Previous candles provide a lightweight local context, not a trade filter.
    prior = [x["close"] for x in cs[-8:-1]]
    rising = len(prior) >= 3 and prior[-1] > prior[0]
    falling = len(prior) >= 3 and prior[-1] < prior[0]
    found = []
    def add(name, direction, condition):
        if condition:
            found.append((name, direction))
    # Single-candle patterns (1-12)
    add("Hammer", "LONG", e["lower"] >= 2 * max(e["body"], 1e-12) and e["upper"] <= e["body"] * .6 and not e["small"])
    add("Inverted Hammer", "LONG", e["upper"] >= 2 * max(e["body"], 1e-12) and e["lower"] <= e["body"] * .6 and falling)
    add("Hanging Man", "SHORT", e["lower"] >= 2 * max(e["body"], 1e-12) and e["upper"] <= e["body"] * .6 and rising)
    add("Shooting Star", "SHORT", e["upper"] >= 2 * max(e["body"], 1e-12) and e["lower"] <= e["body"] * .6 and rising)
    add("Bullish Marubozu", "LONG", e["bull"] and e["long_body"] and e["upper"] / e["range"] < .08 and e["lower"] / e["range"] < .08)
    add("Bearish Marubozu", "SHORT", e["bear"] and e["long_body"] and e["upper"] / e["range"] < .08 and e["lower"] / e["range"] < .08)
    add("Doji", "NEUTRAL", e["small"])
    add("Dragonfly Doji", "LONG", e["small"] and e["upper"] / e["range"] < .08 and e["lower"] / e["range"] > .6)
    add("Gravestone Doji", "SHORT", e["small"] and e["lower"] / e["range"] < .08 and e["upper"] / e["range"] > .6)
    add("Spinning Top", "NEUTRAL", e["body"] / e["range"] < .3 and e["upper"] / e["range"] > .2 and e["lower"] / e["range"] > .2 and not e["small"])
    # Two-candle patterns (13-28)
    add("Bullish Engulfing", "LONG", d["bear"] and e["bull"] and e["o"] <= d["c"] and e["c"] >= d["o"] and e["body"] > d["body"])
    add("Bearish Engulfing", "SHORT", d["bull"] and e["bear"] and e["o"] >= d["c"] and e["c"] <= d["o"] and e["body"] > d["body"])
    add("Bullish Harami", "LONG", d["bear"] and e["bull"] and e["body_hi"] < d["body_hi"] and e["body_lo"] > d["body_lo"])
    add("Bearish Harami", "SHORT", d["bull"] and e["bear"] and e["body_hi"] < d["body_hi"] and e["body_lo"] > d["body_lo"])
    add("Harami Cross Bullish", "LONG", d["bear"] and e["small"] and e["h"] < d["body_hi"] and e["l"] > d["body_lo"])
    add("Harami Cross Bearish", "SHORT", d["bull"] and e["small"] and e["h"] < d["body_hi"] and e["l"] > d["body_lo"])
    add("Piercing Line", "LONG", d["bear"] and e["bull"] and e["o"] < d["l"] and e["c"] > d["mid"] and e["c"] < d["o"])
    add("Dark Cloud Cover", "SHORT", d["bull"] and e["bear"] and e["o"] > d["h"] and e["c"] < d["mid"] and e["c"] > d["o"])
    add("Tweezer Bottom", "LONG", d["bear"] and e["bull"] and abs(d["l"] - e["l"]) <= max(d["range"], e["range"]) * .08)
    add("Tweezer Top", "SHORT", d["bull"] and e["bear"] and abs(d["h"] - e["h"]) <= max(d["range"], e["range"]) * .08)
    add("Bullish Meeting Lines", "LONG", d["bear"] and e["bull"] and abs(e["c"] - d["c"]) <= e["range"] * .05)
    add("Bearish Meeting Lines", "SHORT", d["bull"] and e["bear"] and abs(e["c"] - d["c"]) <= e["range"] * .05)
    add("Bullish Kicking", "LONG", d["bear"] and e["bull"] and e["o"] > d["h"] and d["long_body"] and e["long_body"])
    add("Bearish Kicking", "SHORT", d["bull"] and e["bear"] and e["o"] < d["l"] and d["long_body"] and e["long_body"])
    # Three-candle patterns (29-40)
    add("Morning Star", "LONG", c["bear"] and c["long_body"] and d["body"] < c["body"] * .5 and e["bull"] and e["c"] > (c["o"] + c["c"]) / 2)
    add("Evening Star", "SHORT", c["bull"] and c["long_body"] and d["body"] < c["body"] * .5 and e["bear"] and e["c"] < (c["o"] + c["c"]) / 2)
    add("Morning Doji Star", "LONG", c["bear"] and c["long_body"] and d["small"] and e["bull"] and e["c"] > (c["o"] + c["c"]) / 2)
    add("Evening Doji Star", "SHORT", c["bull"] and c["long_body"] and d["small"] and e["bear"] and e["c"] < (c["o"] + c["c"]) / 2)
    add("Three White Soldiers", "LONG", c["bull"] and d["bull"] and e["bull"] and c["c"] < d["c"] < e["c"] and d["o"] > c["o"] and e["o"] > d["o"])
    add("Three Black Crows", "SHORT", c["bear"] and d["bear"] and e["bear"] and c["c"] > d["c"] > e["c"] and d["o"] < c["o"] and e["o"] < d["o"])
    add("Three Inside Up", "LONG", c["bear"] and d["bull"] and d["body_hi"] < c["body_hi"] and d["body_lo"] > c["body_lo"] and e["bull"] and e["c"] > c["o"])
    add("Three Inside Down", "SHORT", c["bull"] and d["bear"] and d["body_hi"] < c["body_hi"] and d["body_lo"] > c["body_lo"] and e["bear"] and e["c"] < c["o"])
    add("Three Outside Up", "LONG", c["bear"] and d["bull"] and d["c"] > c["o"] and d["o"] < c["c"] and e["bull"] and e["c"] > d["c"])
    add("Three Outside Down", "SHORT", c["bull"] and d["bear"] and d["c"] < c["o"] and d["o"] > c["c"] and e["bear"] and e["c"] < d["c"])
    add("Three Line Strike Bullish", "LONG", c["bull"] and d["bull"] and e["bull"] and e["o"] < c["o"] and e["c"] > d["c"] and e["long_body"])
    add("Three Line Strike Bearish", "SHORT", c["bear"] and d["bear"] and e["bear"] and e["o"] > c["o"] and e["c"] < d["c"] and e["long_body"])
    add("Rising Three Methods", "LONG", a["bull"] and a["long_body"] and b["bear"] and d["bear"] and e["bull"] and e["c"] > a["h"])
    add("Falling Three Methods", "SHORT", a["bear"] and a["long_body"] and b["bull"] and d["bull"] and e["bear"] and e["c"] < a["l"])
    add("Abandoned Baby Bullish", "LONG", c["bear"] and d["small"] and d["h"] < c["l"] and e["bull"] and e["l"] > d["h"])
    add("Abandoned Baby Bearish", "SHORT", c["bull"] and d["small"] and d["l"] > c["h"] and e["bear"] and e["h"] < d["l"])
    return found

def candle_time(c):
    return datetime.fromtimestamp(c["time"] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def atr(cs, period=14):
    values = []
    for i in range(max(1, len(cs) - period), len(cs)):
        cur, prev = cs[i], cs[i - 1]
        values.append(max(cur["high"] - cur["low"], abs(cur["high"] - prev["close"]), abs(cur["low"] - prev["close"])))
    return sum(values) / len(values) if values else cs[-1]["close"] * .005


def init_results_file():
    global RESULTS_FILE
    RESULTS_FILE = ROOT / "evaluation_results_fixed.csv"
    if not RESULTS_FILE.exists():
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "signal_time_utc", "timeframe", "pattern", "direction",
                "entry", "tp", "sl", "result", "exit_price", "checked_time_utc"
            ])


def update_evaluation(candles_by_tf):
    state = read_json(EVAL_FILE, {"pending": []})
    pending = state.get("pending", [])
    remaining = []

    # Combine only pending records with identical trade parameters.
    # This preserves distinct entries and distinct stop/target levels.
    merged = {}
    for p in pending:
        try:
            key = (
                str(p["tf_key"]), int(p["signal_ms"]),
                str(p["direction"]), round(float(p["entry"]), 8),
                round(float(p["tp"]), 8), round(float(p["sl"]), 8)
            )
            if key not in merged:
                merged[key] = dict(p)
                merged[key]["patterns"] = list(
                    p.get("patterns") or [p.get("pattern", "Unknown")]
                )
            else:
                names = p.get("patterns") or [p.get("pattern", "Unknown")]
                for name in names:
                    if name not in merged[key]["patterns"]:
                        merged[key]["patterns"].append(name)
        except (KeyError, TypeError, ValueError):
            # Do not discard malformed or legacy records.
            remaining.append(p)

    pending = list(merged.values())

    header = [
        "timeframe", "direction", "entry_time", "exit_time",
        "entry", "stop_loss", "take_profit", "exit_price",
        "outcome", "pnl_percent", "bars", "patterns"
    ]

    # Keep evaluation output in its own 12-column file.
    RESULTS_FILE = ROOT / "evaluation_results.csv"
    if not RESULTS_FILE.exists():
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(header)

    # Load already-recorded trade signatures to prevent duplicate results.
    recorded = set()
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                required = {"timeframe", "direction", "entry_time", "entry",
                            "stop_loss", "take_profit"}
                if reader.fieldnames and required.issubset(reader.fieldnames):
                    for row in reader:
                        try:
                            recorded.add((
                                str(row["timeframe"]),
                                str(row["direction"]),
                                str(row["entry_time"]),
                                round(float(row["entry"]), 8),
                                round(float(row["stop_loss"]), 8),
                                round(float(row["take_profit"]), 8),
                            ))
                        except (TypeError, ValueError):
                            pass
        except OSError as exc:
            print(f"هشدار: خواندن نتایج قبلی ناموفق بود: {exc}")

    with open(RESULTS_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        for p in pending:
            cs = candles_by_tf.get(p.get("tf_key"), [])
            future = [x for x in cs if x["time"] > p["signal_ms"]]
            result = None
            exit_price = ""
            exit_time = ""
            bars = ""

            for i, x in enumerate(future[:12], start=1):
                if p["direction"] == "LONG":
                    hit_sl = x["low"] <= float(p["sl"])
                    hit_tp = x["high"] >= float(p["tp"])
                else:
                    hit_sl = x["high"] >= float(p["sl"])
                    hit_tp = x["low"] <= float(p["tp"])

                if hit_sl and hit_tp:
                    result = "AMBIGUOUS_BOTH_HIT"
                    exit_price = ""
                    exit_time = candle_time(x)
                    bars = i
                    break
                if hit_sl:
                    result = "SL"
                    exit_price = p["sl"]
                    exit_time = candle_time(x)
                    bars = i
                    break
                if hit_tp:
                    result = "TP"
                    exit_price = p["tp"]
                    exit_time = candle_time(x)
                    bars = i
                    break

            if result is None and len(future) >= 12:
                x = future[11]
                result = "TIMEOUT"
                exit_price = x["close"]
                exit_time = candle_time(x)
                bars = 12

            if result:
                signature = (
                    str(p["timeframe"]),
                    str(p["direction"]),
                    str(p["signal_time"]),
                    round(float(p["entry"]), 8),
                    round(float(p["sl"]), 8),
                    round(float(p["tp"]), 8),
                )
                if signature in recorded:
                    # Already recorded: do not append the same trade again.
                    continue

                pnl = ""
                if result != "AMBIGUOUS_BOTH_HIT":
                    if p["direction"] == "LONG":
                        pnl = (float(exit_price) - float(p["entry"])) / float(p["entry"]) * 100
                    else:
                        pnl = (float(p["entry"]) - float(exit_price)) / float(p["entry"]) * 100
                    pnl = round(pnl, 4)

                names = p.get("patterns") or [p.get("pattern", "Unknown")]
                writer.writerow([
                    p["timeframe"], p["direction"],
                    p["signal_time"], exit_time,
                    p["entry"], p["sl"], p["tp"],
                    exit_price, result, pnl, bars, " | ".join(names)
                ])
                recorded.add(signature)
            else:
                remaining.append(p)

    state["pending"] = remaining
    write_json(EVAL_FILE, state)

def main():
    print("BTC 40 CANDLE PATTERNS | OURBIT | TEST MODE | NO REAL TRADES")
    print("Grouped confirmations | Telegram alerts | No real orders")
    print("Timeframes: 30m, 1h, 4h | Ctrl+C to stop.\n")

    sent = read_json(SENT_FILE, {})

    while True:
        all_candles = {}
        try:
            hourly = None

            for label, interval, seconds in TIMEFRAMES:
                tf_key = str(seconds)

                try:
                    if interval == "AGG4H":
                        if hourly is None:
                            hourly = fetch("Min60", 3600)
                        cs = aggregate_4h(hourly)
                    else:
                        cs = fetch(interval, seconds)

                    if not cs:
                        print(f"{label}: کندل بسته‌شده‌ای دریافت نشد.")
                        continue

                    all_candles[tf_key] = cs
                    last = cs[-1]
                    matches = detect(cs)

                    print(
                        f"\n{label} | کندل بسته‌شده: {candle_time(last)}"
                        f" | BTC: {last['close']:.2f}"
                    )

                    if not matches:
                        print("الگوی جدیدی در آخرین کندل شناسایی نشد.")
                        continue

                    grouped = {"LONG": [], "SHORT": []}
                    for name, direction in matches:
                        print(f"  الگو: {name} | جهت: {direction}")
                        if direction in grouped and name not in grouped[direction]:
                            grouped[direction].append(name)

                    active = [
                        direction for direction in ("LONG", "SHORT")
                        if grouped[direction]
                    ]

                    # Conflicting bullish and bearish patterns:
                    # do not issue a directional signal for this candle.
                    if len(active) == 2:
                        conflict_key = f"{tf_key}:{last['time']}:CONFLICT"
                        if conflict_key not in sent:
                            print("تعارض الگوهای صعودی و نزولی؛ سیگنالی صادر نشد.")
                            sent[conflict_key] = int(time.time())
                        continue

                    if not active:
                        continue

                    direction = active[0]
                    names = sorted(grouped[direction])
                    signal_key = f"{tf_key}:{last['time']}:GROUP:{direction}"

                    if signal_key in sent:
                        continue

                    # Avoid resending a grouped alert for a candle
                    # already processed by the older per-pattern version.
                    old_keys = [
                        f"{tf_key}:{last['time']}:{name}:{direction}"
                        for name in names
                    ]
                    if any(key in sent for key in old_keys):
                        sent[signal_key] = int(time.time())
                        continue

                    entry = float(last["close"])
                    volatility = atr(cs)
                    risk = max(volatility * 1.2, entry * 0.001)

                    if direction == "LONG":
                        sl, tp = entry - risk, entry + risk * 1.5
                        direction_fa = "صعودی (LONG)"
                    else:
                        sl, tp = entry + risk, entry - risk * 1.5
                        direction_fa = "نزولی (SHORT)"

                    entry, tp, sl = round(entry, 2), round(tp, 2), round(sl, 2)

                    state = read_json(EVAL_FILE, {"pending": []})
                    state.setdefault("pending", [])

                    # Do not add the same grouped position twice.
                    exists = any(
                        str(p.get("tf_key")) == tf_key
                        and int(p.get("signal_ms", -1)) == int(last["time"])
                        and p.get("direction") == direction
                        and round(float(p.get("entry", 0)), 8) == round(entry, 8)
                        and round(float(p.get("tp", 0)), 8) == round(tp, 8)
                        and round(float(p.get("sl", 0)), 8) == round(sl, 8)
                        for p in state["pending"]
                    )

                    if not exists:
                        state["pending"].append({
                            "signal_time": candle_time(last),
                            "signal_ms": int(last["time"]),
                            "timeframe": label,
                            "tf_key": tf_key,
                            "patterns": names,
                            "direction": direction,
                            "entry": entry,
                            "tp": tp,
                            "sl": sl
                        })
                        write_json(EVAL_FILE, state)

                    pattern_fa = [PATTERN_FA.get(n, n) for n in names]
                    tf_fa = {
                        "30 دقیقه": "۳۰ دقیقه",
                        "1 ساعت": "۱ ساعت",
                        "4 ساعت": "۴ ساعت"
                    }.get(label, label)

                    message = (
                        "🚨 سیگنال گروهی بیت‌کوین (آزمایشی)\n"
                        f"تایم‌فریم: {tf_fa}\n"
                        f"جهت احتمالی: {direction_fa}\n"
                        f"تعداد الگوهای تأییدکننده: {len(names)}\n"
                        f"الگوها: {'، '.join(pattern_fa)}\n"
                        f"ورود فرضی: {entry:.2f} USDT\n"
                        f"حد سود: {tp:.2f} USDT\n"
                        f"حد ضرر: {sl:.2f} USDT\n"
                        "⚠️ چند الگو یک موقعیت فرضی را تأیید می‌کنند؛ "
                        "معامله واقعی انجام نمی‌شود."
                    )

                    print(f"سیگنال گروهی: {direction} | تأییدها: {len(names)}")
                    print("الگوها:", "، ".join(names))
                    print(f"ورود: {entry:.2f} | حد سود: {tp:.2f} | حد ضرر: {sl:.2f}")

                    send_telegram(message)
                    sent[signal_key] = int(time.time())

                except Exception as exc:
                    print(f"\nخطا در تایم‌فریم {label}: {type(exc).__name__}: {exc}")

            if len(sent) > 5000:
                sent = dict(list(sent.items())[-2500:])
            write_json(SENT_FILE, sent)

            if all_candles:
                update_evaluation(all_candles)
                print(f"\nارزیابی آزمایشی در {RESULTS_FILE.name} ثبت می‌شود.")

        except Exception as exc:
            print(f"خطای عمومی: {type(exc).__name__}: {exc}")

        print(f"\nبررسی بعدی تا {POLL_SECONDS} ثانیه دیگر...\n" + "-" * 55)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nربات با درخواست کاربر متوقف شد.")
