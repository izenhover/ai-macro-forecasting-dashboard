"""فایل اصلی اجرای سیستم پیشبینی و مدیریت ریسک"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO")
logger.add("system_log.log", rotation="10 MB", level="DEBUG")

from config import CONFIG
from data_pipeline import DataPipeline
from sentiment_engine import SentimentEngine
from regime_detector import RegimeDetector
from prediction_engine import PredictionEngine
from risk_manager import RiskManager
from online_learner import OnlineLearner
from causal_engine import CausalEngine


def main():
    logger.info("=" * 60)
    logger.info("🚀 شروع سیستم پیشبینی طلا نفت و دلار")
    logger.info("=" * 60)

    # ==================== ۱. داده ====================
    logger.info("\n📊 مرحله ۱: جمعآوری داده")
    pipeline = DataPipeline()
    df = pipeline.run()
    logger.info(f"✅ داده نهایی: {df.shape}")

    # ==================== ۲. Sentiment ====================
    logger.info("\n🧠 مرحله ۲: تحلیل Sentiment")
    sentiment_engine = SentimentEngine()
    sample_news = [
        "قیمت طلا در بازار جهانی افزایش یافت",
        "تحریمهای جدید علیه صادرات نفت ایران اعمال شد",
        "نرخ دلار در بازار آزاد به بالاترین سطح رسید",
        "توافق تجاری جدید بین ایران و چین امضا شد",
        "تنشهای سیاسی در منطقه خاورمیانه تشدید شد",
    ]
    sentiment_results = sentiment_engine.batch_analyze(
        sample_news,
        ["farsnews", "reuters", "donya-e-eqtesad", "default", "reuters"]
    )
    agg_sentiment = sentiment_engine.aggregate_sentiment(sentiment_results)
    logger.info(f"   Sentiment: {agg_sentiment['avg_sentiment']:.3f}")

    # ==================== ۳. تشخیص ریم ====================
    logger.info("\n🔬 مرحله ۳: تشخیص ریم بازار")
    regime_detector = RegimeDetector()

    ret_cols = [c for c in df.columns if c.endswith("_close_logret")]
    if not ret_cols:
        ret_cols = [c for c in df.columns if c.endswith("_ret") and "log" not in c]

    if not ret_cols:
        logger.error("❌ ستون بازدهی پیدا نشد")
        return

    returns = df[ret_cols[0]].replace([np.inf, -np.inf], np.nan).dropna().clip(-0.5, 0.5)

    if len(returns) < 50:
        logger.error(f"❌ داده کافی نیست: {len(returns)}")
        return

    volatility = returns.rolling(20, min_periods=5).std().dropna()

    try:
        regime_result = regime_detector.fit(returns, volatility)
        current_regime = regime_result["current_regime"]
        logger.info(f"   ریم فعلی: {current_regime}")
        logger.info(f"   توزیع: {regime_result['regime_distribution']}")
    except Exception as e:
        logger.error(f"❌ خطا در ریم: {e}")
        current_regime = "SIDEWAYS"

    # ==================== ۴. پیشبینی ====================
    logger.info("\n📈 مرحله ۴: پیشبینی قیمت")

    # انتخاب ستون هدف: قیمت طلا (نه بازدهی) برای نمایش قابلفهم
    price_target = None
    for c in df.columns:
        if "gc=" in c.lower() and c.endswith("_close"):
            price_target = c
            break

    if price_target is None:
        price_target = ret_cols[0]  # fallback به بازدهی

    # فقط ویگیهای عددی معتبر
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    valid_cols = [c for c in numeric_cols if df[c].notna().sum() > len(df) * 0.8 and c != price_target]
    valid_cols = [price_target] + valid_cols

    df_clean = df[valid_cols].replace([np.inf, -np.inf], np.nan).dropna()
    # حذف outliers شدید
    for c in df_clean.columns:
        q1, q99 = df_clean[c].quantile([0.001, 0.999])
        df_clean[c] = df_clean[c].clip(q1, q99)

    if len(df_clean) < CONFIG.prediction.seq_length + 50:
        logger.error(f"❌ داده کافی نیست: {len(df_clean)}")
        return

    input_dim = len(df_clean.columns)
    pred_engine = PredictionEngine(input_dim)

    try:
        train_results = pred_engine.train_models(df_clean, price_target)
        for name, metrics in train_results.items():
            logger.info(f"   {name}: MAE={metrics['val_mae']:.2f}, MSE={metrics['val_loss']:.2f}")

        prediction = pred_engine.predict(df_clean, price_target)

        # قیمت فعلی برای مقایسه
        current_price = float(df_clean[price_target].iloc[-1])

        logger.info(f"   💰 قیمت فعلی: {current_price:.2f}")
        logger.info(f"   🎯 پیشبینی: {prediction['point_prediction']:.2f}")
        logger.info(f"   📉 بازه ۹۰٪: [{prediction['lower_bound']:.2f}, {prediction['upper_bound']:.2f}]")
        logger.info(f"   📊 عدم قطعیت: {prediction['uncertainty']:.2f}")

        # درصد تغییر
        change_pct = (prediction['point_prediction'] - current_price) / current_price * 100
        logger.info(f"   📈 تغییر انتظاری: {change_pct:+.2f}%")
    except Exception as e:
        logger.error(f"❌ خطا در پیشبینی: {e}")
        import traceback
        traceback.print_exc()
        prediction = {"point_prediction": 0.0, "lower_bound": 0.0, "upper_bound": 0.0, "uncertainty": 0.0}
        current_price = 0.0

    # ==================== ۵. استنتاج علی ====================
    logger.info("\n🌍 مرحله ۵: استنتاج علی")
    causal_engine = CausalEngine()
    gpr = causal_engine.build_gpr_index(sample_news)
    if len(gpr) > 0:
        risk_signal = causal_engine.get_risk_signal(gpr.iloc[-1])
        logger.info(f"   سیگنال ریسک: {risk_signal['signal']}")

    # ==================== ۶. مدیریت ریسک ====================
    logger.info("\n🛡️ مرحله ۶: مدیریت ریسک")
    risk_manager = RiskManager()

    # استفاده از logret برای HRP (پایدارتر از ret خام)
    hrp_cols = [c for c in df.columns if c.endswith("_close_logret")]
    if not hrp_cols:
        hrp_cols = [c for c in df.columns if c.endswith("_close_ret")]

    risk_result = None
    if len(hrp_cols) >= 2:
        returns_df = df[hrp_cols].replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns_df) > 30:
            try:
                risk_result = risk_manager.full_risk_management(
                    returns_df, current_regime, prediction
                )
                if risk_result["weights"]:
                    logger.info(f"   وزنهای نهایی:")
                    for asset, weight in risk_result["weights"].items():
                        logger.info(f"      {asset}: {weight:.2%}")
                    logger.info(f"   CVaR: {risk_result['cvar']:.2%}")
                    logger.info(f"   نوسان پرتفوی: {risk_result['portfolio_volatility']:.2%}")
                    for w in risk_result["warnings"]:
                        logger.warning(f"   {w}")
            except Exception as e:
                logger.error(f"❌ خطا در ریسک: {e}")

    # ==================== ۷. یادگیری آنلاین ====================
    logger.info("\n🔄 مرحله ۷: یادگیری آنلاین")
    online_learner = OnlineLearner()
    for i in range(min(50, len(returns) - 1)):
        online_learner.update(returns.iloc[i], returns.iloc[i + 1])
    perf = online_learner.get_performance_metrics()
    logger.info(f"   MAE فعلی: {perf.get('current_mae', 0):.6f}")
    logger.info(f"   تعداد Drift: {perf.get('drift_events', 0)}")

    # ==================== خلاصه ====================
       # ==================== خلاصه ====================
    logger.info("\n" + "=" * 60)
    logger.info("📋 خلاصه نهایی")
    logger.info("=" * 60)
    logger.info(f"🏷️ رژیم بازار: {current_regime}")
    logger.info(f"📊 Sentiment: {agg_sentiment['avg_sentiment']:.3f}")

    # 💰 بازار جهانی
    if current_price > 0:
        logger.info(f"\n💰 بازار جهانی طلا:")
        logger.info(f"   قیمت فعلی: ${current_price:.2f}")
        logger.info(f"   پیش‌بینی: ${prediction['point_prediction']:.2f}")
        logger.info(f"   بازه ۹۰٪: [${prediction['lower_bound']:.2f}, ${prediction['upper_bound']:.2f}]")
        change_pct = (prediction['point_prediction'] - current_price) / current_price * 100
        logger.info(f"   تغییر انتظاری: {change_pct:+.2f}%")

    # 🇮🇷 بازار ایران
    iran_summary = pipeline.iran_data.get_summary()
    if iran_summary:
        logger.info(f"\n🇮🇷 بازار ایران:")
        logger.info(f"   💵 دلار آزاد: {iran_summary['usd_free']:,.0f} تومان")
        logger.info(f"   🏅 طلای ۱۸ عیار: {iran_summary['gold_18g']:,.0f} تومان")
        logger.info(f"   🪙 سکه امام: {iran_summary['coin_emami']:,.0f} تومان")
        logger.info(f"   📈 نرخ تورم: {iran_summary['inflation']:.1f}%")
        logger.info(f"   💎 نسبت طلا/دلار: {iran_summary['gold_usd_ratio']:.4f}")
        logger.info(f"   🫧 حباب سکه: {iran_summary['coin_bubble']:.2f}")

    if risk_result and risk_result.get("cvar"):
        logger.info(f"\n🛡️ CVaR: {risk_result['cvar']:.2%}")
    logger.info("=" * 60)
    logger.info("✅ پایان")
    

if __name__ == "__main__":
    main()
