import streamlit as st

st.set_page_config(page_title="Week 10 ChatGPT Clone", page_icon=":speech_balloon:")
st.title("Week 10: ChatGPT Clone")

if "HF_TOKEN" not in st.secrets:
    st.error("HF_TOKEN is missing. Add it to .streamlit/secrets.toml")
else:
    st.info("Setup complete. Ready for Task 1.")
