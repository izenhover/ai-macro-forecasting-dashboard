"""مدیریت ریسک: HRP ریممحور + CVaR + Volatility Targeting"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
from loguru import logger
from config import CONFIG


class RiskManager:
    def __init__(self):
        self.cov_matrix = None
        self.weights = None
        self.regime = "SIDEWAYS"

    def _clean_returns(self, returns: pd.DataFrame) -> pd.DataFrame:
        """پاکسازی بازدهیها: حذف outliers و مقادیر غیرعادی"""
        df = returns.copy()
        df = df.replace([np.inf, -np.inf], np.nan)
        # Clip کردن بازدهیها به بازه منطقی
        df = df.clip(-0.5, 0.5)
        # حذف ستونهای با نوسان صفر یا خیلی بالا
        stds = df.std()
        median_std = stds.median()
        if median_std > 0:
            valid = stds[(stds > 1e-6) & (stds < 50 * median_std)].index.tolist()
            df = df[valid]
        df = df.dropna()
        return df

    def compute_hrp_weights(self, returns: pd.DataFrame) -> np.ndarray:
        logger.info("⚖️ محاسبه وزنهای HRP...")
        returns = self._clean_returns(returns)

        if returns.shape[1] < 2 or len(returns) < 20:
            n = returns.shape[1] if returns.shape[1] > 0 else 1
            return np.ones(n) / n

        cov = returns.cov().values
        corr = returns.corr().values
        corr = np.nan_to_num(corr, nan=0.0)
        np.fill_diagonal(corr, 1.0)
        corr = np.clip(corr, -1.0, 1.0)

        self.cov_matrix = cov

        dist = np.sqrt(np.clip((1 - corr) / 2, 0, 1))
        dist_condensed = squareform(dist, checks=False)
        dist_condensed = np.nan_to_num(dist_condensed, nan=0.0)

        link = linkage(dist_condensed, method="ward")
        weights = self._recursive_bisection(link, cov)
        weights = weights / weights.sum()
        logger.info(f"   وزنهای HRP: {weights.round(4).tolist()}")
        return weights

    def _recursive_bisection(self, link, cov):
        n = cov.shape[0]
        weights = np.ones(n)
        clusters = [list(range(n))]
        while clusters:
            new_clusters = []
            for cluster in clusters:
                if len(cluster) > 1:
                    cluster_cov = cov[np.ix_(cluster, cluster)]
                    cluster_var = np.diag(cluster_cov)
                    inv_var = 1.0 / (cluster_var + 1e-8)
                    cluster_weights = inv_var / inv_var.sum()
                    weights[cluster] *= cluster_weights
                    mid = len(cluster) // 2
                    new_clusters.append(cluster[:mid])
                    new_clusters.append(cluster[mid:])
                else:
                    new_clusters.append(cluster)
            clusters = [c for c in new_clusters if len(c) > 1]
        return weights

    def regime_aware_weights(self, returns, regime):
        self.regime = regime
        returns_clean = self._clean_returns(returns)

        if returns_clean.shape[1] < 2:
            n = max(returns_clean.shape[1], 1)
            return np.ones(n) / n

        hrp_weights = self.compute_hrp_weights(returns_clean)
        regime_weights_dict = CONFIG.risk.regime_weights.get(
            regime, {"gold": 0.33, "oil": 0.33, "usd": 0.34}
        )

        asset_names = list(returns_clean.columns)
        regime_weights = np.array([
            regime_weights_dict.get(
                "gold" if "gc" in name.lower() else
                "oil" if "cl" in name.lower() else
                "usd", 0.33
            )
            for name in asset_names
        ])

        combined = 0.5 * hrp_weights + 0.5 * regime_weights
        combined = combined / combined.sum()
        combined = self._apply_constraints(combined)
        self.weights = combined
        return combined

    def _apply_constraints(self, weights):
        w = weights.copy()
        w = np.clip(w, CONFIG.risk.min_weight_per_asset, CONFIG.risk.max_weight_per_asset)
        w = w / w.sum()
        return w

    def compute_cvar(self, returns, confidence=0.95):
        sorted_returns = np.sort(returns)
        var_index = max(int((1 - confidence) * len(sorted_returns)), 1)
        cvar = sorted_returns[:var_index].mean()
        return abs(cvar)

    def volatility_targeting(self, weights, target_vol=None):
        if target_vol is None:
            target_vol = CONFIG.risk.target_volatility
        if self.cov_matrix is None or self.cov_matrix.size == 0:
            return weights

        port_var = float(weights @ self.cov_matrix @ weights)
        if port_var < 0 or np.isnan(port_var):
            port_var = 1e-6
        port_vol = np.sqrt(port_var) * np.sqrt(252)

        # اگه نوسان غیرعادی بود نادیده بگیر
        if port_vol > 5.0 or port_vol < 1e-6:
            logger.warning(f"   ⚠️ نوسان غیرعادی: {port_vol:.4f} — نادیده گرفته شد")
            return weights

        if port_vol > target_vol:
            scale = target_vol / port_vol
            scaled = weights * scale
            scaled = np.clip(scaled, 0, 1)
            scaled = scaled / scaled.sum()
            logger.info(f"   📉 کاهش ریسک: {port_vol:.2%} → {target_vol:.2%}")
            return scaled
        return weights

    def full_risk_management(self, returns, regime, predictions):
        logger.info("🛡️ شروع مدیریت ریسک...")
        returns_clean = self._clean_returns(returns)

        if returns_clean.shape[1] < 2 or len(returns_clean) < 20:
            logger.warning("   ⚠️ داده کافی برای HRP نیست")
            return {
                "weights": {},
                "cvar": 0.0,
                "portfolio_volatility": 0.0,
                "regime": regime,
                "warnings": ["داده کافی نیست"],
            }

        weights = self.regime_aware_weights(returns_clean, regime)
        weights = self.volatility_targeting(weights)

        port_returns = (returns_clean * weights).sum(axis=1).values
        cvar = self.compute_cvar(port_returns)

        port_var = float(weights @ self.cov_matrix @ weights)
        port_vol = np.sqrt(max(port_var, 0)) * np.sqrt(252)

        warnings = []
        if cvar > CONFIG.risk.cvar_limit:
            warnings.append(f"⚠️ CVaR ({cvar:.2%}) از حد مجاز فراتر رفته")

        asset_names = list(returns_clean.columns)
        final_weights = {name: float(w) for name, w in zip(asset_names, weights)}

        return {
            "weights": final_weights,
            "cvar": float(cvar),
            "portfolio_volatility": float(port_vol),
            "regime": regime,
            "warnings": warnings,
        }
