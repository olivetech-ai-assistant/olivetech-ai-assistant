import os, base64, requests
import gradio as gr
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
DIFY_URL = os.environ.get("DIFY_URL", "https://api.dify.ai/v1/chat-messages")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

LOGO_B64 = ""
try:
    with open("logo.jpg", "rb") as f:
        LOGO_B64 = base64.b64encode(f.read()).decode()
except Exception:
    pass
LOGO_HTML = f'<div style="text-align:center"><img src="data:image/jpeg;base64,{LOGO_B64}" style="max-width:320px;width:90%;height:auto;background:white;padding:10px;border-radius:12px"/></div>' if LOGO_B64 else "<h1 style='text-align:center'>OliveTech Solutions</h1>"

CONTACT = """
**Willie Den — Founder & Technical Lead | OliveTech Solutions**  
📞 +675 7741 4389 | ✉️ olivetech.1126@gmail.com | 🌐 olivetech.com.pg  
📍 Wau-Waria, Papua New Guinea — serving Lae, Morobe & PNG-wide
"""

def chat(message, history):
    if not DIFY_API_KEY:
        return ("Hello! I'm the OliveTech Assistant. We help PNG small businesses with AI chatbots, "
                "workflow automation, AI agents, and websites.\n\n"
                "Tell me about your business — e.g. 'I run a shop in Lae and want customers to order on WhatsApp' — "
                "and I'll suggest a simple solution.\n\n"
                "Contact: Willie Den, +675 7741 4389, olivetech.1126@gmail.com")
    try:
        headers = {"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"}
        payload = {"inputs": {}, "query": message, "response_mode": "blocking", "conversation_id": "", "user": "olivetech-visitor"}
        r = requests.post(DIFY_URL, headers=headers, json=payload, timeout=60)
        data = r.json()
        return data.get("answer") or "Sorry, I could not answer that. Please try again or contact Willie on +675 7741 4389."
    except Exception as e:
        return f"Sorry, the AI is temporarily unavailable. Please contact Willie Den directly on +675 7741 4389 / olivetech.1126@gmail.com. ({e})"

def save_lead(name, phone, service, message):
    if not name.strip() or not phone.strip():
        return "Please enter your name and phone / WhatsApp number."
    if supabase is None:
        return "Lead form is not connected yet (Supabase keys missing). Please WhatsApp Willie directly on +675 7741 4389."
    try:
        supabase.table("leads").insert({"name": name.strip(), "phone": phone.strip(), "service": service, "message": message.strip()}).execute()
        return "Thank you! Your request was saved. Willie Den will contact you on the number you gave."
    except Exception as e:
        return f"Could not save online. Please WhatsApp Willie directly on +675 7741 4389. Error: {e}"

with gr.Blocks(title="OliveTech Solutions — Wau-Waria, PNG", theme=gr.themes.Soft(primary_hue="green")) as demo:
    gr.HTML(LOGO_HTML)
    gr.Markdown("### AI chatbots • AI automation • AI agents • Websites for PNG small businesses")
    gr.Markdown(CONTACT)
    with gr.Tab("Ask OliveTech AI"):
        gr.Markdown("Ask about services, pricing approach, or what would suit your business. Example: *“I run a trade store in Lae, how can AI help me?”*")
        gr.ChatInterface(fn=chat)
    with gr.Tab("Request a Service"):
        gr.Markdown("Fill this in and Willie will contact you. No payment is taken here.")
        name = gr.Textbox(label="Your Name *")
        phone = gr.Textbox(label="Phone / WhatsApp *", placeholder="+675 ...")
        service = gr.Dropdown(["AI Chatbot", "AI Workflow Automation", "AI Agent", "Website", "Business System", "Other"], label="Service Needed", value="AI Chatbot")
        message = gr.Textbox(label="Tell us about your business", lines=4, placeholder="e.g. I run a bakery in Wau and want customers to order easily...")
        btn = gr.Button("Send Request to OliveTech", variant="primary")
        out = gr.Textbox(label="Status")
        btn.click(save_lead, inputs=[name, phone, service, message], outputs=out)
    with gr.Tab("About"):
        gr.Markdown("""
        **OliveTech Solutions** — founded by **Willie Den, Founder & Technical Lead**.
        We build practical, affordable AI for PNG businesses: chatbots that answer customers, automation that saves time, and websites that bring in enquiries.
        **Contact:** +675 7741 4389 | olivetech.1126@gmail.com | olivetech.com.pg | Wau-Waria, Papua New Guinea
        """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
