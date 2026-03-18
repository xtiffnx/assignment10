from datetime import datetime
import json
from pathlib import Path
import re
import time

import requests
import streamlit as st

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"
CHATS_DIR = Path("chats")
MEMORY_FILE = Path("memory.json")

st.set_page_config(page_title="My AI Chat", layout="wide")
st.title("My AI Chat")
st.caption("Task 3: User Memory")

hf_token = st.secrets.get("HF_TOKEN", "").strip()
if not hf_token:
    st.error("Missing HF_TOKEN. Add it to .streamlit/secrets.toml and rerun the app.")
    st.stop()

headers = {"Authorization": f"Bearer {hf_token}"}


def stream_assistant_reply(messages, response_placeholder):
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 256,
        "stream": True,
    }

    response = None
    full_reply = ""
    saw_stream_data = False

    def extract_text_from_event(event):
        choice = (event.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        content_piece = delta.get("content")
        if isinstance(content_piece, str):
            return content_piece
        if isinstance(content_piece, list):
            text_bits = []
            for part in content_piece:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_bits.append(part["text"])
            return "".join(text_bits)

        message = choice.get("message") or {}
        if isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(choice.get("text"), str):
            return choice["text"]
        return ""

    try:
        with requests.post(
            HF_CHAT_URL,
            headers=headers,
            json=payload,
            timeout=60,
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                data_str = ""
                if raw_line.startswith("data:"):
                    saw_stream_data = True
                    data_str = raw_line[5:].strip()
                    if data_str == "[DONE]":
                        break
                else:
                    data_str = raw_line.strip()

                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                content_piece = extract_text_from_event(event)
                if not content_piece:
                    continue

                full_reply += content_piece
                response_placeholder.write(full_reply)
                time.sleep(0.01)

            # Fallback: some endpoints ignore stream=True and return one JSON body.
            if not full_reply and not saw_stream_data:
                try:
                    data = response.json()
                    full_reply = extract_text_from_event(data)
                    if full_reply:
                        response_placeholder.write(full_reply)
                except ValueError:
                    pass
    except requests.exceptions.Timeout:
        st.error("Request timed out. The API may be busy; please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Network error while contacting Hugging Face. Check your connection and try again.")
        return None
    except requests.exceptions.HTTPError:
        status_code = response.status_code if response is not None else "unknown"
        if status_code in (401, 403):
            st.error("Authentication failed. Check your HF_TOKEN in .streamlit/secrets.toml.")
        elif status_code == 429:
            st.error("Rate limit reached. Please wait and try again.")
        else:
            response_body = response.text[:300] if response is not None else ""
            st.error(f"API error ({status_code}): {response_body}")
        return None
    except requests.exceptions.RequestException as exc:
        st.error(f"Request failed: {exc}")
        return None

    if not full_reply:
        st.error("No response text was returned by the model.")
        return None
    return full_reply


def ensure_chats_dir():
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_memory_file():
    if not MEMORY_FILE.exists():
        with MEMORY_FILE.open("w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


def load_memory():
    ensure_memory_file()
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_memory(memory):
    ensure_memory_file()
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def merge_memory(existing, update):
    merged = dict(existing)
    for key, value in update.items():
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            seen = set()
            merged_list = []
            for item in merged[key] + value:
                marker = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
                if marker not in seen:
                    seen.add(marker)
                    merged_list.append(item)
            merged[key] = merged_list
        else:
            merged[key] = value
    return merged


def extract_json_object(text):
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced_match:
        try:
            return json.loads(fenced_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def build_memory_system_prompt(memory):
    return (
        "You are a helpful assistant. Personalize responses using this user memory when relevant: "
        f"{json.dumps(memory, ensure_ascii=True)}. "
        "If memory is empty or unrelated, respond naturally without fabricating details."
    )


def extract_memory_from_user_message(user_message, current_memory):
    extraction_messages = [
        {
            "role": "system",
            "content": (
                "Extract stable user preferences or personal traits from the user's latest message. "
                "Return only a JSON object. If nothing relevant is present, return {}."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Current memory JSON: {json.dumps(current_memory, ensure_ascii=True)}\n\n"
                f"Latest user message: {user_message}\n\n"
                "Return an updated memory patch as JSON."
            ),
        },
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": extraction_messages,
        "max_tokens": 180,
    }

    response = None
    try:
        response = requests.post(
            HF_CHAT_URL,
            headers=headers,
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = extract_json_object(content)
        return parsed if isinstance(parsed, dict) else {}
    except requests.exceptions.RequestException:
        return {}
    except (KeyError, IndexError, TypeError, ValueError):
        return {}


def chat_file_path(chat_id):
    return CHATS_DIR / f"{chat_id}.json"


def save_chat(chat):
    ensure_chats_dir()
    with chat_file_path(chat["id"]).open("w", encoding="utf-8") as f:
        json.dump(chat, f, indent=2)


def delete_chat_file(chat_id):
    path = chat_file_path(chat_id)
    if path.exists():
        path.unlink()


def load_chats_from_disk():
    ensure_chats_dir()
    loaded_chats = []
    max_counter = 0

    for path in sorted(CHATS_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as f:
                chat = json.load(f)
            if not isinstance(chat, dict):
                continue

            chat_id = chat.get("id")
            title = chat.get("title")
            created_at = chat.get("created_at")
            messages = chat.get("messages")
            if not isinstance(chat_id, str) or not isinstance(title, str):
                continue
            if not isinstance(created_at, str) or not isinstance(messages, list):
                continue

            loaded_chats.append(
                {
                    "id": chat_id,
                    "title": title,
                    "created_at": created_at,
                    "messages": messages,
                }
            )

            if chat_id.startswith("chat_"):
                try:
                    max_counter = max(max_counter, int(chat_id.split("_", 1)[1]))
                except (ValueError, IndexError):
                    pass
        except (OSError, json.JSONDecodeError):
            continue

    return loaded_chats, max_counter


def create_new_chat():
    st.session_state.chat_counter += 1
    chat_id = f"chat_{st.session_state.chat_counter}"
    created_at = datetime.now().strftime("%b %d, %I:%M %p")
    new_chat = {
        "id": chat_id,
        "title": "New Chat",
        "created_at": created_at,
        "messages": [],
    }
    st.session_state.chats.insert(0, new_chat)
    st.session_state.active_chat_id = chat_id
    save_chat(new_chat)


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
if "memory" not in st.session_state:
    st.session_state.memory = load_memory()
if "chats_initialized" not in st.session_state:
    loaded_chats, max_counter = load_chats_from_disk()
    st.session_state.chats = loaded_chats
    st.session_state.chat_counter = max_counter
    st.session_state.active_chat_id = loaded_chats[0]["id"] if loaded_chats else None
    if not st.session_state.chats:
        create_new_chat()
    st.session_state.chats_initialized = True

with st.sidebar:
    st.subheader("Chats")
    if st.button("New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    with st.expander("User Memory", expanded=True):
        st.json(st.session_state.memory)
        if st.button("Clear Memory", use_container_width=True):
            st.session_state.memory = {}
            save_memory(st.session_state.memory)
            st.rerun()

    st.divider()
    st.caption("Recent Chats")
    chat_list_container = st.container(height=240, border=False)
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
                delete_chat_file(chat["id"])

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
    save_chat(active_chat)

    model_messages = [
        {"role": "system", "content": build_memory_system_prompt(st.session_state.memory)},
        *active_chat["messages"],
    ]

    with history_container:
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            streamed_placeholder = st.empty()
            assistant_reply = stream_assistant_reply(model_messages, streamed_placeholder)
            if assistant_reply is not None:
                active_chat["messages"].append({"role": "assistant", "content": assistant_reply})
                save_chat(active_chat)

                memory_patch = extract_memory_from_user_message(prompt, st.session_state.memory)
                if memory_patch:
                    st.session_state.memory = merge_memory(st.session_state.memory, memory_patch)
                    save_memory(st.session_state.memory)
