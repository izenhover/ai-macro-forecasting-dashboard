# 🌐 AI Macro Forecasting Dashboard

An advanced, multi-asset financial dashboard built with **Python** and **Streamlit**, designed to forecast macro market trends (USD/IRR, Gold, and Oil) across multiple timeframes.

## 🚀 Key Features
* **Multi-Timeframe Forecasting:** 1-Hour, 4-Hour, and 1-Day predictions using advanced time-series models.
* **Bilingual Interface:** Fully responsive UI with dynamic English and Persian (RTL) support.
* **Live Market Data:** Real-time scraping and integration of free-market USD rates and Gold prices.
* **Risk Management:** Built-in Value at Risk (CVaR) and dynamic position sizing suggestions.
* **NLP Sentiment Analysis:** Live news scraping with sentiment analysis to gauge market fear/greed.

## 🛠️ Tech Stack
* **Frontend:** Streamlit, Plotly
* **Backend/Data:** Pandas, NumPy, Requests
* **Machine Learning:** PyTorch (BiGRU), Scikit-learn, Statsmodels (ARIMA)

## ⚙️ Architecture Note
This repository serves as the **public portfolio interface** for the project. The proprietary core strategy, deep learning weights, and specific feature engineering pipelines have been abstracted for intellectual property protection. A `mock_engine.py` is provided to demonstrate the UI functionality.

## 📦 Installation & Run
```bash
git clone https://github.com/izenhover/ai-macro-forecasting-dashboard.git
cd ai-macro-forecasting-dashboard
pip install -r requirements.txt
python -m streamlit run dashboard.py
<img width="1440" height="900" alt="Screenshot (184)" src="https://github.com/user-attachments/assets/b47a2e7e-fd90-4f7e-9359-8623d6139b38" />
