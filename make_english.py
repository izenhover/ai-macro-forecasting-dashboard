# make_english.py
import re

with open("dashboard.py", "r", encoding="utf-8") as f:
    code = f.read()

# ۱. تغییر چیدمان از راست‌به‌چپ به چپ‌به‌راست
code = code.replace("direction: rtl;", "direction: ltr;")
code = code.replace("text-align: right;", "text-align: left;")

# ۲. دیکشنری ترجمه کلمات
replacements = {
    "دلار · طلا · نفت · تایم‌فریم چندگانه": "USD · GOLD · OIL · MULTI-TIMEFRAME",
    "🔮 پیش‌بینی چند تایم‌فریمی دلار": "🔮 Multi-Timeframe USD Forecast",
    "نرخ فعلی دلار آزاد": "Current Free USD Rate",
    "تومان": "Tomans",
    "تومان ·": "Tomans ·",
    "پیش‌بینی ۷ روز آینده": "7-Day Forecast",
    "حد پایین:": "Lower:",
    "حد بالا:": "Upper:",
    "ضریب بتا:": "Beta:",
    "طلا:": "Gold:",
    "بخر": "BUY",
    "بفروش": "SELL",
    "صبر": "HOLD",
    "دلیل:": "Reason:",
    "پیشنهاد سرمایه:": "Capital Suggestion:",
    "مبنا:": "Basis:",
    "۱ ساعته": "1-Hour",
    "۴ ساعته": "4-Hour",
    "۱ روزه": "1-Day",
    "۶ ساعت آینده": "Next 6 Hours",
    "۱۲ ساعت آینده": "Next 12 Hours",
    "۷ روز آینده": "Next 7 Days",
    "نرخ فعلی": "Current",
    "پیش‌بینی": "Forecast",
    "تغییر انتظاری": "Expected Change",
    "رژیم": "Regime",
    "نوسان": "Volatility",
    "سیگنال نهایی": "Final Signal",
}

for fa, en in replacements.items():
    code = code.replace(fa, en)

# ۳. اصلاح تابع سیگنال‌دهی برای اینکه فقط انگلیسی برگرداند
old_signal = '''def tf_signal(change_pct):
    if change_pct is None:
        return "HOLD", "صبر"
    if change_pct > 1.5:
        return "BUY", "بخر"
    elif change_pct < -1.5:
        return "SELL", "بفروش"
    else:
        return "HOLD", "صبر"'''

new_signal = '''def tf_signal(change_pct):
    if change_pct is None:
        return "HOLD", "HOLD"
    if change_pct > 1.5:
        return "BUY", "BUY"
    elif change_pct < -1.5:
        return "SELL", "SELL"
    else:
        return "HOLD", "HOLD"'''

if old_signal in code:
    code = code.replace(old_signal, new_signal)

with open("dashboard.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✅ Dashboard is now fully English and LTR!")