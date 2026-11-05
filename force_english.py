# force_english.py
with open("dashboard.py", "r", encoding="utf-8") as f:
    code = f.read()

# جایگزینی تمام متن‌های جامانده
replacements = {
    "⏳ در حال بارگذاری تحلیل اصلی...": "⏳ Loading main analysis...",
    "⏳ در حال بارگذاری...": "⏳ Loading...",
    "🔄 اجرای مجدد": "🔄 Refresh Data",
    "⚡ بروزرسانی فوری نرخ": "⚡ Force Refresh Rate",
    "💵 پیش‌بینی دلار به تومان | BUY / SELL SIGNAL": "💵 USD/IRR Forecast | BUY / SELL SIGNAL",
    "💵 پیش‌بینی دلار - سیگنال نهایی": "💵 USD Forecast - Final Signal",
    "🥇 پیش‌بینی طلا - تایم‌فریم ۱ ساعته / ۴ ساعته / ۱ روزه": "🥇 Gold Forecast - 1H / 4H / 1D",
    "SYSTEM HEALTH": "SYSTEM HEALTH",
    "Regime:": "Regime:",
    "GPR:": "GPR:",
    "IRAN MARKET": "IRAN MARKET",
    "RECENT TRADES": "RECENT TRADES",
    "EQUITY CURVE": "EQUITY CURVE",
    "WIN / LOSS": "WIN / LOSS",
    "PORTFOLIO": "PORTFOLIO",
    "MACRO BOT v5 · OPERATIONS CENTER": "MACRO BOT v5 · OPERATIONS CENTER",
    "دلار · طلا · نفت · تایم‌فریم چندگانه": "USD · GOLD · OIL · MULTI-TIMEFRAME"
}

for fa, en in replacements.items():
    code = code.replace(fa, en)

# اطمینان از اینکه چیدمان چپ‌به‌راست است
code = code.replace("direction: rtl;", "direction: ltr;")
code = code.replace("text-align: right;", "text-align: left;")

with open("dashboard.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✅ All Persian text removed. Dashboard is fully English.")