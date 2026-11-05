"""موتور استنتاج علّی و شاخص ریسک ژئوپلیتیک"""

import numpy as np
import pandas as pd
from loguru import logger
from config import CONFIG
import warnings
warnings.filterwarnings("ignore")


class CausalEngine:
    """استنتاج علّی با CausalAlpha و GPR Index"""
    
    def __init__(self):
        self.gpr_index = None
        self.causal_graph = None
        self.keyword_categories = {
            "conflict": [
                "جنگ", "درگیری", "حمله", "موشک", "بمباران",
                "war", "conflict", "attack", "missile", "strike"
            ],
            "political": [
                "تحریم", "مذاکره", "توافق", "دولت", "انتخابات",
                "sanction", "negotiation", "deal", "election"
            ],
            "energy": [
                "نفت", "اوپک", "انرژی", "صادرات", "خط لوله",
                "oil", "opec", "energy", "export", "pipeline"
            ],
            "trade": [
                "تجارت", "صادرات", "واردات", "تعرفه", "گمرک",
                "trade", "tariff", "customs", "export", "import"
            ],
            "financial": [
                "بانک", "ارز", "بورس", "سرمایه", "بدهی",
                "bank", "currency", "stock", "capital", "debt"
            ],
        }
    
    def build_gpr_index(
        self, 
        texts: list, 
        timestamps: list = None
    ) -> pd.Series:
        """ساخت شاخص ریسک ژئوپلیتیک از متون"""
        logger.info("🌍 ساخت شاخص GPR...")
        
        if not texts:
            logger.warning("⚠️ هیچ متنی برای تحلیل وجود ندارد")
            return pd.Series(dtype=float)
        
        scores = []
        for text in texts:
            category_scores = {}
            text_lower = text.lower()
            
            for category, keywords in self.keyword_categories.items():
                count = sum(1 for kw in keywords if kw in text_lower)
                category_scores[category] = count
            
            # امتیاز کل
            total = sum(category_scores.values())
            scores.append(total)
        
        if timestamps is not None:
            gpr = pd.Series(scores, index=pd.to_datetime(timestamps))
        else:
            gpr = pd.Series(scores, index=pd.RangeIndex(len(scores)))
        
        # میانگین متحرک ۷ روزه
        gpr_smooth = gpr.rolling(7, min_periods=1).mean()
        self.gpr_index = gpr_smooth
        
        logger.info(f"✅ GPR Index ساخته شد: {len(gpr)} نقطه")
        return gpr_smooth
    
    def estimate_causal_effect(
        self, 
        gpr: pd.Series, 
        asset_returns: pd.Series
    ) -> dict:
        """تخمین اثر علّی GPR بر بازدهی دارایی"""
        # همترازی
        combined = pd.DataFrame({
            "gpr": gpr, 
            "returns": asset_returns
        }).dropna()
        
        if len(combined) < 30:
            return {"effect": 0.0, "p_value": 1.0, "significant": False}
        
        # آزمون علیت گرنجر
        from scipy import stats
        
        # تأخیرهای ممکن
        max_lag = min(10, len(combined) // 5)
        best_p = 1.0
        best_lag = 1
        
        for lag in range(1, max_lag + 1):
            # رگرسیون با تأخیر
            y = combined["returns"].values[lag:]
            X_lagged = combined["gpr"].values[:-lag]
            
            # همبستگی
            corr, p_value = stats.pearsonr(X_lagged, y)
            
            if p_value < best_p:
                best_p = p_value
                best_lag = lag
        
        # اثر
        corr, p_value = stats.pearsonr(
            combined["gpr"].values, 
            combined["returns"].values
        )
        
        return {
            "effect": float(corr),
            "p_value": float(best_p),
            "best_lag": best_lag,
            "significant": best_p < 0.05,
        }
    
    def get_risk_signal(self, gpr_value: float) -> dict:
        """سیگنال ریسک بر اساس GPR"""
        if self.gpr_index is None or len(self.gpr_index) == 0:
            return {"signal": "NEUTRAL", "level": 0.5}
        
        mean_gpr = self.gpr_index.mean()
        std_gpr = self.gpr_index.std()
        
        if std_gpr == 0:
            z_score = 0
        else:
            z_score = (gpr_value - mean_gpr) / std_gpr
        
        if z_score > 2:
            signal = "EXTREME_RISK"
            level = 0.95
        elif z_score > 1:
            signal = "HIGH_RISK"
            level = 0.8
        elif z_score > 0:
            signal = "ELEVATED"
            level = 0.6
        elif z_score > -1:
            signal = "NORMAL"
            level = 0.4
        else:
            signal = "LOW_RISK"
            level = 0.2
        
        return {
            "signal": signal,
            "level": level,
            "z_score": float(z_score),
            "gpr_value": float(gpr_value),
        }