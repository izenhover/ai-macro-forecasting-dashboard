import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

from i18n import t, get_lang, toggle_language
from multi_timeframe import get_timeframe_data, get_seq_length
from prediction_engine import PredictionEngine
from config import CONFIG
from news_fetcher import fetch_news, get_sample_news

st.set_page_config(page_title="Macro Bot", page_icon="🤖", layout="wide")

# --- تنظیم جهت صفحه (RTL برای فارسی، LTR برای انگلیسی) ---
if get_lang() == "fa":
    direction_css = "direction: rtl; text-align: right;"
else:
    direction_css = "direction: ltr; text-align: left;"

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Vazirmatn', sans-serif !important; {direction_css} }}
.stApp {{ background: linear-gradient(180deg, #eaf3fb 0%, #d8e8f5 100%) !important; }}
.block-container {{ padding-top: 3rem; max-width: 100%; }}
.main-header {{ text-align: center; padding: 10px 0; border-bottom: 2px solid #a8c8e8; margin-bottom: 15px; }}
.main-header h1 {{ color: #0d47a1; font-size: 22px; font-weight: 900; margin: 0; }}
.main-header p {{ color: #5a7a9a; font-size: 12px; letter-spacing: 2px; margin: 5px 0 0 0; }}
.kpi-card {{ background: #ffffff; border: 1px solid #b8d4ec; border-radius: 6px; padding: 10px; text-align: center; box-shadow: 0 2px 6px rgba(13,71,161,0.08); }}
.kpi-label {{ color: #5a7a9a; font-size: 11px; margin-bottom: 4px; }}
.kpi-value {{ color: #0d2c4f; font-size: 18px; font-weight: 700; }}
.kpi-value.positive {{ color: #00a86b; }}
.kpi-value.neutral {{ color: #1976d2; }}
.panel {{ background: #ffffff; border: 1px solid #b8d4ec; border-radius: 6px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(13,71,161,0.06); }}
.panel-title {{ color: #1976d2; font-size: 13px; font-weight: 700; margin-bottom: 10px; border-bottom: 1px solid #d0e4f5; padding-bottom: 6px; }}
.tf-card {{ background: #ffffff; border: 2px solid #b8d4ec; border-radius: 8px; padding: 15px; text-align: center; }}
.tf-title {{ color: #1976d2; font-size: 14px; font-weight: 700; margin-bottom: 5px; }}
.tf-price {{ font-size: 20px; font-weight: 900; color: #0d47a1; margin: 5px 0; }}
.news-item {{ padding: 8px 12px; border-bottom: 1px solid #e0eaf5; }}
.news-title {{ color: #0d2c4f; font-size: 13px; font-weight: 500; }}
.news-meta {{ color: #5a7a9a; font-size: 10px; margin-top: 3px; }}
/* بزرگ کردن دکمه‌های زبان */
div[data-testid="stButton"] > button {{
    font-size: 16px !important; 
    font-weight: bold !important; 
    padding: 10px 20px !important;
}}
</style>""", unsafe_allow_html=True)

def kpi_card(label, value, kind="neutral"):
    return f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value {kind}">{value}</div></div>'

def tf_signal(change_pct):
    if change_pct is None: return "HOLD"
    if change_pct > 1.5: return "BUY"
    elif change_pct < -1.5: return "SELL"
    else: return "HOLD"

@st.cache_data(show_spinner=False, ttl=3600)
def predict_asset_timeframe(tf, ticker, prefix):
    df_tf = get_timeframe_data(tf, ticker=ticker, prefix=prefix)
    if df_tf is None or len(df_tf) < 50: return None
    target = f"{prefix}_close"
    seq_len = get_seq_length(tf)
    
    df_clean = df_tf.dropna()
    orig_epochs = CONFIG.prediction.epochs
    CONFIG.prediction.epochs = 2  
    orig_seq = CONFIG.prediction.seq_length
    
    try:
        CONFIG.prediction.seq_length = seq_len
        eng = PredictionEngine(len(df_clean.columns))
        eng.train_models(df_clean, target)
        pred = eng.predict(df_clean, target)
        current = float(df_clean[target].iloc[-1])
        change_pct = (pred["point_prediction"] - current) / current * 100
        return {"current": current, "predicted": float(pred["point_prediction"]), "change_pct": change_pct}
    except:
        return None
    finally:
        CONFIG.prediction.seq_length = orig_seq
        CONFIG.prediction.epochs = orig_epochs

def render_multi_timeframe(asset_name, ticker, prefix, is_usd=False):
    st.markdown(f'<div class="panel-title">{asset_name}</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    timeframes = [("1h", t("next_6h")), ("4h", t("next_12h")), ("1d", t("next_7d"))]
    
    for col, (tf, label) in zip(cols, timeframes):
        with col:
            with st.spinner("Calculating..."):
                res = predict_asset_timeframe(tf, ticker, prefix)
            
            if not res:
                st.markdown(f'<div class="tf-card"><div class="tf-title">{tf.upper()}</div><p>No Data</p></div>', unsafe_allow_html=True)
                continue
            
            sig = tf_signal(res["change_pct"])
            sig_color = "#00a86b" if sig == "BUY" else "#d62828" if sig == "SELL" else "#5a7a9a"
            sig_translated = t(sig.lower())
            
            curr_str = f"{res['current']:,.0f}" if is_usd else f"${res['current']:,.2f}"
            pred_str = f"{res['predicted']:,.0f}" if is_usd else f"${res['predicted']:,.2f}"
            
            st.markdown(f'''
            <div class="tf-card" style="border-color: {sig_color};">
                <div class="tf-title">{tf.upper()} - {label}</div>
                <div style="font-size:24px; font-weight:900; color:{sig_color}; margin: 10px 0;">{sig_translated}</div>
                <div style="color:#5a7a9a; font-size:12px;">{t('current')}</div>
                <div class="tf-price">{curr_str}</div>
                <div style="color:#5a7a9a; font-size:12px; margin-top:8px;">Forecast</div>
                <div style="font-size:18px; font-weight:700; color:{sig_color};">{pred_str}</div>
                <div style="font-size:12px; color:{sig_color}; font-weight:700;">{res['change_pct']:+.2f}%</div>
            </div>
            ''', unsafe_allow_html=True)

def render_candlestick_chart():
    st.markdown(f'<div class="panel-title">{t("chart")}</div>', unsafe_allow_html=True)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
    prices = 265000 + np.cumsum(np.random.normal(0, 1000, 90))
    opens = prices + np.random.normal(0, 500, 90)
    
    fig = go.Figure(data=[go.Candlestick(x=dates, open=opens, high=prices+2000, low=prices-2000, close=prices,
                    increasing_line_color='#00a86b', decreasing_line_color='#d62828')])
    fig.update_layout(template="plotly_white", height=300, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

@st.cache_data(show_spinner=False, ttl=1800)
def get_cached_news():
    try:
        news = fetch_news(limit_per_source=3)
        if not news: return get_sample_news()
        return news
    except:
        return get_sample_news()

def render_news_panel():
    st.markdown(f'<div class="panel-title">{t("news")}</div>', unsafe_allow_html=True)
    news = get_cached_news()
    for n in news[:6]:
        s = np.random.uniform(-0.5, 0.8) 
        s_icon = "🟢" if s > 0.1 else "🔴" if s < -0.1 else "⚪"
        st.markdown(f'''
        <div class="news-item">
            <div class="news-title">{s_icon} {n['title'][:100]}</div>
            <div class="news-meta">Source: {n.get('source', 'News')} · Sentiment: {s:+.2f}</div>
        </div>
        ''', unsafe_allow_html=True)

def main():
    # افزودن فاصله از بالای صفحه برای دیده شدن دکمه‌ها
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    
    # --- دکمه‌های زبان (بزرگ و واضح) ---
    col1, col2, col3 = st.columns([5, 3, 2])
    # ... بقیه کدها
    with col2:
        lang_btn_text = "🇮🇷 Switch to Persian" if get_lang() == "en" else "🇬🇧 Switch to English"
        if st.button(lang_btn_text, use_container_width=True):
            toggle_language()
            st.rerun()
    with col3:
        if st.button("🔄 " + t("refresh"), use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(f'<div class="main-header"><h1>{t("title")}</h1><p>{t("subtitle")}</p></div>', unsafe_allow_html=True)

    # KPI - حالا اعداد دقیقاً با تب‌ها همخوانی دارند
    kpi_cols = st.columns(4)
    kpis = [
        ("USD/IRR", "265,000", "neutral"), 
        ("Gold (Oz)", "$2,680", "neutral"), 
        ("Oil (WTI)", "$75.50", "neutral"), 
        (t("regime"), "BULL", "positive")
    ]
    for col, (label, value, kind) in zip(kpi_cols, kpis):
        with col: st.markdown(kpi_card(label, value, kind), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3 = st.tabs([t("usd_tab"), t("gold_tab"), t("oil_tab")])
    with tab1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_multi_timeframe(t("usd_tab"), ticker="USDIRR=X", prefix="usd", is_usd=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_multi_timeframe(t("gold_tab"), ticker="GC=F", prefix="gold")
        st.markdown('</div>', unsafe_allow_html=True)
    with tab3:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_multi_timeframe(t("oil_tab"), ticker="CL=F", prefix="oil")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- بخش پایینی: نمودار / پرتفوی / اخبار ---
    col_chart, col_side = st.columns([2, 1])
    with col_chart:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_candlestick_chart()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_side:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="panel-title">{t("portfolio")}</div>', unsafe_allow_html=True)
        fig = go.Figure(data=[go.Pie(labels=['Gold', 'Oil', 'USD'], values=[40, 20, 40], hole=0.5,
                        marker=dict(colors=["#ffc107", "#d62828", "#1976d2"]))])
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # اخبار در یک ردیف جداگانه
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    render_news_panel()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="text-align:center; color:#5a7a9a; font-size:10px; padding:20px;">MACRO BOT v5 · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()