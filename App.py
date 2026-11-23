import os
import requests
import urllib.parse
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="OliveTech AI Assistant", page_icon="🤖", layout="centered")

try:
    st.image("Logo.jpg", width=160)
except Exception:
    pass

st.title("OliveTech Solutions")
st.markdown("**Founder & Technical Lead: Willie Den** | Wau-Waria, Papua New Guinea")
st.markdown("📞 +675 7741 4389 | ✉️ olivetech.1126@gmail.com | 🌐 olivetech.com.pg")
st.markdown("AI Chatbots • AI Workflow Automation • AI Agents • Websites")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

supabase = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        st.warning(f"Supabase connection issue: {e}")

tab_chat, tab_lead = st.tabs(["💬 AI Assistant", "📝 Request a Service"])

with tab_chat:
    st.subheader("💬 Ask OliveTech Assistant")
    st.caption("Type or talk. Ask about AI chatbots, automation, agents, or websites for your business.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    st.subheader("🎙️ Talk to OliveTech Assistant")
    st.caption("Tap the mic, speak, and the AI will transcribe it. Then press Send.")
    audio = st.audio_input("Tap to record your voice")

    transcribed = ""
    if audio is not None and GROQ_API_KEY:
        with st.spinner("Transcribing your voice..."):
            try:
                files = {"file": (audio.name if hasattr(audio, "name") else "voice.wav", audio.getvalue(), "audio/wav")}
                r = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    data={"model": "whisper-large-v3"},
                    files=files,
                    timeout=60,
                )
                if r.status_code == 200:
                    transcribed = r.json().get("text", "")
                    st.success(f"You said: {transcribed}")
                else:
                    st.warning("Voice transcription failed. Please type your question instead.")
            except Exception as e:
                st.warning(f"Voice error: {e}")
    elif audio is not None and not GROQ_API_KEY:
        st.warning("GROQ_API_KEY is not set in Render. Voice is off for now, please type your question.")

    prompt = st.chat_input("Ask about OliveTech services, pricing, or a project...")
    if transcribed:
        prompt = transcribed

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        ans = "Sorry, I could not get an answer. Please try again or WhatsApp us on +675 7741 4389."
        if DIFY_API_KEY:
            try:
                r = requests.post(
                    "https://api.dify.ai/v1/chat-messages",
                    headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
                    json={"inputs": {}, "query": prompt, "response_mode": "blocking", "user": "olivetech-web", "conversation_id": ""},
                    timeout=60,
                )
                if r.status_code == 200:
                    ans = r.json().get("answer", ans)
                else:
                    ans = f"Dify returned {r.status_code}. Please try again."
            except Exception as e:
                ans = f"Connection error: {e}"
        else:
            ans = "DIFY_API_KEY is not set in Render. Please contact OliveTech on WhatsApp +675 7741 4389."

        st.session_state.messages.append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)

with tab_lead:
    st.subheader("Request a Service")
    st.caption("Fill this in and OliveTech will contact you.")

    name = st.text_input("Your name *", key="lead_name")
    phone = st.text_input("Phone / WhatsApp *", key="lead_phone")
    service = st.selectbox("Service needed", ["AI Chatbot", "Workflow Automation", "AI Agent", "Website", "AI Agents", "Other"], key="lead_service")
    message = st.text_area("Message - Tell us about your business", key="lead_message")

    if st.button("Send Request to OliveTech"):
        if not name or not phone:
            st.warning("Please fill in your name and phone.")
        elif supabase is None:
            st.error("Supabase is not connected. Please try WhatsApp instead.")
        else:
            try:
                supabase.table("leads").insert({"name": name, "phone": phone, "service": service, "message": message}).execute()
                st.success("Thank you! Your request was saved. Willie Den will contact you on the number you gave.")
                # FIX: URL-encode the whole message so spaces in names like "Tom Cruise" cannot break the link
                wa_text = f"Hi OliveTech, I just sent a request on your website. I am {name}, I need {service}."
                wa_url = "https://wa.me/67577414389?text=" + urllib.parse.quote(wa_text)
                st.link_button("✅ Tap here to confirm on WhatsApp", wa_url)
            except Exception as e:
                st.error(f"Could not save: {e}")

st.divider()
st.markdown("**OliveTech** • olivetech.1126@gmail.com • +675 7741 4389 • olivetech.com.pg")
