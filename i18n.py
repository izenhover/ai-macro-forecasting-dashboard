# در فایل i18n.py این خط را تغییر بده:
def get_lang():
    if "lang" not in st.session_state:
        st.session_state.lang = "en"  # Default to English
    return st.session_state.lang