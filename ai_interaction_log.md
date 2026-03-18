### Task: Setup
**Prompt:** "Initialize Week 10 project structure, virtual environment, and required config/dependency files."
**AI Suggestion:** Created the required folder/file scaffold, added Streamlit config + secrets template, and prepared a minimal app.py with missing-token handling.
**My Modifications & Reflections:** Initial setup scaffold created before task implementation.

### Task: Task 1 Part A - Page Setup & API Connection
**Prompt:** "Implement Streamlit page config and a single hardcoded Hugging Face API call using HF_TOKEN from st.secrets, with graceful error handling."
**AI Suggestion:** Updated `app.py` to use `st.set_page_config(page_title="My AI Chat", layout="wide")`, read `HF_TOKEN` from `st.secrets`, send `Hello!` to the Hugging Face router endpoint with model `meta-llama/Llama-3.2-1B-Instruct`, and display clear UI errors for missing token, auth/rate-limit/network failures, and malformed responses.
**My Modifications & Reflections:** Kept the implementation focused on Part A only and added strict error messages so the app never crashes on token/API issues.

### Task: Task 1 Part B - Multi-Turn Conversation UI
**Prompt:** "Replace the hardcoded message with Streamlit chat UI using st.chat_message and st.chat_input, persist conversation in st.session_state, and send full history for context on each request."
**AI Suggestion:** Refactored `app.py` to maintain `st.session_state.messages`, render chat history with native chat components, keep the input bar fixed using `st.chat_input`, submit full conversation history to Hugging Face every turn, and show non-crashing user-visible errors for API/network/token issues.
**My Modifications & Reflections:** Added a dedicated scrollable history container so messages scroll independently while the input remains visible at the bottom.

### Task: Task 1 Part C - Chat Management
**Prompt:** "Add sidebar chat management with New Chat, chat switching, active-chat highlighting, timestamps, and per-chat delete buttons."
**AI Suggestion:** Refactored session state from a single message list into a multi-chat structure (`chats`, `active_chat_id`, `chat_counter`), added a scrollable sidebar chat list with `New Chat` and `X` delete controls, highlighted the active chat using native Streamlit button styles, and routed all message rendering/API context to the selected chat only.
**My Modifications & Reflections:** Ensured deleting the active chat automatically switches to another chat when available, or falls back to a clean empty state.
