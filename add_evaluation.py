from pathlib import Path

p = Path.home() / "btc40" / "bot.py"
src = p.read_text(encoding="utf-8")
marker = "\ndef main():"

if marker not in src:
    raise SystemExit("تابع main پیدا نشد؛ فایل تغییر نکرد.")

backup = p.with_name("bot.py.before_evaluation.bak")
backup.write_text(src, encoding="utf-8")
prefix = src.split(marker, 1)[0]

new_main = r'''
def main():
    import json
    import csv

    folder = os.path.dirname(os.path.abspath(__file__))
    state_file = os.path.join(folder, "evaluation_state.json")
    results_file = os.path.join(folder, "evaluation_results.csv")

    # حداکثر مدت ارزیابی: ۴ ساعت، ۸ ساعت و ۲۴ ساعت
    max_bars = {"5 دقیقه": 48, "15 دقیقه": 32, "1 ساعت": 24}

    if not os.path.exists(results_file):
        with open(results_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timeframe", "direction", "entry_time", "exit_time",
                "entry", "stop_loss", "take_profit", "exit_price",
                "outcome", "pnl_percent", "bars", "patterns"
            ])

    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}

    state.setdefault("pending", [])
    state.setdefault("last_reported", {})
    pending = state["pending"]
    last_reported = state["last_reported"]

    def save_state():
        state["pending"] = pending
        state["last_reported"] = last_reported
        temp = state_file + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(temp, state_file)

    def record_result(trade, outcome, exit_time, exit_price, bars):
        entry = float(trade["entry"])
        direction = trade["direction"]

        if outcome == "AMBIGUOUS":
            pnl = ""
        else:
            exit_price = float(exit_price)
            pnl = (
                (exit_price - entry) / entry * 100
                if direction == "LONG"
                else (entry - exit_price) / entry * 100
            )

        with open(results_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                trade["timeframe"], direction, trade["entry_time"],
                datetime.fromtimestamp(exit_time).strftime("%Y-%m-%d %H:%M"),
                entry, trade["sl"], trade["tp"],
                "" if exit_price is None else round(float(exit_price), 4),
                outcome, "" if pnl == "" else round(pnl, 5),
                bars, trade["patterns"]
            ])

        if outcome == "TP":
            print(f"ارزیابی: موفق؛ حد سود لمس شد. {trade['timeframe']}")
        elif outcome == "SL":
            print(f"ارزیابی: ناموفق؛ حد ضرر لمس شد. {trade['timeframe']}")
        elif outcome == "AMBIGUOUS":
            print("ارزیابی مبهم: حد سود و ضرر در یک کندل لمس شدند.")
        else:
            print(f"ارزیابی: پایان زمان؛ نتیجه بر اساس قیمت پایانی ثبت شد.")

    def evaluate_pending(candles_by_tf):
        remaining = []

        for trade in pending:
            label = trade["timeframe"]
            cs = candles_by_tf.get(label, [])
            if not cs:
                remaining.append(trade)
                continue

            entry_t = int(trade["entry_t"])
            last_t = int(trade.get("last_eval_t", entry_t))
            bars = int(trade.get("bars", 0))
            finished = False

            for candle in cs:
                t = int(candle["t"])
                if t <= last_t or t <= entry_t:
                    continue

                high = float(candle["h"])
                low = float(candle["l"])
                sl = float(trade["sl"])
                tp = float(trade["tp"])
                direction = trade["direction"]

                hit_sl = low <= sl if direction == "LONG" else high >= sl
                hit_tp = high >= tp if direction == "LONG" else low <= tp

                bars += 1
                trade["last_eval_t"] = t
                trade["bars"] = bars

                # اگر هر دو در یک کندل لمس شوند، ترتیب مشخص نیست.
                if hit_sl and hit_tp:
                    record_result(trade, "AMBIGUOUS", t, None, bars)
                    finished = True
                    break
                if hit_sl:
                    record_result(trade, "SL", t, sl, bars)
                    finished = True
                    break
                if hit_tp:
                    record_result(trade, "TP", t, tp, bars)
                    finished = True
                    break
                if bars >= max_bars.get(label, 24):
                    record_result(trade, "TIMEOUT", t, float(candle["c"]), bars)
                    finished = True
                    break

            if not finished:
                remaining.append(trade)

        pending[:] = remaining

    def print_summary():
        counts = {"TP": 0, "SL": 0, "TIMEOUT": 0, "AMBIGUOUS": 0}
        try:
            with open(results_file, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    outcome = row.get("outcome", "")
                    if outcome in counts:
                        counts[outcome] += 1
        except OSError:
            return

        decided = counts["TP"] + counts["SL"]
        win_rate = counts["TP"] / decided * 100 if decided else 0
        print(
            f"نتایج ثبت‌شده: TP={counts['TP']} | SL={counts['SL']} | "
            f"پایان زمان={counts['TIMEOUT']} | مبهم={counts['AMBIGUOUS']}"
        )
        if decided:
            print(f"درصد موفقیت سیگنال‌های تعیین‌تکلیف‌شده: {win_rate:.1f}%")
        else:
            print("هنوز سیگنال کافی برای محاسبه درصد موفقیت وجود ندارد.")

    print("BTC PATTERN BOT | EVALUATION MODE")
    print("TEST MODE — NO REAL TRADES")
    print("فایل نتایج:", results_file)

    try:
        load_telegram_config()
    except Exception as e:
        print("تنظیم تلگرام مشکل دارد:", str(e))
        return

    send_telegram(
        "ربات ارزیابی بیت‌کوین فعال شد.\n"
        "سیگنال‌ها آزمایشی هستند؛ هیچ معامله‌ای انجام نمی‌شود."
    )

    while True:
        try:
            market = {}
            for label, (interval, seconds) in TIMEFRAMES.items():
                market[label] = fetch(interval, seconds)

            # ابتدا سیگنال‌های قبلی را ارزیابی کن.
            evaluate_pending(market)

            trends = {
                label: trend_direction(cs)
                for label, cs in market.items()
            }

            print("\nروندها:", " | ".join(
                f"{label}: {('صعودی' if d == 'LONG' else 'نزولی' if d == 'SHORT' else 'خنثی')}"
                for label, d in trends.items()
            ))

            for label, (interval, seconds) in TIMEFRAMES.items():
                cs = market.get(label, [])
                if len(cs) < 60:
                    continue

                candle_time = int(cs[-1]["t"])
                if last_reported.get(label) == candle_time:
                    continue
                last_reported[label] = candle_time

                price = float(cs[-1]["c"])
                stamp = datetime.fromtimestamp(candle_time).strftime("%Y-%m-%d %H:%M")
                print(f"\n{label} | کندل بسته‌شده: {stamp} | BTC: {price:.2f}")

                found = detect(cs)
                directional = [
                    (name, direction) for name, direction in found
                    if direction in ("LONG", "SHORT")
                ]

                if not directional:
                    print("سیگنال جدیدی پیدا نشد.")
                    continue

                directions = {d for _, d in directional}
                if len(directions) != 1:
                    print("رد شد: الگوها هم‌جهت نیستند.")
                    continue

                direction = next(iter(directions))
                if any(trends.get(tf) != direction for tf in TIMEFRAMES):
                    print("رد شد: روند هر سه تایم‌فریم تأیید نمی‌کند.")
                    continue

                # جلوگیری از چند سیگنال باز هم‌زمان در یک تایم‌فریم
                if any(t["timeframe"] == label for t in pending):
                    print("رد شد: برای این تایم‌فریم هنوز سیگنال باز وجود دارد.")
                    continue

                atr = calculate_atr(cs)
                if atr is None:
                    print("رد شد: ATR معتبر نیست.")
                    continue

                sl = price - atr if direction == "LONG" else price + atr
                tp = price + 2 * atr if direction == "LONG" else price - 2 * atr
                pattern_names = ", ".join(name for name, _ in directional)

                trade = {
                    "timeframe": label,
                    "direction": direction,
                    "entry_t": candle_time,
                    "last_eval_t": candle_time,
                    "entry_time": stamp,
                    "entry": price,
                    "sl": sl,
                    "tp": tp,
                    "bars": 0,
                    "patterns": pattern_names
                }
                pending.append(trade)

                direction_fa = "صعودی (LONG)" if direction == "LONG" else "نزولی (SHORT)"
                pattern_fa = "\n".join(
                    f"• {PATTERN_FA.get(name, name)}" for name, _ in directional
                )

                message = (
                    "₿ سیگنال آزمایشی برای ارزیابی\n"
                    f"تایم‌فریم: {label}\n"
                    f"جهت: {direction_fa}\n"
                    f"ورود فرضی: {price:.2f} USDT\n"
                    f"حد ضرر: {sl:.2f} USDT\n"
                    f"حد سود: {tp:.2f} USDT\n"
                    f"زمان کندل: {stamp}\n\n"
                    f"{pattern_fa}\n\n"
                    "هیچ سفارش واقعی ثبت نمی‌شود."
                )
                print(f"سیگنال ثبت شد: {direction_fa} | SL {sl:.2f} | TP {tp:.2f}")
                send_telegram(message)

            save_state()
            print(f"سیگنال‌های در انتظار نتیجه: {len(pending)}")
            print_summary()

        except Exception as e:
            print("خطای حلقه اصلی:", type(e).__name__, str(e)[:180])

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nربات با درخواست کاربر متوقف شد.")
'''

p.write_text(prefix + "\n" + new_main.lstrip(), encoding="utf-8")
print("سیستم ارزیابی اضافه شد.")
print("پشتیبان:", backup)
