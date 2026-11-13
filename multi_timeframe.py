import pandas as pd
import numpy as np
from loguru import logger
import warnings
warnings.filterwarnings("ignore")

# در نسخه رزومه True است تا بدون نیاز به اینترنت، فوری لود شود
USE_MOCK_DATA = True 

def get_timeframe_data(timeframe, ticker="GC=F", prefix="gold"):
    logger.info(f"Fetching {prefix} timeframe: {timeframe}")
    
    rows = 200 if timeframe == "1h" else 100 if timeframe == "4h" else 500
    
    if USE_MOCK_DATA:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=rows, freq='h' if timeframe!="1d" else 'D')
        
        # تعیین قیمت واقعی پایه (بازار)
        if prefix == "usd":
            base_price = 265000
        elif prefix == "gold":
            base_price = 2680
        else: # oil
            base_price = 75.5
            
        # ساخت نویز و روند
        noise = np.random.normal(0, base_price * 0.005, rows)
        prices = base_price + np.cumsum(noise)
        
        # 🎯 نکته کلیدی: آخرین قیمت را دقیقاً برابر قیمت پایه (مارکت) می‌کنیم
        prices = prices - prices[-1] + base_price
        
        df = pd.DataFrame({"close": prices}, index=dates)
    else:
        import yfinance as yf
        try:
            df = yf.download(ticker, interval=timeframe, period="60d" if timeframe!="1d" else "2y", progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
            else:
                df.columns = [str(c).lower() for c in df.columns]
            df = df.rename(columns={"adj close": "close"})
        except:
            return None

    out = pd.DataFrame(index=df.index)
    out[f"{prefix}_close"] = df["close"].values
    out[f"{prefix}_ret"] = out[f"{prefix}_close"].pct_change()
    out[f"{prefix}_sma20"] = out[f"{prefix}_close"].rolling(20, min_periods=1).mean()
    out[f"{prefix}_sma50"] = out[f"{prefix}_close"].rolling(50, min_periods=1).mean()
    return out.dropna()

def get_seq_length(timeframe):
    if timeframe == "1h": return 48
    elif timeframe == "4h": return 30
    else: return 60