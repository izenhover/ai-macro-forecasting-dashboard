"""یادگیری آنلاین و مقابله با Concept Drift - نسخه بدون river"""

import numpy as np
import pandas as pd
from loguru import logger
from config import CONFIG
import joblib
import os


class SimpleDriftDetector:
    """
    تشخیص Drift با روش ADWIN ساده‌شده
    بر اساس مقایسه میانگین دو پنجره
    """
    
    def __init__(self, delta: float = 0.002, window: int = 30):
        self.delta = delta
        self.window = window
        self.history = []
        self.drift_detected = False
    
    def update(self, value: float):
        """به‌روزرسانی با مقدار جدید"""
        self.history.append(value)
        self.drift_detected = False
        
        if len(self.history) < 2 * self.window:
            return
        
        # دو پنجره: قدیمی و جدید
        old_window = self.history[-2 * self.window:-self.window]
        new_window = self.history[-self.window:]
        
        mean_old = np.mean(old_window)
        mean_new = np.mean(new_window)
        
        # آستانه بر اساس انحراف معیار
        std_old = np.std(old_window) + 1e-8
        threshold = self.delta * std_old * np.sqrt(self.window)
        
        if abs(mean_new - mean_old) > threshold:
            self.drift_detected = True


class OnlineLearner:
    """یادگیری آنلاین با تشخیص Drift ساده"""
    
    def __init__(self):
        self.drift_detector = SimpleDriftDetector(
            delta=CONFIG.online.drift_threshold
        )
        self.performance_history = []
        self.drift_events = []
        self.retrain_counter = 0
    
    def update(self, prediction: float, actual: float) -> dict:
        """به‌روزرسانی با داده جدید"""
        error = abs(prediction - actual)
        self.performance_history.append(error)
        
        self.drift_detector.update(error)
        drift_detected = self.drift_detector.drift_detected
        
        if drift_detected:
            logger.warning("🚨 Concept Drift تشخیص داده شد!")
            self.drift_events.append({
                "index": len(self.performance_history),
                "error": error,
                "timestamp": pd.Timestamp.now(),
            })
        
        self.retrain_counter += 1
        
        need_retrain = (
            drift_detected or
            self.retrain_counter >= CONFIG.online.retrain_frequency
        )
        
        if need_retrain:
            self.retrain_counter = 0
        
        return {
            "drift_detected": drift_detected,
            "error": error,
            "need_retrain": need_retrain,
            "total_drifts": len(self.drift_events),
        }
    
    def get_performance_metrics(self) -> dict:
        """معیارهای عملکرد"""
        if not self.performance_history:
            return {}
        
        errors = np.array(self.performance_history)
        recent = errors[-30:] if len(errors) >= 30 else errors
        
        trend = 0.0
        if len(recent) >= 10:
            trend = float(np.polyfit(range(len(recent)), recent, 1)[0])
        
        return {
            "current_mae": float(np.mean(recent)),
            "overall_mae": float(np.mean(errors)),
            "mae_trend": trend,
            "total_updates": len(self.performance_history),
            "drift_events": len(self.drift_events),
        }
    
    def save_state(self, path: str = "online_state.pkl"):
        state = {
            "performance_history": self.performance_history,
            "drift_events": self.drift_events,
            "retrain_counter": self.retrain_counter,
        }
        joblib.dump(state, path)
        logger.info(f"💾 وضعیت ذخیره شد: {path}")
    
    def load_state(self, path: str = "online_state.pkl"):
        if os.path.exists(path):
            state = joblib.load(path)
            self.performance_history = state["performance_history"]
            self.drift_events = state["drift_events"]
            self.retrain_counter = state["retrain_counter"]
            logger.info(f"📂 وضعیت بارگذاری شد: {path}")