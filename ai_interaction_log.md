### Task: Setup
**Prompt:** "Initialize Week 10 project structure, virtual environment, and required config/dependency files."
**AI Suggestion:** Created the required folder/file scaffold, added Streamlit config + secrets template, and prepared a minimal app.py with missing-token handling.
**My Modifications & Reflections:** Initial setup scaffold created before task implementation.

### Task: Task 1 Part A - Page Setup & API Connection
**Prompt:** "Implement Streamlit page config and a single hardcoded Hugging Face API call using HF_TOKEN from st.secrets, with graceful error handling."
**AI Suggestion:** Updated `app.py` to use `st.set_page_config(page_title="My AI Chat", layout="wide")`, read `HF_TOKEN` from `st.secrets`, send `Hello!` to the Hugging Face router endpoint with model `meta-llama/Llama-3.2-1B-Instruct`, and display clear UI errors for missing token, auth/rate-limit/network failures, and malformed responses.
**My Modifications & Reflections:** Kept the implementation focused on Part A only and added strict error messages so the app never crashes on token/API issues.
