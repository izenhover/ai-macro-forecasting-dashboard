"""پیش‌بینی دلار به تومان در تایم‌فریم‌های مختلف"""

from loguru import logger


def beta_coefficient(regime, cvar):
    """ضریب بتای دلار نسبت به طلا بر اساس رژیم و ریسک"""
    if regime == "HIGH_VOL":
        beta = 0.5
    elif regime == "BEAR":
        beta = 0.9
    elif regime == "BULL":
        beta = 0.7
    else:
        beta = 0.7
    if cvar is not None and cvar > 0.03:
        beta *= 0.85
    if cvar is not None and cvar > 0.05:
        beta *= 0.85
    return beta


def predict_usd_from_gold(gold_pred_tf, usd_current, regime, cvar, tf):
    """تبدیل پیش‌بینی طلا به پیش‌بینی دلار

    دلار ایران معمولاً همبستگی مثبت با طلا دارد.
    ضریب بتا بر اساس رژیم و CVaR تنظیم می‌شود.
    """
    if gold_pred_tf is None or "error" in gold_pred_tf:
        return None
    if usd_current is None or usd_current <= 0:
        return None

    gold_change = gold_pred_tf.get("change_pct", 0)
    beta = beta_coefficient(regime, cvar)
    usd_change = gold_change * beta
    usd_predicted = usd_current * (1 + usd_change / 100)

    # بازه اطمینان بر اساس عدم قطعیت طلا
    if "upper" in gold_pred_tf and "lower" in gold_pred_tf and "current" in gold_pred_tf:
        gold_range = (gold_pred_tf["upper"] - gold_pred_tf["lower"]) / gold_pred_tf["current"]
    else:
        gold_range = 0.05

    usd_lower = usd_predicted * (1 - gold_range * 0.4)
    usd_upper = usd_predicted * (1 + gold_range * 0.4)

    return {
        "timeframe": tf,
        "current": usd_current,
        "predicted": usd_predicted,
        "change_pct": usd_change,
        "lower": usd_lower,
        "upper": usd_upper,
        "beta": beta,
        "gold_change": gold_change,
    }
