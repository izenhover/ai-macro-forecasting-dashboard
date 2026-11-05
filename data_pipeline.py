"""خط لوله داده: جمعآوری همگامسازی و مهندسی ویگی"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from loguru import logger
from config import CONFIG
import yfinance as yf
import ta
import warnings
warnings.filterwarnings("ignore")

from iran_market import IranMarketData


def _flatten_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """صاف کردن ستونهای MultiIndex به نامهای ساده"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            f"{ticker}_{col[0].lower()}" if isinstance(col, tuple)
            else f"{ticker}_{col.lower()}"
            for col in df.columns
        ]
    else:
        df.columns = [f"{ticker}_{str(c).lower()}" for c in df.columns]
    return df


class DataPipeline:
    """خط لوله داده کامل"""

    def __init__(self):
        self.scaler = RobustScaler()
        self.feature_columns = []
        self.data = None
        self.iran_data = IranMarketData()

    def fetch_data(self) -> pd.DataFrame:
        """دریافت داده از Yahoo Finance"""
        logger.info("📥 دریافت داده قیمتی...")

        frames = {}
        for ticker in CONFIG.data.assets:
            try:
                df = yf.download(
                    ticker,
                    period=f"{CONFIG.data.lookback_days}d",
                    interval=CONFIG.data.freq,
                    progress=False,
                    auto_adjust=True,
                )
                if df is None or df.empty:
                    logger.warning(f"⚠️ داده {ticker} خالی است")
                    continue

                df = df.dropna(how="all")
                df = _flatten_columns(df, ticker)
                frames[ticker] = df
                logger.info(f"✅ {ticker}: {len(df)} رکورد")
            except Exception as e:
                logger.error(f"❌ خطا در دریافت {ticker}: {e}")

        if not frames:
            raise ValueError("هیچ دادهای دریافت نشد")

        merged = pd.concat(frames.values(), axis=1)
        merged = merged.loc[:, ~merged.columns.duplicated()]
        merged = merged.ffill().bfill()

        nunique = merged.nunique()
        valid_cols = nunique[nunique > 1].index.tolist()
        merged = merged[valid_cols]

        self.data = merged
        logger.info(f"✅ داده ادغام شده: {merged.shape}")
        return merged

    def add_iran_market(self, df: pd.DataFrame) -> pd.DataFrame:
        """اضافه کردن دادههای بازار ایران (دلار آزاد طلا سکه)"""
        iran_df = self.iran_data.build_dataframe(df.index)

        # ادغام ستونهای ایران
        for col in iran_df.columns:
            df[f"iran_{col}"] = iran_df[col].values

        logger.info(f"✅ {len(iran_df.columns)} ویگی ایران اضافه شد")
        return df

    def add_macro_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """افزودن شاخصهای کلان بینالمللی"""
        logger.info("📊 افزودن شاخصهای کلان...")

        macro_tickers = {
            "DX-Y.NYB": "dxy",
            "^TNX": "us10y",
            "^VIX": "vix",
        }

        for ticker, name in macro_tickers.items():
            try:
                mdf = yf.download(
                    ticker, period="1y", interval="1d",
                    progress=False, auto_adjust=True
                )
                if mdf is None or mdf.empty:
                    continue
                mdf = mdf.dropna(how="all")
                mdf = _flatten_columns(mdf, name)
                close_cols = [c for c in mdf.columns if "close" in c]
                if close_cols:
                    df = df.join(mdf[close_cols], how="left")
                    logger.info(f"   ✅ {name} اضافه شد")
            except Exception as e:
                logger.warning(f"   ⚠️ خطا در {name}: {e}")

        df = df.ffill().bfill()
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """مهندسی ویگیها"""
        logger.info("🔧 مهندسی ویگیها...")

        close_cols = [c for c in df.columns if "close" in c.lower()]
        if not close_cols:
            logger.warning("⚠️ هیچ ستون Close پیدا نشد")
            return df

        # بازدهی برای ستونهای بینالمللی
        for col in close_cols:
            df[f"{col}_ret"] = df[col].pct_change()
            df[f"{col}_logret"] = np.log1p(
                df[col].pct_change().clip(-0.99, 10)
            )

        # میانگینهای متحرک
        for col in close_cols:
            df[f"{col}_sma20"] = df[col].rolling(20, min_periods=1).mean()
            df[f"{col}_sma50"] = df[col].rolling(50, min_periods=1).mean()
            df[f"{col}_ema12"] = df[col].ewm(span=12, adjust=False).mean()
            df[f"{col}_ema26"] = df[col].ewm(span=26, adjust=False).mean()

        # نوسان
        for col in close_cols:
            ret_col = f"{col}_ret"
            if ret_col in df.columns:
                df[f"{col}_vol20"] = df[ret_col].rolling(20, min_periods=5).std()
                df[f"{col}_vol60"] = df[ret_col].rolling(60, min_periods=10).std()

        # RSI و MACD
        for col in close_cols:
            try:
                df[f"{col}_rsi"] = ta.momentum.RSIIndicator(
                    df[col].ffill(), window=14
                ).rsi()
            except Exception:
                pass
            try:
                macd = ta.trend.MACD(df[col].ffill())
                df[f"{col}_macd"] = macd.macd()
                df[f"{col}_macd_hist"] = macd.macd_diff()
            except Exception:
                pass

        # نسبت طلا/نفت جهانی
        gold_cols = [c for c in close_cols if "gc=" in c.lower()]
        oil_cols = [c for c in close_cols if "cl=" in c.lower()]
        if gold_cols and oil_cols:
            g, o = gold_cols[0], oil_cols[0]
            df["gold_oil_ratio"] = df[g] / df[o].replace(0, np.nan)

        # مقایسه طلای جهانی و طلای ایران
        if "iran_gold_18g" in df.columns and "GC=F_close" in df.columns:
            df["gold_global_vs_iran"] = (
                df["GC=F_close"] / df["iran_gold_18g"].replace(0, np.nan)
            )

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill().bfill()
        df = df.dropna(axis=1, how="all")

        logger.info(f"✅ {len(df.columns)} ویگی ساخته شد")
        self.feature_columns = list(df.columns)
        return df

    def normalize(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """نرمالسازی مقاوم"""
        if fit:
            scaled = self.scaler.fit_transform(df)
        else:
            scaled = self.scaler.transform(df)
        return pd.DataFrame(scaled, columns=df.columns, index=df.index)

    def run(self) -> pd.DataFrame:
        """اجرای کل خط لوله"""
        df = self.fetch_data()
        df = self.add_iran_market(df)       # ← جدید: داده ایران
        df = self.add_macro_features(df)
        df = self.engineer_features(df)
        return df
