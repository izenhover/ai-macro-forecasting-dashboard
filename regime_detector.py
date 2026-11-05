"""تشخیص ریم بازار با HMM GMM و K-Means"""

import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from loguru import logger
from config import CONFIG
import warnings
warnings.filterwarnings("ignore")


class RegimeDetector:
    """تشخیص ریم بازار با سه مدل موازی"""

    def __init__(self):
        self.hmm_model = None
        self.gmm_model = None
        self.kmeans_model = None
        self.scaler = StandardScaler()
        self.regime_labels = {}

    def prepare_features(self, returns, volatility):
        """آمادهسازی ویگیها برای تشخیص ریم"""
        combined = pd.DataFrame({
            "returns": returns,
            "volatility": volatility
        }).dropna()

        if len(combined) < 30:
            raise ValueError(f"داده کافی وجود ندارد: {len(combined)}")

        X = combined.values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X = self.scaler.fit_transform(X)
        return X

    def fit_hmm(self, X):
        """آموزش HMM"""
        logger.info("آموزش HMM...")
        self.hmm_model = hmm.GaussianHMM(
            n_components=CONFIG.regime.n_regimes,
            covariance_type=CONFIG.regime.hmm_covariance,
            n_iter=CONFIG.regime.hmm_iter,
            random_state=CONFIG.random_seed
        )
        self.hmm_model.fit(X)
        states = self.hmm_model.predict(X)
        logger.info(f"HMM: {len(set(states))} ریم")
        return states

    def fit_gmm(self, X):
        """آموزش GMM"""
        logger.info("آموزش GMM...")
        self.gmm_model = GaussianMixture(
            n_components=CONFIG.regime.gmm_components,
            covariance_type="full",
            random_state=CONFIG.random_seed
        )
        self.gmm_model.fit(X)
        states = self.gmm_model.predict(X)
        logger.info(f"GMM: {len(set(states))} ریم")
        return states

    def fit_kmeans(self, X):
        """آموزش K-Means"""
        logger.info("آموزش K-Means...")
        self.kmeans_model = KMeans(
            n_clusters=CONFIG.regime.n_regimes,
            random_state=CONFIG.random_seed,
            n_init=10
        )
        states = self.kmeans_model.fit_predict(X)
        logger.info(f"K-Means: {len(set(states))} ریم")
        return states

    def label_regimes(self, states, returns):
        """برچسبگذاری خودکار ریمها"""
        labels = {}
        unique_states = set(states)

        all_vols = []
        for s in unique_states:
            mask = states == s
            if mask.sum() > 0:
                all_vols.append(np.std(returns[mask]))
        median_vol = np.median(all_vols) if all_vols else 0.01

        for s in unique_states:
            mask = states == s
            if mask.sum() == 0:
                labels[s] = "SIDEWAYS"
                continue

            mean_ret = np.mean(returns[mask])
            vol = np.std(returns[mask])

            if mean_ret > 0.001 and vol < median_vol:
                labels[s] = "BULL"
            elif mean_ret < -0.001:
                labels[s] = "BEAR"
            elif vol > median_vol:
                labels[s] = "HIGH_VOL"
            else:
                labels[s] = "SIDEWAYS"

        return labels

    def fit(self, returns, volatility):
        """آموزش همه مدلها"""
        combined = pd.DataFrame({
            "returns": returns,
            "volatility": volatility
        }).dropna()

        if len(combined) < 30:
            raise ValueError(f"داده کافی وجود ندارد: {len(combined)}")

        returns_clean = combined["returns"]
        vol_clean = combined["volatility"]

        X = self.prepare_features(returns_clean, vol_clean)
        returns_arr = returns_clean.values

        hmm_states = self.fit_hmm(X)
        gmm_states = self.fit_gmm(X)
        kmeans_states = self.fit_kmeans(X)

        self.regime_labels = {
            "hmm": self.label_regimes(hmm_states, returns_arr),
            "gmm": self.label_regimes(gmm_states, returns_arr),
            "kmeans": self.label_regimes(kmeans_states, returns_arr),
        }

        final_states = self._vote(hmm_states, gmm_states, kmeans_states)
        final_labels = self.label_regimes(final_states, returns_arr)

        current = final_labels.get(final_states[-1], "SIDEWAYS")

        return {
            "states": final_states,
            "labels": final_labels,
            "current_regime": current,
            "regime_distribution": {
                int(s): int(np.sum(final_states == s))
                for s in set(final_states)
            },
            "clean_returns": returns_clean,
            "clean_volatility": vol_clean,
        }

    def _vote(self, hmm_states, gmm_states, kmeans_states):
        """رأیگیری وزنی بین مدلها"""
        n = len(hmm_states)
        final = np.zeros(n, dtype=int)

        for i in range(n):
            votes = {}
            for states, weight in [
                (hmm_states, 0.5),
                (gmm_states, 0.3),
                (kmeans_states, 0.2)
            ]:
                s = states[i]
                votes[s] = votes.get(s, 0) + weight

            final[i] = max(votes, key=votes.get)

        return final

    def predict_current(self, recent_returns):
        """پیشبینی ریم فعلی"""
        if self.hmm_model is None:
            return "SIDEWAYS"

        try:
            X = recent_returns.values.reshape(-1, 1)
            X = np.nan_to_num(X, nan=0.0)
            X_scaled = self.scaler.transform(
                np.column_stack([X, np.zeros_like(X)])
            )
            state = self.hmm_model.predict(X_scaled)[-1]
            return self.regime_labels["hmm"].get(state, "SIDEWAYS")
        except Exception:
            return "SIDEWAYS"
