"""
WhatsApp Notification System via Twilio
Alex uses this to notify Jayraj Barad for:
- Pricing decisions
- Discounts / custom deals
- Confusion / uncertainty  
- Product knowledge questions
- Important updates
- Daily summary
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC266d9bd3eb0a9d2785917b784f1feb8d")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "50313259ac0e48869aa1d07ac2ec8678")
TWILIO_FROM        = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
JAYRAJ_WHATSAPP    = os.getenv("JAYRAJ_WHATSAPP", "whatsapp:+919104277272")

def send_whatsapp(message: str) -> bool:
    """Send WhatsApp message to Jayraj via Twilio"""
    try:
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
            timeout=15
        )
        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp sent to Jayraj Barad")
            return True
        else:
            print(f"❌ WhatsApp failed: {response.status_code} — {response.text}")
            return False
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")
        return False

def notify_pricing_decision(context: str, recommendation: str, options: list) -> bool:
    """Alex asks Jayraj for pricing approval"""
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    msg = f"""🏷️ *PRICING DECISION NEEDED*
From: Alex (CEO Agent)
Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

📋 Situation:
{context}

💡 My Recommendation:
{recommendation}

🔘 Your Options:
{options_text}

Please login to HQ or reply here to decide.
— SecureAI Gateway | Aventrix Technologies"""
    return send_whatsapp(msg)

def notify_confusion(agent_name: str, situation: str, what_tried: str, question: str) -> bool:
    """Agent needs Jayraj's help"""
    msg = f"""🤔 *ALEX NEEDS YOUR INPUT*
From: Alex (CEO Agent)
Agent: {agent_name}
Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

📋 Situation:
{situation}

🔄 What I tried:
{what_tried}

❓ My Question:
{question}

Waiting for your response before proceeding.
— SecureAI Gateway | Aventrix Technologies"""
    return send_whatsapp(msg)

def notify_important_update(title: str, message: str) -> bool:
    """Send important update to Jayraj"""
    msg = f"""🔔 *{title.upper()}*
From: Alex (CEO Agent)
Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

{message}
— SecureAI Gateway | Aventrix Technologies"""
    return send_whatsapp(msg)

def send_daily_summary(metrics: dict, highlights: list, decisions_pending: int) -> bool:
    """Send daily summary to Jayraj"""
    highlights_text = "\n".join([f"• {h}" for h in highlights[:5]]) or "• All agents ran smoothly"
    msg = f"""📊 *DAILY SUMMARY — {datetime.now().strftime('%d %b %Y')}*
From: Alex (CEO Agent)

📈 Today's Numbers:
• Leads found: {metrics.get('leads_found', 0)}
• Emails sent: {metrics.get('emails_sent', 0)}
• Demos booked: {metrics.get('demos', 0)}
• Pipeline: ${metrics.get('pipeline', 0)}

⭐ Highlights:
{highlights_text}

⏳ Pending your attention: {decisions_pending} items

— SecureAI Gateway | Aventrix Technologies"""
    return send_whatsapp(msg)
