import streamlit as st

TRANSLATIONS = {
    "en": {
        "title": "MACRO BOT v5 · OPERATIONS CENTER",
        "subtitle": "USD · GOLD · OIL · MULTI-TIMEFRAME",
        "refresh": "🔄 Refresh Data",
        "usd_tab": "💵 USD/IRR",
        "gold_tab": "🥇 Gold",
        "oil_tab": "🛢️ Crude Oil",
        "current": "Current Price",
        "next_6h": "Next 6 Hours",
        "next_12h": "Next 12 Hours",
        "next_7d": "Next 7 Days",
        "buy": "BUY",
        "sell": "SELL",
        "hold": "HOLD",
        "tomans": "Tomans",
        "regime": "Regime",
    },
    "fa": {
        "title": "مرکز عملیات مکرو بات",
        "subtitle": "دلار · طلا · نفت · تایم‌فریم چندگانه",
        "refresh": "🔄 اجرای مجدد",
        "usd_tab": "💵 دلار",
        "gold_tab": "🥇 طلا",
        "oil_tab": "🛢️ نفت",
        "current": "قیمت فعلی",
        "next_6h": "۶ ساعت آینده",
        "next_12h": "۱۲ ساعت آینده",
        "next_7d": "۷ روز آینده",
        "buy": "بخر",
        "sell": "بفروش",
        "hold": "صبر",
        "tomans": "تومان",
        "regime": "رژیم بازار",
    }
}

def get_lang():
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    return st.session_state.lang

def t(key):
    return TRANSLATIONS.get(get_lang(), {}).get(key, key)

def toggle_language():
    st.session_state.lang = "fa" if get_lang() == "en" else "en"