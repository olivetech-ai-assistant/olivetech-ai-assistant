import os
import io
import requests
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="OliveTech Solutions - AI Assistant", page_icon="🤖", layout="centered")

# --- Keys from Render Environment (never hard-code) ---
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

st.title("🤖 OliveTech Solutions")
st.write("**Founder & Technical Lead: Willie Den** | Wau-Waria, Papua New Guinea")
st.write("📞 +675 7741 4389 | ✉️ olivetech.1126@gmail.com | 🌐 olivetech.com.pg")
st.write("AI Chatbots • AI Workflow Automation • AI Agents • Websites")

tab1, tab2 = st.tabs(["💬 AI Assistant", "📝 Request a Service"])

# ============ TAB 1 - AI ASSISTANT + VOICE ============
with tab1:
    st.markdown("### 💬 Ask OliveTech Assistant")
    st.write("Type or talk. Ask about AI chatbots, automation, agents, or websites for your business.")

    # ----- VOICE MODE -----
    st.markdown("### 🎤 Talk to OliveTech Assistant")
    st.write("Tap the mic, speak, and the AI will transcribe it. Then press Send.")
    audio = st.audio_input("Tap to record your voice")
    voice_text = ""
    if audio is not None and GROQ_API_KEY:
        audio_bytes = audio.read()
        files = {"file": ("voice.wav", io.BytesIO(audio_bytes), "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "en"}
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        try:
            r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=60)
            if r.status_code == 200:
                voice_text = r.json().get("text", "")
                st.success(f"You said: {voice_text}")
            else:
                st.error(f"Voice transcription failed: {r.text[:200]}")
        except Exception as e:
            st.error(f"Voice error: {e}")
    elif audio is not None and not GROQ_API_KEY:
        st.error("GROQ_API_KEY missing in Render Environment.")

    # ----- TEXT CHAT -----
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    # If voice was just transcribed, pre-fill it
    default_q = voice_text if voice_text else ""
    user_q = st.chat_input("Ask about OliveTech services...")

    # Use voice text if user recorded but didn't type
    if not user_q and voice_text:
        user_q = voice_text

    if user_q:
        st.session_state.messages.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.write(user_q)
        # Call Dify
        if not DIFY_API_KEY:
            ans = "DIFY_API_KEY missing in Render Environment."
        else:
            try:
                resp = requests.post(
                    "https://api.dify.ai/v1/chat-messages",
                    headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
                    json={"inputs": {}, "query": user_q, "response_mode": "blocking", "user": "olivetech-user", "conversation_id": ""},
                    timeout=60,
                )
                if resp.status_code == 200:
                    ans = resp.json().get("answer", "No answer from Dify.")
                else:
                    ans = f"Dify error: {resp.text[:300]}"
            except Exception as e:
                ans = f"Error calling Dify: {e}"
        st.session_state.messages.append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.write(ans)
        # Speak answer aloud in browser (TTS)
        st.markdown(f"<script>try{{var u=new SpeechSynthesisUtterance({repr(ans[:500])});u.lang='en-US';window.speechSynthesis.speak(u);}}catch(e){{}}</script>", unsafe_allow_html=True)

# ============ TAB 2 - LEAD FORM ============
with tab2:
    st.markdown("### 📝 Request a Service")
    st.write("Fill this form and Willie Den will contact you on the number you gave.")
    with st.form("lead_form"):
        name = st.text_input("Your Name")
        phone = st.text_input("Your Phone / WhatsApp Number")
        service = st.selectbox("Service Needed", ["AI Chatbot", "AI Workflow Automation", "AI Agents", "Website", "Other"])
        message = st.text_area("Message - Tell us about your business")
        submitted = st.form_submit_button("Send Request to OliveTech")

    if submitted:
        if not name or not phone:
            st.error("Please enter your Name and Phone.")
        elif not SUPABASE_URL or not SUPABASE_ANON_KEY:
            st.error("Supabase keys missing in Render Environment.")
        else:
            try:
                supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                supabase.table("leads").insert({"name": name, "phone": phone, "service": service, "message": message}).execute()
                st.success("Thank you! Your request was saved. Willie Den will contact you on the number you gave.")
                st.markdown(f"[✅ Tap here to confirm on WhatsApp](https://wa.me/67577414389?text=Hi%20OliveTech,%20I%20just%20sent%20a%20request%20on%20your%20website.%20I%20am%20{name},%20I%20need%20{service}.)")
            except Exception as e:
                st.error(f"Could not save online. Please WhatsApp Willie directly on +675 7741 4389. Error: {e}")
