from pathlib import Path

p = Path("fvg_backtest.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
'''        entry_c = candles[entry_i]
        entry = (zlo + zhi) / 2''',
'''        entry_c = candles[entry_i]
        entry = max(zlo, entry_c["low"])
        entry = min(entry, zhi)
        if not (entry_c["low"] <= entry <= entry_c["high"]):
            continue'''
)

s = s.replace(
'''        outcome = "TIMEOUT"
        exit_price = candles[min(entry_i+LIMIT, len(candles)-1)]["close"]
        exit_i = min(entry_i+LIMIT, len(candles)-1)

        for k in range(entry_i+1, min(entry_i+LIMIT+1, len(candles))):''',
'''        outcome = "TIMEOUT"
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

        for k in range(entry_i+1, min(entry_i+LIMIT+1, len(candles))) if outcome == "TIMEOUT" else ():'''
)

p.write_text(s, encoding="utf-8")
print("FVG backtest patched")
