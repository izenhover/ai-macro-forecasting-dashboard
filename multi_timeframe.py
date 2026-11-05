"""دریافت داده چند تایم‌فریمی: 1h, 4h, 1d"""

import yfinance as yf
import pandas as pd
import numpy as np
from loguru import logger
import warnings
warnings.filterwarnings("ignore")


def fetch_ohlcv(ticker, interval, period):
    """دریافت OHLCV برای یک تایم‌فریم"""
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
        else:
            df.columns = [str(c).lower() for c in df.columns]
        df = df.rename(columns={"adj close": "close"})
        return df
    except Exception as e:
        logger.warning("fetch " + ticker + " " + interval + " failed: " + str(e))
        return None


def resample_to_4h(df_1h):
    """تبدیل داده ۱ ساعته به ۴ ساعته"""
    if df_1h is None or df_1h.empty:
        return None
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    agg = {k: v for k, v in agg.items() if k in df_1h.columns}
    df_4h = df_1h.resample("4H").agg(agg).dropna()
    return df_4h


def build_features(df, prefix):
    """مهندسی ویژگی‌های پایه"""
    if df is None or df.empty or "close" not in df.columns:
        return None
    out = pd.DataFrame(index=df.index)
    out[prefix + "_close"] = df["close"].values
    if "volume" in df.columns:
        out[prefix + "_volume"] = df["volume"].values
    out[prefix + "_ret"] = out[prefix + "_close"].pct_change()
    out[prefix + "_logret"] = np.log1p(out[prefix + "_ret"].clip(-0.5, 0.5))
    out[prefix + "_sma20"] = out[prefix + "_close"].rolling(20, min_periods=1).mean()
    out[prefix + "_sma50"] = out[prefix + "_close"].rolling(50, min_periods=1).mean()
    out[prefix + "_vol20"] = out[prefix + "_ret"].rolling(20, min_periods=5).std()
    out[prefix + "_range"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan) if "high" in df.columns else 0
    return out


def get_timeframe_data(timeframe):
    """دریافت داده برای یک تایم‌فریم مشخص
    timeframe: '1h', '4h', '1d'
    """
    logger.info("Fetching timeframe: " + timeframe)

    if timeframe == "1h":
        raw = fetch_ohlcv("GC=F", "1h", "60d")
        if raw is None or len(raw) < 200:
            return None
        features = build_features(raw, "gold")
        if features is None:
            return None
        features = features.dropna()
        logger.info("   1h rows: " + str(len(features)))
        return features

    elif timeframe == "4h":
        raw_1h = fetch_ohlcv("GC=F", "1h", "60d")
        if raw_1h is None:
            return None
        raw_4h = resample_to_4h(raw_1h)
        if raw_4h is None or len(raw_4h) < 100:
            return None
        features = build_features(raw_4h, "gold")
        if features is None:
            return None
        features = features.dropna()
        logger.info("   4h rows: " + str(len(features)))
        return features

    elif timeframe == "1d":
        raw = fetch_ohlcv("GC=F", "1d", "2y")
        if raw is None or len(raw) < 100:
            return None
        features = build_features(raw, "gold")
        if features is None:
            return None
        features = features.dropna()
        logger.info("   1d rows: " + str(len(features)))
        return features

    return None


def get_seq_length(timeframe):
    """seq_length مناسب برای هر تایم‌فریم"""
    if timeframe == "1h":
        return 48
    elif timeframe == "4h":
        return 30
    else:
        return 60
