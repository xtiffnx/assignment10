from datetime import datetime

import requests
import streamlit as st

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"

st.set_page_config(page_title="My AI Chat", layout="wide")
st.title("My AI Chat")
st.caption("Task 1C: Chat Management")

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


def create_new_chat():
    st.session_state.chat_counter += 1
    chat_id = f"chat_{st.session_state.chat_counter}"
    created_at = datetime.now().strftime("%b %d, %I:%M %p")
    st.session_state.chats.insert(
        0,
        {
            "id": chat_id,
            "title": "New Chat",
            "created_at": created_at,
            "messages": [],
        },
    )
    st.session_state.active_chat_id = chat_id


def get_active_chat():
    for chat in st.session_state.chats:
        if chat["id"] == st.session_state.active_chat_id:
            return chat
    return None


if "chats" not in st.session_state:
    st.session_state.chats = []
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 0
if not st.session_state.chats:
    create_new_chat()

with st.sidebar:
    st.subheader("Chats")
    if st.button("New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    chat_list_container = st.container(height=460, border=True)
    with chat_list_container:
        for chat in st.session_state.chats:
            chat_cols = st.columns([5, 1])
            chat_label = f"{chat['title']}  |  {chat['created_at']}"

            if chat_cols[0].button(
                chat_label,
                key=f"select_{chat['id']}",
                use_container_width=True,
                type="primary" if chat["id"] == st.session_state.active_chat_id else "secondary",
            ):
                st.session_state.active_chat_id = chat["id"]
                st.rerun()

            if chat_cols[1].button("X", key=f"delete_{chat['id']}", use_container_width=True):
                deleted_active_chat = chat["id"] == st.session_state.active_chat_id
                st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]

                if deleted_active_chat:
                    if st.session_state.chats:
                        st.session_state.active_chat_id = st.session_state.chats[0]["id"]
                    else:
                        st.session_state.active_chat_id = None
                st.rerun()

active_chat = get_active_chat()
if active_chat is None:
    st.info("No active chat. Create a new chat from the sidebar.")
else:
    history_container = st.container(height=520, border=True)
    with history_container:
        for message in active_chat["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

prompt = st.chat_input("Type a message and press Enter", disabled=active_chat is None)
if prompt and active_chat is not None:
    active_chat["messages"].append({"role": "user", "content": prompt})
    if active_chat["title"] == "New Chat":
        active_chat["title"] = prompt[:28] + ("..." if len(prompt) > 28 else "")

    with st.spinner("Thinking..."):
        assistant_reply = get_assistant_reply(active_chat["messages"])
    if assistant_reply is not None:
        active_chat["messages"].append({"role": "assistant", "content": assistant_reply})
    st.rerun()
