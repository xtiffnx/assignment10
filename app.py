import requests
import streamlit as st

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"

st.set_page_config(page_title="My AI Chat", layout="wide")
st.title("My AI Chat")
st.caption("Task 1A: Page Setup and API Connection")

hf_token = st.secrets.get("HF_TOKEN", "").strip()
if not hf_token:
    st.error("Missing HF_TOKEN. Add it to .streamlit/secrets.toml and rerun the app.")
    st.stop()

payload = {
    "model": MODEL_NAME,
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 256,
}
headers = {"Authorization": f"Bearer {hf_token}"}

with st.spinner("Sending test message to Hugging Face..."):
    try:
        response = requests.post(
            HF_CHAT_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        st.error("Request timed out. The API may be busy; please try again.")
        st.stop()
    except requests.exceptions.ConnectionError:
        st.error("Network error while contacting Hugging Face. Check your connection and try again.")
        st.stop()
    except requests.exceptions.HTTPError:
        status_code = response.status_code
        if status_code in (401, 403):
            st.error("Authentication failed. Check your HF_TOKEN in .streamlit/secrets.toml.")
        elif status_code == 429:
            st.error("Rate limit reached. Please wait and try again.")
        else:
            st.error(f"API error ({status_code}): {response.text[:300]}")
        st.stop()
    except requests.exceptions.RequestException as exc:
        st.error(f"Request failed: {exc}")
        st.stop()
    except ValueError:
        st.error("API returned invalid JSON.")
        st.stop()

try:
    model_reply = data["choices"][0]["message"]["content"]
except (KeyError, IndexError, TypeError):
    st.error("Unexpected API response format.")
    st.stop()

st.subheader("Model Reply")
st.write(model_reply)
