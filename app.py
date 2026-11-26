import os, io, re, json, time, uuid, base64, hashlib, datetime
from urllib.parse import quote

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(page_title="OliveTech Assistant", page_icon="🫒", layout="centered")


def env(key, default=""):
    return os.getenv(key, default).strip()


GROQ_KEY = env("GROQ_API_KEY")
CHAT_MODEL = env("GROQ_CHAT_MODEL", "openai/gpt-oss-20b")
VISION_MODEL = env("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
STT_MODEL = env("GROQ_STT_MODEL", "whisper-large-v3-turbo")
STT_LANG = env("STT_LANGUAGE", "en")
SB_URL = re.sub(r"/rest/v1/?$", "", env("SUPABASE_URL").rstrip("/"))
SB_KEY = env("SUPABASE_SERVICE_KEY")
RESEND_KEY = env("RESEND_API_KEY")
EMAIL_FROM = env("EMAIL_FROM", "OliveTech <onboarding@resend.dev>")
EMAIL_TO = env("EMAIL_TO")
WA_NUMBER = re.sub(r"\D", "", env("WHATSAPP_NUMBER"))
BIZ_NAME = env("BUSINESS_NAME", "OliveTech Solutions")
BIZ_INFO = env("BUSINESS_INFO", "OliveTech Solutions builds AI chatbots, workflow automation, AI agents and websites for small businesses in Papua New Guinea. Based in Wau, Morobe.")
OPENAI_KEY = env("OPENAI_API_KEY")
IMAGE_MODEL = env("IMAGE_MODEL", "gpt-image-1")
IMAGE_QUALITY = env("IMAGE_QUALITY", "low")
DAILY_IMG_CAP = int(env("DAILY_IMAGE_CAP", "20") or 20)
SESSION_IMG_CAP = int(env("SESSION_IMAGE_CAP", "3") or 3)
MAX_MESSAGES = 80
SERVICES = ["AI Chatbot", "Workflow Automation", "AI Agent", "Website", "Other"]
FILE_TYPES = ["jpg", "jpeg", "png", "webp", "pdf", "docx", "txt", "csv"]

S = st.session_state
S.setdefault("msgs", [])
S.setdefault("img_n", 0)
S.setdefault("last_lead", 0.0)
S.setdefault("voice_text", "")
S.setdefault("img_prompt", "")
S.setdefault("pending", "")
S.setdefault("last_img", None)
S.setdefault("chat_id", uuid.uuid4().hex[:12])
S.setdefault("hist", None)

# Anonymous device code kept in the page link (?d=...). Bookmark the page to keep history.
_d = st.query_params.get("d", "")
if not re.fullmatch(r"[a-f0-9]{16}", _d or ""):
    _d = uuid.uuid4().hex[:16]
    st.query_params["d"] = _d
S.device = _d


@st.cache_resource
def usage():
    return {"day": "", "img": 0}


def log(*a):
    print(*a, flush=True)  # goes to Render logs only, never shown to visitors


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------- Tok Pisin detection ----------
TPI_WORDS = set("""mi yu em ol mipela yupela yumi bilong blo laik ken inap olsem tru gutpela wanem wanpela
tupela tripela stoa bisnis wok tasol nau pastaim planti sampela liklik helpim askim salim toktok mekim gat ating
wantaim hamamas tenkiu tenkyu moni haus olgeta kisim lukim harim tokim painim wokim makim pikinini meri dispela
displa sapos bagarap gen moa tude tumora asde apinun moning belo wanem inap bilong ating nogat yet""".split())
TPI_WORDS.discard("yet")


def looks_tok_pisin(text):
    words = re.findall(r"[a-z']+", text.lower())
    hits = sum(1 for w in words if w in TPI_WORDS)
    return hits >= 2 or (len(words) <= 4 and hits >= 1)


# ---------- AI helpers ----------
def system_prompt(lang):
    rule = {
        "auto": "If the customer's latest message is in Tok Pisin, you MUST reply in Tok Pisin. If it is in English, reply in English. If it mixes both, reply in the main language they used.",
        "tpi": "Always reply in Tok Pisin only.",
        "en": "Always reply in English only.",
    }[lang]
    example = (
        "Example of correct Tok Pisin style:\n"
        "Customer: Mi laik wanpela AI chatbot bilong stoa bilong mi. Yu ken helpim mi?\n"
        "Assistant: Yes, mipela inap helpim yu! Mipela mekim AI chatbot husait i ken bekim askim bilong ol kastama long Tok Pisin na English. "
        "Plis go long Request a Service, putim nem na nambawan bilong yu, na mipela bai kontaktim yu."
    )
    return (
        f"You are the friendly assistant for {BIZ_NAME} in Papua New Guinea. {rule} "
        "Use short, simple sentences that are easy to read on a phone. "
        "For facts about the business (prices, hours, services, location) use ONLY the business information below. "
        "If the answer is not there, say you are not sure and suggest the Request a Service page. "
        "Never invent prices, dates or promises. Do not present legal, medical or financial advice as certain.\n\n"
        + example + "\n\nBUSINESS INFORMATION:\n" + BIZ_INFO
    )


def groq_chat(messages, model):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 1500},
        timeout=60,
    )
    if r.status_code != 200:
        log("GROQ CHAT ERROR", r.status_code, r.text[:300])
        raise RuntimeError("chat failed")
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    if not text:
        raise RuntimeError("empty reply")
    return text


def transcribe(audio_bytes):
    if len(audio_bytes) > 5 * 1024 * 1024:
        raise ValueError("audio too large")
    data = {
        "model": STT_MODEL,
        "temperature": "0",
        "response_format": "json",
        "prompt": "Tok Pisin and English: gutpela, hamamas, laik, bisnis, wok, mi, yu, stoa, moni.",
    }
    if STT_LANG:
        data["language"] = STT_LANG
    r = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        files={"file": ("audio.wav", audio_bytes, "audio/wav")},
        data=data,
        timeout=60,
    )
    if r.status_code != 200:
        log("GROQ STT ERROR", r.status_code, r.text[:300])
        raise RuntimeError("stt failed")
    return r.json().get("text", "").strip()


def read_file(f):
    name = f.name.lower()
    data = f.getvalue()
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("too big")
    if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((1280, 1280))
        q = 85
        while True:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=q)
            if buf.tell() < 900_000 or q <= 40:
                break
            q -= 15
        return "image", base64.b64encode(buf.getvalue()).decode()
    if name.endswith(".pdf"):
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        return "text", "\n".join(p.get_text() for p in doc)[:12000]
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        return "text", "\n".join(p.text for p in d.paragraphs)[:12000]
    if name.endswith((".txt", ".csv")):
        return "text", data.decode("utf-8", "ignore")[:12000]
    raise ValueError("unsupported")


def make_image(prompt):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model": IMAGE_MODEL, "prompt": prompt, "size": "1024x1024", "quality": IMAGE_QUALITY, "n": 1},
        timeout=150,
    )
    if r.status_code != 200:
        log("IMAGE ERROR", r.status_code, r.text[:300])
        raise RuntimeError("image failed")
    return base64.b64decode(r.json()["data"][0]["b64_json"])


def listen_button(text):
    safe = json.dumps(text).replace("</", "<\\/")
    components.html(
        """<button id="b" style="padding:6px 12px;border:1px solid #ccc;border-radius:8px;background:#fff;cursor:pointer;font-size:14px">🔊 Listen</button>
<script>
const t = %s;
document.getElementById('b').onclick = () => {
  if (!('speechSynthesis' in window)) { alert('Listen is not supported on this phone. Please read the text.'); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(t);
  u.lang = 'en-US'; u.rate = 0.95;
  speechSynthesis.speak(u);
};
</script>""" % safe,
        height=44,
    )


# ---------- Database helpers (Supabase) ----------
def sb_ready():
    return bool(SB_URL and SB_KEY)


def sb_headers(prefer="return=minimal"):
    h = {"apikey": SB_KEY, "Content-Type": "application/json", "Prefer": prefer}
    if SB_KEY.startswith("eyJ"):  # legacy JWT keys also need the Authorization header
        h["Authorization"] = f"Bearer {SB_KEY}"
    return h


def sb(method, table, params=None, body=None, prefer="return=minimal"):
    r = requests.request(method, f"{SB_URL}/rest/v1/{table}", headers=sb_headers(prefer),
                         params=params, json=body, timeout=20)
    if r.status_code not in (200, 201, 204):
        log("SUPABASE ERROR", method, table, r.status_code, r.text[:300])
        raise RuntimeError(f"database error {r.status_code}")
    return r.json() if r.text else None


def msg_row(role, content, chat_id, ts, kind="chat"):
    return {"device_id": S.device, "chat_id": chat_id, "role": role,
            "content": content[:7500], "kind": kind, "created_at": ts.isoformat()}


def save_history(rows):
    if not sb_ready():
        return
    try:
        sb("POST", "chat_messages", body=rows)
    except Exception as e:
        log("HISTORY SAVE FAILED", e)


def load_chat_list():
    try:
        rows = sb("GET", "chat_messages", params={
            "device_id": f"eq.{S.device}", "kind": "eq.chat", "select": "chat_id,role,content,created_at",
            "order": "created_at.desc", "limit": "400"}) or []
    except Exception:
        return None
    chats = {}
    for r in rows:  # newest first, so the last user message seen per chat is the first one asked
        c = chats.setdefault(r["chat_id"], {"id": r["chat_id"], "last": r["created_at"], "title": ""})
        if r["role"] == "user":
            c["title"] = r["content"]
    return sorted(chats.values(), key=lambda c: c["last"], reverse=True)[:15]


def new_chat():
    S.msgs = []
    S.chat_id = uuid.uuid4().hex[:12]
    S.hist = None


def open_chat(cid):
    try:
        rows = sb("GET", "chat_messages", params={
            "device_id": f"eq.{S.device}", "chat_id": f"eq.{cid}", "kind": "eq.chat",
            "select": "role,content", "order": "created_at.asc", "limit": "200"}) or []
        S.msgs = [{"role": r["role"], "content": r["content"]} for r in rows]
        S.chat_id = cid
    except Exception:
        pass


def delete_history():
    try:
        sb("DELETE", "chat_messages", params={"device_id": f"eq.{S.device}"})
        S.msgs = []
        S.chat_id = uuid.uuid4().hex[:12]
        S.hist = None
    except Exception:
        pass


def save_lead(row):
    return sb("POST", "leads", body=row, prefer="return=representation")[0]["id"]


def set_status(lead_id, status):
    try:
        sb("PATCH", "leads", params={"id": f"eq.{lead_id}"}, body={"notification_status": status})
    except Exception as e:
        log("STATUS UPDATE ERROR", e)


def send_email(row):
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_KEY}"},
        json={
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": f"New lead: {row['name']} - {row['service']}",
            "text": f"Name: {row['name']}\nPhone: {row['phone']}\nService: {row['service']}\nMessage: {row['message']}",
        },
        timeout=20,
    )
    if r.status_code not in (200, 201):
        log("RESEND ERROR", r.status_code, r.text[:300])
        raise RuntimeError("email failed")


# ---------- Sidebar ----------
if S.hist is None and sb_ready():
    _res = load_chat_list()
    S.hist = _res if _res is not None else "ERR"

with st.sidebar:
    st.title("🫒 OliveTech")
    lang = st.radio(
        "Toktok / Language",
        ["auto", "tpi", "en"],
        format_func=lambda k: {"auto": "Tok Pisin + English (auto)", "tpi": "Tok Pisin tasol", "en": "English only"}[k],
    )
    st.button("➕ New chat", on_click=new_chat)
    st.markdown("**History**")
    if not sb_ready() or S.hist == "ERR":
        st.caption("History is not available right now.")
    elif not S.hist:
        st.caption("No saved chats yet.")
    else:
        for c in S.hist:
            label = ("▶ " if c["id"] == S.chat_id else "") + ((c["title"] or "Chat")[:38])
            st.button(label, key=f"h_{c['id']}", on_click=open_chat, args=(c["id"],))
        st.button("🗑 Delete my history", on_click=delete_history)
    st.caption("Chats are saved so you can reopen them here. Bookmark this page to keep your history. "
               "Anyone with this page link can see it, so do not share the link. "
               "Pilot version: AI can make mistakes, so check prices, dates and important details. "
               "If the first load is slow, wait one minute and refresh. "
               "Please do not share passwords, bank details or other sensitive information.")

CHAT, IMG, LEAD = "💬 Chat", "🎨 Create image", "📝 Request a Service"
page = st.radio("Page", [CHAT, IMG, LEAD], horizontal=True, label_visibility="collapsed")


def queue_voice():
    S.pending = S.voice_text.strip()
    S.voice_text = ""


# ---------- Chat page ----------
if page == CHAT:
    if not S.msgs:
        st.markdown("## Gutpela dei! 👋")
        st.write("Askim mi long Tok Pisin o English. Yu ken toktok, o salim poto o fail tu.")
    for m in S.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant" and not m.get("err"):
                listen_button(m["content"])

    with st.expander("🎤 Speak instead of typing"):
        audio = st.audio_input("Record a short message (about 30 seconds)")
        if audio is not None:
            raw = audio.getvalue()
            h = hashlib.md5(raw).hexdigest()
            if S.get("audio_hash") != h:
                S.audio_hash = h
                try:
                    S.voice_text = transcribe(raw)
                except Exception:
                    st.error("Sori, mi no harim gut. Please type your message instead.")
        st.text_area("Check and fix your message, then send:", key="voice_text", max_chars=600)
        st.button("Send voice message", on_click=queue_voice)

    box = st.chat_input("Askim long Tok Pisin o English...", accept_file=True, file_type=FILE_TYPES)
    text, files = "", []
    if S.pending:
        text, S.pending = S.pending, ""
    if box:
        text = (box.text or "").strip() or text
        files = list(box.files or [])

    if text or files:
        if len(S.msgs) >= MAX_MESSAGES:
            st.warning("This chat is long. Please tap New chat to continue.")
            st.stop()
        text = text or "Explain exactly what is in this file."
        user_content, model, shown = text, CHAT_MODEL, text
        if files:
            f = files[0]
            try:
                kind, val = read_file(f)
                shown = f"{text}\n\n📎 {f.name}"
                if kind == "image":
                    model = VISION_MODEL
                    user_content = [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + val}},
                    ]
                else:
                    user_content = f"{text}\n\nFILE CONTENT:\n{val}"
            except Exception:
                st.warning("Sori, mi no inap ridim dispela fail. Try a JPG, PNG, PDF, DOCX, TXT or CSV under 8 MB.")
                st.stop()

        nudge = ""
        if lang == "tpi" or (lang == "auto" and looks_tok_pisin(text)):
            nudge = "\n\n(Reply in simple, correct Tok Pisin.)"
        elif lang == "en":
            nudge = "\n\n(Reply in English.)"
        if isinstance(user_content, list):
            user_content[0]["text"] += nudge
        else:
            user_content += nudge

        history = [{"role": m["role"], "content": m["content"]} for m in S.msgs[-12:] if not m.get("err")]
        S.msgs.append({"role": "user", "content": shown})
        messages = [{"role": "system", "content": system_prompt(lang)}] + history + [{"role": "user", "content": user_content}]
        ok = True
        with st.spinner("Wait liklik..."):
            try:
                answer = groq_chat(messages, model)
            except Exception:
                ok = False
                answer = "Sori, AI i no bekim nau. Traim gen long sampela minit. (Sorry, the assistant is not available right now. Please try again shortly.)"
        S.msgs.append({"role": "assistant", "content": answer, "err": not ok})
        if ok:
            t = now_utc()
            save_history([
                msg_row("user", shown, S.chat_id, t),
                msg_row("assistant", answer, S.chat_id, t + datetime.timedelta(milliseconds=5)),
            ])
            S.hist = None
        st.rerun()

# ---------- Image page ----------
elif page == IMG:
    st.subheader("🎨 Create image by voice or text")
    if not OPENAI_KEY:
        st.info("Create image is coming soon.")
    else:
        st.caption("Image creation uses paid credits and is limited per visit and per day.")
        a = st.audio_input("Speak your image idea (optional)", key="img_audio")
        if a is not None:
            raw = a.getvalue()
            h = hashlib.md5(raw).hexdigest()
            if S.get("img_audio_hash") != h:
                S.img_audio_hash = h
                try:
                    S.img_prompt = transcribe(raw)
                except Exception:
                    st.error("Sori, mi no harim gut. Please type your idea instead.")
        st.text_area("Image idea (check and edit before creating):", key="img_prompt", max_chars=400,
                     placeholder="Example: a colourful poster for a coffee shop in Wau")
        if st.button("Create image"):
            u = usage()
            today = str(datetime.date.today())
            if u["day"] != today:
                u["day"], u["img"] = today, 0
            prompt = S.img_prompt.strip()
            if not prompt:
                st.warning("Please say or type your image idea first.")
            elif S.img_n >= SESSION_IMG_CAP or u["img"] >= DAILY_IMG_CAP:
                st.warning("Image limit reached for now. Please try again tomorrow.")
            else:
                with st.spinner("Creating your image..."):
                    try:
                        S.last_img = make_image(prompt)
                        S.img_n += 1
                        u["img"] += 1
                        save_history([msg_row("user", prompt, "images", now_utc(), "image")])
                    except Exception:
                        st.error("Sori, image creation is not available now. Your idea is saved above, try again soon.")
        if S.last_img:
            st.image(S.last_img)
            st.download_button("Download image", S.last_img, file_name="olivetech-image.png", mime="image/png")
        if sb_ready():
            try:
                recent = sb("GET", "chat_messages", params={
                    "device_id": f"eq.{S.device}", "kind": "eq.image", "select": "content,created_at",
                    "order": "created_at.desc", "limit": "5"}) or []
            except Exception:
                recent = []
            if recent:
                with st.expander("Your recent image ideas"):
                    for r in recent:
                        st.write(f"• {r['created_at'][:10]} · {r['content'][:80]}")

# ---------- Request a Service page ----------
else:
    st.subheader("📝 Request a Service")
    with st.form("lead", clear_on_submit=True):
        name = st.text_input("Name", max_chars=80)
        phone = st.text_input("Phone (WhatsApp if possible)", max_chars=20)
        service = st.selectbox("Service", SERVICES)
        message = st.text_area("Tell us what you need", max_chars=1000)
        go = st.form_submit_button("Send request")
    if go:
        name, phone, message = name.strip(), phone.strip(), message.strip()
        if len(name) < 2 or not re.fullmatch(r"\+?[0-9 ]{7,15}", phone):
            st.error("Please enter your name and a valid phone number.")
        elif time.time() - S.last_lead < 60:
            st.warning("Please wait a minute before sending another request.")
        else:
            row = {"name": name, "phone": phone, "service": service, "message": message, "device_id": S.device}
            try:
                lead_id = save_lead(row)
                S.last_lead = time.time()
                try:
                    send_email(row)
                    set_status(lead_id, "email_sent")
                except Exception:
                    set_status(lead_id, "email_failed")
                st.success("Tenkiu! We got your request and will contact you soon.")
                if WA_NUMBER:
                    wa = f"Hello {BIZ_NAME}, my name is {name}. Phone: {phone}. Service: {service}. {message}"
                    st.link_button("💬 Confirm on WhatsApp (tap Send there)", f"https://wa.me/{WA_NUMBER}?text={quote(wa)}")
            except Exception as e:
                st.error(f"Sori, we could not save your request. Please try again or contact us on WhatsApp. ({e})")
    if sb_ready():
        try:
            mine = sb("GET", "leads", params={
                "device_id": f"eq.{S.device}", "select": "created_at,service,message",
                "order": "created_at.desc", "limit": "5"}) or []
        except Exception:
            mine = []
        if mine:
            with st.expander("Your recent requests"):
                for r in mine:
                    st.write(f"• {r['created_at'][:10]} · {r['service']} · {(r.get('message') or '')[:60]}")

# ---------- Diagnostics: add ?debug=1 to the page link ----------
if st.query_params.get("debug") == "1":
    with st.sidebar:
        st.markdown("**Diagnostics**")
        try:
            for nm, val in [("GROQ_API_KEY", GROQ_KEY), ("SUPABASE_URL", SB_URL), ("SUPABASE_SERVICE_KEY", SB_KEY),
                            ("RESEND_API_KEY", RESEND_KEY), ("EMAIL_TO", EMAIL_TO)]:
                st.write(f"{nm}: {'set' if val else 'MISSING'}")
            if GROQ_KEY:
                r = requests.get("https://api.groq.com/openai/v1/models",
                                 headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=20)
                st.write("Groq key test:", r.status_code)
                if r.status_code == 200:
                    ids = [m["id"] for m in r.json().get("data", [])]
                    st.write("Chat model found:", CHAT_MODEL in ids)
                    st.write("Vision model found:", VISION_MODEL in ids)
                    st.write("Voice model found:", STT_MODEL in ids)
            if sb_ready():
                for tbl in ("leads", "chat_messages"):
                    r = requests.get(f"{SB_URL}/rest/v1/{tbl}?select=id&limit=1", headers=sb_headers(), timeout=20)
                    st.write(f"Supabase {tbl}:", r.status_code)
                    if r.status_code != 200:
                        st.write(r.text[:200])
        except Exception as e:
            st.write("Diagnostic error:", str(e)[:200])
