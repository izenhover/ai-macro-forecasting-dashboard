"""Central Configuration for Macro Forecasting System"""

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class DataConfig:
    """Data Fetching Configuration"""
    assets: List[str] = field(default_factory=lambda: [
        "GC=F",      # Gold Futures
        "CL=F",      # Crude Oil
        "USDIRR=X",  # USD/IRR (Free Market Rate)
    ])
    lookback_days: int = 365
    freq: str = "1d"
    train_ratio: float = 0.8

@dataclass
class SentimentConfig:
    """NLP Sentiment Analysis Configuration"""
    model_name: str = "ProsusAI/finbert"
    confidence_threshold: float = 0.6
    source_credibility: Dict[str, float] = field(default_factory=lambda: {
        "reuters": 0.9,
        "bloomberg": 0.9,
        "farsnews": 0.7,
        "donya-e-eqtesad": 0.8,
        "default": 0.5,
    })

@dataclass
class RegimeConfig:
    """Market Regime Detection Configuration"""
    n_regimes: int = 4
    hmm_covariance: str = "full"
    hmm_iter: int = 1000
    gmm_components: int = 4
    rolling_window: int = 252

@dataclass
class PredictionConfig:
    """Deep Learning Model Hyperparameters (Optimized for speed)"""
    hidden_dim: int = 32
    lstm_layers: int = 1
    dropout: float = 0.2
    seq_length: int = 30
    forecast_horizon: int = 7
    conformal_alpha: float = 0.10  # 90% Confidence Interval
    batch_size: int = 32
    epochs: int = 10               # Reduced for faster dashboard loading

@dataclass
class RiskConfig:
    """Risk Management and Portfolio Optimization Configuration"""
    max_drawdown: float = 0.15
    max_weight_per_asset: float = 0.40
    min_weight_per_asset: float = 0.10
    target_volatility: float = 0.15
    cvar_limit: float = 0.25
    regime_weights: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "BULL":     {"gold": 0.35, "oil": 0.25, "usd": 0.40},
        "BEAR":     {"gold": 0.50, "oil": 0.10, "usd": 0.40},
        "HIGH_VOL": {"gold": 0.40, "oil": 0.15, "usd": 0.45},
        "SIDEWAYS": {"gold": 0.30, "oil": 0.30, "usd": 0.40},
    })

@dataclass
class OnlineConfig:
    """Online Learning and Concept Drift Configuration"""
    drift_detector: str = "ADWIN"
    drift_threshold: float = 0.002
    retrain_frequency: int = 7
    update_frequency: int = 1

@dataclass
class SystemConfig:
    """Main System Configuration"""
    data: DataConfig = field(default_factory=DataConfig)
    sentiment: SentimentConfig = field(default_factory=SentimentConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    online: OnlineConfig = field(default_factory=OnlineConfig)
    random_seed: int = 42

CONFIG = SystemConfig()