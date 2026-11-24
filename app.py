import os
import requests
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
import base64
import io
from datetime import datetime

st.set_page_config(page_title="OliveTech AI Assistant", page_icon="🤖", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 0.6rem !important; padding-bottom: 1rem !important; max-width: 880px; }
    .topbar { display: flex; align-items: center; gap: 10px; padding: 4px 0 10px 0; border-bottom: 1px solid #E8EDF2; margin-bottom: 12px; }
    .topbar b { font-size: 17px; color: #0F2A44; }
    .topbar span { font-size: 13px; color: #6B7A8D; }
    .hero { text-align: center; padding: 26px 12px 4px 12px; }
    .hero h1 { font-size: 2rem; color: #0F2A44; margin: 6px 0; }
    .hero p { color: #5B6B7E; font-size: 15px; }
    .pill { display: inline-block; background: #EEF3F8; color: #0F2A44; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin: 3px 4px; }
    .success-box { background: #E6F4EA; border: 1px solid #A8D5B5; color: #1A5C2E; padding: 14px 16px; border-radius: 12px; margin: 12px 0; }
    /* Composer bar - like the reference: rounded, soft shadow */
    div[data-testid="stHorizontalBlock"] { align-items: center; }
    /* Clean composer buttons - make + / mic / send same height */
    div[data-testid="column"] button { height: 44px !important; }
    /* Hide Streamlit file_uploader drag-drop chrome when it is shown below bar */
    div[data-testid="stFileUploader"] section { padding: 8px 12px !important; min-height: 0 !important; }
    div[data-testid="stFileUploader"] section > div { display: none !important; }
    div[data-testid="stFileUploader"] small { display: none !important; }
    div[data-testid="stSidebar"] { background-color: #F7F8FA; }
    div[data-testid="stSidebar"] button { border-radius: 10px; font-weight: 600; }
    @media (max-width: 768px) {
        .block-container { padding-left: 12px !important; padding-right: 12px !important; }
        .hero h1 { font-size: 1.5rem !important; }
    }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

supabase = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception:
        pass

if "chats" not in st.session_state:
    st.session_state.chats = [{"title": "New Chat", "messages": [], "created": datetime.now().strftime("%d %b %H:%M")}]
if "active_chat" not in st.session_state:
    st.session_state.active_chat = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "lang" not in st.session_state:
    st.session_state.lang = "Tok Pisin + English (Auto)"
if "mode" not in st.session_state:
    st.session_state.mode = "chat"  # chat or lead
if "show_mic" not in st.session_state:
    st.session_state.show_mic = False
if "show_upload" not in st.session_state:
    st.session_state.show_upload = False
if "uploaded_image_b64" not in st.session_state:
    st.session_state.uploaded_image_b64 = None
if "uploaded_context" not in st.session_state:
    st.session_state.uploaded_context = ""
    # keep image b64 until vision call above runs - it is cleared there if used

def new_chat():
    st.session_state.chats.insert(0, {"title": "New Chat", "messages": [], "created": datetime.now().strftime("%d %b %H:%M")})
    st.session_state.active_chat = 0
    st.session_state.messages = []
    st.session_state.mode = "chat"

def switch_chat(i):
    st.session_state.active_chat = i
    st.session_state.messages = st.session_state.chats[i]["messages"]
    st.session_state.mode = "chat"


def extract_file_content(uploaded):
    """Return (text_context, image_base64_or_None) for real file understanding."""
    try:
        name = uploaded.name.lower()
        data = uploaded.getvalue()
        if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            b64 = base64.b64encode(data).decode("utf-8")
            return ("[User attached an IMAGE - it will be sent to the vision model for real analysis.]", b64)
        if name.endswith(".txt") or name.endswith(".csv"):
            return ("File content:\n" + data.decode("utf-8", errors="ignore")[:8000], None)
        if name.endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=data, filetype="pdf")
                txt = ""
                for page in doc:
                    txt += page.get_text() + "\n"
                if not txt.strip():
                    return ("[PDF attached but no readable text found - it may be scanned images.]", None)
                return ("PDF content:\n" + txt[:8000], None)
            except Exception as e:
                return (f"[PDF attached but could not read: {e}]", None)
        if name.endswith(".docx"):
            try:
                from docx import Document
                doc = Document(io.BytesIO(data))
                txt = "\n".join([para.text for para in doc.paragraphs])
                return ("DOCX content:\n" + txt[:8000], None)
            except Exception as e:
                return (f"[DOCX attached but could not read: {e}]", None)
        if name.endswith(".xlsx"):
            try:
                import pandas as pd
                df = pd.read_excel(io.BytesIO(data))
                return ("XLSX content (first rows):\n" + df.head(30).to_string()[:8000], None)
            except Exception as e:
                return (f"[XLSX attached but could not read: {e}]", None)
        return (f"File {uploaded.name} attached.", None)
    except Exception as e:
        return (f"[Could not read file: {e}]", None)

def ask_groq_vision(prompt, sys_prompt, image_b64, api_key):
    """Call Groq vision with real image. Returns (answer_or_None, error_string)."""
    import requests as _r
    errors = []
    for model_name in ["meta-llama/llama-4-maverick-17b-128e-instruct", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.2-90b-vision-preview", "llama-3.2-11b-vision-preview"]:
        try:
            payload = {"model": model_name,
                "messages": [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": [
                                 {"type": "text", "text": prompt + "\n\nPlease look at the attached image carefully and describe / analyze / summarize what you actually see in it. Do NOT say you cannot view images."},
                                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}],
                "temperature": 0.5, "max_tokens": 1200}
            r = _r.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"},
                json=payload, timeout=90)
            if r.status_code == 200:
                return (r.json()["choices"][0]["message"]["content"], "")
            else:
                try:
                    errors.append(f"{model_name} -> {r.status_code}: {r.json().get('error', {}).get('message', r.text[:250])}")
                except Exception:
                    errors.append(f"{model_name} -> {r.status_code}: {r.text[:250]}")
        except Exception as e:
            errors.append(f"{model_name} exception: {e}")
    return (None, " | ".join(errors))

# ===== SIDEBAR - LEFT =====
with st.sidebar:
    try:
        st.image("Logo.jpg", width=100)
    except Exception:
        st.markdown("### 🤖 OliveTech")
    st.markdown("**OliveTech**")
    st.caption("AI Solutions • Wau-Waria, PNG")
    if st.button("➕  New Chat", use_container_width=True):
        new_chat()
        st.rerun()
    st.markdown("### 🕘 History")
    for idx, c in enumerate(st.session_state.chats):
        label = c["title"] if c["title"] != "New Chat" else f"New Chat • {c['created']}"
        if c["messages"]:
            first = next((m["content"] for m in c["messages"] if m["role"] == "user"), "")
            if first:
                label = (first[:34] + "…") if len(first) > 34 else first
        is_active = "✅ " if idx == st.session_state.active_chat else ""
        if st.button(f"{is_active}{label}", key=f"hist_{idx}", use_container_width=True):
            switch_chat(idx)
            st.rerun()
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.chats = [{"title": "New Chat", "messages": [], "created": datetime.now().strftime("%d %b %H:%M")}]
        st.session_state.active_chat = 0
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.markdown("### 🌐 Toktok / Language")
    st.session_state.lang = st.radio("Choose language:", ["Tok Pisin + English (Auto)", "Tok Pisin tasol", "English only"], index=0)
    st.caption("Auto = Yu toktok Tok Pisin, AI bai bekim Tok Pisin.")
    st.divider()
    st.markdown("**Willie Den** — Founder")
    st.caption("📞 +675 7741 4389\n✉️ olivetech.1126@gmail.com\n🌐 olivetech.com.pg")

# ===== TOP BAR =====
st.markdown('<div class="topbar"><b>🤖 OliveTech Assistant</b><span>• Wau-Waria, PNG • +675 7741 4389</span></div>', unsafe_allow_html=True)

# ===== HERO - only when chat empty =====
if not st.session_state.messages and st.session_state.mode == "chat":
    st.markdown("""
    <div class="hero">
        <h1>Gutpela dei! 👋</h1>
        <p>Askim long Tok Pisin o English — AI bai bekim long sem tok yu yusim.<br>Ask, create, or build anything for your business.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;"><span class="pill">AI Chatbots</span><span class="pill">Workflow Automation</span><span class="pill">AI Agents</span><span class="pill">Websites</span></div>', unsafe_allow_html=True)
    st.write("")

# ===== CHAT HISTORY =====
if st.session_state.mode == "chat":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            # show uploaded file preview if attached to that message
            if m.get("file_name"):
                st.caption(f"📎 {m['file_name']}")

# ===== LEAD FORM (when mode == lead) =====
if st.session_state.mode == "lead":
    st.subheader("📝 Request a Service")
    st.caption("Fillim dispela na OliveTech bai kontakim yu. WhatsApp confirmation bai op automatically.")
    name = st.text_input("Your name *", key="lead_name")
    phone = st.text_input("Phone / WhatsApp *", key="lead_phone", placeholder="e.g. 7741 4389")
    service = st.selectbox("Service needed", ["AI Chatbot", "Workflow Automation", "AI Agent", "AI Agents", "Website", "Other"], key="lead_service")
    message = st.text_area("Message - Tell us about your business", key="lead_message", placeholder="e.g. I need an AI Agent for my trade store")
    if st.button("Send Request & Confirm on WhatsApp", type="primary", use_container_width=True):
        if not name or not phone:
            st.warning("Please fill in your name and phone.")
        elif supabase is None:
            st.error("Supabase is not connected. Please try WhatsApp directly.")
        else:
            try:
                supabase.table("leads").insert({"name": name, "phone": phone, "service": service, "message": message}).execute()
                st.markdown('<div class="success-box">✅ <b>Thank you! Your request was saved.</b><br>Willie Den will contact you. WhatsApp confirmation is opening...</div>', unsafe_allow_html=True)
                wa_text = f"Hi OliveTech, I just sent a request on your website. I am {name} ({phone}), I need {service}. My message: {message}. Please confirm you received my request."
                wa_url = "https://wa.me/67577414389?text=" + urllib.parse.quote(wa_text)
                components.html(f"<script>window.open({repr(wa_url)}, '_blank');</script>", height=0)
                st.caption("If WhatsApp did not open automatically, tap here:")
                st.link_button("💬 Open WhatsApp Confirmation", wa_url, use_container_width=True)
                st.caption("Note: WhatsApp does not allow a website to send a message to your phone by itself without you tapping Send in WhatsApp first — this is WhatsApp's anti-spam rule. This auto-open is the official way.")
            except Exception as e:
                st.error(f"Could not save: {e}")

# ===== SMART COMPOSER BAR - Streamlit-correct version =====
# WHY: A Form with 3 submit buttons breaks Enter (Enter triggers FIRST button = +).
# FIX: Toolbar row ( + | Fast | Mic ) + st.chat_input below it.
# st.chat_input is the ONLY Streamlit input where Enter is guaranteed to send.
# CSS makes them look like one bar.
st.markdown('<div style="border:1px solid #E2E8F0; border-radius:16px; padding:8px 8px 2px 8px; background:#FFFFFF; box-shadow:0 1px 6px rgba(0,0,0,0.06);">', unsafe_allow_html=True)
tb_plus, tb_fast, tb_mic, tb_help = st.columns([0.8, 1.6, 0.8, 4.5], gap="small")
with tb_plus:
    if st.button("+  Attach", key="plus_btn2", use_container_width=True):
        st.session_state.show_upload = not st.session_state.show_upload
        st.session_state.show_mic = False
        st.rerun()
with tb_fast:
    speed = st.selectbox("speed", ["Fast", "Smart", "Balanced"], label_visibility="collapsed", key="composer_speed")
with tb_mic:
    if st.button("🎤  Speak", key="mic_btn2", use_container_width=True):
        st.session_state.show_mic = not st.session_state.show_mic
        if st.session_state.show_mic:
            st.session_state.show_upload = False
        st.rerun()
with tb_help:
    st.caption("➕ Attach = file &nbsp;•&nbsp; 🎤 = voice &nbsp;•&nbsp; Press **Enter** to send")
# THE input - chat_input guarantees Enter works on phone + desktop
composer_text = st.chat_input("Ask, create images, or build anything...  (Press Enter to send)", key="composer_chat_input")
send_clicked = composer_text is not None and composer_text.strip() != ""
# chat_input returns the text when Enter / Send is pressed, so send_clicked = True then
st.markdown('</div>', unsafe_allow_html=True)
uploaded = None

# Clean upload panel - appears BELOW bar when + tapped (fixes clutter)
if st.session_state.show_upload:
    st.caption("📎 Attach a file — image, PDF, TXT, DOCX, CSV, XLSX")
    uploaded = st.file_uploader("Attach a file", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "csv", "xlsx"], label_visibility="collapsed", key="composer_upload")
    if uploaded is not None:
        txt_ctx, img_b64 = extract_file_content(uploaded)
        st.session_state.uploaded_context = txt_ctx
        st.session_state.uploaded_image_b64 = img_b64
        st.session_state["last_vision_error"] = ""
        if img_b64:
            st.image(uploaded, width=200)
            st.caption(f"📎 Attached: {uploaded.name} ✅ — AI will REALLY look at this image. Now type your question and press Enter or tap ➤")
        else:
            st.caption(f"📎 Attached: {uploaded.name} ✅ — AI will read this file. Now type your question and press Enter or tap ➤")

# Mic recorder - appears below bar when 🎤 tapped (like reference voice button)
transcribed = ""
if st.session_state.show_mic:
    st.caption("🎤 Tap to record — toktok na AI bai transleit-im.")
    audio = st.audio_input("Tap to record your voice", label_visibility="collapsed", key="mic_audio")
    if audio is not None and GROQ_API_KEY:
        with st.spinner("Transcribing..."):
            try:
                files = {"file": (audio.name if hasattr(audio, "name") else "voice.wav", audio.getvalue(), "audio/wav")}
                r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, data={"model": "whisper-large-v3"}, files=files, timeout=60)
                if r.status_code == 200:
                    transcribed = r.json().get("text", "")
                    st.success(f"You said: {transcribed}")
                    st.session_state.show_mic = False
                else:
                    st.warning("Voice failed. Please type instead.")
            except Exception as e:
                st.warning(f"Voice error: {e}")

# ===== BELOW THE BAR: AI Assistant & Request a Service - like you asked =====
b_chat, b_lead = st.columns(2, gap="small")
with b_chat:
    if st.button("💬  AI Assistant", use_container_width=True, type="primary" if st.session_state.mode == "chat" else "secondary"):
        st.session_state.mode = "chat"
        st.rerun()
with b_lead:
    if st.button("📝  Request a Service", use_container_width=True, type="primary" if st.session_state.mode == "lead" else "secondary"):
        st.session_state.mode = "lead"
        st.rerun()
st.caption("➕ = Attach a file &nbsp;•&nbsp; 🎤 = Speak &nbsp;•&nbsp; Fast = Quick answer, Smart = Deeper answer")

# ===== SEND LOGIC =====
prompt = transcribed if transcribed else (composer_text.strip() if send_clicked else None)
# Also handle Enter in text input: Streamlit text_input doesn't submit on Enter alone, so Send button is the submit.
# If user typed and pressed Send, use it.
if prompt and st.session_state.mode == "chat":
    if not st.session_state.messages:
        st.session_state.chats[st.session_state.active_chat]["title"] = prompt[:40]
    file_ctx = st.session_state.uploaded_context
    msg = {"role": "user", "content": prompt}
    if st.session_state.uploaded_context:
        # Show file name from context if present
        import re as _re
        _m = _re.search(r"User attached file: ([^ ]+)", st.session_state.uploaded_context)
        msg["file_name"] = _m.group(1) if _m else "Attached file"
    st.session_state.messages.append(msg)
    st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages
    # Clear composer for next question
    st.session_state.uploaded_context = ""
    # keep image b64 until vision call above runs - it is cleared there if used

    if st.session_state.lang == "Tok Pisin tasol":
        sys_prompt = ("You are OliveTech Assistant, Wau-Waria PNG. Answer ONLY in fluent, correct Papua New Guinea Tok Pisin. "
            "Use natural Tok Pisin: gutpela, hamamas, laik, ken, bai, tasol, olsem, helpim, wok, bisnis. "
            "Example: 'Gutpela dei! Yes, mi ken helpim yu mekim AI chatbot bilong bisnis bilong yu.' Never answer in English.")
    elif st.session_state.lang == "English only":
        sys_prompt = "You are OliveTech Assistant, Wau-Waria PNG. Answer ONLY in clear English."
    else:
        sys_prompt = ("You are OliveTech Assistant, Wau-Waria PNG. Match the user's language exactly. "
            "If user writes Tok Pisin, answer in fluent, correct PNG Tok Pisin, not broken English. Use gutpela, hamamas, laik, ken, bai, tasol, olsem, helpim, wok, bisnis. "
            "Example: 'Gutpela dei! Yes, mi ken helpim yu. Yu laik AI chatbot bilong wanem kain bisnis?' "
            "If user writes English, answer in clear English. Be helpful, short, friendly, professional. If user attached a file, help with that file first.")

    full_prompt = prompt + (f"\n\n[Attached file context: {file_ctx}]" if file_ctx else "")

    # Model by speed: Fast = quick, Smart = deeper
    if speed == "Smart":
        models = ["openai/gpt-oss-120b", "llama-3.1-8b-instant"]
    elif speed == "Balanced":
        models = ["llama-3.1-8b-instant", "openai/gpt-oss-120b"]
    else:
        models = ["llama-3.1-8b-instant", "openai/gpt-oss-120b"]

    ans = None
    groq_error = ""
    # If image attached, use VISION model with real image bytes (fixes "can't view image")
    vision_err = ""
    if st.session_state.get("uploaded_image_b64") and GROQ_API_KEY:
        ans, vision_err = ask_groq_vision(full_prompt, sys_prompt, st.session_state.uploaded_image_b64, GROQ_API_KEY)
        if ans:
            st.session_state.uploaded_image_b64 = None
        else:
            # Save error so user can SEE why vision failed instead of silent fallback
            st.session_state["last_vision_error"] = vision_err
    if GROQ_API_KEY:
        for model_name in models:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": full_prompt}], "temperature": 0.7, "max_tokens": 900},
                    timeout=60)
                if r.status_code == 200:
                    ans = r.json()["choices"][0]["message"]["content"]
                    break
                else:
                    try:
                        groq_error = f"Groq {model_name} -> {r.status_code}: {r.json().get('error', {}).get('message', r.text[:200])}"
                    except Exception:
                        groq_error = f"Groq {model_name} -> {r.status_code}: {r.text[:200]}"
            except Exception as e:
                groq_error = f"Groq {model_name} exception: {e}"
    if ans is None and DIFY_API_KEY:
        try:
            r = requests.post("https://api.dify.ai/v1/chat-messages",
                headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
                json={"inputs": {}, "query": full_prompt, "response_mode": "blocking", "user": "olivetech-web"}, timeout=60)
            if r.status_code == 200:
                ans = r.json().get("answer")
        except Exception:
            pass
    if ans is None:
        ans = "Sori, AI i no bekim nau. Traim gen liklik taim o WhatsAppim mipela long +675 7741 4389."
        if groq_error or st.session_state.get("last_vision_error"):
            with st.expander("🔧 Debug - Why AI failed (tap to see)", expanded=True):
                if groq_error:
                    st.code("TEXT MODEL: " + groq_error)
                if st.session_state.get("last_vision_error"):
                    st.code("VISION MODEL: " + str(st.session_state.get("last_vision_error"))[:2000])
                st.caption(f"Image attached? {'YES - ' + str(len(str(st.session_state.get('uploaded_image_b64') or ''))) + ' chars' if st.session_state.get('uploaded_image_b64') else 'NO - no image bytes stored'}")
                st.caption(f"File context: {(st.session_state.get('uploaded_context') or '')[:300]}")

    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages
    st.rerun()

st.divider()
st.caption("OliveTech • olivetech.1126@gmail.com • +675 7741 4389 • olivetech.com.pg")
