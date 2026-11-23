import os
import requests
import urllib.parse
import streamlit as st
from supabase import create_client
from datetime import datetime

st.set_page_config(page_title="OliveTech AI Assistant", page_icon="🤖", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 920px; }
    .hero-card { background: linear-gradient(135deg, #0F2A44 0%, #1A4A73 100%); color: white; padding: 20px 22px; border-radius: 16px; margin-bottom: 14px; }
    .hero-card p { color: #D9E8F5; margin: 3px 0; }
    .pill { display: inline-block; background: #E6F0FA; color: #0F2A44; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin: 3px 4px 3px 0; }
    .success-box { background: #E6F4EA; border: 1px solid #A8D5B5; color: #1A5C2E; padding: 14px 16px; border-radius: 12px; margin: 12px 0; }
    div[data-testid="stSidebar"] { background-color: #0F2A44;  }
    div[data-testid="stSidebar"] * { color: #EAF2FA !important; }
    div[data-testid="stSidebar"] button { background: white !important; color: #0F2A44 !important; border-radius: 10px; font-weight: 700; }
    div[data-testid="stSidebar"] .stButton>button { width: 100%; text-align: left; }
    /* MOBILE FIX: phones */
    @media (max-width: 768px) {
        .block-container { padding-left: 12px !important; padding-right: 12px !important; padding-top: 0.8rem !important; }
        .hero-card { padding: 16px 14px !important; border-radius: 12px !important; }
        .hero-card h1 { font-size: 1.5rem !important; }
        .pill { font-size: 12px !important; padding: 5px 9px !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
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

def new_chat():
    st.session_state.chats.insert(0, {"title": "New Chat", "messages": [], "created": datetime.now().strftime("%d %b %H:%M")})
    st.session_state.active_chat = 0
    st.session_state.messages = []

def switch_chat(i):
    st.session_state.active_chat = i
    st.session_state.messages = st.session_state.chats[i]["messages"]

# ===== SIDEBAR - LEFT SIDE - HISTORY =====
with st.sidebar:
    try:
        st.image("Logo.jpg", width=110)
    except Exception:
        st.markdown("### 🤖 OliveTech")
    st.markdown("## OliveTech")
    st.caption("AI Solutions • Wau-Waria, PNG")
    st.divider()

    # Language selector - THIS controls Tok Pisin
    st.markdown("### 🌐 Toktok / Language")
    st.session_state.lang = st.radio(
        "Choose language:",
        ["Tok Pisin + English (Auto)", "Tok Pisin tasol", "English only"],
        index=0,
    )
    st.caption("Auto = If yu toktok Tok Pisin, AI bai bekim long Tok Pisin. If yu toktok English, AI bai bekim long English.")

    if st.button("➕  New Chat", use_container_width=True):
        new_chat()
        st.rerun()

    st.markdown("### 🕘 History — Ol Toksave Bipo")
    st.caption(f"{len(st.session_state.chats)} toktok")
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
    st.markdown("### Contact OliveTech")
    st.markdown("**Willie Den**")
    st.markdown("Founder & Technical Lead")
    st.markdown("📞 +675 7741 4389")
    st.markdown("✉️ olivetech.1126@gmail.com")
    st.markdown("🌐 olivetech.com.pg")
    st.link_button("💬 WhatsApp OliveTech", "https://wa.me/67577414389?text=" + urllib.parse.quote("Hi OliveTech, I have a question about your AI services."))

# ===== MAIN =====
st.markdown("""
<div class="hero-card">
  <h1 style="margin:0; color:white;">🤖 OliveTech Solutions</h1>
  <p><b>Founder & Technical Lead: Willie Den</b> &nbsp;|&nbsp; Wau-Waria, Papua New Guinea</p>
  <p>📞 +675 7741 4389 &nbsp;|&nbsp; ✉️ olivetech.1126@gmail.com &nbsp;|&nbsp; 🌐 olivetech.com.pg</p>
  <p>Gutpela dei! Askim long Tok Pisin o English — AI bai bekim long sem tok yu yusim.</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<span class="pill">AI Chatbots</span><span class="pill">AI Workflow Automation</span><span class="pill">AI Agents</span><span class="pill">Websites</span>', unsafe_allow_html=True)
st.write("")

tab_chat, tab_lead = st.tabs(["💬 AI Assistant", "📝 Request a Service"])

with tab_chat:
    st.subheader("💬 Ask OliveTech Assistant")
    st.caption("Toksave long Tok Pisin o English. Example: \"Yu ken mekim AI chatbot bilong bisnis bilong mi?\"")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    st.subheader("🎙️ Talk to OliveTech Assistant")
    st.caption("Tapim mic, toktok, AI bai transleit-im. Then press Send.")
    audio = st.audio_input("Tap to record your voice")

    transcribed = ""
    if audio is not None and GROQ_API_KEY:
        with st.spinner("Transcribing your voice..."):
            try:
                files = {"file": (audio.name if hasattr(audio, "name") else "voice.wav", audio.getvalue(), "audio/wav")}
                r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    data={"model": "whisper-large-v3"}, files=files, timeout=60)
                if r.status_code == 200:
                    transcribed = r.json().get("text", "")
                    st.success(f"You said: {transcribed}")
                else:
                    st.warning("Voice transcription failed. Please type your question instead.")
            except Exception as e:
                st.warning(f"Voice error: {e}")
    elif audio is not None and not GROQ_API_KEY:
        st.warning("GROQ_API_KEY is not set in Render. Voice is off for now, please type your question.")

    prompt = st.chat_input("Askim long Tok Pisin o English...")
    if transcribed:
        prompt = transcribed

    if prompt:
        if not st.session_state.messages:
            st.session_state.chats[st.session_state.active_chat]["title"] = prompt[:40]
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- TOK PISIN LANGUAGE INSTRUCTION - sent to Dify every time ---
        if st.session_state.lang == "Tok Pisin tasol":
            lang_instruction = (
                "IMPORTANT: Answer ONLY in fluent, correct Papua New Guinea Tok Pisin. "
                "Use natural Tok Pisin grammar, not broken English. Use words like: gutpela, hamamas, laik, ken, bai, tasol, olsem, long wanem, helpim, wok, bisnis, mani, taim. "
                "Example style: 'Gutpela dei! Yes, mi ken helpim yu mekim AI chatbot bilong bisnis bilong yu.' "
                "Do NOT answer in English."
            )
        elif st.session_state.lang == "English only":
            lang_instruction = "IMPORTANT: Answer ONLY in clear English."
        else:
            lang_instruction = (
                "IMPORTANT: Match the user's language exactly. "
                "If the user writes in Tok Pisin, answer in fluent, correct Papua New Guinea Tok Pisin — natural Tok Pisin, not broken English. "
                "Use: gutpela, hamamas, laik, ken, bai, tasol, olsem, helpim, wok, bisnis. "
                "Example Tok Pisin reply: 'Gutpela dei! Yes, mi ken helpim yu. Yu laik AI chatbot bilong wanem kain bisnis?' "
                "If the user writes in English, answer in clear English. "
                "If the user mixes both, answer mainly in Tok Pisin with English for technical words."
            )
        dify_query = f"{lang_instruction}\n\nUser question: {prompt}"

        ans = "Sori, mi no kisim bek. Traim gen o WhatsAppim mipela long +675 7741 4389."
        if DIFY_API_KEY:
            try:
                r = requests.post("https://api.dify.ai/v1/chat-messages",
                    headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
                    json={"inputs": {}, "query": dify_query, "response_mode": "blocking", "user": "olivetech-web", "conversation_id": ""},
                    timeout=60)
                if r.status_code == 200:
                    ans = r.json().get("answer", ans)
                else:
                    ans = f"Dify returned {r.status_code}. Please try again."
            except Exception as e:
                ans = f"Connection error: {e}"
        else:
            ans = "DIFY_API_KEY is not set in Render. Please contact OliveTech on WhatsApp +675 7741 4389."

        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages
        with st.chat_message("assistant"):
            st.markdown(ans)
        st.rerun()

with tab_lead:
    st.subheader("Request a Service")
    st.caption("Fillim dispela na OliveTech bai kontakim yu.")
    name = st.text_input("Your name *", key="lead_name")
    phone = st.text_input("Phone / WhatsApp *", key="lead_phone")
    service = st.selectbox("Service needed", ["AI Chatbot", "Workflow Automation", "AI Agent", "AI Agents", "Website", "Other"], key="lead_service")
    message = st.text_area("Message - Tell us about your business", key="lead_message", placeholder="e.g. I need an AI Agent for my small business")
    if st.button("Send Request to OliveTech", type="primary", use_container_width=True):
        if not name or not phone:
            st.warning("Please fill in your name and phone.")
        elif supabase is None:
            st.error("Supabase is not connected. Please try WhatsApp instead.")
        else:
            try:
                supabase.table("leads").insert({"name": name, "phone": phone, "service": service, "message": message}).execute()
                st.markdown('<div class="success-box">✅ <b>Thank you! Your request was saved.</b><br>Willie Den will contact you on the number you gave.</div>', unsafe_allow_html=True)
                wa_text = f"Hi OliveTech, I just sent a request on your website. I am {name}, I need {service}. My message: {message}"
                wa_url = "https://wa.me/67577414389?text=" + urllib.parse.quote(wa_text)
                st.link_button("✅ Tap here to confirm on WhatsApp", wa_url, use_container_width=True)
            except Exception as e:
                st.error(f"Could not save: {e}")

st.divider()
st.caption("OliveTech • olivetech.1126@gmail.com • +675 7741 4389 • olivetech.com.pg")
