import requests
import streamlit as st

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"

st.set_page_config(page_title="My AI Chat", layout="wide")
st.title("My AI Chat")
st.caption("Task 1B: Multi-Turn Conversation UI")

hf_token = st.secrets.get("HF_TOKEN", "").strip()
if not hf_token:
    st.error("Missing HF_TOKEN. Add it to .streamlit/secrets.toml and rerun the app.")
    st.stop()

headers = {"Authorization": f"Bearer {hf_token}"}


def get_assistant_reply(messages):
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 256,
    }

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
        return None
    except requests.exceptions.ConnectionError:
        st.error("Network error while contacting Hugging Face. Check your connection and try again.")
        return None
    except requests.exceptions.HTTPError:
        status_code = response.status_code
        if status_code in (401, 403):
            st.error("Authentication failed. Check your HF_TOKEN in .streamlit/secrets.toml.")
        elif status_code == 429:
            st.error("Rate limit reached. Please wait and try again.")
        else:
            st.error(f"API error ({status_code}): {response.text[:300]}")
        return None
    except requests.exceptions.RequestException as exc:
        st.error(f"Request failed: {exc}")
        return None
    except ValueError:
        st.error("API returned invalid JSON.")
        return None

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        st.error("Unexpected API response format.")
        return None


if "messages" not in st.session_state:
    st.session_state.messages = []

history_container = st.container(height=520, border=True)
with history_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

prompt = st.chat_input("Type a message and press Enter")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with history_container:
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                assistant_reply = get_assistant_reply(st.session_state.messages)
            if assistant_reply is not None:
                st.write(assistant_reply)

    if assistant_reply is not None:
        st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
