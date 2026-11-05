"""بک‌تست ۶ ماهه سیستم پیش‌بینی"""

import numpy as np
import pandas as pd
from loguru import logger


class Backtester:
    """بک‌تست walk-forward"""

    def __init__(self, engine_class, seq_length=60, horizon=7, step=15, test_days=180):
        self.engine_class = engine_class
        self.seq_length = seq_length
        self.horizon = horizon
        self.step = step
        self.test_days = test_days

    def run(self, df, target_col):
        """اجرای بک‌تست"""
        logger.info("Backtest started: " + target_col)
        n = len(df)
        start = max(n - self.test_days, self.seq_length + 50)

        results = []
        for i in range(start, n - self.horizon, self.step):
            train = df.iloc[:i]
            try:
                actual = float(df[target_col].iloc[i + self.horizon - 1])
                engine = self.engine_class(len(train.columns))
                engine.train_models(train, target_col)
                pred = engine.predict(train, target_col)
                predicted = float(pred["point_prediction"])

                results.append({
                    "date": df.index[i].strftime("%Y-%m-%d"),
                    "actual": actual,
                    "predicted": predicted,
                    "error": predicted - actual,
                    "error_pct": (predicted - actual) / actual * 100 if actual != 0 else 0,
                    "lower": float(pred["lower_bound"]),
                    "upper": float(pred["upper_bound"]),
                })
                logger.info("   step " + str(i) + " -> " + str(round(predicted, 2)) + " (actual: " + str(round(actual, 2)) + ")")
            except Exception as e:
                logger.warning("   step " + str(i) + " failed: " + str(e))
                continue

        df_res = pd.DataFrame(results)
        metrics = self.compute_metrics(df_res)
        return df_res, metrics

    def compute_metrics(self, df_res):
        """محاسبه معیارهای بک‌تست"""
        if df_res.empty:
            return {}

        actual = df_res["actual"].values
        predicted = df_res["predicted"].values
        errors = predicted - actual

        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        mape = float(np.mean(np.abs(errors / actual)) * 100) if np.all(actual != 0) else 0

        # ضریب تعیین
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((actual - actual.mean()) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0

        # سیگنال‌های معاملاتی
        signals = np.sign(df_res["error_pct"].values)
        returns = np.diff(actual) / actual[:-1]
        if len(returns) > 0 and len(signals) > 1:
            strategy_returns = signals[:-1] * returns
            sharpe = float(np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-8) * np.sqrt(252))
            cum_returns = np.cumprod(1 + strategy_returns)
            running_max = np.maximum.accumulate(cum_returns)
            drawdown = (cum_returns - running_max) / running_max
            max_dd = float(np.min(drawdown))
        else:
            sharpe = 0.0
            max_dd = 0.0

        # دقت جهت
        if len(actual) > 1:
            direction_actual = np.sign(np.diff(actual))
            direction_pred = np.sign(np.diff(predicted))
            dir_accuracy = float(np.mean(direction_actual == direction_pred) * 100)
        else:
            dir_accuracy = 0.0

        return {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "r2": r2,
            "sharpe": sharpe,
            "max_drawdown": max_dd * 100,
            "direction_accuracy": dir_accuracy,
            "n_tests": len(df_res),
        }
