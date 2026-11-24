import os
import requests
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from datetime import datetime

st.set_page_config(page_title="OliveTech AI Assistant", page_icon="🤖", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem !important; padding-bottom: 1rem !important; max-width: 860px; }
    /* Slim top bar like ChatGPT / Meta AI */
    .topbar { display: flex; align-items: center; gap: 10px; padding: 6px 0 12px 0; border-bottom: 1px solid #E8EDF2; margin-bottom: 14px; }
    .topbar b { font-size: 17px; color: #0F2A44; }
    .topbar span { font-size: 13px; color: #6B7A8D; }
    .hero { text-align: center; padding: 28px 12px 8px 12px; }
    .hero h1 { font-size: 2rem; color: #0F2A44; margin: 6px 0; }
    .hero p { color: #5B6B7E; font-size: 15px; }
    .pill { display: inline-block; background: #EEF3F8; color: #0F2A44; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin: 3px 4px; }
    .suggest { background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px 14px; margin: 6px 0; cursor: pointer; }
    .success-box { background: #E6F4EA; border: 1px solid #A8D5B5; color: #1A5C2E; padding: 14px 16px; border-radius: 12px; margin: 12px 0; }
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
if "pending_wa_url" not in st.session_state:
    st.session_state.pending_wa_url = None

def new_chat():
    st.session_state.chats.insert(0, {"title": "New Chat", "messages": [], "created": datetime.now().strftime("%d %b %H:%M")})
    st.session_state.active_chat = 0
    st.session_state.messages = []

def switch_chat(i):
    st.session_state.active_chat = i
    st.session_state.messages = st.session_state.chats[i]["messages"]

# ===== SIDEBAR - LEFT - ChatGPT style =====
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

# ===== TOP BAR - slim, always visible, hero is NOT sticky =====
st.markdown('<div class="topbar"><b>🤖 OliveTech Assistant</b><span>• Wau-Waria, PNG • +675 7741 4389</span></div>', unsafe_allow_html=True)

tab_chat, tab_lead = st.tabs(["💬 AI Assistant", "📝 Request a Service"])

with tab_chat:
    # HERO ONLY WHEN CHAT IS EMPTY - like ChatGPT / Meta AI / Perplexity
    # Once you send a message, hero disappears and chat gets full room
    if not st.session_state.messages:
        st.markdown("""
        <div class="hero">
            <h1>Gutpela dei! 👋</h1>
            <p>Askim long Tok Pisin o English — AI bai bekim long sem tok yu yusim.<br>Ask about AI chatbots, automation, agents, or websites for your business.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><span class="pill">AI Chatbots</span><span class="pill">Workflow Automation</span><span class="pill">AI Agents</span><span class="pill">Websites</span></div>', unsafe_allow_html=True)
        st.write("")
        st.caption("Try one:")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💬 Yu ken mekim AI chatbot bilong bisnis bilong mi?", use_container_width=True):
                st.session_state._suggest = "Yu ken mekim AI chatbot bilong bisnis bilong mi?"
        with c2:
            if st.button("📄 Can you make a quotation template for a trade store?", use_container_width=True):
                st.session_state._suggest = "Can you make a quotation template for a trade store?"
    else:
        st.caption("OliveTech Assistant — Tok Pisin / English")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Voice - compact
    with st.expander("🎙️ Talk to OliveTech Assistant — Tap to record", expanded=False):
        audio = st.audio_input("Tap to record your voice")
    transcribed = ""
    if 'audio' in locals() and audio is not None and GROQ_API_KEY:
        with st.spinner("Transcribing..."):
            try:
                files = {"file": (audio.name if hasattr(audio, "name") else "voice.wav", audio.getvalue(), "audio/wav")}
                r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, data={"model": "whisper-large-v3"}, files=files, timeout=60)
                if r.status_code == 200:
                    transcribed = r.json().get("text", "")
                    st.success(f"You said: {transcribed}")
                else:
                    st.warning("Voice failed. Please type instead.")
            except Exception as e:
                st.warning(f"Voice error: {e}")

    prompt = st.chat_input("Askim long Tok Pisin o English...")
    if getattr(st.session_state, "_suggest", None):
        prompt = st.session_state._suggest
        st.session_state._suggest = None
    if transcribed:
        prompt = transcribed

    if prompt:
        if not st.session_state.messages:
            st.session_state.chats[st.session_state.active_chat]["title"] = prompt[:40]
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages

        # Language instruction - fluent Tok Pisin
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
                "If user writes English, answer in clear English. Be helpful, short, friendly, professional. End with a helpful next step.")

        ans = None
        groq_error = ""
        # PRIMARY: Groq direct - try 3 CURRENT models (old llama-3.3-70b-versatile is retired by Groq)
        if GROQ_API_KEY:
            for model_name in ["llama-3.1-8b-instant", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]:
                try:
                    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"},
                        json={"model": model_name,
                              "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                              "temperature": 0.7, "max_tokens": 800},
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
            # Debug: show real error in an expander so we can fix it fast (remove later)
            if ans is None and groq_error:
                with st.expander("🔧 Debug - Why AI failed (tap to see)", expanded=False):
                    st.code(groq_error)
                    if "401" in groq_error or "Invalid API key" in groq_error:
                        st.warning("GROQ_API_KEY in Render is wrong or has a space. Go to Render → Environment → GROQ_API_KEY, check it starts with gsk_ and has no space, then Save.")
                    if "404" in groq_error or "model" in groq_error.lower():
                        st.warning("That Groq model is retired. This app already tries 3 models, so if all 3 say 404, Groq changed models again — tell me the error above.")
        else:
            with st.expander("🔧 Debug - Why AI failed", expanded=False):
                st.warning("GROQ_API_KEY is MISSING in Render → Environment. Add it from your Notepad and Save.")
        # FALLBACK: Dify only if Groq fails
        if ans is None and DIFY_API_KEY:
            try:
                r = requests.post("https://api.dify.ai/v1/chat-messages",
                    headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
                    json={"inputs": {}, "query": prompt, "response_mode": "blocking", "user": "olivetech-web"},
                    timeout=60)
                if r.status_code == 200:
                    ans = r.json().get("answer")
            except Exception:
                pass
        if ans is None:
            ans = "Sori, AI i no bekim nau. Traim gen liklik taim o WhatsAppim mipela long +675 7741 4389. (Groq / Dify i no bekim)"

        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.session_state.chats[st.session_state.active_chat]["messages"] = st.session_state.messages
        st.rerun()

with tab_lead:
    st.subheader("Request a Service")
    st.caption("Fillim dispela na OliveTech bai kontakim yu. WhatsApp confirmation bai op automatically.")
    name = st.text_input("Your name *", key="lead_name")
    phone = st.text_input("Phone / WhatsApp *", key="lead_phone", placeholder="e.g. 7741 4389")
    service = st.selectbox("Service needed", ["AI Chatbot", "Workflow Automation", "AI Agent", "AI Agents", "Website", "Other"], key="lead_service")
    message = st.text_area("Message - Tell us about your business", key="lead_message", placeholder="e.g. I need an AI Agent for my trade store")
    # ONE BUTTON ONLY - no extra WhatsApp button below
    if st.button("Send Request & Confirm on WhatsApp", type="primary", use_container_width=True):
        if not name or not phone:
            st.warning("Please fill in your name and phone.")
        elif supabase is None:
            st.error("Supabase is not connected. Please try WhatsApp directly.")
        else:
            try:
                supabase.table("leads").insert({"name": name, "phone": phone, "service": service, "message": message}).execute()
                st.markdown('<div class="success-box">✅ <b>Thank you! Your request was saved.</b><br>Willie Den will contact you. WhatsApp confirmation is opening...</div>', unsafe_allow_html=True)
                # AUTO-OPEN WhatsApp: customer gets confirmation, no extra button to click
                # Message goes to OliveTech, customer just taps Send in WhatsApp - this is the closest WhatsApp allows to auto-confirm
                wa_text = f"Hi OliveTech, I just sent a request on your website. I am {name} ({phone}), I need {service}. My message: {message}. Please confirm you received my request."
                wa_url = "https://wa.me/67577414389?text=" + urllib.parse.quote(wa_text)
                # Auto-open in new tab + show fallback link only if popup blocked
                components.html(f"<script>window.open({repr(wa_url)}, '_blank');</script>", height=0)
                st.caption("If WhatsApp did not open automatically, tap here:")
                st.link_button("💬 Open WhatsApp Confirmation", wa_url, use_container_width=True)
                st.caption("Note: WhatsApp does not allow a website to send a message to your phone by itself without you tapping Send in WhatsApp first — this is WhatsApp's anti-spam rule. This auto-open is the official way: you tap Send once in WhatsApp and your confirmation is sent.")
            except Exception as e:
                st.error(f"Could not save: {e}")

st.divider()
st.caption("OliveTech • olivetech.1126@gmail.com • +675 7741 4389 • olivetech.com.pg")
