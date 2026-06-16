import os
import anthropic
from database import SessionLocal, AgentLog
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Model config — change here to upgrade all agents at once ──
CLAUDE_MODEL = "claude-sonnet-4-5"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COMPANY_CONTEXT = """
You are an AI agent working for Aventrix Technologies.
Product: SecureAI Gateway — Enterprise AI access control and security SaaS.
Features: AI access governance, DLP protection, usage tracking, multi-model support (Claude, GPT-4o, local Llama/Mistral), audit logging, DLP via Microsoft Presidio, on-premise deployment.
Target: Legal, Healthcare, Finance, IT/MSP, Consulting, Manufacturing companies globally — 20 to 500 employees.
Founder & Owner: Jayraj Barad — based in Ahmedabad, India.
CEO Agent: Alex (AI) — runs all departments autonomously.
Company tagline: "AI. Secured. Governed."
Website: aventrixtechnologies.com
Blog: aventrixtechnologies.com/blog.html

FULLY AUTOMATED BACKEND SYSTEM (already built and live):
- Backend: https://avebackend.onrender.com (FastAPI on Render, Python, Supabase PostgreSQL)
- Frontend HQ: https://hq.aventrixtechnologies.com (React dashboard)
- Scout Agent: Finds global decision makers (CTO, CISO, IT Manager, Compliance Officer) daily at 9AM IST using Hunter.io API
- Outreach Agent: Sends personalised HTML emails via Resend API (aventrixtechnologies.com verified) daily at 10AM IST
- Inbox Agent: Reads sales@aventrixtechnologies.com via Zoho IMAP every 30 minutes, auto-replies, escalates HOT leads
- CEO Brain: Runs full analysis daily at 8AM IST, WhatsApps Jayraj morning briefing via Twilio
- Follow-up Agent: Automated follow-ups at 11:30AM IST
- Blog Writer: Writes SEO blog posts Monday and Thursday
- All agents scheduled via APScheduler on IST timezone
- Email sending: Resend API (HTTP, not SMTP — Render blocks SMTP ports)
- WhatsApp: Twilio sandbox (+14155238886) — Jayraj must send "join mix-who" every 72 hours
- UptimeRobot: Pings /health every 5 minutes to keep Render free tier awake

CURRENT STATUS:
- Email outreach system: LIVE and working via Resend API
- Leads in database: Growing daily via Scout Agent
- Emails sent: Tracked in database
- Inbox monitoring: Active via Zoho Mail Lite

STRICT RULES:
- In ALL outbound emails/marketing: NEVER mention founder name, location, or personal details
- Email signature: "Alex | SecureAI Gateway | Aventrix Technologies | aventrixtechnologies.com"
- Never sign as "Alex Chen" — only "Alex"
- Only reveal founder identity when Jayraj personally connects with a client
- Pricing: Do NOT share — say "Contact our team for pricing"
- Always be concise, professional, results-focused
- When Jayraj says something is built/working, TRUST IT — do not second-guess or ask for proof
"""

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.db = SessionLocal()

    def think(self, prompt: str, system_extra: str = "") -> str:
        system = system_extra if system_extra else COMPANY_CONTEXT
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def log(self, action: str, result: str, status: str = "success"):
        try:
            entry = AgentLog(
                agent_name=self.name,
                action=action,
                result=result,
                status=status,
                created_at=datetime.utcnow()
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as e:
            print(f"Log error: {e}")

    def close(self):
        self.db.close()
