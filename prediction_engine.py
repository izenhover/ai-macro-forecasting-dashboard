"""موتور پیش‌بینی با Ensemble و Conformal Prediction"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import RobustScaler
from loguru import logger
from config import CONFIG
from typing import Tuple, Dict, List
import warnings
warnings.filterwarnings("ignore")


# ==================== مدل‌های عصبی ====================

class LSTMModel(nn.Module):
    """مدل LSTM پایه"""
    def __init__(self, input_dim, hidden_dim, output_dim, n_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, n_layers,
            batch_first=True, dropout=dropout if n_layers > 1 else 0
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]
        return self.fc(last_out)


class BiGRUModel(nn.Module):
    """مدل BiGRU (بهترین برای طلا)"""
    def __init__(self, input_dim, hidden_dim, output_dim, n_layers=2, dropout=0.2):
        super().__init__()
        self.gru = nn.GRU(
            input_dim, hidden_dim, n_layers,
            batch_first=True, bidirectional=True,
            dropout=dropout if n_layers > 1 else 0
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        gru_out, _ = self.gru(x)
        last_out = gru_out[:, -1, :]
        return self.fc(last_out)


class TransformerModel(nn.Module):
    """مدل Transformer (بهترین برای horizons بلندمدت)"""
    def __init__(self, input_dim, d_model, nhead, output_dim, n_layers=2, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.fc = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, output_dim)
        )
    
    def forward(self, x):
        x = self.input_proj(x)
        x = self.transformer(x)
        x = x[:, -1, :]
        return self.fc(x)


# ==================== Conformal Prediction ====================

class ConformalPredictor:
    """پیش‌بینی بازه‌ای با Conformal Prediction"""
    
    def __init__(self, alpha=0.10):
        self.alpha = alpha
        self.calibration_scores = []
        self.quantile = None
    
    def calibrate(self, y_true: np.ndarray, y_pred: np.ndarray):
        """کالیبراسیون با داده‌های اعتبارسنجی"""
        residuals = np.abs(y_true - y_pred)
        self.calibration_scores = residuals
        n = len(residuals)
        q_level = np.ceil((n + 1) * (1 - self.alpha)) / n
        self.quantile = np.quantile(residuals, min(q_level, 1.0))
        logger.info(f"✅ Conformal quantile: {self.quantile:.4f}")
    
    def predict_interval(
        self, 
        y_pred: np.ndarray, 
        volatility: np.ndarray = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """پیش‌بینی بازه اطمینان"""
        if self.quantile is None:
            raise ValueError("ابتدا کالیبراسیون انجام دهید")
        
        if volatility is not None:
            # بازه تطبیقی بر اساس نوسان
            scale = volatility / np.mean(volatility)
            q = self.quantile * scale
        else:
            q = self.quantile
        
        lower = y_pred - q
        upper = y_pred + q
        return lower, upper


# ==================== موتور پیش‌بینی ====================

class PredictionEngine:
    """موتور پیش‌بینی Ensemble"""
    
    def __init__(self, input_dim: int):
        self.input_dim = input_dim
        self.models = {}
        self.scalers = {}
        self.conformal = {}
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info(f"🖥️ دستگاه: {self.device}")
    
    def _create_sequences(
        self, 
        data: np.ndarray, 
        seq_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """ساخت دنباله‌های زمانی"""
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i + seq_length])
            y.append(data[i + seq_length, 0])  # قیمت بسته شدن
        return np.array(X), np.array(y)
    
    def train_models(
        self, 
        data: pd.DataFrame,
        target_col: str
    ) -> Dict:
        """آموزش همه مدل‌ها"""
        logger.info(f"🚀 شروع آموزش برای {target_col}...")
        
        # آماده‌سازی داده
        feature_cols = [c for c in data.columns if c != target_col]
        X_raw = data[feature_cols].values
        y_raw = data[target_col].values
        
        # نرمال‌سازی
        x_scaler = RobustScaler()
        y_scaler = RobustScaler()
        X_scaled = x_scaler.fit_transform(X_raw)
        y_scaled = y_scaler.fit_transform(y_raw.reshape(-1, 1)).flatten()
        
        # ساخت دنباله‌ها
        combined = np.column_stack([y_scaled, X_scaled])
        X_seq, y_seq = self._create_sequences(
            combined, CONFIG.prediction.seq_length
        )
        
        # تقسیم
        n_train = int(len(X_seq) * CONFIG.data.train_ratio)
        X_train, X_val = X_seq[:n_train], X_seq[n_train:]
        y_train, y_val = y_seq[:n_train], y_seq[n_train:]
        
        # DataLoader
        train_ds = TensorDataset(
            torch.FloatTensor(X_train), 
            torch.FloatTensor(y_train)
        )
        train_loader = DataLoader(
            train_ds, 
            batch_size=CONFIG.prediction.batch_size, 
            shuffle=True
        )
        
        # آموزش هر مدل
        results = {}
        model_configs = {
            "lstm": LSTMModel(
                self.input_dim, CONFIG.prediction.hidden_dim, 1,
                CONFIG.prediction.lstm_layers, CONFIG.prediction.dropout
            ),
            "bigru": BiGRUModel(
                self.input_dim, CONFIG.prediction.hidden_dim, 1,
                CONFIG.prediction.lstm_layers, CONFIG.prediction.dropout
            ),
            "transformer": TransformerModel(
                self.input_dim, 64, 4, 1, 2, 0.1
            ),
        }
        
        for name, model in model_configs.items():
            logger.info(f"   📈 آموزش {name}...")
            model = model.to(self.device)
            optimizer = torch.optim.Adam(
                model.parameters(), lr=1e-3, weight_decay=1e-5
            )
            criterion = nn.MSELoss()
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, patience=10, factor=0.5
            )
            
            best_val_loss = float("inf")
            patience_counter = 0
            
            for epoch in range(CONFIG.prediction.epochs):
                model.train()
                train_loss = 0
                for X_batch, y_batch in train_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    
                    optimizer.zero_grad()
                    pred = model(X_batch).squeeze()
                    loss = criterion(pred, y_batch)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    train_loss += loss.item()
                
                # اعتبارسنجی
                model.eval()
                with torch.no_grad():
                    X_val_t = torch.FloatTensor(X_val).to(self.device)
                    val_pred = model(X_val_t).squeeze().cpu().numpy()
                    val_loss = np.mean((val_pred - y_val) ** 2)
                
                scheduler.step(val_loss)
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_state = model.state_dict().copy()
                else:
                    patience_counter += 1
                    if patience_counter >= 15:
                        break
            
            model.load_state_dict(best_state)
            self.models[name] = model
            
            # کالیبراسیون Conformal
            conformal = ConformalPredictor(CONFIG.prediction.conformal_alpha)
            conformal.calibrate(y_val, val_pred)
            self.conformal[name] = conformal
            
            results[name] = {
                "val_loss": float(best_val_loss),
                "val_mae": float(np.mean(np.abs(val_pred - y_val))),
            }
            logger.info(f"   ✅ {name}: MSE={best_val_loss:.6f}")
        
        # ذخیره Scalerها
        self.scalers[target_col] = {
            "x": x_scaler, 
            "y": y_scaler
        }
        
        return results
    
    def predict(
        self, 
        data: pd.DataFrame, 
        target_col: str,
        ensemble_weights: Dict[str, float] = None
    ) -> Dict:
        """پیش‌بینی با Ensemble"""
        if ensemble_weights is None:
            ensemble_weights = {"lstm": 0.33, "bigru": 0.34, "transformer": 0.33}
        
        feature_cols = [c for c in data.columns if c != target_col]
        X_raw = data[feature_cols].values
        
        scaler = self.scalers[target_col]
        X_scaled = scaler["x"].transform(X_raw)
        y_scaled = scaler["y"].transform(
            data[target_col].values.reshape(-1, 1)
        ).flatten()
        
        combined = np.column_stack([y_scaled, X_scaled])
        X_seq, _ = self._create_sequences(
            combined, CONFIG.prediction.seq_length
        )
        
        X_tensor = torch.FloatTensor(X_seq[-1:]).to(self.device)
        
        predictions = {}
        intervals = {}
        
        for name, model in self.models.items():
            model.eval()
            with torch.no_grad():
                pred_scaled = model(X_tensor).cpu().numpy().flatten()
            
            # بازگردانی مقیاس
            pred = scaler["y"].inverse_transform(
                pred_scaled.reshape(-1, 1)
            ).flatten()
            predictions[name] = pred[0]
            
            # بازه اطمینان
            lower, upper = self.conformal[name].predict_interval(pred_scaled)
            lower = scaler["y"].inverse_transform(
                lower.reshape(-1, 1)
            ).flatten()[0]
            upper = scaler["y"].inverse_transform(
                upper.reshape(-1, 1)
            ).flatten()[0]
            intervals[name] = (lower, upper)
        
        # ترکیب وزنی
        ensemble_pred = sum(
            ensemble_weights.get(name, 0) * predictions[name]
            for name in predictions
        )
        
        # بازه اطمینان Ensemble
        lower_bound = np.mean([intervals[n][0] for n in intervals])
        upper_bound = np.mean([intervals[n][1] for n in intervals])
        
        return {
            "point_prediction": float(ensemble_pred),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "confidence": 1 - CONFIG.prediction.conformal_alpha,
            "individual_predictions": {
                n: float(p) for n, p in predictions.items()
            },
            "uncertainty": float(upper_bound - lower_bound),
        }