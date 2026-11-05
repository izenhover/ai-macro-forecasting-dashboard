"""دریافت نرخ زنده بازار ایران از TGJU"""

import requests
import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime


class IranMarketData:
    """دریافت داده‌های بازار ایران از API زنده TGJU"""

    # TGJU public JSON endpoint
    TGJU_URL = "https://call1.tgju.org/ajax.json"

    # نمادهای TGJU
    SYMBOLS = {
        "usd_free": "price_dollar_rl",
        "gold_18g": "geram18",
        "coin_emami": "sekee",
    }

    def __init__(self):
        self.data = None
        self.last_update = None
        self.live_status = "UNKNOWN"

    def fetch_live(self):
        """دریافت نرخ‌های لحظه‌ای از TGJU"""
        try:
            logger.info("🌐 درخواست از TGJU...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
            r = requests.get(self.TGJU_URL, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()

            current = data.get("current", {})

            usd = current.get(self.SYMBOLS["usd_free"], {}).get("p", "0")
            gold = current.get(self.SYMBOLS["gold_18g"], {}).get("p", "0")
            coin = current.get(self.SYMBOLS["coin_emami"], {}).get("p", "0")

            usd = float(str(usd).replace(",", ""))
            gold = float(str(gold).replace(",", ""))
            coin = float(str(coin).replace(",", ""))

            if usd <= 0:
                raise ValueError("Invalid USD price from TGJU")

            self.last_update = datetime.now()
            self.live_status = "LIVE"

            logger.info("   ✅ LIVE - دلار آزاد: " + format(usd, ",.0f") + " تومان")
            logger.info("   ✅ LIVE - طلای ۱۸ عیار: " + format(gold, ",.0f") + " تومان")
            logger.info("   ✅ LIVE - سکه امام: " + format(coin, ",.0f") + " تومان")
            logger.info("   ⏰ زمان به‌روزرسانی: " + self.last_update.strftime("%H:%M:%S"))

            return {
                "usd_free": usd,
                "gold_18g": gold,
                "coin_emami": coin,
                "inflation_rate": 17.5,
                "timestamp": self.last_update,
                "source": "TGJU",
            }
        except Exception as e:
            logger.error("❌ TGJU failed: " + str(e))
            return self._get_fallback_data()

    def _get_fallback_data(self):
        """داده پشتیبان در صورت قطعی"""
        logger.warning("⚠️ استفاده از داده پشتیبان (hardcoded)")
        self.live_status = "FALLBACK"
        return {
            "usd_free": 265159,
            "gold_18g": 8300000,
            "coin_emami": 84000000,
            "inflation_rate": 17.5,
            "timestamp": datetime.now(),
            "source": "FALLBACK",
        }

    def build_dataframe(self, target_index):
        live = self.fetch_live()
        current_usd = live["usd_free"]
        current_gold = live["gold_18g"]
        current_coin = live["coin_emami"]

        df = pd.DataFrame(index=target_index)
        df["usd_free"] = current_usd
        df["gold_18g"] = current_gold
        df["coin_emami"] = current_coin
        df["inflation_rate"] = live["inflation_rate"]

        for col in ["usd_free", "gold_18g", "coin_emami"]:
            df[col + "_ret"] = 0.0
            df[col + "_logret"] = 0.0

        df["gold_usd_ratio"] = df["gold_18g"] / df["usd_free"]
        df["coin_bubble"] = df["coin_emami"] / (df["gold_18g"] * 8.13 + 1)

        self.data = df
        logger.info("   ✅ " + str(len(df)) + " روز داده ایران ساخته شد (نرخ: " + format(current_usd, ",.0f") + ")")
        return df

    def get_summary(self):
        if self.data is None or self.data.empty:
            live = self._get_fallback_data()
            return {
                "usd_free": live["usd_free"],
                "gold_18g": live["gold_18g"],
                "coin_emami": live["coin_emami"],
                "inflation": live["inflation_rate"],
                "gold_usd_ratio": live["gold_18g"] / live["usd_free"],
                "coin_bubble": 1.0,
                "source": live["source"],
                "last_update": live["timestamp"].strftime("%H:%M:%S"),
            }
        latest = self.data.iloc[-1]
        return {
            "usd_free": float(latest["usd_free"]),
            "gold_18g": float(latest["gold_18g"]),
            "coin_emami": float(latest["coin_emami"]),
            "inflation": float(latest["inflation_rate"]),
            "gold_usd_ratio": float(latest["gold_usd_ratio"]),
            "coin_bubble": float(latest["coin_bubble"]),
            "source": self.live_status,
            "last_update": self.last_update.strftime("%H:%M:%S") if self.last_update else "N/A",
        }
