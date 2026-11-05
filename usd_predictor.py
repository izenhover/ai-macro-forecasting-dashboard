"""پیش‌بینی و سیگنال خرید/فروش دلار به تومان"""

import numpy as np
import pandas as pd
from loguru import logger
import warnings
from usd_predictor import USDPredictor
warnings.filterwarnings("ignore")


class USDPredictor:
    """پیش‌بینی دلار به تومان با سیگنال خرید/فروش"""

    def __init__(self):
        self.current_price = 0
        self.predictions = {}
        self.history = None

    def fit_predict(self, df, target_col="iran_usd_free", horizons=[7, 14, 30]):
        """آموزش و پیش‌بینی برای چند افق زمانی"""
        from prediction_engine import PredictionEngine
        from config import CONFIG

        if target_col not in df.columns:
            logger.error(f"ستون {target_col} پیدا نشد")
            return None

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        valid_cols = [c for c in numeric_cols
                      if df[c].notna().sum() > len(df) * 0.8 and c != target_col]
        valid_cols = [target_col] + valid_cols

        df_clean = df[valid_cols].replace([np.inf, -np.inf], np.nan).dropna()
        for c in df_clean.columns:
            q1, q99 = df_clean[c].quantile([0.001, 0.999])
            df_clean[c] = df_clean[c].clip(q1, q99)

        if len(df_clean) < CONFIG.prediction.seq_length + 50:
            logger.error(f"داده کافی نیست: {len(df_clean)}")
            return None

        logger.info("💵 آموزش مدل دلار...")
        engine = PredictionEngine(len(df_clean.columns))
        engine.train_models(df_clean, target_col)

        self.current_price = float(df_clean[target_col].iloc[-1])
        self.history = df_clean[target_col]

        # پیش‌بینی ۷ روزه (مدل اصلی)
        pred = engine.predict(df_clean, target_col)
        base_change = (pred["point_prediction"] - self.current_price) / self.current_price

        # شبیه‌سازی افق‌های بلندتر با فرض مومنتوم خطی
        for h in horizons:
            if h == 7:
                point = pred["point_prediction"]
                lower = pred["lower_bound"]
                upper = pred["upper_bound"]
            else:
                # مقیاس‌دهی خطی به افق بلندتر
                scale = h / 7
                point = self.current_price * (1 + base_change * np.sqrt(scale))
                spread = (pred["upper_bound"] - pred["lower_bound"]) / 2
                lower = point - spread * np.sqrt(scale)
                upper = point + spread * np.sqrt(scale)

            self.predictions[h] = {
                "point": float(point),
                "lower": float(lower),
                "upper": float(upper),
                "change_pct": float((point - self.current_price) / self.current_price * 100),
            }

        return {
            "current": self.current_price,
            "predictions": self.predictions,
        }

    def get_signal(self, df):
        """سیگنال خرید/فروش با ترکیب چند شاخص"""
        if not self.predictions:
            return None

        pred_7d = self.predictions.get(7, {})
        pred_change = pred_7d.get("change_pct", 0)

        # RSI
        rsi = 50.0
        if "iran_usd_free_ret" in df.columns:
            returns = df["iran_usd_free_ret"].tail(14).dropna()
            if len(returns) > 0:
                gains = returns[returns > 0].sum()
                losses = -returns[returns < 0].sum()
                if losses > 0:
                    rs = gains / losses
                    rsi = float(100 - 100 / (1 + rs))
                elif gains > 0:
                    rsi = 100.0

        # مومنتوم
        mom_signal = "NEUTRAL"
        if "iran_usd_free" in df.columns:
            price = df["iran_usd_free"].dropna()
            if len(price) >= 30:
                ma7 = price.tail(7).mean()
                ma30 = price.tail(30).mean()
                if ma7 > ma30 * 1.01:
                    mom_signal = "BULLISH"
                elif ma7 < ma30 * 0.99:
                    mom_signal = "BEARISH"

        # امتیاز ترکیبی
        score = 0
        # پیش‌بینی ۷ روزه
        if pred_change > 5: score += 3
        elif pred_change > 2: score += 2
        elif pred_change > 0.5: score += 1
        elif pred_change < -5: score -= 3
        elif pred_change < -2: score -= 2
        elif pred_change < -0.5: score -= 1

        # RSI
        if rsi < 30: score += 2
        elif rsi < 45: score += 1
        elif rsi > 70: score -= 2
        elif rsi > 55: score -= 1

        # مومنتوم
        if mom_signal == "BULLISH": score += 1
        elif mom_signal == "BEARISH": score -= 1

        # تصمیم نهایی
        if score >= 3:
            action, action_fa = "BUY", "بخر"
            urgency = "فوری 🔥" if score >= 5 else "معمولی"
            color = "#00a86b"
            timing = "امروز یا فردا"
            reasoning = "پیش‌بینی صعودی + RSI پایین"
            target = self.current_price * 1.08
            stop_loss = self.current_price * 0.95
        elif score <= -3:
            action, action_fa = "SELL", "بفروش"
            urgency = "فوری 🔥" if score <= -5 else "معمولی"
            color = "#d62828"
            timing = "امروز یا فردا"
            reasoning = "پیش‌بینی نزولی + RSI بالا"
            target = self.current_price * 0.92
            stop_loss = self.current_price * 1.03
        else:
            action, action_fa = "HOLD", "صبر کن"
            urgency = "بدون عجله"
            color = "#5a7a9a"
            timing = "منتظر سیگنال واضح‌تر"
            reasoning = "بازار در تعادل"
            target = self.current_price
            stop_loss = self.current_price

        return {
            "action": action,
            "action_fa": action_fa,
            "urgency": urgency,
            "color": color,
            "score": int(score),
            "pred_change_7d": float(pred_change),
            "rsi": float(rsi),
            "momentum": mom_signal,
            "timing": timing,
            "reasoning": reasoning,
            "target": float(target),
            "stop_loss": float(stop_loss),
        }