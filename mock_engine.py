# mock_engine.py
# This is a placeholder for the proprietary forecasting engine.
# In the private version, this connects to deep learning models (BiGRU/ARIMA).

import pandas as pd
import numpy as np

def get_mock_forecast(current_price, days=7):
    """Returns a dummy forecast for demonstration purposes."""
    dates = pd.date_range(start=pd.Timestamp.today(), periods=days)
    # Simulate a slight upward trend
    predictions = [current_price * (1 + 0.005 * i) for i in range(1, days + 1)]
    return predictions