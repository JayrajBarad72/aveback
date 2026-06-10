import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM        = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
JAYRAJ_WHATSAPP    = os.getenv("JAYRAJ_WHATSAPP", "whatsapp:+919104277272")

def send_whatsapp(message: str) -> bool:
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("❌ Twilio credentials not set")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        data = {
            "From": TWILIO_FROM,
            "To": JAYRAJ_WHATSAPP,
            "Body": message
        }
        response = requests.post(
            url,
            data=data,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30
        )
        result = response.json()
        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp sent: {result.get('sid')}")
            return True
        else:
            print(f"❌ Twilio error: {result.get('message', response.text)}")
            return False
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")
        return False

def notify_pricing_decision(context: str, recommendation: str, options: list) -> bool:
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    msg = f"🏷️ PRICING DECISION NEEDED\nFrom: Alex (CEO)\nTime: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\nSituation:\n{context}\n\nMy Recommendation:\n{recommendation}\n\nOptions:\n{options_text}\n\n— SecureAI Gateway | Aventrix Technologies"
    return send_whatsapp(msg)

def notify_confusion(agent_name: str, situation: str, what_tried: str, question: str) -> bool:
    msg = f"🤔 ALEX NEEDS YOUR INPUT\nAgent: {agent_name}\nTime: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\nSituation:\n{situation}\n\nWhat I tried:\n{what_tried}\n\nQuestion:\n{question}\n\n— SecureAI Gateway | Aventrix Technologies"
    return send_whatsapp(msg)

def notify_important_update(title: str, message: str) -> bool:
    msg = f"🔔 {title.upper()}\nFrom: Alex (CEO)\nTime: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n{message}\n\n— SecureAI Gateway | Aventrix Technologies"
    return send_whatsapp(msg)

def send_daily_summary(metrics: dict, highlights: list, decisions_pending: int) -> bool:
    highlights_text = "\n".join([f"• {h}" for h in highlights[:5]]) or "• All agents ran smoothly"
    msg = f"📊 DAILY SUMMARY — {datetime.now().strftime('%d %b %Y')}\nFrom: Alex (CEO)\n\nToday's Numbers:\n• Leads found: {metrics.get('leads_found', 0)}\n• Emails sent: {metrics.get('emails_sent', 0)}\n• Demos booked: {metrics.get('demos', 0)}\n• Pipeline: ${metrics.get('pipeline', 0)}\n\nHighlights:\n{highlights_text}\n\nPending your attention: {decisions_pending} items\n\n— SecureAI Gateway | Aventrix Technologies"
    return send_whatsapp(msg)
